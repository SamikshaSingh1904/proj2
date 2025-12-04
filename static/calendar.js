/*
  calendar.js
  Authors: clump (all members)

  Purpose:
    Displays events on a weekly calendar grid and allows users to
    view, join, leave, edit, and delete events through a detail panel.
*/



// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get week start date from data attribute
    const calendarSection = document.querySelector('.calendar-section');
    let currentWeekStart = null;

    if (calendarSection && calendarSection.dataset.weekStart) {
        currentWeekStart = calendarSection.dataset.weekStart;
    }

    // Navigate weeks
    document.getElementById('prev-week').addEventListener('click', function() {
        if (currentWeekStart) {
            // Parse the date string properly (YYYY-MM-DD)
            const parts = currentWeekStart.split('-');
            // Month 0-indexed
            const date = new Date(parts[0], parts[1] - 1, parts[2]); 
            date.setDate(date.getDate() - 7); // Go back 1 week
            
            // Format back to YYYY-MM-DD
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const newDate = `${year}-${month}-${day}`;
            
            window.location.href = `/calendar/${newDate}`;
        }
    });

    document.getElementById('next-week').addEventListener('click', function() {
        if (currentWeekStart) {
            // Parse the date string properly (YYYY-MM-DD)
            const parts = currentWeekStart.split('-');
            // Month is 0-indexed
            const date = new Date(parts[0], parts[1] - 1, parts[2]); 
            date.setDate(date.getDate() + 7); // Go forward 1 week
            
            // Format back to YYYY-MM-DD
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const newDate = `${year}-${month}-${day}`;
            
            window.location.href = `/calendar/${newDate}`;
        }
    });

    // Today button - go back to current week
    document.getElementById('today-btn').addEventListener('click', function() {
        window.location.href = '/calendar/';
    });

    // Add click handlers to event blocks
    document.querySelectorAll('.event-block').forEach(function(eventBlock) {
        eventBlock.addEventListener('click', function() {
            const eventId = this.getAttribute('data-eid');
            openEventPanel(eventId);
        });
    });

    // Add click handler to close button
    const closeBtn = document.querySelector('.close-panel-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeEventPanel);
    }
});

function loadWeek(offset) {
    window.location.href = `/calendar/?offset=${offset}`;
}

