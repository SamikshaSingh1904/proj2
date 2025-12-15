/*
  calendar.js
  Authors: Beatrix Kim, Bessie Li, Samiksha Singh

  Purpose:
    Displays events on a weekly calendar grid and allows users to
    view, join, leave, edit, and delete events through a detail panel.
*/



// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
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

/**
 * Update navigation based on login status
 */
function updateNavigation(loggedIn) {
    const navRight = document.querySelector('.nav-right ul');
    if (!navRight) return;
    
    if (loggedIn) {
        navRight.innerHTML = `
            <li><a href="/profile">Profile</a></li>
            <li><a href="/logout">Logout</a></li>
        `;
    } else {
        navRight.innerHTML = `
            <li><a href="/login">Login</a></li>
            <li><a href="/signup">Sign Up</a></li>
        `;
    }
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

            const photoEl = document.getElementById('panel-event-photo');
            if (photoEl) {
                if (data.photo_url) {
                    photoEl.src = data.photo_url;
                    photoEl.style.display = 'block';
                } else {
                    photoEl.removeAttribute('src');
                    photoEl.style.display = 'none';
                }
            }
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
                    showConfirmModal(
                        'Delete this event? This action cannot be undone.',
                        () => deleteEvent(data.eid),
                        'Delete Event'
                    );
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
            showFlashMessage('Failed to load event details', 'error');
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
            showFlashMessage(data.error || 'Failed to delete event', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting event:', error);
        showFlashMessage('Failed to delete event', 'error');
    })
}

function joinEvent(eventId) {
    fetch(`/api/event/${eventId}/join`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload the event panel to show updated participant list
            openEventPanel(eventId);
        } else {
            showFlashMessage(data.error || 'Failed to join event', 'error');
        }
    })
    .catch(error => {
        console.error('Error joining event:', error);
        showFlashMessage('Failed to join event', 'error');
    });
}

