const API_BASE = 'http://127.0.0.1:5000/api';

let currentStream = null;
let processingInterval = null;
let pollInterval = null;
let isAdminLoggedIn = false;
let loggedInRole = '';
let allAttendanceData = [];
let currentDashboardTab = 'present';
let dashboardStudents = [];
let dashboardPresentMap = new Map();
let chartInstances = {}; // to keep track of chart instances and destroy them on reload

function switchDashboardTab(tab) {
    currentDashboardTab = tab;
    
    const btnPresent = document.getElementById('tab-present');
    const btnAbsent = document.getElementById('tab-absent');
    
    if (tab === 'present') {
        btnPresent.className = "px-4 py-2 bg-emerald-50 text-emerald-600 font-bold rounded-lg text-sm border border-emerald-100 transition-colors";
        btnAbsent.className = "px-4 py-2 bg-white text-gray-500 font-bold rounded-lg text-sm border border-gray-100 hover:bg-gray-50 transition-colors";
    } else {
        btnAbsent.className = "px-4 py-2 bg-rose-50 text-rose-600 font-bold rounded-lg text-sm border border-rose-100 transition-colors";
        btnPresent.className = "px-4 py-2 bg-white text-gray-500 font-bold rounded-lg text-sm border border-gray-100 hover:bg-gray-50 transition-colors";
    }
    
    renderDashboardTable();
}

function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
}

async function navigate(viewId) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    
    // Stop camera if navigating away
    stopCamera();
    document.getElementById('video-stream').classList.add('hidden');
    document.getElementById('overlay-canvas').classList.add('hidden');
    document.getElementById('video-placeholder').classList.remove('hidden');
    document.getElementById('reg-video-stream').classList.add('hidden');
    document.getElementById('reg-video-placeholder').classList.remove('hidden');
    
    if (viewId === 'landing' || viewId === 'login') {
        document.getElementById('app-container').classList.add('hidden');
        document.getElementById(`view-${viewId}`).classList.remove('hidden');
        return;
    }

    // Inside app
    document.getElementById('app-container').classList.remove('hidden');
    document.getElementById(`view-${viewId}`).classList.remove('hidden');
    
    // Sidebar visibility
    if (isAdminLoggedIn) {
        document.getElementById('sidebar').classList.remove('hidden');
        document.getElementById('btn-exit-scanner').classList.add('hidden'); // admin uses sidebar
        document.getElementById('btn-manage-candidates').classList.remove('hidden');
    } else {
        document.getElementById('sidebar').classList.add('hidden');
    }

    // Reset active button state
    ['dashboard', 'manage-attendance', 'scanner', 'register', 'manage-candidates', 'calendar'].forEach(id => {
        const btn = document.getElementById(`btn-${id}`);
        if(btn) btn.className = 'w-full flex items-center px-4 py-3 text-sm font-bold rounded-xl text-gray-700 hover:bg-gray-50 transition-colors';
    });
    
    // Set active button state
    const activeBtn = document.getElementById(`btn-${viewId}`);
    if(activeBtn) activeBtn.className = 'w-full flex items-center px-4 py-3 text-sm font-bold rounded-xl transition-colors bg-emerald-50 text-emerald-600';
    
    if (viewId === 'dashboard') {
        loadDashboard();
    } else if (viewId === 'manage-attendance') {
        loadManageAttendance();
    } else if (viewId === 'manage-candidates') {
        loadManageCandidates();
    } else if (viewId === 'calendar') {
        loadCalendar();
    }
}

