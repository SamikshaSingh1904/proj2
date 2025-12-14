/*
  event_forum.js
  Authors: Beatrix Kim, Bessie Li, Samiksha Singh

  Purpose:
    Handle threaded comments on event forum page
*/

document.addEventListener('DOMContentLoaded', function() {
    // Get event ID from the container
    const container = document.querySelector('.event-forum-container');
    const eventId = parseInt(container.dataset.eventId);
    const loggedIn = container.dataset.loggedIn === 'true';
    
    // Load comments on page load
    if (eventId) {
        loadForumComments(eventId, loggedIn);
    }

    // Handle delete event button on event forum page
    const deleteEventForm = document.getElementById('delete-event-form');
    if (deleteEventForm) {
        deleteEventForm.addEventListener('submit', function(e) {
            e.preventDefault();
            showConfirmModal(
                'Delete this event? This action cannot be undone.',
                () => {
                    // Submit the form after confirmation
                    deleteEventForm.submit();
                },
                'Delete Event'
            );
        });
    }

    // Handle leave event button
    const leaveEventForm = document.getElementById('leave-event-form');
    if (leaveEventForm) {
        leaveEventForm.addEventListener('submit', function(e) {
            e.preventDefault();
            showConfirmModal(
                'Are you sure you want to leave this event?',
                () => leaveEventForm.submit(),
                'Leave Event'
            );
        });
    }
});

// Load forum comments (reuse from calendar.js with slight modifications)
function loadForumComments(eventId, loggedIn) {
    fetch(`/api/event/${eventId}/forum`)
        .then(response => response.json())
        .then(data => {
            const commentsContainer = document.getElementById('comments-list');
            const commentCount = document.getElementById('comment-count');
            
            // Update comment count
            if (commentCount) {
                commentCount.textContent = data.comment_count || 0;
            }
            
            // Display threaded comments
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

                // Render top-level comments
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
                commentsContainer.innerHTML = `
                    <div class="empty-comments">
                        No comments yet. Be the first to comment!
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading comments:', error);
        });
}

// Create comment element with nested replies
function createCommentElement(comment, currentUid, loggedIn, 
                            eventId, childrenByParent) {
    const commentDiv = document.createElement('div');
    commentDiv.className = 'comment';
    commentDiv.dataset.commId = comment.commId;

    // Header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'comment-header';

    const authorInfo = document.createElement('div');
    authorInfo.className = 'comment-author-info';

    const authorSpan = document.createElement('span');
    authorSpan.className = 'comment-author';
    authorSpan.textContent = comment.author_name;

    const timeSpan = document.createElement('span');
    timeSpan.className = 'comment-time';
    timeSpan.textContent = formatCommentTime(comment.postedAt);

    authorInfo.appendChild(authorSpan);
    authorInfo.appendChild(timeSpan);
    headerDiv.appendChild(authorInfo);

    // Content
    const contentDiv = document.createElement('div');
    contentDiv.className = 'comment-content';
    contentDiv.textContent = comment.text;

    commentDiv.appendChild(headerDiv);
    commentDiv.appendChild(contentDiv);

    // Actions div for reply and delete (below content)
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'comment-actions';

    // Reply button
    if (loggedIn) {
        const replyBtn = document.createElement('button');
        replyBtn.textContent = 'Reply';
        replyBtn.className = 'btn-reply';
        replyBtn.onclick = function() {
            showInlineReplyForm(commentDiv, comment.commId, eventId);
        };
        actionsDiv.appendChild(replyBtn);
    }

    // Delete button
    if (currentUid && comment.author_uid === currentUid) {
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'delete-comment-btn';
        deleteBtn.onclick = function() {
            showConfirmModal(
                'Delete this comment? This action cannot be undone.',
                () => deleteComment(comment.commId, eventId),
                'Delete Comment'
            );
        };
        actionsDiv.appendChild(deleteBtn);
    }

    commentDiv.appendChild(actionsDiv);

    // Nested replies container
    const repliesContainer = document.createElement('div');
    repliesContainer.className = 'comment-replies';

    const children = 
        (childrenByParent && childrenByParent[comment.commId]) || [];
    children.forEach(child => {
        const childEl = createCommentElement(
            child,
            currentUid,
            loggedIn,
            eventId,
            childrenByParent
        );
        childEl.classList.add('comment-reply');
        repliesContainer.appendChild(childEl);
    });

    commentDiv.appendChild(repliesContainer);

    return commentDiv;
}

// Show inline reply form
function showInlineReplyForm(commentDiv, parentCommId, eventId) {
    // Remove any existing reply forms
    const existing = commentDiv.querySelector('.inline-reply-form');
    if (existing) {
        existing.remove();
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
    submitBtn.className = 'btn-reply';
    submitBtn.textContent = 'Submit';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'btn-cancel-reply';
    cancelBtn.textContent = 'Cancel';

    submitBtn.onclick = function() {
        const text = textarea.value.trim();
        if (!text) {
            showFlashMessage('Please enter a reply', 'error');
            return;
        }
        submitReply(parentCommId, eventId, text);
    };

    cancelBtn.onclick = function() {
        form.remove();
    };

    buttonContainer.appendChild(submitBtn);
    buttonContainer.appendChild(cancelBtn);
    
    form.appendChild(textarea);
    form.appendChild(buttonContainer);

    commentDiv.appendChild(form);
    textarea.focus();
}

// Submit reply
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
            loadForumComments(eventId, true);
        } else {
            showFlashMessage(
                data.error || 'Failed to post reply', 'error');
        }
    })
    .catch(error => {
        console.error('Error posting reply:', error);
        showFlashMessage('Failed to post reply', 'error');
    });
}

// Delete comment
function deleteComment(commId, eventId) {
    fetch(`/api/comment/${commId}/delete`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadForumComments(eventId, true);
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

// Format comment time
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

// Handle main comment form submission
const mainCommentForm = document.getElementById('main-comment-form');
if (mainCommentForm) {
    mainCommentForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const eventId = parseInt(document.body.dataset.eventId);
        const textarea = document.getElementById('comment-text');
        const text = textarea.value.trim();
        
        if (!text) {
            showFlashMessage('Please enter a comment', 'error');
            return;
        }
        
        fetch(`/api/event/${eventId}/forum/comment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: text })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                textarea.value = '';
                loadForumComments(eventId, true);
            } else {
                showFlashMessage(
                    data.error || 'Failed to post comment', 'error');
            }
        })
        .catch(error => {
            console.error('Error posting comment:', error);
            showFlashMessage('Failed to post comment', 'error');
        });
    });
}