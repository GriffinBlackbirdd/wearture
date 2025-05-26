// Replace the profile dropdown functionality in your profile-view.js with this enhanced version

document.addEventListener('DOMContentLoaded', function() {
    console.log('Profile dropdown script loaded');
    
    // Elements
    const profileIcon = document.querySelector('.nav-icons a:nth-child(2)');
    const profileDropdown = document.getElementById('profile-dropdown');
    const logoutBtn = document.getElementById('logout-btn');
    const guestOptions = document.querySelector('.guest-options');
    const userOptions = document.querySelector('.user-options');
    const guestHeader = document.querySelector('.guest-header');
    const userHeader = document.querySelector('.user-header');
    const userEmail = document.getElementById('user-email');
    
    // Debug function to check cookies
    function debugCookies() {
        console.log('=== Cookie Debug ===');
        console.log('All cookies:', document.cookie);
        
        const cookies = document.cookie.split(';').reduce((acc, cookie) => {
            const [key, value] = cookie.trim().split('=');
            acc[key] = value;
            return acc;
        }, {});
        
        console.log('Parsed cookies:', cookies);
        console.log('Auth token:', cookies.user_access_token ? 'Found' : 'Not found');
        
        if (cookies.user_access_token) {
            console.log('Auth token (first 50 chars):', cookies.user_access_token.substring(0, 50));
        }
        
        return cookies.user_access_token;
    }
    
    // Check auth status on page load
    checkAuthStatus();
    
    // Toggle profile dropdown
    if (profileIcon) {
        profileIcon.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Profile icon clicked');
            debugCookies(); // Debug cookies when dropdown is opened
            
            profileDropdown.classList.toggle('active');
            
            // Close cart if it's open
            if (window.closeCart && document.getElementById('cart-sidebar').classList.contains('active')) {
                window.closeCart();
            }
            
            // Close search if it's open
            const searchOverlay = document.getElementById('search-overlay');
            if (searchOverlay && searchOverlay.classList.contains('active')) {
                searchOverlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (profileDropdown && !profileDropdown.contains(e.target) && !profileIcon.contains(e.target)) {
            profileDropdown.classList.remove('active');
        }
    });
    
    // Logout functionality
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            
            try {
                const response = await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Clear the cookie manually
                    document.cookie = 'user_access_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
                    
                    // Show notification
                    if (window.showNotification) {
                        window.showNotification('Logged out successfully');
                    } else {
                        alert('Logged out successfully');
                    }
                    
                    // Update UI
                    updateUIForGuest();
                    
                    // Close dropdown
                    profileDropdown.classList.remove('active');
                    
                    // Redirect to home if on a protected page
                    const currentPath = window.location.pathname;
                    const protectedPaths = ['/account', '/orders', '/wishlist'];
                    
                    if (protectedPaths.some(path => currentPath.startsWith(path))) {
                        window.location.href = '/';
                    }
                } else {
                    console.error('Logout failed:', data.message);
                }
            } catch (error) {
                console.error('Logout error:', error);
            }
        });
    }
    
    // Check authentication status
    async function checkAuthStatus() {
        console.log('=== Checking Auth Status ===');
        
        // First check if we have a cookie
        const authToken = debugCookies();
        
        if (!authToken) {
            console.log('No auth token found, showing guest UI');
            updateUIForGuest();
            return;
        }
        
        try {
            console.log('Making auth status request...');
            const response = await fetch('/api/auth/status', {
                method: 'GET',
                credentials: 'include', // Important: include cookies
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            console.log('Auth status response status:', response.status);
            
            const data = await response.json();
            console.log('Auth status response data:', data);
            
            if (response.ok && data.authenticated) {
                console.log('User is authenticated:', data.user);
                updateUIForUser(data.user);
            } else {
                console.log('User not authenticated:', data);
                updateUIForGuest();
            }
        } catch (error) {
            console.error('Auth check error:', error);
            updateUIForGuest();
        }
    }
    
    // Update UI for logged in user
    function updateUIForUser(user) {
        console.log('Updating UI for authenticated user:', user);
        
        if (guestOptions) guestOptions.style.display = 'none';
        if (userOptions) userOptions.style.display = 'block';
        if (guestHeader) guestHeader.style.display = 'none';
        if (userHeader) userHeader.style.display = 'block';
        
        // Set user info
        if (user && user.email && userEmail) {
            userEmail.textContent = user.email;
        }
        
        // Check for pending orders
        checkPendingOrders();
        
        console.log('UI updated for authenticated user');
    }
    
    // Update UI for guest (not logged in)
    function updateUIForGuest() {
        console.log('Updating UI for guest user');
        
        if (guestOptions) guestOptions.style.display = 'block';
        if (userOptions) userOptions.style.display = 'none';
        if (guestHeader) guestHeader.style.display = 'block';
        if (userHeader) userHeader.style.display = 'none';
        
        console.log('UI updated for guest user');
    }
    
    // Check for pending orders (optional)
    async function checkPendingOrders() {
        try {
            const response = await fetch('/api/user/orders', {
                credentials: 'include'
            });
            const orders = await response.json();
            
            if (response.ok && Array.isArray(orders)) {
                // Count pending/new orders
                const pendingOrders = orders.filter(order => 
                    order.order_status === 'pending' || 
                    order.order_status === 'confirmed' ||
                    order.order_status === 'processing'
                );
                
                // Update orders menu item with badge if there are pending orders
                const ordersMenuItem = document.querySelector('.user-options a[href="/orders"]');
                
                if (ordersMenuItem && pendingOrders.length > 0) {
                    if (!ordersMenuItem.querySelector('.notification-badge')) {
                        const badge = document.createElement('span');
                        badge.className = 'notification-badge';
                        badge.textContent = pendingOrders.length;
                        ordersMenuItem.appendChild(badge);
                    } else {
                        ordersMenuItem.querySelector('.notification-badge').textContent = pendingOrders.length;
                    }
                }
            }
        } catch (error) {
            console.error('Error checking orders:', error);
        }
    }
    
    // Expose debug function globally for manual testing
    window.debugAuth = function() {
        console.log('=== Manual Auth Debug ===');
        debugCookies();
        checkAuthStatus();
    };
    
    // Auto-recheck auth status every 30 seconds to catch any issues
    setInterval(checkAuthStatus, 30000);
    
    console.log('Profile dropdown initialization complete');
});
    // Search functionality
    document.addEventListener('DOMContentLoaded', function() {
        // Elements
        const searchIcon = document.querySelector('.nav-icons a:first-child');
        const searchOverlay = document.getElementById('search-overlay');
        const closeSearchBtn = document.getElementById('close-search');
        const searchInput = document.getElementById('search-input');
        const searchButton = document.getElementById('search-button');
        const searchResults = document.getElementById('search-results');
        
        // Open search overlay
        searchIcon.addEventListener('click', function(e) {
            e.preventDefault();
            searchOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
            setTimeout(() => {
                searchInput.focus();
            }, 300);
        });
        
        // Close search overlay
        closeSearchBtn.addEventListener('click', function() {
            searchOverlay.classList.remove('active');
            document.body.style.overflow = '';
        });
        
        // Close on overlay click (outside container)
        searchOverlay.addEventListener('click', function(e) {
            if (e.target === searchOverlay) {
                searchOverlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
        
        // Close on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && searchOverlay.classList.contains('active')) {
                searchOverlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
        
        // Handle search
        function performSearch() {
            const query = searchInput.value.trim().toLowerCase();
            
            if (query.length < 2) {
                searchResults.innerHTML = `
                    <div class="no-results">
                        <p>Please enter at least 2 characters to search</p>
                    </div>`;
                return;
            }
            
            // Show loading indicator
            searchResults.innerHTML = `
                <div class="no-results">
                    <p><i class="fas fa-spinner fa-spin"></i> Searching...</p>
                </div>`;
            
            // Fetch products from the API
            fetch('/api/products')
                .then(response => response.json())
                .then(products => {
                    // Filter products based on search query
                    const filteredProducts = products.filter(product => 
                        product.name.toLowerCase().includes(query) ||
                        (product.description && product.description.toLowerCase().includes(query)) ||
                        (product.category_name && product.category_name.toLowerCase().includes(query))
                    );
                    
                    // Display results
                    if (filteredProducts.length === 0) {
                        searchResults.innerHTML = `
                            <div class="no-results">
                                <p>No products found for "${query}"</p>
                            </div>`;
                    } else {
                        const resultsHTML = `
                            <div class="search-results-grid">
                                ${filteredProducts.map(product => `
                                    <a href="/product/${product.id}" class="search-result-item">
                                        <div class="search-result-image">
                                            <img src="${product.image_url}" alt="${product.name}">
                                        </div>
                                        <div class="search-result-info">
                                            <h4 class="search-result-name">${product.name}</h4>
                                            <div class="search-result-price">
                                                ₹${product.sale_price || product.price}
                                                ${product.sale_price ? `<span class="search-result-original">₹${product.price}</span>` : ''}
                                            </div>
                                        </div>
                                    </a>
                                `).join('')}
                            </div>`;
                        
                        searchResults.innerHTML = resultsHTML;
                    }
                })
                .catch(error => {
                    console.error('Search error:', error);
                    searchResults.innerHTML = `
                        <div class="no-results">
                            <p>Error searching products. Please try again.</p>
                        </div>`;
                });
        }
        
        // Search on button click
        searchButton.addEventListener('click', performSearch);
        
        // Search on Enter key
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
        
        // Live search (optional) - only activate if you want search results to appear as user types
        searchInput.addEventListener('input', debounce(function() {
            if (this.value.trim().length >= 2) {
                performSearch();
            } else if (this.value.trim().length === 0) {
                searchResults.innerHTML = `
                    <div class="no-results">
                        <p>Start typing to search for products</p>
                    </div>`;
            }
        }, 500));
        
        // Debounce function to limit how often the search is performed while typing
        function debounce(func, wait) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        }
    });