async function doLogin() {
    const user = document.getElementById('login-user').value;
    const pass = document.getElementById('login-pass').value;
    const errorMsg = document.getElementById('login-error');
    const spinner = document.getElementById('login-spinner');
    const btnText = document.getElementById('login-text');
    const btn = document.getElementById('btn-login');
    
    spinner.classList.remove('hidden');
    btnText.innerText = 'Authenticating...';
    btn.disabled = true;
    errorMsg.classList.add('hidden');
    
    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            isAdminLoggedIn = true;
            loggedInRole = data.data && data.data.role ? data.data.role : 'admin';
            errorMsg.classList.add('hidden');
            navigate('dashboard');
        } else {
            errorMsg.classList.remove('hidden');
            errorMsg.innerText = data.message || "Invalid credentials";
        }
    } catch(e) {
        errorMsg.classList.remove('hidden');
        errorMsg.innerText = "Cannot connect to server.";
    } finally {
        spinner.classList.add('hidden');
        btnText.innerText = 'Login';
        btn.disabled = false;
    }
}

function logout() {
    isAdminLoggedIn = false;
    loggedInRole = '';
    document.getElementById('login-user').value = '';
    document.getElementById('login-pass').value = '';
    navigate('landing');
}

function startPublicScanner() {
    isAdminLoggedIn = false;
    navigate('scanner');
    document.getElementById('btn-exit-scanner').classList.remove('hidden');
    startScanner();
}

async function loadDashboard() {
    try {
        const studentsRes = await fetch(`${API_BASE}/students`);
        dashboardStudents = await studentsRes.json();
        
        const attendanceRes = await fetch(`${API_BASE}/attendance`);
        const attendance = await attendanceRes.json();
        
        // Filter for today
        const todayStr = new Date().toISOString().split('T')[0];
        const todayAttendance = attendance.filter(a => a.date === todayStr);
        
        const uniquePresentToday = new Set(todayAttendance.map(a => a.student_id)).size;
        
        document.getElementById('stat-total').innerText = dashboardStudents.length;
        document.getElementById('stat-present').innerText = uniquePresentToday;
        
        dashboardPresentMap = new Map();
        todayAttendance.forEach(a => dashboardPresentMap.set(a.student_id, a.time));
        
        renderDashboardTable();
        renderDashboardCharts(attendance, todayAttendance, dashboardStudents);
        
        renderDashboardTable();
        renderDashboardCharts(attendance, todayAttendance, dashboardStudents);
        
    } catch (e) {
        console.error("Dashboard load failed", e);
    }
}

async function loadManageCandidates() {
    try {
        const studentsRes = await fetch(`${API_BASE}/students`);
        const students = await studentsRes.json();
        dashboardStudents = students; // keep in sync
        
        const manageBody = document.getElementById('manage-candidates-body');
        manageBody.innerHTML = '';
        students.forEach(s => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-50 hover:bg-gray-50 transition-colors';
            tr.innerHTML = `
                <td class="py-4 px-8 font-bold text-gray-800">${s.name}</td>
                <td class="py-4 px-8 text-gray-600">${s.class_name || 'N/A'}</td>
                <td class="py-4 px-8 text-right flex gap-2 justify-end">
                    <button onclick="generateStudentPDF('${s.id}')" class="px-3 py-1 bg-indigo-50 text-indigo-600 font-bold rounded-lg text-xs border border-indigo-100 hover:bg-indigo-100 transition-colors shadow-sm transform hover:-translate-y-0.5">PDF Report</button>
                    <button onclick="deleteStudent('${s.id}')" class="px-3 py-1 bg-rose-50 text-rose-500 font-bold rounded-lg text-xs border border-rose-100 hover:bg-rose-100 transition-colors shadow-sm transform hover:-translate-y-0.5">Delete</button>
                </td>
            `;
            manageBody.appendChild(tr);
        });
    } catch (e) {
        console.error("Manage candidates load failed", e);
    }
}

let calendarData = {
    attendance: [],
    students: []
};

