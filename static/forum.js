/*
  forum.js
  Authors: clump

  Purpose:
    Makes event cards on the forum page clickable so users can
    view full event details.
*/




document.addEventListener('DOMContentLoaded', function() {
    // Handle event card clicks
    document.querySelectorAll('.event-card').forEach(card => {
        card.addEventListener('click', function() {
            window.location.href = this.dataset.url;
        });
    });
});