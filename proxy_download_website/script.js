// Interactive elements and smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Subtle parallax effect on hero visual
document.addEventListener('mousemove', (e) => {
    const mockup = document.querySelector('.glass-mockup');
    if(window.innerWidth > 1024 && mockup) {
        const xAxis = (window.innerWidth / 2 - e.pageX) / 50;
        const yAxis = (window.innerHeight / 2 - e.pageY) / 50;
        
        // Base rotation + mouse movement
        mockup.style.transform = `perspective(1000px) rotateY(${xAxis - 5}deg) rotateX(${yAxis + 5}deg)`;
    }
});

// Reset transform when mouse leaves
document.addEventListener('mouseleave', () => {
    const mockup = document.querySelector('.glass-mockup');
    if(window.innerWidth > 1024 && mockup) {
        mockup.style.transform = `perspective(1000px) rotateY(-5deg) rotateX(5deg)`;
    }
});