async function loadCalendar() {
    try {
        const d = new Date();
        const monthInput = document.getElementById('calendar-month');
        monthInput.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        
        const studentsRes = await fetch(`${API_BASE}/students`);
        calendarData.students = await studentsRes.json();
        
        const classFilter = document.getElementById('calendar-class-filter');
        const uniqueClasses = new Set();
        calendarData.students.forEach(s => { if(s.class_name) uniqueClasses.add(s.class_name); });
        
        classFilter.innerHTML = '<option value="all">All Classes</option>';
        Array.from(uniqueClasses).sort().forEach(className => {
            const opt = document.createElement('option');
            opt.value = className;
            opt.innerText = className;
            classFilter.appendChild(opt);
        });
        
        const attendanceRes = await fetch(`${API_BASE}/attendance`);
        calendarData.attendance = await attendanceRes.json();
        
        renderCalendar();
    } catch(e) {
        console.error("Calendar load failed", e);
    }
}

function renderCalendar() {
    const monthInput = document.getElementById('calendar-month').value;
    if (!monthInput) return;
    const [year, month] = monthInput.split('-');
    
    const selectedClass = document.getElementById('calendar-class-filter').value;
    
    const grid = document.getElementById('calendar-grid');
    grid.innerHTML = '';
    
    const firstDay = new Date(year, month - 1, 1).getDay();
    const daysInMonth = new Date(year, month, 0).getDate();
    
    // Empty slots for start of month
    for (let i = 0; i < firstDay; i++) {
        const div = document.createElement('div');
        div.className = 'p-4 rounded-2xl bg-transparent';
        grid.appendChild(div);
    }
    
    // Filter students by class
    const relevantStudents = selectedClass === 'all' ? calendarData.students : calendarData.students.filter(s => s.class_name === selectedClass);
    const relevantStudentIds = new Set(relevantStudents.map(s => s.id));
    
    // Filter attendance for the month
    const monthPrefix = `${year}-${month}`;
    const monthlyAttendance = calendarData.attendance.filter(a => a.date.startsWith(monthPrefix) && relevantStudentIds.has(a.student_id));
    
    const attendanceMap = new Map(); // date -> count
    monthlyAttendance.forEach(a => {
        if(!attendanceMap.has(a.date)) attendanceMap.set(a.date, new Set());
        attendanceMap.get(a.date).add(a.student_id);
    });
    
    const todayDate = new Date();
    todayDate.setHours(0,0,0,0);

    for (let i = 1; i <= daysInMonth; i++) {
        const div = document.createElement('div');
        const dateStr = `${year}-${month}-${String(i).padStart(2, '0')}`;
        const presentCount = attendanceMap.has(dateStr) ? attendanceMap.get(dateStr).size : 0;
        const totalCount = relevantStudents.length;
        
        const iterDate = new Date(year, parseInt(month) - 1, i);
        const isFuture = iterDate > todayDate;
        
        let bgColor = 'bg-white';
        let textColor = 'text-gray-800';
        let cursorClass = 'cursor-pointer hover:shadow-md hover:border-emerald-200';
        let subtitle = `${presentCount}/${totalCount} Pres.`;
        
        if (isFuture) {
            bgColor = 'bg-gray-50/50 opacity-60';
            textColor = 'text-gray-400';
            cursorClass = 'cursor-not-allowed';
            subtitle = '—';
        } else if (totalCount > 0) {
            if (presentCount === totalCount) { bgColor = 'bg-emerald-100'; textColor = 'text-emerald-700'; }
            else if (presentCount > 0) { bgColor = 'bg-indigo-50'; textColor = 'text-indigo-600'; }
            else { bgColor = 'bg-gray-50'; }
        }
        
        div.className = `p-3 rounded-2xl border border-gray-100 shadow-sm transition-all flex flex-col items-center justify-center min-h-[80px] ${bgColor} ${cursorClass}`;
        
        if (!isFuture) {
            div.onclick = () => showCalendarDayDetails(dateStr, relevantStudents, monthlyAttendance);
        }
        
        div.innerHTML = `
            <span class="text-xl font-bold ${textColor}">${i}</span>
            <span class="text-xs font-medium mt-1 text-gray-500">${subtitle}</span>
        `;
        grid.appendChild(div);
    }
}

