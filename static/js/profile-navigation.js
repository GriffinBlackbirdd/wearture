// Add this JavaScript to your main template or create a separate profile-navigation.js file

document.addEventListener('DOMContentLoaded', function() {
    // Handle profile icon click
    const profileIcon = document.querySelector('.nav-icons .icon-link:nth-child(2)'); // Profile icon
    
    if (profileIcon) {
        profileIcon.addEventListener('click', async function(e) {
            e.preventDefault();
            
            try {
                // Check if user is authenticated
                const response = await fetch('/api/auth/me');
                const result = await response.json();
                
                if (result.success && result.user) {
                    // User is authenticated, redirect to profile
                    window.location.href = '/profile';
                } else {
                    // User is not authenticated, redirect to login
                    window.location.href = '/login?redirect=profile';
                }
            } catch (error) {
                // On error, redirect to login
                window.location.href = '/login?redirect=profile';
            }
        });
    }
    
    // Update profile dropdown functionality if it exists
    updateProfileDropdown();
});

async function updateProfileDropdown() {
    try {
        const response = await fetch('/api/auth/me');
        const result = await response.json();
        
        const profileDropdown = document.getElementById('profile-dropdown');
        if (!profileDropdown) return;
        
        if (result.success && result.user) {
            // User is logged in - show user options
            const guestOptions = profileDropdown.querySelector('.guest-options');
            const userOptions = profileDropdown.querySelector('.user-options');
            const userHeader = profileDropdown.querySelector('.user-header');
            const guestHeader = profileDropdown.querySelector('.guest-header');
            
            if (guestOptions) guestOptions.style.display = 'none';
            if (userOptions) userOptions.style.display = 'block';
            if (guestHeader) guestHeader.style.display = 'none';
            if (userHeader) {
                userHeader.style.display = 'block';
                const emailElement = userHeader.querySelector('#user-email');
                if (emailElement) {
                    emailElement.textContent = result.user.email;
                }
            }
            
            // Update profile link to go directly to profile page
            const profileLinks = profileDropdown.querySelectorAll('a[href="/profile"]');
            profileLinks.forEach(link => {
                link.href = '/profile';
            });
            
        } else {
            // User is not logged in - show guest options
            const guestOptions = profileDropdown.querySelector('.guest-options');
            const userOptions = profileDropdown.querySelector('.user-options');
            const userHeader = profileDropdown.querySelector('.user-header');
            const guestHeader = profileDropdown.querySelector('.guest-header');
            
            if (guestOptions) guestOptions.style.display = 'block';
            if (userOptions) userOptions.style.display = 'none';
            if (guestHeader) guestHeader.style.display = 'block';
            if (userHeader) userHeader.style.display = 'none';
        }
    } catch (error) {
        console.error('Error updating profile dropdown:', error);
    }
}