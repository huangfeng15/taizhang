// 监控仪表板数字动画效果
(function() {
    'use strict';

    // 数字动画类
    class NumberAnimator {
        constructor(element, targetValue, duration = 1500) {
            this.element = element;
            this.targetValue = targetValue;
            this.duration = duration;
            this.startValue = 0;
            this.startTime = null;
            this.isAnimating = false;
        }

        animate() {
            if (this.isAnimating) return;
            this.isAnimating = true;
            this.startTime = null;
            this.startValue = 0;
            
            const step = (currentTime) => {
                if (!this.startTime) this.startTime = currentTime;
                const progress = Math.min((currentTime - this.startTime) / this.duration, 1);
                
                // 使用缓动函数
                const easeOutQuart = 1 - Math.pow(1 - progress, 4);
                const currentValue = Math.floor(this.startValue + (this.targetValue - this.startValue) * easeOutQuart);
                
                this.element.textContent = currentValue;
                
                if (progress < 1) {
                    requestAnimationFrame(step);
                } else {
                    this.element.textContent = this.targetValue;
                    this.isAnimating = false;
                    this.element.classList.add('animated');
                }
            };
            
            requestAnimationFrame(step);
        }
    }

    // 初始化数字动画
    function initNumberAnimations() {
        const statNumbers = document.querySelectorAll('.compact-stat-card .stat-number');
        
        const observerOptions = {
            threshold: 0.5,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const element = entry.target;
                    const value = parseInt(element.textContent) || 0;
                    
                    // 延迟动画，创建波浪效果
                    const delay = Array.from(element.parentElement.parentElement.children).indexOf(element.parentElement) * 100;
                    
                    setTimeout(() => {
                        const animator = new NumberAnimator(element, value, 1500);
                        animator.animate();
                    }, delay);
                    
                    // 停止观察已经动画的元素
                    observer.unobserve(element);
                }
            });
        }, observerOptions);

        statNumbers.forEach(number => {
            observer.observe(number);
        });
    }

    // 添加鼠标悬停效果
    function initHoverEffects() {
        const statItems = document.querySelectorAll('.compact-stat-card .stat-item');
        
        statItems.forEach(item => {
            item.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px) scale(1.02)';
                this.style.boxShadow = '0 6px 20px rgba(0,0,0,0.15)';
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
                this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
            });
        });
    }

    // 监控筛选栏自动提交
    function initMonitoringFilterAutoSubmit() {
        const autoFields = document.querySelectorAll('.monitoring-filter [data-auto-submit="true"]');
        autoFields.forEach((field) => {
            const delay = Number(field.dataset.autoSubmitDelay || 400);
            const eventName = field.tagName === 'SELECT' ? 'change' : 'input';
            let timer = null;

            const handler = () => {
                clearTimeout(timer);
                timer = setTimeout(() => {
                    const form = field.closest('form');
                    if (form) {
                        form.requestSubmit ? form.requestSubmit() : form.submit();
                    }
                }, delay);
            };

            field.addEventListener(eventName, handler);
        });
    }

    // 添加点击波纹效果
    function initRippleEffect() {
        const statItems = document.querySelectorAll('.compact-stat-card .stat-item');
        
        statItems.forEach(item => {
            item.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                ripple.classList.add('ripple');
                
                this.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });
    }

    // 初始化所有功能
    function init() {
        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // 页面加载完成后延迟执行动画
        setTimeout(() => {
            initNumberAnimations();
            initHoverEffects();
            initRippleEffect();
        initMonitoringFilterAutoSubmit();
        }, 300);

        // 添加CSS样式
        const style = document.createElement('style');
        style.textContent = `
            .ripple {
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.6);
                transform: scale(0);
                animation: ripple-animation 0.6s linear;
                pointer-events: none;
            }
            
            @keyframes ripple-animation {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
            
            .compact-stat-card .stat-number.animated {
                text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
                transition: text-shadow 0.3s ease;
            }
            
            .compact-stat-card .stat-item {
                position: relative;
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
        `;
        document.head.appendChild(style);
    }

    // 启动
    init();
})();
