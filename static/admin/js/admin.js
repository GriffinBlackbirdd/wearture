/**
 * WEARXTURE Admin Panel JavaScript
 * Main functionality for admin dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    // Toggle mobile sidebar
    const toggleSidebar = document.getElementById('toggle-sidebar');
    const sidebar = document.getElementById('sidebar');
    
    if (toggleSidebar && sidebar) {
        toggleSidebar.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
        
        // Close sidebar when clicking outside
        document.addEventListener('click', function(e) {
            if (sidebar.classList.contains('show') && 
                !sidebar.contains(e.target) && 
                e.target !== toggleSidebar) {
                sidebar.classList.remove('show');
            }
        });
    }
    
    // Initialize modals
    const modals = document.querySelectorAll('.modal-backdrop');
    const modalTriggers = document.querySelectorAll('[data-modal]');
    const closeModals = document.querySelectorAll('.modal-close');
    
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('show');
            }
        });
    });
    
    closeModals.forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            const modal = this.closest('.modal-backdrop');
            if (modal) {
                modal.classList.remove('show');
            }
        });
    });
    
    // Close modal when clicking on backdrop
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('show');
            }
        });
    });
    
    // Product Specific Functionality
    initProductsPage();
    
    // Category Specific Functionality
    initCategoriesPage();
});

/**
 * Initialize the Products page functionality
 */
