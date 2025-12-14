/*
  flash_helper.js
  Authors: Beatrix Kim

  Purpose:
    Shared helper functions for showing flash messages and confirmation modals
    across all pages of the application.
*/

/**
 * Show a flash message in the UI (mimics Flask flash messages)
 * @param {string} message - The message to display
 * @param {string} category - 'success' or 'error'
 */
function showFlashMessage(message, category = 'error') {
    // Get or create messages container
    let messagesDiv = document.getElementById('messages');
    if (!messagesDiv) {
        messagesDiv = document.createElement('div');
        messagesDiv.id = 'messages';
        document.body.appendChild(messagesDiv);
    }
    
    // Create message element
    const messageP = document.createElement('p');
    messageP.className = `flash-${category}`;
    messageP.textContent = message;
    
    // Add to container
    messagesDiv.appendChild(messageP);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        messageP.style.opacity = '0';
        setTimeout(() => messageP.remove(), 300);
    }, 5000);
}

/**
 * Show a confirmation dialog
 * @param {string} message - The confirmation message
 * @param {function} onConfirm - Callback function if user confirms
 * @param {string} title - Optional title for the modal
 */
function showConfirmModal(message, onConfirm, title = 'Confirm Action') {
    const modal = document.getElementById('confirm-modal');
    const titleEl = document.getElementById('confirm-title');
    const messageEl = document.getElementById('confirm-message');
    const yesBtn = document.getElementById('confirm-yes-btn');
    const noBtn = document.getElementById('confirm-no-btn');
    
    // Set content
    titleEl.textContent = title;
    messageEl.textContent = message;
    
    // Show modal
    modal.style.display = 'flex';
    
    // Handle yes
    const handleYes = function() {
        modal.style.display = 'none';
        yesBtn.removeEventListener('click', handleYes);
        noBtn.removeEventListener('click', handleNo);
        onConfirm();
    };
    
    // Handle no
    const handleNo = function() {
        modal.style.display = 'none';
        yesBtn.removeEventListener('click', handleYes);
        noBtn.removeEventListener('click', handleNo);
    };
    
    yesBtn.addEventListener('click', handleYes);
    noBtn.addEventListener('click', handleNo);
    
    // Close on outside click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            handleNo();
        }
    });
}