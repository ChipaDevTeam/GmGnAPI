// Modern JavaScript for GmGnAPI Documentation

class DocumentationApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupMobileMenu();
        this.setupTabSwitching();
        this.setupCopyButtons();
        this.setupScrollEffects();
        this.setupSmoothScrolling();
        this.setupThemeToggle();
        this.setupSearchFunctionality();
        this.initializeAnimations();
    }

    // Navigation Functionality
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPage || (currentPage === '' && href === 'index.html')) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });

        // Handle hash-based navigation for single page
        if (window.location.hash) {
            this.scrollToSection(window.location.hash);
        }

        // Update active link on scroll
        this.updateActiveNavOnScroll();
    }

    updateActiveNavOnScroll() {
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-link[href^="#"]');

        if (sections.length === 0) return;

        const observerOptions = {
            threshold: 0.3,
            rootMargin: '-100px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    navLinks.forEach(link => link.classList.remove('active'));
                    const activeLink = document.querySelector(`.nav-link[href="#${entry.target.id}"]`);
                    if (activeLink) {
                        activeLink.classList.add('active');
                    }
                }
            });
        }, observerOptions);

        sections.forEach(section => observer.observe(section));
    }

    // Mobile Menu
    setupMobileMenu() {
        const hamburger = document.querySelector('.hamburger');
        const navMenu = document.querySelector('.nav-menu');

        if (!hamburger || !navMenu) return;

        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
            document.body.classList.toggle('menu-open');
        });

        // Close menu when clicking nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
                document.body.classList.remove('menu-open');
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
                document.body.classList.remove('menu-open');
            }
        });
    }

    // Tab Switching for Examples
    setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.example-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.textContent.toLowerCase().replace(/\s+/g, '-');
                
                // Remove active class from all buttons and contents
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Add active class to clicked button
                button.classList.add('active');
                
                // Show corresponding content
                const targetContent = document.getElementById(`${targetTab}-example`);
                if (targetContent) {
                    targetContent.classList.add('active');
                    this.animateElementIn(targetContent);
                }
            });
        });
    }

    // Copy to Clipboard Functionality
    setupCopyButtons() {
        document.querySelectorAll('.copy-btn').forEach(button => {
            button.addEventListener('click', () => {
                const codeBlock = button.closest('.code-block') || button.closest('.install-method');
                const code = codeBlock.querySelector('pre code, pre');
                
                if (code) {
                    this.copyToClipboard(code.textContent.trim(), button);
                }
            });
        });
    }

    async copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            this.showCopyFeedback(button, true);
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();
            
            try {
                document.execCommand('copy');
                this.showCopyFeedback(button, true);
            } catch (fallbackErr) {
                this.showCopyFeedback(button, false);
            }
            
            document.body.removeChild(textArea);
        }
    }

    showCopyFeedback(button, success) {
        const originalContent = button.innerHTML;
        const icon = success ? 'fa-check' : 'fa-times';
        const color = success ? '#10b981' : '#ef4444';
        
        button.innerHTML = `<i class="fas ${icon}"></i>`;
        button.style.color = color;
        button.style.borderColor = color;
        
        setTimeout(() => {
            button.innerHTML = originalContent;
            button.style.color = '';
            button.style.borderColor = '';
        }, 2000);
    }

    // Scroll Effects
    setupScrollEffects() {
        // Navbar background on scroll
        const navbar = document.querySelector('.navbar');
        
        const handleScroll = () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        };

        window.addEventListener('scroll', this.throttle(handleScroll, 10));

        // Reveal animations
        this.setupRevealAnimations();
    }

    setupRevealAnimations() {
        const revealElements = document.querySelectorAll('.feature-card, .doc-card, .install-method');
        
        const revealOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    // Add staggered animation delay
                    const delay = Array.from(entry.target.parentElement.children).indexOf(entry.target) * 100;
                    entry.target.style.animationDelay = `${delay}ms`;
                }
            });
        }, revealOptions);

        revealElements.forEach(element => {
            element.classList.add('reveal-element');
            revealObserver.observe(element);
        });
    }

    // Smooth Scrolling
    setupSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    this.scrollToSection(anchor.getAttribute('href'));
                }
            });
        });
    }

    scrollToSection(hash) {
        const target = document.querySelector(hash);
        if (target) {
            const offsetTop = target.offsetTop - 80; // Account for fixed navbar
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    }

    // Theme Toggle (for future dark/light mode)
    setupThemeToggle() {
        const themeToggle = document.querySelector('.theme-toggle');
        if (!themeToggle) return;

        const currentTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);

        themeToggle.addEventListener('click', () => {
            const newTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // Search Functionality
    setupSearchFunctionality() {
        const searchInput = document.querySelector('.search-input');
        const searchResults = document.querySelector('.search-results');
        
        if (!searchInput) return;

        let searchTimeout;
        
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value);
            }, 300);
        });

        // Close search results when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchResults?.contains(e.target)) {
                if (searchResults) {
                    searchResults.style.display = 'none';
                }
            }
        });
    }

    performSearch(query) {
        if (query.length < 2) return;

        // This would typically connect to a search API or index
        // For now, we'll search through visible content
        const searchableElements = document.querySelectorAll('h1, h2, h3, p, .feature-card, .doc-card');
        const results = [];

        searchableElements.forEach(element => {
            if (element.textContent.toLowerCase().includes(query.toLowerCase())) {
                results.push({
                    title: this.getElementTitle(element),
                    text: element.textContent.trim().substring(0, 150) + '...',
                    element: element
                });
            }
        });

        this.displaySearchResults(results);
    }

    getElementTitle(element) {
        if (element.tagName.match(/H[1-6]/)) {
            return element.textContent;
        }
        const parentSection = element.closest('section');
        const heading = parentSection?.querySelector('h1, h2, h3');
        return heading?.textContent || 'Untitled Section';
    }

    displaySearchResults(results) {
        const searchResults = document.querySelector('.search-results');
        if (!searchResults) return;

        if (results.length === 0) {
            searchResults.innerHTML = '<div class="no-results">No results found</div>';
        } else {
            searchResults.innerHTML = results.map(result => `
                <div class="search-result" onclick="this.scrollIntoView()">
                    <h4>${result.title}</h4>
                    <p>${result.text}</p>
                </div>
            `).join('');
        }

        searchResults.style.display = 'block';
    }

    // Animation Utilities
    initializeAnimations() {
        // Initialize any entrance animations
        this.animateHeroElements();
        this.setupParallaxEffects();
    }

    animateHeroElements() {
        const heroElements = document.querySelectorAll('.hero-content > *, .hero-code > *');
        
        heroElements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(30px)';
            
            setTimeout(() => {
                element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 150);
        });
    }

    setupParallaxEffects() {
        const parallaxElements = document.querySelectorAll('.parallax');
        
        if (parallaxElements.length === 0) return;

        const handleParallax = () => {
            const scrolled = window.pageYOffset;
            
            parallaxElements.forEach(element => {
                const rate = scrolled * -0.5;
                element.style.transform = `translateY(${rate}px)`;
            });
        };

        window.addEventListener('scroll', this.throttle(handleParallax, 10));
    }

    animateElementIn(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        requestAnimationFrame(() => {
            element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        });
    }

    // Utility Functions
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    debounce(func, wait, immediate) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }

    // Accessibility Enhancements
    setupAccessibility() {
        // Skip to main content link
        this.addSkipLink();
        
        // Keyboard navigation improvements
        this.improveKeyboardNavigation();
        
        // ARIA labels and roles
        this.enhanceAriaLabels();
    }

    addSkipLink() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main';
        skipLink.textContent = 'Skip to main content';
        skipLink.className = 'skip-link';
        skipLink.style.cssText = `
            position: absolute;
            top: -40px;
            left: 6px;
            background: var(--primary-color);
            color: white;
            padding: 8px;
            text-decoration: none;
            border-radius: 4px;
            z-index: 1000;
            transition: top 0.2s;
        `;
        
        skipLink.addEventListener('focus', () => {
            skipLink.style.top = '6px';
        });
        
        skipLink.addEventListener('blur', () => {
            skipLink.style.top = '-40px';
        });
        
        document.body.insertBefore(skipLink, document.body.firstChild);
    }

    improveKeyboardNavigation() {
        // Add focus styles and keyboard handlers
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Close any open modals or menus
                const openMenu = document.querySelector('.nav-menu.active');
                if (openMenu) {
                    this.setupMobileMenu(); // This will close the menu
                }
            }
        });
    }

    enhanceAriaLabels() {
        // Add ARIA labels to interactive elements
        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.setAttribute('aria-label', 'Copy code to clipboard');
        });
        
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.setAttribute('role', 'tab');
        });
    }
}