function initProductsPage() {
    const addProductBtn = document.getElementById('add-product-btn');
    const productModal = document.getElementById('product-modal');
    
    if (!addProductBtn || !productModal) return; // Not on products page
    
    // Add Product Button
    addProductBtn.addEventListener('click', function() {
        productModal.classList.add('show');
    });
    
    // Image Upload for Product
    const imageUploadContainer = document.getElementById('image-upload-container');
    const fileInput = document.getElementById('fileInput');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    
    if (imageUploadContainer && fileInput) {
        imageUploadContainer.addEventListener('click', function() {
            fileInput.click();
        });
        
        fileInput.addEventListener('change', function() {
            handleFiles(this.files);
        });
        
        // Drag and drop functionality
        imageUploadContainer.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.borderColor = 'var(--primary-color)';
        });
        
        imageUploadContainer.addEventListener('dragleave', function() {
            this.style.borderColor = 'var(--border-color)';
        });
        
        imageUploadContainer.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderColor = 'var(--border-color)';
            handleFiles(e.dataTransfer.files);
        });
    }
    
    function handleFiles(files) {
        if (!imagePreviewContainer) return;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (!file.type.match('image.*')) continue;
            
            const reader = new FileReader();
            reader.onload = function(e) {
                const previewContainer = document.createElement('div');
                previewContainer.className = 'image-preview';
                previewContainer.style.backgroundImage = `url(${e.target.result})`;
                previewContainer.style.backgroundSize = 'cover';
                previewContainer.style.backgroundPosition = 'center';
                
                const removeBtn = document.createElement('div');
                removeBtn.className = 'remove-image';
                removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                removeBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    previewContainer.remove();
                });
                
                previewContainer.appendChild(removeBtn);
                imagePreviewContainer.appendChild(previewContainer);
            };
            
            reader.readAsDataURL(file);
        }
    }
    
    // Product Search Functionality
    const productSearch = document.getElementById('product-search');
    if (productSearch) {
        const productRows = document.querySelectorAll('#products-tbody tr');
        
        productSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            
            productRows.forEach(row => {
                const productName = row.querySelector('.product-name').textContent.toLowerCase();
                const productCategory = row.querySelector('.product-category').textContent.toLowerCase();
                
                if (productName.includes(searchTerm) || productCategory.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
    
    // Product Filter Functionality
    const categoryFilter = document.getElementById('category-filter');
    const statusFilter = document.getElementById('status-filter');
    
    if (categoryFilter && statusFilter) {
        const productRows = document.querySelectorAll('#products-tbody tr');
        
        categoryFilter.addEventListener('change', filterProducts);
        statusFilter.addEventListener('change', filterProducts);
        
        function filterProducts() {
            const selectedCategory = categoryFilter.value.toLowerCase();
            const selectedStatus = statusFilter.value;
            
            productRows.forEach(row => {
                const productCategory = row.querySelector('.product-category').textContent.toLowerCase();
                const isInStock = row.querySelector('.product-status').classList.contains('status-active');
                
                let showByCategory = true;
                let showByStatus = true;
                
                if (selectedCategory && !productCategory.includes(selectedCategory)) {
                    showByCategory = false;
                }
                
                if (selectedStatus === 'active' && !isInStock) {
                    showByStatus = false;
                } else if (selectedStatus === 'inactive' && isInStock) {
                    showByStatus = false;
                }
                
                row.style.display = (showByCategory && showByStatus) ? '' : 'none';
            });
        }
    }
    
    // Save Product Functionality
    const saveProductBtn = document.getElementById('save-product-btn');
    const productForm = document.getElementById('product-form');
    
    if (saveProductBtn && productForm) {
        saveProductBtn.addEventListener('click', function() {
            if (validateForm(productForm)) {
                // In a real app, submit form data to server
                showNotification('Product saved successfully!', 'success');
                productModal.classList.remove('show');
            }
        });
    }
    
    // Delete Product Functionality
    const deleteButtons = document.querySelectorAll('.action-btn.delete');
    const deleteModal = document.getElementById('delete-modal');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    let productToDelete = null;
    
    if (deleteButtons.length && deleteModal && confirmDeleteBtn) {
        deleteButtons.forEach(button => {
            button.addEventListener('click', function() {
                productToDelete = this.getAttribute('data-id');
                deleteModal.classList.add('show');
            });
        });
        
        confirmDeleteBtn.addEventListener('click', function() {
            if (productToDelete) {
                // In a real app, send delete request to server
                const rowToDelete = document.querySelector(`.action-btn.delete[data-id="${productToDelete}"]`).closest('tr');
                if (rowToDelete) {
                    rowToDelete.remove();
                    showNotification('Product deleted successfully!', 'success');
                }
                
                deleteModal.classList.remove('show');
                productToDelete = null;
            }
        });
    }
}

/**
 * Initialize the Categories page functionality
 */
function initCategoriesPage() {
    const addCategoryBtn = document.getElementById('add-category-btn');
    const categoryModal = document.getElementById('category-modal');
    const modalTitle = document.querySelector('#category-modal .modal-title');
    
    if (!addCategoryBtn || !categoryModal) return; // Not on categories page
    
    // Form elements
    const categoryForm = document.getElementById('category-form');
    const categoryId = document.getElementById('category-id');
    const categoryName = document.getElementById('category-name');
    const categoryDescription = document.getElementById('category-description');
    const categoryParent = document.getElementById('category-parent');
    const saveButton = document.getElementById('save-category-btn');
    
    // Image preview
    const imageInput = document.getElementById('category-image');
    const imagePreview = document.getElementById('preview-img');
    const uploadTrigger = document.getElementById('upload-trigger');
    
    // Add category button
    addCategoryBtn.addEventListener('click', function() {
        resetForm();
        modalTitle.textContent = 'Add New Category';
        categoryModal.classList.add('show');
    });
    
    // Image upload
    if (uploadTrigger && imageInput) {
        uploadTrigger.addEventListener('click', function() {
            imageInput.click();
        });
        
        imageInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    
    // Edit category buttons
    const editButtons = document.querySelectorAll('.category-action.edit');
    
    if (editButtons.length) {
        editButtons.forEach(button => {
            button.addEventListener('click', function() {
                const categoryId = this.getAttribute('data-id');
                editCategory(categoryId);
            });
        });
    }
    
    // Delete category buttons
    const deleteButtons = document.querySelectorAll('.category-action.delete');
    const deleteModal = document.getElementById('delete-modal');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    let categoryToDelete = null;
    
    if (deleteButtons.length && deleteModal && confirmDeleteBtn) {
        deleteButtons.forEach(button => {
            button.addEventListener('click', function() {
                categoryToDelete = this.getAttribute('data-id');
                deleteModal.classList.add('show');
            });
        });
        
        confirmDeleteBtn.addEventListener('click', function() {
            if (categoryToDelete) {
                deleteCategory(categoryToDelete);
                deleteModal.classList.remove('show');
            }
        });
    }
    
    // Save category
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            if (validateForm(categoryForm)) {
                if (categoryId && categoryId.value) {
                    // Update existing category
                    updateCategory();
                } else {
                    // Create new category
                    createCategory();
                }
            }
        });
    }
    
    // Populate parent category dropdown
    if (categoryParent) {
        populateParentCategories();
    }
    
    // Functions
    function resetForm() {
        if (!categoryForm) return;
        
        categoryForm.reset();
        if (categoryId) categoryId.value = '';
        if (imagePreview) {
            imagePreview.style.display = 'none';
            imagePreview.src = '';
        }
    }
    
    function populateParentCategories() {
        // Clear existing options
        categoryParent.innerHTML = '<option value="">None (Top Level)</option>';
        
        // Get categories
        const categories = Array.from(document.querySelectorAll('.category-card')).map(card => {
            return {
                id: card.getAttribute('data-id'),
                name: card.querySelector('.category-name').textContent
            };
        });
        
        // Add options to select
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            categoryParent.appendChild(option);
        });
    }
    
    function editCategory(id) {
        try {
            // In a real app, fetch category data from server
            // For now, get it from the DOM
            const categoryCard = document.querySelector(`.category-card[data-id="${id}"]`);
            
            if (categoryCard) {
                resetForm();
                
                categoryId.value = id;
                categoryName.value = categoryCard.querySelector('.category-name').textContent;
                categoryDescription.value = categoryCard.querySelector('.category-description').textContent;
                
                // Set image preview
                const imgSrc = categoryCard.querySelector('.category-image img').src;
                if (imgSrc) {
                    imagePreview.src = imgSrc;
                    imagePreview.style.display = 'block';
                }
                
                // Set parent category (in a real app, this would be more complex)
                // For now, leave it as the default
                
                modalTitle.textContent = 'Edit Category';
                categoryModal.classList.add('show');
            }
        } catch (error) {
            console.error('Error fetching category:', error);
            showNotification('Failed to load category data', 'error');
        }
    }
    
    function createCategory() {
        try {
            // For demo, just update the UI
            const maxId = Math.max(...Array.from(document.querySelectorAll('.category-card'))
                .map(card => parseInt(card.getAttribute('data-id'))), 0);
            
            const newId = maxId + 1;
            const name = categoryName.value;
            const description = categoryDescription.value || 'No description available';
            // Use a placeholder image URL if no image was selected
            const imageUrl = imagePreview.style.display !== 'none' ? imagePreview.src : '/static/images/categories/placeholder.jpg';
            
            const newCategory = document.createElement('div');
            newCategory.className = 'category-card';
            newCategory.setAttribute('data-id', newId);
            newCategory.innerHTML = `
                <div class="category-image">
                    <img src="${imageUrl}" alt="${name}">
                    <div class="category-actions">
                        <div class="category-action edit" data-id="${newId}" title="Edit Category">
                            <i class="fas fa-edit"></i>
                        </div>
                        <div class="category-action delete" data-id="${newId}" title="Delete Category">
                            <i class="fas fa-trash"></i>
                        </div>
                    </div>
                </div>
                <div class="category-content">
                    <h3 class="category-name">${name}</h3>
                    <p class="category-description">${description}</p>
                    <div class="category-meta">
                        <div class="category-products">
                            <i class="fas fa-tshirt"></i>
                            <span>0 Products</span>
                        </div>
                        <div class="category-date">
                            Added: ${new Date().toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })}
                        </div>
                    </div>
                </div>
            `;
            
            document.querySelector('.category-grid').appendChild(newCategory);
            
            // Add event listeners to new buttons
            const newEditBtn = newCategory.querySelector('.category-action.edit');
            newEditBtn.addEventListener('click', function() {
                editCategory(this.getAttribute('data-id'));
            });
            
            const newDeleteBtn = newCategory.querySelector('.category-action.delete');
            newDeleteBtn.addEventListener('click', function() {
                categoryToDelete = this.getAttribute('data-id');
                deleteModal.classList.add('show');
            });
            
            // Update parent categories dropdown
            populateParentCategories();
            
            // Show success message
            showNotification('Category created successfully!', 'success');
            
            // Close modal
            categoryModal.classList.remove('show');
            
        } catch (error) {
            console.error('Error creating category:', error);
            showNotification('Failed to create category', 'error');
        }
    }
    
    function updateCategory() {
        try {
            const id = categoryId.value;
            const name = categoryName.value;
            const description = categoryDescription.value || 'No description available';
            
            // Update the category card in DOM
            const categoryCard = document.querySelector(`.category-card[data-id="${id}"]`);
            
            if (categoryCard) {
                categoryCard.querySelector('.category-name').textContent = name;
                categoryCard.querySelector('.category-description').textContent = description;
                
                // Update image if changed
                if (imagePreview.style.display !== 'none') {
                    categoryCard.querySelector('.category-image img').src = imagePreview.src;
                }
                
                // Show success message
                showNotification('Category updated successfully!', 'success');
                
                // Close modal
                categoryModal.classList.remove('show');
            }
            
        } catch (error) {
            console.error('Error updating category:', error);
            showNotification('Failed to update category', 'error');
        }
    }
    
    function deleteCategory(id) {
        try {
            // Remove from DOM
            const categoryCard = document.querySelector(`.category-card[data-id="${id}"]`);
            
            if (categoryCard) {
                categoryCard.remove();
                
                // Update parent categories dropdown
                populateParentCategories();
                
                // Show success message
                showNotification('Category deleted successfully!', 'success');
            }
            
        } catch (error) {
            console.error('Error deleting category:', error);
            showNotification('Failed to delete category', 'error');
        }
    }
}

