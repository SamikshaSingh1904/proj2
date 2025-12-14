/*
  profile.js
  Authors: Beatrix Kim, Bessie Li, Samiksha Singh

  Purpose:
    Makes event cards on the profile page clickable so users can
    view full event details.
*/



document.addEventListener('DOMContentLoaded', function() {
    // Handle event item clicks
    const eventItems = document.querySelectorAll('.event-item');
    eventItems.forEach(item => {
        item.addEventListener('click', function() {
            const url = this.dataset.eventUrl;
            if (url) {
                window.location.href = url;
            }
        });
        
        // Add hover cursor
        item.style.cursor = 'pointer';
    });

    // Handle delete account button
    const deleteAccountForm = document.getElementById('delete-account-form');
    if (deleteAccountForm) {
        deleteAccountForm.addEventListener('submit', function(e) {
            e.preventDefault();
            showConfirmModal(
                'Delete account? This action cannot be undone.',
                () => deleteAccountForm.submit(),
                'Delete Account'
            );
        });
    }
});