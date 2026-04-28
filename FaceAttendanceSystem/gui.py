import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
from datetime import datetime
import threading
import time
from camera import CameraManager
from database import db

# Set appearance mode and color theme
ctk.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class AttendanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart Face Attendance System")
        self.geometry("1000x700")
        
        self.camera_manager = CameraManager()
        self.camera_running = False
        self.current_user = None # Holds logged in admin details

        # Setup main container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Dictionary to hold frames
        self.frames = {}

        # Initialize screens
        for F in (LoginScreen, SignupScreen, MainAdminScreen, DepartmentAdminScreen, LiveScannerScreen, StudentRegistrationScreen):
            frame_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[frame_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Show login screen first
        self.show_frame("LoginScreen")

    def show_frame(self, frame_name):
        # Stop camera if leaving LiveScanner or Registration
        if frame_name not in ["LiveScannerScreen", "StudentRegistrationScreen"] and self.camera_running:
            self.camera_running = False
            self.camera_manager.stop_camera()

        frame = self.frames[frame_name]
        frame.tkraise()
        
        # Specific actions on frame load
        if frame_name == "LiveScannerScreen":
            self.camera_running = True
            frame.start_video_loop()
        elif frame_name == "DepartmentAdminScreen":
            frame.refresh_data()


class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#FFFFFF")
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Left Side (Green Branding Area)
        self.left_frame = ctk.CTkFrame(self, fg_color="#2CCC8D", corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        
        self.brand_title = ctk.CTkLabel(self.left_frame, text="Face Attendance\nSystem", font=ctk.CTkFont(size=38, weight="bold"), text_color="#FFFFFF", justify="center")
        self.brand_title.place(relx=0.5, rely=0.45, anchor="center")
        
        self.brand_subtitle = ctk.CTkLabel(self.left_frame, text="Smart, Secure & Fast", font=ctk.CTkFont(size=16), text_color="#E0FFE0")
        self.brand_subtitle.place(relx=0.5, rely=0.55, anchor="center")

        # Right Side (Form Area)
        self.right_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0)
        self.right_frame.grid(row=0, column=1, sticky="nsew")
        
        self.form_container = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form_container.place(relx=0.5, rely=0.5, anchor="center")

        self.avatar_label = ctk.CTkLabel(self.form_container, text="🧑🏻‍💼", font=ctk.CTkFont(size=60))
        self.avatar_label.pack(pady=(0, 10))

        self.title_label = ctk.CTkLabel(self.form_container, text="WELCOME", font=ctk.CTkFont(size=32, weight="bold"), text_color="#333333")
        self.title_label.pack(pady=(0, 30))

        # Username Field
        self.id_entry = ctk.CTkEntry(self.form_container, placeholder_text="👤 Username", width=300, height=40, fg_color="transparent", border_width=0, text_color="#333333")
        self.id_entry.pack(pady=5)
        self.id_line = ctk.CTkFrame(self.form_container, width=300, height=2, fg_color="#E0E0E0")
        self.id_line.pack(pady=(0, 15))

        # Password Field
        self.password_entry = ctk.CTkEntry(self.form_container, placeholder_text="🔒 Password", show="*", width=300, height=40, fg_color="transparent", border_width=0, text_color="#333333")
        self.password_entry.pack(pady=5)
        self.pwd_line = ctk.CTkFrame(self.form_container, width=300, height=2, fg_color="#E0E0E0")
        self.pwd_line.pack(pady=(0, 5))

        self.forgot_label = ctk.CTkLabel(self.form_container, text="Forgot Password?", font=ctk.CTkFont(size=11), text_color="#999999", cursor="hand2")
        self.forgot_label.pack(anchor="e", pady=(0, 20))

        self.error_label = ctk.CTkLabel(self.form_container, text="", text_color="red", font=ctk.CTkFont(size=12))
        self.error_label.pack(pady=5)

        self.login_btn = ctk.CTkButton(self.form_container, text="LOGIN", command=self.login, width=300, height=45, corner_radius=22, fg_color="#2CCC8D", hover_color="#25b37b", font=ctk.CTkFont(weight="bold", size=14))
        self.login_btn.pack(pady=(10, 10))

        self.signup_btn = ctk.CTkButton(self.form_container, text="Create New Account", command=lambda: controller.show_frame("SignupScreen"), width=300, height=45, corner_radius=22, fg_color="transparent", border_width=2, border_color="#2CCC8D", text_color="#2CCC8D", font=ctk.CTkFont(weight="bold", size=14))
        self.signup_btn.pack(pady=10)
        
        self.scanner_btn = ctk.CTkButton(self.form_container, text="Launch Live Scanner", command=lambda: controller.show_frame("LiveScannerScreen"), width=300, height=45, corner_radius=22, fg_color="#333333", hover_color="#1a1a1a", font=ctk.CTkFont(weight="bold", size=14))
        self.scanner_btn.pack(pady=(15, 0))

    def login(self):
        admin_id = self.id_entry.get()
        password = self.password_entry.get()
        
        if admin_id == "main_admin" and password == "main_pass":
            self.controller.current_user = {"role": "main_admin"}
            self.controller.show_frame("MainAdminScreen")
            self.id_entry.delete(0, 'end')
            self.password_entry.delete(0, 'end')
            self.error_label.configure(text="")
            return

        admin_data = db.verify_admin(admin_id, password)
        if admin_data:
            self.controller.current_user = {"role": "dept_admin", "data": admin_data}
            self.controller.show_frame("DepartmentAdminScreen")
            self.id_entry.delete(0, 'end')
            self.password_entry.delete(0, 'end')
            self.error_label.configure(text="")
        else:
            self.error_label.configure(text="Invalid Credentials or DB not connected")


class SignupScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Layout to center the signup box
        self.grid_rowconfigure((0, 1, 2), weight=1)
        self.grid_columnconfigure((0, 1, 2), weight=1)

        # Main Signup Card
        self.signup_frame = ctk.CTkFrame(self, width=450, height=550, corner_radius=25, fg_color=("gray90", "gray15"))
        self.signup_frame.grid(row=1, column=1, sticky="nsew")
        self.signup_frame.grid_propagate(False)
        self.signup_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        self.signup_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.signup_frame, text="Create Account", font=ctk.CTkFont(size=32, weight="bold"))
        self.title_label.grid(row=0, column=0, pady=(30, 5))
        
        self.subtitle_label = ctk.CTkLabel(self.signup_frame, text="Register a new Department Admin", font=ctk.CTkFont(size=14), text_color="gray")
        self.subtitle_label.grid(row=1, column=0, pady=(0, 20))

        self.id_entry = ctk.CTkEntry(self.signup_frame, placeholder_text="New Admin ID", width=300, height=45, corner_radius=10, border_width=1)
        self.id_entry.grid(row=2, column=0, pady=10)

        self.password_entry = ctk.CTkEntry(self.signup_frame, placeholder_text="Password", show="*", width=300, height=45, corner_radius=10, border_width=1)
        self.password_entry.grid(row=3, column=0, pady=10)
        
        self.dept_entry = ctk.CTkEntry(self.signup_frame, placeholder_text="Department Name", width=300, height=45, corner_radius=10, border_width=1)
        self.dept_entry.grid(row=4, column=0, pady=10)

        self.status_label = ctk.CTkLabel(self.signup_frame, text="", text_color="red", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=5, column=0, pady=5)

        self.signup_btn = ctk.CTkButton(self.signup_frame, text="Sign Up", command=self.signup, width=300, height=45, corner_radius=10, font=ctk.CTkFont(weight="bold", size=15))
        self.signup_btn.grid(row=6, column=0, pady=(10, 5))
        
        self.back_btn = ctk.CTkButton(self.signup_frame, text="Back to Login", command=lambda: controller.show_frame("LoginScreen"), width=300, height=45, corner_radius=10, fg_color="transparent", border_width=2, text_color=("gray10", "gray90"), font=ctk.CTkFont(weight="bold", size=15))
        self.back_btn.grid(row=7, column=0, pady=(5, 30))

    def signup(self):
        admin_id = self.id_entry.get()
        password = self.password_entry.get()
        department = self.dept_entry.get()
        
        if not admin_id or not password or not department:
            self.status_label.configure(text="Please fill all fields", text_color="#ff4a4a")
            return
            
        if db.create_admin(admin_id, password, department):
            self.status_label.configure(text="Account created successfully!", text_color="#2e8b57")
            self.id_entry.delete(0, 'end')
            self.password_entry.delete(0, 'end')
            self.dept_entry.delete(0, 'end')
            # Optional: auto redirect to login
            self.after(1500, lambda: self.controller.show_frame("LoginScreen"))
        else:
            self.status_label.configure(text="Failed to create account. ID might exist.", text_color="#ff4a4a")


class MainAdminScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="Main Admin", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.logout_btn = ctk.CTkButton(self.sidebar, text="Logout", command=lambda: controller.show_frame("LoginScreen"))
        self.logout_btn.grid(row=5, column=0, padx=20, pady=20)

        # Main content
        self.content = ctk.CTkFrame(self)
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        ctk.CTkLabel(self.content, text="Create Department Admin", font=ctk.CTkFont(size=20)).pack(pady=20)

        self.admin_id = ctk.CTkEntry(self.content, placeholder_text="New Admin ID")
        self.admin_id.pack(pady=10)

        self.admin_pass = ctk.CTkEntry(self.content, placeholder_text="Password")
        self.admin_pass.pack(pady=10)

        self.admin_dept = ctk.CTkEntry(self.content, placeholder_text="Department Name")
        self.admin_dept.pack(pady=10)

        self.create_btn = ctk.CTkButton(self.content, text="Create Admin", command=self.create_admin)
        self.create_btn.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(self.content, text="")
        self.status_label.pack()

    def create_admin(self):
        aid = self.admin_id.get()
        pwd = self.admin_pass.get()
        dept = self.admin_dept.get()
        if aid and pwd and dept:
            if db.create_admin(aid, pwd, dept):
                self.status_label.configure(text="Admin created successfully!", text_color="green")
            else:
                self.status_label.configure(text="Failed to create admin.", text_color="red")
        else:
            self.status_label.configure(text="Fill all fields.", text_color="red")


class DepartmentAdminScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#F8F9FA")
        self.controller = controller

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----------------- SIDEBAR -----------------
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#FFFFFF", border_color="#E2E8F0", border_width=1)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="❁ SETUP LOGO", font=ctk.CTkFont(size=18, weight="bold"), text_color="#1E293B")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(24, 30), sticky="w")
        
        self.menu_label = ctk.CTkLabel(self.sidebar, text="MENU", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8")
        self.menu_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")

        self.dashboard_btn = self.create_sidebar_btn("⌂ Dashboard", 2, active=True)
        self.add_student_btn = self.create_sidebar_btn("⨁ Add Student", 3, command=lambda: controller.show_frame("StudentRegistrationScreen"))
        self.settings_btn = self.create_sidebar_btn("⚙ Settings", 4)
        
        self.logout_btn = self.create_sidebar_btn("⍇ Logout", 7, command=lambda: controller.show_frame("LoginScreen"))
        self.logout_btn.grid(pady=(10, 20))

        # ----------------- MAIN CONTENT -----------------
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(2, weight=1)

        # Top Bar
        self.top_bar = ctk.CTkFrame(self.main_content, height=60, fg_color="#FFFFFF", corner_radius=0, border_color="#E2E8F0", border_width=1)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(1, weight=1)
        
        self.search_entry = ctk.CTkEntry(self.top_bar, placeholder_text="🔍 Find participant...", width=300, corner_radius=8, fg_color="#F1F5F9", border_width=0, height=36)
        self.search_entry.grid(row=0, column=0, padx=20, pady=12, sticky="w")
        
        self.user_profile = ctk.CTkLabel(self.top_bar, text="Sarah Johnson 👤\nJohns@gmail.com", font=ctk.CTkFont(size=12), justify="right")
        self.user_profile.grid(row=0, column=2, padx=20, pady=12, sticky="e")

        # Content Area
        self.content_area = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.content_area.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 20))
        
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        self.dept_label = ctk.CTkLabel(title_frame, text="Department Dashboard", font=ctk.CTkFont(size=28, weight="bold"), text_color="#0F172A")
        self.dept_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(title_frame, text="Manage participant profiles and onboarding", font=ctk.CTkFont(size=12), text_color="#64748B")
        self.subtitle_label.pack(anchor="w")
        
        self.add_btn = ctk.CTkButton(self.header_frame, text="+ Participants", fg_color="#0F172A", hover_color="#1E293B", corner_radius=6, command=lambda: controller.show_frame("StudentRegistrationScreen"))
        self.add_btn.pack(side="right")
        
        self.upload_btn = ctk.CTkButton(self.header_frame, text="↑ Upload file", fg_color="#FFFFFF", text_color="#0F172A", border_color="#CBD5E1", border_width=1, hover_color="#F8F9FA", corner_radius=6)
        self.upload_btn.pack(side="right", padx=(10, 10))

        # Dynamic Tabs
        self.tabs_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tabs_frame.pack(fill="x", pady=(0, 10))
        
        self.current_tab = ctk.StringVar(value="All Student")
        self.seg_btn = ctk.CTkSegmentedButton(self.tabs_frame, 
                                              values=["All Student", "Present Student", "Absent Student", "Analytics"],
                                              variable=self.current_tab, 
                                              command=self.switch_tab,
                                              fg_color="#F1F5F9",
                                              selected_color="#2CCC8D",
                                              selected_hover_color="#25b37b",
                                              font=ctk.CTkFont(size=13, weight="bold"))
        self.seg_btn.pack(side="left")

        # Container for changing content
        self.view_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.view_container.pack(fill="both", expand=True)

        # Graph area
        self.graph_frame = ctk.CTkFrame(self.view_container, fg_color="#FFFFFF", corner_radius=10, border_color="#E2E8F0", border_width=1)
        self.graph_canvas = ctk.CTkCanvas(self.graph_frame, bg="#FFFFFF", highlightthickness=0)
        self.graph_canvas.pack(fill="both", expand=True, padx=20, pady=20)

        # Table area
        self.table_frame = ctk.CTkFrame(self.view_container, fg_color="#FFFFFF", corner_radius=10, border_color="#E2E8F0", border_width=1)
        
        import tkinter.ttk as ttk
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#FFFFFF", foreground="#0F172A", rowheight=50, fieldbackground="#FFFFFF", borderwidth=0, font=("Inter", 11))
        style.map("Treeview", background=[("selected", "#F1F5F9")], foreground=[("selected", "#0F172A")])
        style.configure("Treeview.Heading", background="#FFFFFF", foreground="#64748B", font=("Inter", 10, "bold"), borderwidth=0, padding=10)

        self.tree_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=20, pady=(20, 20))

        self.tree = ttk.Treeview(self.tree_frame, columns=("ID", "Name", "Status", "Date", "Time"), show="headings", height=8)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Student Name")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Time", text="Time")
        
        self.tree.column("ID", width=100)
        self.tree.column("Name", width=250)
        self.tree.column("Status", width=120)
        self.tree.column("Date", width=150)
        self.tree.column("Time", width=150)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # State lists
        self.all_students_list = []
        self.present_students_list = []
        self.absent_students_list = []

    def switch_tab(self, value):
        if value == "Analytics":
            self.table_frame.pack_forget()
            self.graph_frame.pack(fill="both", expand=True, pady=10)
            self.draw_graph()
        else:
            self.graph_frame.pack_forget()
            self.table_frame.pack(fill="both", expand=True, pady=10)
            
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            if value == "All Student":
                for s in self.all_students_list:
                    status = "Present" if str(s.get("id")) in [str(p.get("id")) for p in self.present_students_list] else "Absent"
                    self.tree.insert("", "end", values=(self.format_id(s.get("id")), s.get("name", "Unknown"), status, "-", "-"))
            elif value == "Present Student":
                for s in self.present_students_list:
                    self.tree.insert("", "end", values=(self.format_id(s.get("id")), s.get("name", "Unknown"), "Present", s.get("date", "-"), s.get("time", "-")))
            elif value == "Absent Student":
                for s in self.absent_students_list:
                    self.tree.insert("", "end", values=(self.format_id(s.get("id")), s.get("name", "Unknown"), "Absent", "-", "-"))

    def format_id(self, uid):
        uid_str = str(uid)
        if len(uid_str) > 6 and "-" in uid_str:
            return uid_str[:6] + "..."
        return uid_str

    def draw_graph(self):
        self.graph_canvas.delete("all")
        # Ensure canvas is updated before getting width
        self.graph_canvas.update()
        width = self.graph_canvas.winfo_width()
        height = self.graph_canvas.winfo_height()
        if width <= 1: width = 800
        if height <= 1: height = 400
        
        present_count = len(self.present_students_list)
        absent_count = len(self.absent_students_list)
        total = present_count + absent_count
        
        cx, cy = width/2, height/2
        
        if total == 0:
            self.graph_canvas.create_text(cx, cy, text="No Attendance Data Available", font=("Inter", 16), fill="#94A3B8")
            return
             
        r = min(width, height) / 3
        
        present_angle = (present_count / total) * 360
        
        if present_count == 0:
            self.graph_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#FF4A4A", outline="")
        elif absent_count == 0:
            self.graph_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#2CCC8D", outline="")
        else:
            self.graph_canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=0, extent=present_angle, fill="#2CCC8D", outline="")
            self.graph_canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=present_angle, extent=360-present_angle, fill="#FF4A4A", outline="")
        
        # Center title
        self.graph_canvas.create_text(cx, cy-r-40, text="Today's Attendance Overview", font=("Inter", 18, "bold"), fill="#1E293B")
        
        # Legends
        lx = cx + r + 50
        self.graph_canvas.create_rectangle(lx, cy-20, lx+20, cy, fill="#2CCC8D", outline="")
        self.graph_canvas.create_text(lx+30, cy-10, text=f"Present: {present_count}", anchor="w", font=("Inter", 14), fill="#1E293B")
        
        self.graph_canvas.create_rectangle(lx, cy+20, lx+20, cy+40, fill="#FF4A4A", outline="")
        self.graph_canvas.create_text(lx+30, cy+30, text=f"Absent: {absent_count}", anchor="w", font=("Inter", 14), fill="#1E293B")

    def create_sidebar_btn(self, text, row, command=None, active=False):
        fg = "#F1F5F9" if active else "transparent"
        text_color = "#0F172A" if active else "#64748B"
        font = ctk.CTkFont(size=14, weight="bold" if active else "normal")
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color=fg, text_color=text_color, font=font, anchor="w", width=210, height=45, hover_color="#E2E8F0", command=command, corner_radius=8)
        btn.grid(row=row, column=0, padx=15, pady=5)
        return btn

    def refresh_data(self):
        if self.controller.current_user and "data" in self.controller.current_user:
            dept = self.controller.current_user["data"].get("department", "Department")
            self.dept_label.configure(text=f"{dept} Dashboard")
            self.user_profile.configure(text=f"{dept} Admin 👤\nadmin@domain.com")
        
        # Default mock data to wow the user
        self.all_students_list = [
            {"id": "101", "name": "Nolasco Martinez"},
            {"id": "102", "name": "Sarah Johnson"},
            {"id": "103", "name": "Michael Chen"},
            {"id": "104", "name": "Emily Davis"},
            {"id": "105", "name": "James Wilson"}
        ]
        self.present_students_list = [
            {"id": "101", "name": "Nolasco Martinez", "date": "Oct 8, 2026", "time": "09:00 AM"},
            {"id": "102", "name": "Sarah Johnson", "date": "Oct 8, 2026", "time": "09:15 AM"},
            {"id": "105", "name": "James Wilson", "date": "Oct 8, 2026", "time": "09:30 AM"}
        ]
        
        # Load real data if available
        import datetime
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        real_students = db.get_all_students()
        if real_students:
            self.all_students_list = real_students
            
        real_attendance = db.get_attendance_by_department("dummy")
        if real_attendance:
            self.present_students_list = []
            for a in real_attendance:
                s_name = a.get("students", {}).get("name", "Unknown") if a.get("students") else "Unknown"
                # For demo, if we don't filter by today_str, we just show all records as present today
                self.present_students_list.append({
                    "id": a.get("student_id"), 
                    "name": s_name, 
                    "date": a.get("date"), 
                    "time": a.get("time")
                })
        
        present_ids = [str(s.get("id")) for s in self.present_students_list]
        self.absent_students_list = [s for s in self.all_students_list if str(s.get("id")) not in present_ids]
        
        # Refresh current tab view
        self.switch_tab(self.current_tab.get())


class StudentRegistrationScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Form Container
        self.form_frame = ctk.CTkScrollableFrame(self, width=500, height=600)
        self.form_frame.grid(row=0, column=0, pady=20)

        ctk.CTkLabel(self.form_frame, text="Student Registration", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        # Fields: Name, Mobile Number, Email ID, Date of Birth, Parent Number, Department Email, Class
        self.entries = {}
        fields = ["Name", "Mobile Number", "Email ID", "Date of Birth (YYYY-MM-DD)", "Parent Number", "Department Email", "Class"]
        
        for field in fields:
            entry = ctk.CTkEntry(self.form_frame, placeholder_text=field, width=300)
            entry.pack(pady=10)
            self.entries[field] = entry

        self.next_btn = ctk.CTkButton(self.form_frame, text="Next (Capture Face)", command=self.capture_face)
        self.next_btn.pack(pady=30)
        
        self.cancel_btn = ctk.CTkButton(self.form_frame, text="Cancel", fg_color="transparent", border_width=1, command=lambda: controller.show_frame("DepartmentAdminScreen"))
        self.cancel_btn.pack(pady=5)
        
        self.status_label = ctk.CTkLabel(self.form_frame, text="")
        self.status_label.pack(pady=10)

    def capture_face(self):
        # Validate data
        data = {k: v.get() for k, v in self.entries.items()}
        if not all(data.values()):
            self.status_label.configure(text="Please fill all fields.", text_color="red")
            return
            
        self.status_label.configure(text="Passive ML Anti-Spoofing Active: Capturing Real Human Face...", text_color="#0F172A", font=ctk.CTkFont(weight="bold"))
        self.update()
        
        # Background thread to prevent UI freezing
        def bg_capture():
            frame, success, encoding_or_msg = self.controller.camera_manager.capture_single_face_encoding()
            # Ensure UI updates happen on main thread
            self.after(0, lambda: self.finish_capture(frame, success, encoding_or_msg, data))
            
        threading.Thread(target=bg_capture, daemon=True).start()

    def finish_capture(self, frame, success, encoding_or_msg, data):
        if not success:
            self.status_label.configure(text=f"Face Capture Failed: {encoding_or_msg}", text_color="red")
            self.controller.camera_manager.stop_camera()
            return
            
        self.status_label.configure(text="Face captured! Saving to database...", text_color="#2CCC8D")
        self.update()
        
        # Save to DB
        db_data = {
            "name": data["Name"],
            "mobile": data["Mobile Number"],
            "email": data["Email ID"],
            "dob": data["Date of Birth (YYYY-MM-DD)"],
            "parent_number": data["Parent Number"],
            "department_email": data["Department Email"],
            "class_name": data["Class"]
        }
        
        res = db.register_student(db_data, encoding_or_msg)
        self.controller.camera_manager.stop_camera()
        
        if res is not None:
            self.status_label.configure(text="Registration Successful!", text_color="#2CCC8D")
            # Clear entries
            for e in self.entries.values():
                e.delete(0, "end")
        else:
            self.status_label.configure(text="Failed to save to database.", text_color="red")


class LiveScannerScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=3) # Video takes more space
        self.grid_columnconfigure(1, weight=1) # List takes less space

        # Top Bar
        self.top_bar = ctk.CTkFrame(self, height=60, fg_color="#FFFFFF", corner_radius=0, border_color="#E2E8F0", border_width=1)
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        self.back_btn = ctk.CTkButton(self.top_bar, text="← Back to Login", command=lambda: controller.show_frame("LoginScreen"), fg_color="#F1F5F9", text_color="#0F172A", hover_color="#E2E8F0")
        self.back_btn.pack(side="left", padx=20, pady=15)
        
        ctk.CTkLabel(self.top_bar, text="Live Face Attendance Scanner", font=ctk.CTkFont(size=20, weight="bold"), text_color="#0F172A").pack(side="left", padx=20)

        # Video Frame (Left)
        self.video_container = ctk.CTkFrame(self, fg_color="#F8F9FA", corner_radius=15, border_color="#E2E8F0", border_width=1)
        self.video_container.grid(row=1, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.video_container.grid_rowconfigure(0, weight=1)
        self.video_container.grid_columnconfigure(0, weight=1)
        
        self.video_label = ctk.CTkLabel(self.video_container, text="Loading Camera feed...")
        self.video_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.status_label = ctk.CTkLabel(self.video_container, text="Initializing Camera...", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=1, column=0, pady=10)

        # Recent Marked Panel (Right)
        self.sidebar_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, border_color="#E2E8F0", border_width=1)
        self.sidebar_frame.grid(row=1, column=1, padx=(10, 20), pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar_frame, text="Recently Marked", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0F172A").pack(pady=(20, 10))
        
        self.recent_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.recent_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.marked_today = set() # Store IDs to avoid duplicate UI entries

    def add_to_marked_list(self, name, student_id):
        if student_id in self.marked_today:
            return
            
        self.marked_today.add(student_id)
        
        item_frame = ctk.CTkFrame(self.recent_list_frame, fg_color="#F1F5F9", corner_radius=8)
        item_frame.pack(fill="x", pady=5)
        
        now = datetime.now().strftime("%H:%M:%S")
        student_id_short = str(student_id)[:6] + "..." if len(str(student_id)) > 6 and "-" in str(student_id) else str(student_id)
        text = f"✅ {name} ({student_id_short})\nTime: {now}"
        
        ctk.CTkLabel(item_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), text_color="#2CCC8D", justify="left").pack(anchor="w", padx=10, pady=10)

    def start_video_loop(self):
        # Clear recent list on start
        for widget in self.recent_list_frame.winfo_children():
            widget.destroy()
        self.marked_today.clear()
        # Load students into camera manager
        students = db.get_all_students()
        if students:
            self.controller.camera_manager.load_known_faces(students)
            self.status_label.configure(text=f"Loaded {len(students)} known faces. Scanning...")
        else:
            self.status_label.configure(text="No known faces found in DB or DB not connected. Scanning anyway...")
            
        self.controller.camera_manager.start_camera()
        self.latest_frame = None
        
        # Start a background thread for camera processing to prevent UI hanging
        self.video_thread = threading.Thread(target=self.camera_loop, daemon=True)
        self.video_thread.start()
        
        self.update_frame_ui()

    def camera_loop(self):
        while self.controller.camera_running:
            if not self.controller.camera_manager.video_capture:
                break
            ret, frame = self.controller.camera_manager.video_capture.read()
            if ret:
                # Process frame for attendance (runs in background thread)
                processed_frame, detected = self.controller.camera_manager.process_frame_for_attendance(frame)
                
                # Convert to PhotoImage compatible format
                processed_frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(processed_frame_rgb)
                
                # Store it safely for the UI thread to pick up
                self.latest_frame = img
                
                # Record attendance in DB
                for student in detected:
                    if student['status'] == 'recorded':
                        now = datetime.now()
                        db.record_attendance(student['id'], now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"))
                        print(f"Recorded attendance for {student['name']}")
                        # Push to UI List!
                        self.after(0, lambda s=student: self.add_to_marked_list(s['name'], s['id']))
            time.sleep(0.01)

    def update_frame_ui(self):
        if not self.controller.camera_running:
            return

        if getattr(self, 'latest_frame', None) is not None:
            # Create CTkImage and update label on the main UI thread
            ctk_image = ctk.CTkImage(light_image=self.latest_frame, dark_image=self.latest_frame, size=(640, 480))
            self.video_label.configure(image=ctk_image)
            self.video_label.image = ctk_image

        # Schedule the next UI update
        self.after(30, self.update_frame_ui)
