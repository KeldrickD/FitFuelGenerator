// Initialize Feather icons
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Budget input handler
    const budgetInput = document.getElementById('weekly_budget');
    if (budgetInput) {
        budgetInput.addEventListener('input', function() {
            const value = parseFloat(this.value);
            if (value < 40) {
                this.setCustomValidity('Minimum budget is $40 per week');
            } else if (value > 200) {
                this.setCustomValidity('Maximum budget is $200 per week');
            } else {
                this.setCustomValidity('');
            }
        });
    }

    // Alert auto-dismiss
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Preview page enhancements
    const previewContainer = document.querySelector('.preview-container');
    if (previewContainer) {
        // Add loading state for PDF generation
        const pdfButton = document.querySelector('a[href*="generate_pdf"]');
        if (pdfButton) {
            pdfButton.addEventListener('click', function() {
                const icon = this.querySelector('i');
                icon.setAttribute('data-feather', 'loader');
                feather.replace();
                this.classList.add('disabled');
                setTimeout(() => {
                    icon.setAttribute('data-feather', 'download');
                    feather.replace();
                    this.classList.remove('disabled');
                }, 3000);
            });
        }

        // Lazy loading for plan sections
        const planSections = document.querySelectorAll('.workout-day, .meal-day');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        });

        planSections.forEach(section => {
            observer.observe(section);
        });
    }
});

// Error handling for AJAX requests
window.addEventListener('error', function(e) {
    console.error('Global error handler:', e.error);
    // Show user-friendly error message
    const errorAlert = document.createElement('div');
    errorAlert.className = 'alert alert-danger alert-dismissible fade show';
    errorAlert.innerHTML = `
        An error occurred. Please try again later.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('main').prepend(errorAlert);
});