function showCalendarDayDetails(dateStr, relevantStudents, monthlyAttendance) {
    document.getElementById('calendar-details').classList.remove('hidden');
    document.getElementById('calendar-selected-date').innerText = new Date(dateStr).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    
    const presentList = document.getElementById('calendar-present-list');
    const absentList = document.getElementById('calendar-absent-list');
    presentList.innerHTML = '';
    absentList.innerHTML = '';
    
    const dayAttendance = monthlyAttendance.filter(a => a.date === dateStr);
    const presentMap = new Map();
    dayAttendance.forEach(a => presentMap.set(a.student_id, a.time));
    
    relevantStudents.forEach(s => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-gray-50 transition-colors";
        if (presentMap.has(s.id)) {
            tr.innerHTML = `<td class="py-3 px-6 font-medium text-gray-800">${s.name}</td><td class="py-3 px-6 text-right text-gray-500 font-medium">${presentMap.get(s.id)}</td>`;
            presentList.appendChild(tr);
        } else {
            tr.innerHTML = `<td class="py-3 px-6 font-medium text-gray-800">${s.name}</td><td class="py-3 px-6 text-right text-rose-500 font-bold">Absent</td>`;
            absentList.appendChild(tr);
        }
    });
}

async function deleteStudent(id) {
    if (!confirm("Are you sure you want to delete this student and all their attendance records?")) return;
    try {
        const res = await fetch(`${API_BASE}/students/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            if (!document.getElementById('view-manage-candidates').classList.contains('hidden')) {
                loadManageCandidates();
            } else {
                loadDashboard();
            }
        } else {
            alert("Failed to delete student: " + data.message);
        }
    } catch (e) {
        alert("Error deleting student.");
    }
}

function renderDashboardTable() {
    const tbody = document.getElementById('student-table-body');
    tbody.innerHTML = '';
    
    dashboardStudents.forEach(s => {
        const time = dashboardPresentMap.get(s.id);
        const isPresent = !!time;
        
        if (currentDashboardTab === 'present' && !isPresent) return;
        if (currentDashboardTab === 'absent' && isPresent) return;

        const statusColor = isPresent ? 'text-emerald-600 bg-emerald-100' : 'text-rose-500 bg-rose-100';
        const statusText = isPresent ? 'Present' : 'Absent';
        const displayTime = isPresent ? time : '--:--:--';
        
        const tr = document.createElement('tr');
        tr.className = 'border-b border-gray-50 hover:bg-gray-50 transition-colors';
        tr.innerHTML = `
            <td class="py-4 px-8 font-bold text-gray-800">${s.name}</td>
            <td class="py-4 px-8 text-gray-600">${s.class_name || 'N/A'}</td>
            <td class="py-4 px-8 font-medium text-gray-500">${displayTime}</td>
            <td class="py-4 px-8">
                <span class="px-3 py-1 rounded-full text-xs font-bold ${statusColor}">${statusText}</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderDashboardCharts(allAttendance, todayAttendance, allStudents) {
    if (typeof Chart === 'undefined') return;

    // Destroy old charts
    if (chartInstances.pie) chartInstances.pie.destroy();
    if (chartInstances.bar) chartInstances.bar.destroy();
    if (chartInstances.wave) chartInstances.wave.destroy();

    // 1. Pie Chart
    const totalStudents = allStudents.length;
    const presentToday = new Set(todayAttendance.map(a => a.student_id)).size;
    const absentToday = Math.max(0, totalStudents - presentToday);

    const ctxPie = document.getElementById('dash-pie-chart').getContext('2d');
    chartInstances.pie = new Chart(ctxPie, {
        type: 'pie',
        data: {
            labels: ['Present', 'Absent'],
            datasets: [{
                data: [presentToday, absentToday],
                backgroundColor: ['#10b981', '#f43f5e'],
                borderWidth: 0
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
    });

    // 2. Bar Chart (By Class Today)
    const classCounts = {};
    allStudents.forEach(s => {
        if (!classCounts[s.class_name]) classCounts[s.class_name] = { total: 0, present: 0 };
        classCounts[s.class_name].total++;
        if (dashboardPresentMap.has(s.id)) classCounts[s.class_name].present++;
    });

    const classes = Object.keys(classCounts);
    const presentByClass = classes.map(c => classCounts[c].present);

    const ctxBar = document.getElementById('dash-bar-chart').getContext('2d');
    chartInstances.bar = new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: classes,
            datasets: [{
                label: 'Present Students',
                data: presentByClass,
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
    });

    // 3. Wave Chart (Last 7 Days)
    const dateCounts = {};
    allAttendance.forEach(a => {
        if (!dateCounts[a.date]) dateCounts[a.date] = new Set();
        dateCounts[a.date].add(a.student_id);
    });

    // Get last 7 days sorted
    const sortedDates = Object.keys(dateCounts).sort().slice(-7);
    const trendData = sortedDates.map(d => dateCounts[d].size);

    const ctxWave = document.getElementById('dash-wave-chart').getContext('2d');
    chartInstances.wave = new Chart(ctxWave, {
        type: 'line',
        data: {
            labels: sortedDates,
            datasets: [{
                label: 'Total Present',
                data: trendData,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.2)',
                fill: true,
                tension: 0.4 // Makes it wavy
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
    });
}

async function generateStudentPDF(studentId) {
    if (typeof html2pdf === 'undefined') {
        alert("PDF generator library not loaded.");
        return;
    }
    
    const student = dashboardStudents.find(s => s.id === studentId || s.id == studentId);
    if (!student) return;
    
    // Fetch all attendance
    const attendanceRes = await fetch(`${API_BASE}/attendance`);
    const allAttendance = await attendanceRes.json();
    
    // Filter student attendance
    const studentAttendance = allAttendance.filter(a => a.student_id === studentId || a.student_id == studentId).sort((a,b) => new Date(b.date) - new Date(a.date));
    
    // Get total unique days from all attendance to represent "Total School Days"
    const allUniqueDays = new Set(allAttendance.map(a => a.date)).size;
    const studentPresentDays = new Set(studentAttendance.map(a => a.date)).size;
    const studentAbsentDays = Math.max(0, allUniqueDays - studentPresentDays);
    const percentage = allUniqueDays > 0 ? Math.round((studentPresentDays / allUniqueDays) * 100) : 100;
    
    // Populate template
    document.getElementById('pdf-date').innerText = "Generated: " + new Date().toLocaleDateString();
    document.getElementById('pdf-student-name').innerText = student.name;
    document.getElementById('pdf-student-class').innerText = student.class_name || 'N/A';
    document.getElementById('pdf-total-days').innerText = allUniqueDays;
    document.getElementById('pdf-present-days').innerText = studentPresentDays;
    document.getElementById('pdf-absent-days').innerText = studentAbsentDays;
    document.getElementById('pdf-percentage').innerText = percentage + "%";
    
    // Populate logs
    const tbody = document.getElementById('pdf-log-body');
    tbody.innerHTML = '';
    studentAttendance.forEach(a => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td class="py-2 px-4 border text-gray-700">${a.date}</td><td class="py-2 px-4 border text-gray-700">${a.time}</td>`;
        tbody.appendChild(tr);
    });
    
    // Make container visible temporarily to draw the chart and capture
    const container = document.getElementById('pdf-template-container');
    container.style.display = 'block';
    
    // Draw Pie Chart
    const ctx = document.getElementById('pdf-pie-chart').getContext('2d');
    if (chartInstances.pdfPie) chartInstances.pdfPie.destroy();
    chartInstances.pdfPie = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Present', 'Absent'],
            datasets: [{
                data: [studentPresentDays, studentAbsentDays],
                backgroundColor: ['#10b981', '#f43f5e'],
                borderWidth: 0
            }]
        },
        options: { responsive: false, animation: false } // no animation so it captures immediately
    });
    
    // Wait for chart render
    setTimeout(() => {
        const element = document.getElementById('student-pdf-report');
        const opt = {
            margin:       0.5,
            filename:     `Attendance_Report_${student.name.replace(/\s+/g, '_')}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2 },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };
        
        html2pdf().set(opt).from(element).save().then(() => {
            container.style.display = 'none'; // hide it back
        });
    }, 500);
}

let currentAttendanceView = [];

async function loadManageAttendance() {
    try {
        const attendanceRes = await fetch(`${API_BASE}/attendance`);
        allAttendanceData = await attendanceRes.json();
        
        const studentsRes = await fetch(`${API_BASE}/students`);
        const students = await studentsRes.json();
        
        // Populate class dropdown
        const classFilter = document.getElementById('class-filter');
        const uniqueClasses = new Set();
        students.forEach(s => { if(s.class_name) uniqueClasses.add(s.class_name); });
        
        // Keep "All Classes" option but clear the rest
        classFilter.innerHTML = '<option value="all">All Classes</option>';
        Array.from(uniqueClasses).sort().forEach(className => {
            const opt = document.createElement('option');
            opt.value = className;
            opt.innerText = className;
            classFilter.appendChild(opt);
        });
        
        const uniqueAttendance = new Set(allAttendanceData.map(a => a.student_id + '_' + a.date)).size;
        
        document.getElementById('manage-stat-total').innerText = students.length;
        document.getElementById('manage-stat-present').innerText = uniqueAttendance;
        
        const uniqueDays = new Set(allAttendanceData.map(a => a.date)).size;
        let percentage = 0;
        if (students.length > 0 && uniqueDays > 0) {
            percentage = Math.round((uniqueAttendance / (students.length * uniqueDays)) * 100);
        } else if (uniqueDays > 0) {
            percentage = 100;
        }
        document.getElementById('manage-stat-percent').innerText = `${percentage}%`;
        
        allAttendanceData.sort((a, b) => {
            const dateA = new Date(a.date + 'T' + a.time);
            const dateB = new Date(b.date + 'T' + b.time);
            return dateB - dateA;
        });
        
        currentAttendanceView = allAttendanceData;
        renderAttendanceTable(currentAttendanceView);
        
    } catch(e) {
        console.error("Manage attendance load failed", e);
    }
}

function filterAttendanceData() {
    const selectedClass = document.getElementById('class-filter').value;
    const selectedDate = document.getElementById('date-filter').value;
    
    currentAttendanceView = allAttendanceData;
    
    if (selectedClass !== 'all') {
        currentAttendanceView = currentAttendanceView.filter(a => a.students && a.students.class_name === selectedClass);
    }
    
    if (selectedDate) {
        currentAttendanceView = currentAttendanceView.filter(a => a.date === selectedDate);
    }
    
    renderAttendanceTable(currentAttendanceView);
}

function renderAttendanceTable(data) {
    const tbody = document.getElementById('all-attendance-body');
    tbody.innerHTML = '';
    
    data.forEach(a => {
        const studentName = a.students ? a.students.name : 'Unknown';
        const studentClass = a.students ? a.students.class_name : 'N/A';
        const tr = document.createElement('tr');
        tr.className = 'border-b border-gray-50 hover:bg-gray-50 transition-colors';
        tr.innerHTML = `
            <td class="py-4 px-8 font-medium text-gray-700">${a.date}</td>
            <td class="py-4 px-8 text-gray-500">${a.time}</td>
            <td class="py-4 px-8 font-bold text-gray-800">${studentName}</td>
            <td class="py-4 px-8 text-gray-600">${studentClass}</td>
        `;
        tbody.appendChild(tr);
    });
}

function downloadAttendanceCSV() {
    if (currentAttendanceView.length === 0) return;
    
    let csvContent = "Date,Time,Student Name,Class\n";
    currentAttendanceView.forEach(a => {
        const studentName = a.students ? a.students.name : 'Unknown';
        const studentClass = a.students ? a.students.class_name : 'N/A';
        csvContent += `${a.date},${a.time},${studentName},${studentClass}\n`;
    });
    
    const selectedClass = document.getElementById('class-filter').value;
    const filenameClass = selectedClass === 'all' ? 'All' : selectedClass;
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `attendance_export_${filenameClass}_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

async function startScanner() {
    document.getElementById('video-placeholder').classList.add('hidden');
    const video = document.getElementById('video-stream');
    const overlay = document.getElementById('overlay-canvas');
    video.classList.remove('hidden');
    overlay.classList.remove('hidden');
    
    document.getElementById('live-logs').innerHTML = '<p class="text-gray-400 text-sm italic mt-4">Waiting for faces...</p>';
    lastLogCount = 0;
    
    try {
        currentStream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
        video.srcObject = currentStream;
        
        video.onloadedmetadata = () => {
            overlay.width = video.videoWidth;
            overlay.height = video.videoHeight;
        };
        
        await fetch(`${API_BASE}/start_scanner`, { method: 'POST' });
        
        if(pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(updateLiveLogs, 3000);
        
        if(processingInterval) clearInterval(processingInterval);
        processingInterval = setInterval(processScannerFrame, 400); // 2.5 FPS
    } catch(e) {
        alert("Failed to start camera or connect to backend: " + e);
    }
}

async function processScannerFrame() {
    const video = document.getElementById('video-stream');
    const overlay = document.getElementById('overlay-canvas');
    if (video.paused || video.ended || !currentStream) return;
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const base64Image = canvas.toDataURL('image/jpeg', 0.7);
    
    try {
        const res = await fetch(`${API_BASE}/process_frame`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: base64Image })
        });
        const data = await res.json();
        
        const overlayCtx = overlay.getContext('2d');
        overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
        
        if (data.status === 'success' && data.results) {
            let spoofDetected = false;

            data.results.forEach(student => {
                const [top, right, bottom, left] = student.box;
                let color = 'red';
                let displayName = student.name;
                
                if (student.status === 'spoof') {
                    color = '#ef4444'; // red
                    displayName = "FAKE (Screen Detected)";
                    spoofDetected = true;
                } else if (student.status === 'already_marked' || (student.id && typeof todayPresentSet !== 'undefined' && todayPresentSet.has(student.id))) {
                    color = '#3b82f6'; // blue
                    displayName += " (Already Marked Today)";
                } else if (student.status === 'recorded' || (student.status === 'cooldown' && student.time_since_last < 5.0)) {
                    color = '#10b981'; // green
                    if (student.time_since_last < 5.0) displayName += " (Marked)";
                } else if (student.status === 'cooldown') {
                    color = '#eab308'; // yellow
                }
                
                overlayCtx.strokeStyle = color;
                overlayCtx.lineWidth = 4;
                overlayCtx.strokeRect(left, top, right - left, bottom - top);
                
                overlayCtx.fillStyle = color;
                overlayCtx.fillRect(left, bottom, right - left, 40);
                
                overlayCtx.fillStyle = 'white';
                overlayCtx.font = '24px Inter, sans-serif';
                overlayCtx.fillText(displayName, left + 8, bottom + 28);
            });

            // Toggle massive Illegal Activity overlay
            const spoofOverlay = document.getElementById('spoof-warning-overlay');
            if (spoofOverlay) {
                if (spoofDetected) {
                    spoofOverlay.classList.remove('hidden');
                } else {
                    spoofOverlay.classList.add('hidden');
                }
            }
        }
    } catch (e) {
        console.error("Frame processing error:", e);
    }
}

async function startRegScanner() {
    document.getElementById('reg-video-placeholder').classList.add('hidden');
    const video = document.getElementById('reg-video-stream');
    video.classList.remove('hidden');
    
    try {
        currentStream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } });
        video.srcObject = currentStream;
    } catch(e) {
        alert("Failed to start camera.");
    }
}

let todayPresentSet = new Set();
let lastLogCount = 0;
async function updateLiveLogs() {
    if (document.getElementById('view-scanner').classList.contains('hidden')) return;
    
    try {
        const attendanceRes = await fetch(`${API_BASE}/attendance`);
        const attendance = await attendanceRes.json();
        
        const todayStr = new Date().toISOString().split('T')[0];
        const todayAttendance = attendance.filter(a => a.date === todayStr);
        
        // Update global set for scanner text
        todayPresentSet.clear();
        todayAttendance.forEach(a => todayPresentSet.add(a.student_id));
        
        if (todayAttendance.length > lastLogCount) {
            const logsDiv = document.getElementById('live-logs');
            if (lastLogCount === 0) logsDiv.innerHTML = ''; 
            
            for (let i = lastLogCount; i < todayAttendance.length; i++) {
                const a = todayAttendance[i];
                const div = document.createElement('div');
                div.className = 'p-4 bg-emerald-50 border border-emerald-100 rounded-2xl mb-3 shadow-sm';
                div.innerHTML = `<p class="text-sm font-bold text-emerald-700">✅ ${a.students ? a.students.name : 'Unknown'}</p><p class="text-xs text-emerald-500 font-medium mt-1">${a.time || new Date().toLocaleTimeString()}</p>`;
                logsDiv.prepend(div);
            }
            lastLogCount = todayAttendance.length;
        }
    } catch(e) {}
}

async function captureRegistration() {
    const name = document.getElementById('reg-name').value;
    const id = document.getElementById('reg-class').value;
    const status = document.getElementById('reg-status');
    const video = document.getElementById('reg-video-stream');
    
    if (!name || !id) {
        status.innerText = "Please fill all fields";
        status.className = "text-sm text-center mt-4 text-rose-500 font-bold";
        return;
    }
    
    if (video.classList.contains('hidden') || !currentStream) {
        status.innerText = "Please start the camera feed first.";
        status.className = "text-sm text-center mt-4 text-rose-500 font-bold";
        return;
    }
    
    status.innerText = "Analyzing Face via Deep ML... Please hold still.";
    status.className = "text-sm text-center mt-4 text-blue-500 font-bold animate-pulse";
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const base64Image = canvas.toDataURL('image/jpeg', 0.8);
    
    try {
        const res = await fetch(`${API_BASE}/capture_registration`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name: name, 
                class_name: id, 
                image: base64Image,
                mobile: '', email: '', parent_number: '', department_email: '', dob: '' 
            })
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            status.innerText = "✅ Successfully Scanned & Registered!";
            status.className = "text-sm text-center mt-4 text-emerald-500 font-bold";
            document.getElementById('reg-name').value = '';
            document.getElementById('reg-class').value = '';
        } else {
            status.innerText = `❌ Failed: ${data.message}`;
            status.className = "text-sm text-center mt-4 text-rose-500 font-bold";
        }
    } catch (e) {
        status.innerText = "Server Error. Ensure Python API is running.";
        status.className = "text-sm text-center mt-4 text-rose-500 font-bold";
    }
}

// Init - PUBG-style Splash Screen Sequence
window.onload = () => {
    const splash = document.getElementById('splash-screen');
    const splash1 = document.getElementById('splash-1');
    const splash2 = document.getElementById('splash-2');

    if (!splash || !splash1 || !splash2) {
        navigate('landing');
        return;
    }

    // Step 1: Fade in Splash 1 (DevSoft logo + "proxy.ai" text)
    setTimeout(() => {
        splash1.style.opacity = '1';
    }, 300);

    // Step 2: Fade out Splash 1
    setTimeout(() => {
        splash1.style.opacity = '0';
    }, 2500);

    // Step 3: Fade in Splash 2 (Main Proxy logo)
    setTimeout(() => {
        splash2.style.opacity = '1';
    }, 3200);

    // Step 4: Fade out Splash 2
    setTimeout(() => {
        splash2.style.opacity = '0';
    }, 5700);

    // Step 5: Fade out entire splash screen and show landing
    setTimeout(() => {
        splash.style.opacity = '0';
        setTimeout(() => {
            splash.style.display = 'none';
            navigate('landing');
        }, 800);
    }, 6400);
};
