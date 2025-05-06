document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            this.classList.toggle('active');
            
            if (navLinks.classList.contains('show')) {
                navLinks.classList.remove('show');
                setTimeout(() => {
                    navLinks.style.display = 'none';
                }, 300);
            } else {
                navLinks.style.display = 'flex';
                navLinks.classList.add('show');
            }
        });
    }
    
    // Product Slider Functionality
    const productSlider = document.querySelector('.product-slider');
    const prevBtn = document.querySelector('.prev-btn');
    const nextBtn = document.querySelector('.next-btn');
    
    if (productSlider && prevBtn && nextBtn) {
        let slidePosition = 0;
        const productCards = document.querySelectorAll('.product-card');
        const totalSlides = productCards.length;
        
        // Determine visible slides based on screen width
        const getVisibleSlides = () => {
            if (window.innerWidth > 1200) return 4;
            if (window.innerWidth > 992) return 3;
            if (window.innerWidth > 576) return 2;
            return 1;
        };
        
        // Update slide position
        const updateSlider = () => {
            const visibleSlides = getVisibleSlides();
            const slideWidth = productSlider.clientWidth / visibleSlides;
            
            productSlider.style.display = 'grid';
            
            // Reset position at ends
            if (slidePosition < 0) slidePosition = 0;
            if (slidePosition > totalSlides - visibleSlides) {
                slidePosition = totalSlides - visibleSlides;
            }
            
            // Apply transform to each card for smoother animation
            productCards.forEach((card, index) => {
                const translateValue = index >= slidePosition && index < slidePosition + visibleSlides 
                    ? 0 
                    : (index < slidePosition ? -100 : 100);
                
                card.style.opacity = (index >= slidePosition && index < slidePosition + visibleSlides) ? '1' : '0';
                card.style.transform = `translateX(${translateValue}%)`;
                card.style.transition = 'transform 0.5s ease, opacity 0.5s ease';
                
                // Ensure visible cards are clickable
                card.style.pointerEvents = (index >= slidePosition && index < slidePosition + visibleSlides) 
                    ? 'auto' 
                    : 'none';
            });
            
            // Update button states
            prevBtn.disabled = slidePosition === 0;
            nextBtn.disabled = slidePosition >= totalSlides - visibleSlides;
            
            prevBtn.style.opacity = prevBtn.disabled ? '0.5' : '1';
            nextBtn.style.opacity = nextBtn.disabled ? '0.5' : '1';
        };
        
        // Initialize slider
        updateSlider();
        
        // Button event listeners
        prevBtn.addEventListener('click', () => {
            slidePosition--;
            updateSlider();
        });
        
        nextBtn.addEventListener('click', () => {
            slidePosition++;
            updateSlider();
        });
        
        // Update on window resize
        window.addEventListener('resize', updateSlider);
    }
    
    // Testimonial slider
    const testimonialCards = document.querySelectorAll('.testimonial-card');
    
    if (testimonialCards.length > 0) {
        let currentTestimonial = 0;
        const testimonialCount = testimonialCards.length;
        
        const showTestimonial = (index) => {
            testimonialCards.forEach((card, i) => {
                card.style.opacity = i === index ? '1' : '0';
                card.style.transform = i === index ? 'translateY(0)' : 'translateY(20px)';
                card.style.zIndex = i === index ? '1' : '0';
            });
        };
        
        // Auto rotate testimonials
        const rotateTestimonials = () => {
            currentTestimonial = (currentTestimonial + 1) % testimonialCount;
            showTestimonial(currentTestimonial);
        };
        
        // Initialize
        showTestimonial(0);
        
        // Set interval for testimonial rotation
        setInterval(rotateTestimonials, 5000);
    }
    
    // Add to cart functionality
    const addToCartButtons = document.querySelectorAll('.action-btn:nth-child(2)');
    const cartCount = document.querySelector('.cart-count');
    
    if (addToCartButtons.length > 0 && cartCount) {
        let count = 0;
        
        addToCartButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                count++;
                cartCount.textContent = count;
                
                // Show added to cart notification
                const product = this.closest('.product-card');
                const productName = product.querySelector('h3').textContent;
                
                showNotification(`${productName} added to cart!`);
                
                // Add animation
                this.classList.add('added');
                setTimeout(() => {
                    this.classList.remove('added');
                }, 1000);
            });
        });
    }
    
    // Notification system
    function showNotification(message) {
        // Remove any existing notification
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        // Create new notification
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-check-circle"></i>
                <p>${message}</p>
                <button class="close-notification"><i class="fas fa-times"></i></button>
            </div>
        `;
        
        // Append to body
        document.body.appendChild(notification);
        
        // Show notification with animation
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Auto hide after 3 seconds
        setTimeout(() => {
            hideNotification(notification);
        }, 3000);
        
        // Close button functionality
        const closeBtn = notification.querySelector('.close-notification');
        closeBtn.addEventListener('click', () => {
            hideNotification(notification);
        });
    }
    
    function hideNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }
    
    // Add CSS for notifications
    const notificationStyles = document.createElement('style');
    notificationStyles.textContent = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #fff;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 15px;
            transform: translateX(100%);
            opacity: 0;
            transition: transform 0.3s ease, opacity 0.3s ease;
            z-index: 1000;
        }
        
        .notification.show {
            transform: translateX(0);
            opacity: 1;
        }
        
        .notification-content {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .notification .fa-check-circle {
            color: #28a745;
            font-size: 18px;
        }
        
        .notification p {
            margin: 0;
            color: #333;
        }
        
        .close-notification {
            background: none;
            border: none;
            cursor: pointer;
            padding: 5px;
            color: #777;
        }
        
        .close-notification:hover {
            color: #333;
        }
        
        .action-btn.added {
            background-color: #28a745;
            color: #fff;
            border-color: #28a745;
            animation: pulse 0.5s;
        }
        
        @keyframes pulse {
            0% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.2);
            }
            100% {
                transform: scale(1);
            }
        }
        
        /* Mobile menu styles */
        @media (max-width: 992px) {
            .nav-links {
                position: absolute;
                top: 70px;
                left: 0;
                width: 100%;
                background-color: #fff;
                flex-direction: column;
                padding: 20px;
                box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
                display: none;
                opacity: 0;
                transform: translateY(-10px);
                transition: opacity 0.3s ease, transform 0.3s ease;
                z-index: 99;
            }
            
            .nav-links.show {
                display: flex;
                opacity: 1;
                transform: translateY(0);
            }
            
            .nav-links li {
                margin: 10px 0;
            }
            
            .mobile-menu-toggle.active i:before {
                content: '\\f00d';
            }
        }
    `;
    
    document.head.appendChild(notificationStyles);
    
    // Newsletter form submission
    const newsletterForm = document.querySelector('.newsletter-form');
    
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const emailInput = this.querySelector('input[type="email"]');
            const email = emailInput.value.trim();
            
            if (email) {
                // Simulate submission
                emailInput.value = '';
                
                // Show success message
                showNotification('Thanks for subscribing! Check your email for ₹500 off coupon.');
            }
        });
    }
    
    // Lazy Loading Images
    const lazyImages = document.querySelectorAll('img:not([loading="eager"])');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('loaded');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => {
            if (img.dataset.src) {
                imageObserver.observe(img);
            }
        });
    } else {
        // Fallback for browsers that don't support Intersection Observer
        lazyImages.forEach(img => {
            if (img.dataset.src) {
                img.src = img.dataset.src;
            }
        });
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href !== '#') {
                e.preventDefault();
                
                const targetElement = document.querySelector(href);
                
                if (targetElement) {
                    window.scrollTo({
                        top: targetElement.offsetTop - 80,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
});