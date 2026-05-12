// Dark mode toggle
document.addEventListener('DOMContentLoaded', function() {
    const themeBtn = document.getElementById('theme-btn');
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    
    // Apply saved theme preference
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        themeBtn.textContent = '☀️';
    }
    
    // Toggle dark mode
    if (themeBtn) {
        themeBtn.addEventListener('click', function() {
            const isDark = document.body.classList.toggle('dark-mode');
            localStorage.setItem('darkMode', isDark);
            themeBtn.textContent = isDark ? '☀️' : '🌙';
        });
    }
    
    // Close alerts
    const closeButtons = document.querySelectorAll('.close-alert');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.target.closest('.alert').remove();
        });
    });
    
    // Auto-close alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-success, .alert-info');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });
});
