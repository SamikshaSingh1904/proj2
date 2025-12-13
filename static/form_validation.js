/*
  form_validation.js
  Authors: Beatrix Kim

  Purpose: Client-side form validation for all app forms
*/

document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // EVENT FORM VALIDATION (create & edit)
    // ===================================
    const eventForm = document.getElementById('event-form');
    if (eventForm) {
        eventForm.addEventListener('submit', function(e) {
            const start = document.getElementById('event-start').value;
            const end = document.getElementById('event-end').value;
            
            // Make sure the event end time is after start time
            if (start && end && end <= start) {
                e.preventDefault();
                alert('End time must be after start time');
                return false;
            }
        });
    }
    
    // ===================================
    // SIGNUP FORM VALIDATION
    // ===================================
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            const email = document.getElementById('email').value;
            
            // Check that passwords match
            if (password !== confirmPassword) {
                e.preventDefault();
                alert('Passwords do not match');
                return false;
            }
            
        });
    }
    
});