// Product Image Hover Transition
document.addEventListener('DOMContentLoaded', function() {
    // Find all product cards
    const productCards = document.querySelectorAll('.product-card');
    
    productCards.forEach(card => {
        // Get the main image container and image
        const imageContainer = card.querySelector('.product-image-container');
        const mainImage = card.querySelector('.product-image');
        const productOverlay = card.querySelector('.product-overlay');
        
        if (!imageContainer || !mainImage) return;
        
        // Check if this product has additional images in data attribute
        const productData = card.dataset.productData;
        let additionalImages = [];
        
        if (productData) {
            try {
                const parsedData = JSON.parse(productData);
                additionalImages = parsedData.additional_images || [];
            } catch (e) {
                console.error('Error parsing product data:', e);
            }
        }
        
        // If there's at least one additional image, create the hover effect
        if (additionalImages.length > 0) {
            // Store the original image URL
            const originalSrc = mainImage.src;
            
            // Create a second image element that will be hidden initially
            const secondImage = document.createElement('img');
            secondImage.src = additionalImages[0]; // Use the first additional image
            secondImage.alt = mainImage.alt;
            secondImage.className = 'product-second-image';
            imageContainer.appendChild(secondImage);
            
            // Add hover event listeners to the card (not just image container)
            // This helps maintain consistent behavior with the overlay
            card.addEventListener('mouseenter', function() {
                secondImage.classList.add('show');
                mainImage.classList.add('hide');
                // Don't modify the overlay - let its own hover behavior work
            });
            
            card.addEventListener('mouseleave', function() {
                secondImage.classList.remove('show');
                mainImage.classList.remove('hide');
                // Don't modify the overlay - let its own hover behavior work
            });
        }
    });
});