// Global functions for HTML onclick handlers
window.showExample = function(exampleType) {
    const app = window.documentationApp;
    if (app) {
        const button = document.querySelector(`.tab-btn[onclick*="${exampleType}"]`);
        if (button) {
            button.click();
        }
    }
};

window.copyToClipboard = function(button) {
    const app = window.documentationApp;
    if (app) {
        const codeBlock = button.closest('.code-block') || button.closest('.install-method');
        const code = codeBlock.querySelector('pre code, pre');
        
        if (code) {
            app.copyToClipboard(code.textContent.trim(), button);
        }
    }
};

// Performance monitoring
class PerformanceMonitor {
    constructor() {
        this.metrics = {};
        this.init();
    }

    init() {
        if ('performance' in window) {
            this.measurePageLoad();
            this.measureResourceLoad();
        }
    }

    measurePageLoad() {
        window.addEventListener('load', () => {
            const navigation = performance.getEntriesByType('navigation')[0];
            this.metrics.pageLoad = {
                domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
                totalTime: navigation.loadEventEnd - navigation.fetchStart
            };
        });
    }

    measureResourceLoad() {
        const observer = new PerformanceObserver((list) => {
            list.getEntries().forEach((entry) => {
                if (entry.entryType === 'resource') {
                    this.metrics.resources = this.metrics.resources || [];
                    this.metrics.resources.push({
                        name: entry.name,
                        duration: entry.duration,
                        size: entry.transferSize
                    });
                }
            });
        });
        
        observer.observe({entryTypes: ['resource']});
    }

    getMetrics() {
        return this.metrics;
    }
}

// Error handling and logging
class ErrorHandler {
    constructor() {
        this.init();
    }

    init() {
        window.addEventListener('error', this.handleError.bind(this));
        window.addEventListener('unhandledrejection', this.handlePromiseRejection.bind(this));
    }

    handleError(event) {
        console.error('JavaScript Error:', {
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            error: event.error
        });
        
        // In production, you might want to send this to an error tracking service
        this.logError('javascript', event.error || event.message);
    }

    handlePromiseRejection(event) {
        console.error('Unhandled Promise Rejection:', event.reason);
        this.logError('promise', event.reason);
    }

    logError(type, error) {
        // This would typically send to an error logging service
        if (window.gtag) {
            window.gtag('event', 'exception', {
                description: error.toString(),
                fatal: false
            });
        }
    }
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.documentationApp = new DocumentationApp();
    window.performanceMonitor = new PerformanceMonitor();
    window.errorHandler = new ErrorHandler();
});

// Service Worker registration for offline functionality
if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}