/**
 * Form validation helper
 * @param {HTMLFormElement} form - The form to validate
 * @returns {boolean} - Whether the form is valid
 */
function validateForm(form) {
    if (!form) return false;
    
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    // Clear previous errors
    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('error');
            
            // Add error message
            const errorMsg = document.createElement('div');
            errorMsg.className = 'error-message';
            errorMsg.textContent = 'This field is required';
            field.parentNode.insertBefore(errorMsg, field.nextSibling);
            
            // Remove error on input
            field.addEventListener('input', function() {
                this.classList.remove('error');
                const nextEl = this.nextElementSibling;
                if (nextEl && nextEl.classList.contains('error-message')) {
                    nextEl.remove();
                }
            }, { once: true });
        }
    });
    
    return isValid;
}

/**
 * Show notification
 * @param {string} message - The message to show
 * @param {string} type - The type of notification (success or error)
 */
function showNotification(message, type = 'success') {
    // Remove existing notification
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <p>${message}</p>
            <button class="close-notification"><i class="fas fa-times"></i></button>
        </div>
    `;
    
    // Append to body
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
    
    // Close button functionality
    const closeButton = notification.querySelector('.close-notification');
    closeButton.addEventListener('click', () => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    });
}

// Make functions globally available
window.showNotification = showNotification;
window.validateForm = validateForm;