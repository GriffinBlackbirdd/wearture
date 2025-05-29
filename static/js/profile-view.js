
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