// Leave an event
function leaveEvent(eventId) {
    showConfirmModal(
        'Are you sure you want to leave this event?',
        () => {
            fetch(`/api/event/${eventId}/leave`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload event panel to show updated participant list
                    openEventPanel(eventId);
                } else {
                    showFlashMessage(
                        data.error || 'Failed to leave event', 'error');
                }
            })
            .catch(error => {
                console.error('Error leaving event:', error);
                showFlashMessage('Failed to leave event', 'error');
            });
        },
    'Leave Event'
    );
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

            // Display comments (threaded: parents + replies)
            if (data.comments && data.comments.length > 0) {
                commentsContainer.innerHTML = '';

                // Build parent → children map
                const childrenByParent = {};
                data.comments.forEach(comment => {
                    const parent = comment.parent_commId || null;
                    if (!childrenByParent[parent]) {
                        childrenByParent[parent] = [];
                    }
                    childrenByParent[parent].push(comment);
                });

                // Render top-level comments (parent_commId = null)
                const topLevel = childrenByParent[null] || [];
                topLevel.forEach(comment => {
                    const commentDiv = createCommentElement(
                        comment,
                        data.current_uid,
                        loggedIn,
                        eventId,
                        childrenByParent
                    );
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

// Create a comment element (with nested replies)
function createCommentElement(comment, currentUid, loggedIn, 
                            eventId, childrenByParent) {
    // Wrapper holds comment + timestamp (NOT replies)
    const wrapper = document.createElement('div');
    wrapper.className = 'forum-comment-wrapper';
    wrapper.style.position = 'relative';
    wrapper.style.marginBottom = '1rem';
    
    const commentDiv = document.createElement('div');
    commentDiv.className = 'forum-comment';
    commentDiv.dataset.commId = comment.commId;

    // Header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'forum-comment-header';

    const authorSpan = document.createElement('span');
    authorSpan.className = 'forum-comment-author';
    authorSpan.textContent = comment.author_name;

    headerDiv.appendChild(authorSpan);

    // Actions (reply + delete)
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'forum-comment-actions';

    if (loggedIn) {
        const replyBtn = document.createElement('button');
        replyBtn.textContent = 'Reply';
        replyBtn.className = 'action-btn reply-btn';
        replyBtn.onclick = function () {
            showInlineReplyForm(commentDiv, comment.commId, eventId);
        };
        actionsDiv.appendChild(replyBtn);
    }

    if (currentUid && comment.author_uid === currentUid) {
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'action-btn delete-btn';
        deleteBtn.onclick = function () {
            showConfirmModal(
                'Delete this comment? This action cannot be undone.',
                () => deleteComment(comment.commId),
                'Delete Comment'
            );
        };
        actionsDiv.appendChild(deleteBtn);
    }

    headerDiv.appendChild(actionsDiv);

    // Text
    const textP = document.createElement('p');
    textP.className = 'forum-comment-text';
    textP.textContent = comment.text;

    commentDiv.appendChild(headerDiv);
    commentDiv.appendChild(textP);

    // Timestamp - goes in wrapper
    const timeSpan = document.createElement('span');
    timeSpan.className = 'forum-comment-time';
    const formattedTime = formatCommentTime(comment.postedAt);
    timeSpan.textContent = formattedTime;
    
    // Add comment and timestamp to wrapper
    wrapper.appendChild(commentDiv);
    wrapper.appendChild(timeSpan);

    // CONTAINER for this comment + its replies
    const container = document.createElement('div');
    container.className = 'forum-comment-container';
    container.appendChild(wrapper);

    // Replies go AFTER the wrapper, in a separate div
    const children = 
        (childrenByParent && childrenByParent[comment.commId]) || [];
    if (children.length > 0) {
        const repliesContainer = document.createElement('div');
        repliesContainer.className = 'forum-replies';
        
        children.forEach(child => {
            const childEl = createCommentElement(
                child,
                currentUid,
                loggedIn,
                eventId,
                childrenByParent
            );
            repliesContainer.appendChild(childEl);
        });
        
        container.appendChild(repliesContainer);
    }

    return container;
}

// Show an inline reply form under a comment
function showInlineReplyForm(commentDiv, parentCommId, eventId) {
    // Avoid adding multiple reply forms under the same comment
    if (commentDiv.querySelector('.inline-reply-form')) {
        return;
    }

    const form = document.createElement('div');
    form.className = 'inline-reply-form';

    const textarea = document.createElement('textarea');
    textarea.className = 'reply-textarea';
    textarea.placeholder = 'Write a reply...';
    textarea.rows = 2;

    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'reply-form-actions';

    const submitBtn = document.createElement('button');
    submitBtn.type = 'button';
    submitBtn.className = 'action-btn reply-btn';
    submitBtn.textContent = 'Submit';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'action-btn cancel-reply-btn';
    cancelBtn.textContent = 'Cancel';

    // Hide the action buttons when form is shown
    const actionsDiv = commentDiv.querySelector('.forum-comment-actions');
    if (actionsDiv) {
        actionsDiv.style.display = 'none';
    }

    submitBtn.onclick = function() {
        const text = textarea.value.trim();
        if (!text) {
            showFlashMessage('Please enter a reply', 'error');
            return;
        }
        submitReply(parentCommId, eventId, text);
    };

    cancelBtn.onclick = function() {
        // Show the action buttons again when form is cancelled
        if (actionsDiv) {
            actionsDiv.style.display = 'flex';
        }
        form.remove();
    };

    buttonContainer.appendChild(submitBtn);
    buttonContainer.appendChild(cancelBtn);
    
    form.appendChild(textarea);
    form.appendChild(buttonContainer);

    commentDiv.appendChild(form);
    textarea.focus();
}

// Send reply via AJAX and reload comments (no full page refresh)
function submitReply(parentCommId, eventId, text) {
    fetch(`/api/comment/${parentCommId}/reply`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin',
        body: JSON.stringify({ text: text })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload all comments for this event (still no page reload)
            loadForumComments(eventId, true);
        } else {
            showFlashMessage(data.error || 'Failed to post reply', 'error');
        }
    })
    .catch(error => {
        console.error('Error posting reply:', error);
        showFlashMessage('Failed to post reply', 'error');
    });
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
    if (diffMins < 60) {
        return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    }
    if (diffHours < 24) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    }
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
}

// Submit a new comment
function submitComment(eventId) {
    const commentText = document.getElementById('comment-text').value.trim();
    
    if (!commentText) {
        showFlashMessage('Please enter a comment', 'error');
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
            showFlashMessage(data.error || 'Failed to post comment', 'error');
        }
    })
    .catch(error => {
        console.error('Error posting comment:', error);
        showFlashMessage('Failed to post comment', 'error');
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
            showFlashMessage(
                data.error || 'Failed to delete comment', 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting comment:', error);
        showFlashMessage('Failed to delete comment', 'error');
    });
}
