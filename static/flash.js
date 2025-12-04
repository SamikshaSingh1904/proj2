/*
  flash.js
  Authors: Beatrix Kim

  Purpose:
    Auto-hide flash messages after 2 seconds
*/


document.addEventListener('DOMContentLoaded', function() {
    const messagesDiv = document.getElementById('messages');
    if (messagesDiv) {
        setTimeout(function() {
            messagesDiv.style.transition = 'opacity 0.5s';
            messagesDiv.style.opacity = '0';
            setTimeout(function() {
                messagesDiv.remove();
            }, 500); // Wait for fade out animation
        }, 2000); // 2 seconds
    }
});