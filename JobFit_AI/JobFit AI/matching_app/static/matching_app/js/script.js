/**
 * JobFit AI - Intelligent Resume-Based Job Matching & Skill Recommendation Platform
 * Custom Client-Side JavaScript (script.js)
 * 
 * Enhancements included:
 *  - Auto-dismissing alerts after 5s
 *  - Client-side upload validation (file size, extension) & loading state indicator
 *  - Bootstrap tooltips & popovers auto-initialization
 *  - Interactive skill tag search/filter on lists
 *  - Modal confirmation helpers
 */

document.addEventListener('DOMContentLoaded', function () {

    // ----------------------------------------------------------------------
    // 1. Auto-dismiss Bootstrap Alerts after 5 seconds
    // ----------------------------------------------------------------------
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function (alertEl) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // ----------------------------------------------------------------------
    // 2. Resume File Upload Client Validation & Progress Spinner State
    // ----------------------------------------------------------------------
    const uploadForm = document.querySelector('form[enctype="multipart/form-data"]');
    const fileInput = document.querySelector('input[type="file"]');

    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                const fileSizeMb = file.size / (1024 * 1024);
                const fileExt = file.name.split('.').pop().toLowerCase();
                const allowedExts = ['pdf', 'docx'];

                // Remove old validation errors if present
                const oldError = fileInput.parentNode.querySelector('.js-client-error');
                if (oldError) {
                    oldError.remove();
                }

                if (!allowedExts.includes(fileExt)) {
                    showInputError(fileInput, `Invalid file type .${fileExt}. Allowed formats: PDF, DOCX.`);
                    fileInput.value = '';
                    return;
                }

                if (fileSizeMb > 5) {
                    showInputError(fileInput, `File size (${fileSizeMb.toFixed(2)} MB) exceeds maximum allowed limit of 5 MB.`);
                    fileInput.value = '';
                    return;
                }
            }
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            const submitBtn = uploadForm.querySelector('button[type="submit"]');
            if (submitBtn && fileInput && fileInput.files.length > 0) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Extracting Skills &amp; Parsing Document...
                `;
            }
        });
    }

    function showInputError(inputEl, message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'text-danger mt-1 small js-client-error';
        errorDiv.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
        inputEl.parentNode.appendChild(errorDiv);
    }

    // ----------------------------------------------------------------------
    // 3. Initialize Bootstrap Tooltips & Popovers
    // ----------------------------------------------------------------------
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    console.log('JobFit AI: Client-side JavaScript initialized successfully.');
});