// Open event panel (split screen)
function openEventPanel(eventId) {
    // Store for forum reload
    window.currentEventId = eventId;
    
    // Clear previous event data and messages
    const panel = document.getElementById('event-panel');
    const eventActions = document.getElementById('event-actions');
    
    // Clear any "Event is full" messages from previous events
    const fullMessages = eventActions.querySelectorAll('p:not(#login-prompt)');
    fullMessages.forEach(msg => msg.remove());
    
    // Show loading state
    document.getElementById('panel-event-title').textContent = 'Loading...';
    
    fetch(`/api/event/${eventId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Populate panel with event details
            document.getElementById('panel-event-title')
                .textContent = data.title;
            document.getElementById('panel-event-date').textContent = 
                data.date;
            document.getElementById('panel-event-time').textContent = 
                `${data.start} - ${data.end}`;
            document.getElementById('panel-event-location').textContent = 
                `${data.city}, ${data.state}`;
            document.getElementById('panel-event-category')
                .textContent = data.category;
            document.getElementById('panel-event-creator')
                .textContent = data.creator_name;
            document.getElementById('panel-event-desc')
                .textContent = data.desc || 'No description provided.';
            document.getElementById('panel-event-capacity').textContent = 
                `${data.current_participants}/${data.cap} spots filled`;

            // Display participants
            const participantsList = 
                document.getElementById('panel-participants-list');
            participantsList.innerHTML = '';
            if (data.participants && data.participants.length > 0) {
                data.participants.forEach(participant => {
                    const li = document.createElement('li');
                    li.textContent = 
                        `${participant.name} (${participant.pronouns}) - 
                        Class of ${participant.year}`;
                    participantsList.appendChild(li);
                });
            } else {
                participantsList.textContent = 'No participants yet';
            }

            // Show/hide action buttons based on user status
            const joinBtn = document.getElementById('join-event-btn');
            const leaveBtn = document.getElementById('leave-event-btn');
            const editBtn = document.getElementById('edit-event-btn');
            const deleteBtn = document.getElementById('delete-event-btn');
            const loginPrompt = document.getElementById('login-prompt');

            // Hide all buttons first
            joinBtn.style.display = 'none';
            leaveBtn.style.display = 'none';
            editBtn.style.display = 'none';
            deleteBtn.style.display = 'none';
            loginPrompt.style.display = 'none';

            if (!data.logged_in) {
                // Not logged in - show login prompt
                loginPrompt.style.display = 'block';
            } else if (data.is_creator) {
                // User is the creator - show edit/delete buttons
                editBtn.style.display = 'inline-block';
                deleteBtn.style.display = 'inline-block';
                
                // Set up edit button
                editBtn.onclick = function() {
                    window.location.href = `/event/${data.eid}/edit`;
                };
                
                // Set up delete button
                deleteBtn.onclick = function() {
                    if (confirm(
                        'Are you sure you want to delete this event?')) {
                        deleteEvent(data.eid);
                    }
                };
            } else {
                // Regular logged-in user
                const isFull = data.current_participants >= data.cap;
                const hasPassed = data.event_has_passed;
                
                if (data.is_participant) {
                    // User is already a participant - show leave button
                    leaveBtn.style.display = 'inline-block';
                    leaveBtn.onclick = function() {
                        leaveEvent(data.eid);
                    };
                } else if (hasPassed) {
                    // Event has passed, show message
                    const passedMsg = document.createElement('p');
                    passedMsg.className = 'event-status-message';
                    passedMsg.textContent = 'This event has passed!';
                    eventActions.appendChild(passedMsg);
                } else if (!isFull) { // User not participant, event not full
                    // show join button
                    joinBtn.style.display = 'inline-block';
                    joinBtn.onclick = function() {
                        joinEvent(data.eid);
                    };
                } else {
                    // Event is full
                    const fullMsg = document.createElement('p');
                    fullMsg.className = 'event-full-message';
                    fullMsg.textContent = 'This event is full';
                    eventActions.appendChild(fullMsg);
                }
            }

            // Show panel with slide-in animation (if not already open)
            if (!panel.classList.contains('panel-open')) {
                panel.classList.add('panel-open');
            }
            panel.setAttribute('aria-hidden', 'false');

            // Load forum comments if function exists
            if (typeof loadForumComments === 'function') {
                loadForumComments(data.eid, data.logged_in);
            }
        })
        .catch(error => {
            console.error('Error loading event:', error);
            alert('Failed to load event details. Error: ' + error.message);
        });
}

function deleteEvent(eventId) {
    fetch(`/api/event/${eventId}/delete`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close the panel and reload the page to update the calendar
            closeEventPanel();
            window.location.reload();
        } else {
            alert(data.error || 'Failed to delete event');
        }
    })
    .catch(error => {
        console.error('Error deleting event:', error);
        alert('Failed to delete event');
    })
}

function closeEventPanel() {
    const panel = document.getElementById('event-panel');
    panel.classList.remove('panel-open');
    panel.setAttribute('aria-hidden', 'true'); 
}


// =================================
// FORUM FUNCTIONALITY FOR CALENDAR
// =================================


// Load forum comments for an event
function loadForumComments(eventId, loggedIn) {
    fetch(`/api/event/${eventId}/forum`)
        .then(response => response.json())
        .then(data => {
            const commentsContainer = 
                document.getElementById('forum-comments');
            const commentFormContainer = 
                document.getElementById('comment-form-container');
            const forumLoginPrompt = 
                document.getElementById('forum-login-prompt');
            
            // Show/hide comment form based on login status
            if (loggedIn) {
                commentFormContainer.style.display = 'block';
                forumLoginPrompt.style.display = 'none';
                
                // Set up comment submission
                const submitBtn = 
                    document.getElementById('submit-comment-btn');
                submitBtn.onclick = function() {
                    submitComment(eventId);
                };
            } else {
                commentFormContainer.style.display = 'none';
                forumLoginPrompt.style.display = 'block';
            }
            
            // Display comments
            if (data.comments && data.comments.length > 0) {
                commentsContainer.innerHTML = '';
                data.comments.forEach(comment => {
                    const commentDiv = 
                        createCommentElement(comment, data.current_uid);
                    commentsContainer.appendChild(commentDiv);
                });
            } else {
                commentsContainer.innerHTML = '';
                const placeholder = document.createElement('p');
                placeholder.className = 'placeholder-text';
                placeholder.textContent = 
                    'No comments yet. Be the first to share your thoughts!';
                commentsContainer.appendChild(placeholder);
            }
        })
        .catch(error => {
            console.error('Error loading forum comments:', error);
            const commentsContainer = 
                document.getElementById('forum-comments');
            commentsContainer.innerHTML = '';
            const errorMsg = document.createElement('p');
            errorMsg.className = 'comment-error-message';
            errorMsg.textContent = 'Failed to load comments.';
            commentsContainer.appendChild(errorMsg);
        });
}

// Create a comment element
function createCommentElement(comment, currentUid) {
    const commentDiv = document.createElement('div');
    commentDiv.className = 'forum-comment';
    
    // Comment header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'forum-comment-header';
    
    const authorSpan = document.createElement('span');
    authorSpan.className = 'forum-comment-author';
    authorSpan.textContent = comment.author_name;
    
    const timeSpan = document.createElement('span');
    timeSpan.className = 'forum-comment-time';
    timeSpan.textContent = formatCommentTime(comment.postedAt);
    
    headerDiv.appendChild(authorSpan);
    headerDiv.appendChild(timeSpan);
    
    // Comment text
    const textP = document.createElement('p');
    textP.className = 'forum-comment-text';
    textP.textContent = comment.text;
    
    commentDiv.appendChild(headerDiv);
    commentDiv.appendChild(textP);
    
    // Add delete button if user owns the comment
    if (currentUid && comment.author_uid === currentUid) {
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'action-btn delete-btn';
        deleteBtn.onclick = function() {
            if (confirm(
                'Are you sure you want to delete this comment?')) {
                    deleteComment(comment.commId);
            }
        };
        commentDiv.appendChild(deleteBtn);
    }
    
    return commentDiv;
}

// Format comment timestamp
function formatCommentTime(timestamp) {
    if (!timestamp) return 'just now';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return 
        `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return 
        `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
}

// Submit a new comment
function submitComment(eventId) {
    const commentText = document.getElementById('comment-text').value.trim();
    
    if (!commentText) {
        alert('Please enter a comment');
        return;
    }
    
    fetch(`/api/event/${eventId}/forum/comment`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: commentText })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Clear the textarea
            document.getElementById('comment-text').value = '';
            // Reload comments
            loadForumComments(eventId, true);
        } else {
            alert(data.error || 'Failed to post comment');
        }
    })
    .catch(error => {
        console.error('Error posting comment:', error);
        alert('Failed to post comment');
    });
}

// Delete a comment
function deleteComment(commId) {
    fetch(`/api/comment/${commId}/delete`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload comments for current event
            if (window.currentEventId) {
                loadForumComments(window.currentEventId, true);
            }
        } else {
            alert(data.error || 'Failed to delete comment');
        }
    })
    .catch(error => {
        console.error('Error deleting comment:', error);
        alert('Failed to delete comment');
    });
}
