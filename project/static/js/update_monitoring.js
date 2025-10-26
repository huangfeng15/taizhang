(function () {
    'use strict';

    function initYearAutosubmit() {
        const yearField = document.getElementById('update-monitoring-year');
        if (!yearField) return;
        const handler = () => {
            if (yearField.form) {
                yearField.form.requestSubmit ? yearField.form.requestSubmit() : yearField.form.submit();
            }
        };
        yearField.addEventListener('change', handler);
    }

    function initStartDateValidation() {
        const input = document.getElementById('update-monitoring-start-date');
        if (!input) return;

        let debounceTimer = null;

        const isValidDate = (value) => {
            if (!value) return false;
            const clean = value.replace(/\D/g, '');
            if (clean.length !== 8) return false;
            const year = Number(clean.slice(0, 4));
            const month = Number(clean.slice(4, 6));
            const day = Number(clean.slice(6, 8));
            if ([year, month, day].some(Number.isNaN)) return false;
            return year >= 1900 && year <= 2100 && month >= 1 && month <= 12 && day >= 1 && day <= 31;
        };

        const getErrorEl = () => {
            let el = input.parentElement?.querySelector('.date-error');
            if (!el) {
                el = document.createElement('small');
                el.className = 'date-error';
                input.parentElement?.appendChild(el);
            }
            return el;
        };

        const showError = (msg) => {
        input.classList.add('update-monitoring__input--error');
            const el = getErrorEl();
            el.textContent = msg;
            el.classList.add('update-monitoring__error');
        };

        const clearError = () => {
            input.classList.remove('update-monitoring__input--error');
            const el = input.parentElement?.querySelector('.date-error');
            if (el) el.remove();
        };

        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            clearError();
            const value = input.value.trim();
            debounceTimer = window.setTimeout(() => {
                if (value.length >= 8) {
                    if (isValidDate(value)) {
                        clearError();
                        input.form?.requestSubmit?.() ?? input.form?.submit?.();
                    } else {
                        showError('日期格式无效，请输入YYYYMMDD');
                    }
                }
            }, 800);
        });

        input.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                clearTimeout(debounceTimer);
                const value = input.value.trim();
                if (isValidDate(value)) {
                    clearError();
                    input.form?.requestSubmit?.() ?? input.form?.submit?.();
                } else {
                    showError('日期格式无效，请输入YYYYMMDD');
                }
            }
        });
    }

    function init() {
        initYearAutosubmit();
        initStartDateValidation();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
