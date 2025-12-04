"""
clump: Flask web app for Wellesley students to clump together and plan events.
Authors: clump 

Features:
- Weekly calendar of events (public)
- Login / signup and user profiles
- Create / join events and view participants
- Event forums with comments and JSON API for AJAX
"""

from flask import (Flask, render_template, make_response, url_for, request,
                   redirect, flash, session, send_from_directory, jsonify)
from werkzeug.utils import secure_filename
app = Flask(__name__)

import secrets
import cs304dbi as dbi
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import event as e 
import form
import forum as forum_db
import bcrypt
import password as password_db

# we need a secret_key to use flash() and sessions
app.secret_key = secrets.token_hex()

# configure DBI
print(dbi.conf('clump_db'))

# This gets better error messages for certain common request errors
app.config['TRAP_BAD_REQUEST_ERRORS'] = True

# =================
# HELPER FUNCTIONS 
# =================

# Helper function to get connection
def get_conn():
    """Get database connection"""
    return dbi.connect()

# Helper function to require login
def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'uid' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========
# APP ROUTES
# ==========

@app.route('/')
def index():
    """Redirects to calendar home"""
    return redirect(url_for('calendar'))

@app.route('/about/')
def about():
    """Redirects to about page"""
    return render_template('about.html', page_title='About')

@app.route('/calendar/')
@app.route('/calendar/<date_str>')
def calendar(date_str=None):
    ''' Main calendar view - PUBLIC (no login required)
    date_str format: YYYY-MM-DD 
    Renders template for the calendar!
    '''
    conn = dbi.connect()

    if date_str: # Manual URL entry
        try:
            # Parse the date from URL
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format')
            return redirect(url_for('calendar'))
    else:
        # No date specified, default to today
        target_date = datetime.now().date()

    # Find the most recent Sunday
    days_since_sunday = (target_date.weekday() + 1) % 7
    start_of_week = target_date - timedelta(days=days_since_sunday)
    end_of_week = start_of_week + timedelta(days=6)
    
    # Fetch ALL events for the week
    events = e.get_week_events(conn, start_of_week, end_of_week)

    # Get today's date for highlighting
    today = datetime.now().date()

    # Get logged in status
    logged_in = 'uid' in session
    
    return render_template('calendar.html', 
                         page_title='Calendar Home',
                         events=events,
                         week_start=start_of_week,
                         week_end=end_of_week,
                         today=today,
                         logged_in=logged_in,
                         datetime=datetime,
                         timedelta=timedelta)

@app.route('/create_event/', methods=['GET', 'POST'])
@login_required
def create_event():
    '''
    Shows the Create Event form (GET) and handles form submission (POST).
    - GET: fetches categories and displays the blank form.
    - POST: validates required fields, inserts the event into the database,
            auto-adds the creator as a participant, then redirects to calendar.
    '''
    conn = get_conn()
    uid = session['uid'] 

    #fetch category options for the drop down 
    categories = form.get_categories(conn)

    #get shows an empty form 
    if request.method == 'GET':
        return render_template('create_event.html',
                               page_title='Create Event',
                               categories=categories)

    #post reads the information from the form
    title = request.form.get('event-title', '').strip()
    date_str = request.form.get('event-date', '').strip()
    start_str = request.form.get('event-start', '').strip()
    end_str = request.form.get('event-end', '').strip()
    city = request.form.get('event-city', '').strip()
    state = request.form.get('event-state', '').strip()
    desc = request.form.get('event-desc', '').strip()
    cap_str = request.form.get('event-cap', '').strip()
    cid_str = request.form.get('event-cid', '').strip()

    error = False

    #required field checks 
    if not title:
        flash("Title is required.", 'error')
        error = True
    if not date_str:
        flash("Date is required.", 'error')
        error = True
    if not start_str:
        flash("Start time is required.", 'error')
        error = True
    if not end_str:
        flash("End time is required.", 'error')
        error = True
    if not city:
        flash("City is required.", 'error')
        error = True
    if not state:
        flash("State is required.", 'error')
        error = True
    if not cid_str:
        flash("Category is required.", 'error')
        error = True

    #capacity handling that defaults to 10 
    cap = None
    if cap_str:
        if cap_str.isnumeric():
            cap = int(cap_str)
            if cap < 0:
                flash("Capacity must be non-negative.", 'error')
                error = True
        else:
            flash("Capacity must be a non-negative integer.", 'error')
            error = True
    else:
        cap = 10

    #checking valid category 
    cid = None
    if cid_str:
        if cid_str.isnumeric():
            cid = int(cid_str)
        else:
            flash("Invalid category.", 'error')
            error = True

    #if any errors, re-render the form with previous values 
    if error:
        return render_template(
            'create_event.html',
            page_title='Create Event',
            categories=categories,
            title=title,
            date=date_str,
            start=start_str,
            end=end_str,
            city=city,
            state=state,
            desc=desc,
            cap=cap_str,
            cid=cid
        )
    
    # Get flexible checkbox value
    flexible = request.form.get('event-flexible') == 'on'

    #insert event and auto-add creator 
    eid = form.insert_event(
        conn,
        title, date_str, start_str, end_str,
        desc, uid, city, state, cap, 
        flexible=flexible, cid=cid
    )

    form.add_participant(conn, eid, uid)

    flash("Event created and you have been added as a participant.", 'success')
    return redirect(url_for('calendar'))

@app.route('/forum')
def forum():
    """Display main forum page with all events and their forums"""
    try:
        conn = get_conn()

        # Get show_past parameter from query string (default False)
        show_past = request.args.get('show_past', 'false').lower() == 'true'
        
        # Get all events with their forums
        events = forum_db.get_all_events_with_forums(conn, show_past)
        
        # Get comment count for each event's forum
        for evt in events:
            evt['start_formatted'] = e.format_time(evt.get('start'))
            evt['end_formatted'] = e.format_time(evt.get('end'))
            evt['comment_count'] = forum_db.get_comment_count(conn, evt['fid'])
        
        return render_template('forum.html', 
                               page_title='Forum', 
                               events=events, 
                               show_past=show_past)
    
    except Exception as ex:
        flash(f'Error loading forum: {str(ex)}', 'error')
        return render_template('forum.html', 
                               page_title='Forum', 
                               events=[], 
                               show_past=False)

@app.route('/forum/event/<int:eid>')
def view_event_forum(eid):
    """View a specific event with its forum and comments"""
    try:
        conn = get_conn()
        
        # Get event details
        evt = forum_db.get_event_details(conn, eid)
        
        if not evt:
            flash('Event not found', 'error')
            return redirect(url_for('forum'))

        # Format times using the 'event' module
        evt['start_formatted'] = e.format_time(evt.get('start'))
        evt['end_formatted'] = e.format_time(evt.get('end'))
        
        # Get participants
        participants = forum_db.get_event_participants(conn, eid)
        evt['participants'] = participants
        evt['participant_count'] = len(participants)
        
        # Get comments for this forum
        comments = forum_db.get_forum_comments(conn, evt['fid'])

        # Get today's date for comparison
        today = datetime.now().date()

        # Determine back URL (where they came from)
        referrer = request.referrer
        # If they came from clump, use that; otherwise default to forum
        back_url = (referrer if referrer and request.host in referrer
                    else url_for('forum'))
        
        return render_template('event_forum.html', 
                               page_title='Event Forum', 
                               event=evt, 
                               comments=comments,
                               today=today,
                               back_url=back_url)
    
    except Exception as ex:
        flash(f'Error loading event forum: {str(ex)}', 'error')
        return redirect(url_for('forum'))

@app.route('/forum/event/<int:eid>/comment', methods=['POST'])
@login_required
def add_comment_to_event(eid):
    """Add a comment to an event's forum"""
    try: 
        text = request.form.get('text')
        
        if not text or not text.strip():
            flash('Comment cannot be empty', 'error')
            return redirect(url_for('view_event_forum', eid=eid))
        
        conn = get_conn()
        
        # Get the forum id for this event
        fid = forum_db.get_forum_id_by_event(conn, eid)
        
        if not fid:
            flash('Forum not found', 'error')
            return redirect(url_for('forum'))
        
        # Insert the comment - database handles the ID
        forum_db.insert_comment(conn, text, session['uid'], fid)
        
        flash('Comment added!', 'success')
        return redirect(url_for('view_event_forum', eid=eid))
    
    except Exception as ex:
        flash(f'Error adding comment: {str(ex)}', 'error')
        return redirect(url_for('view_event_forum', eid=eid))
    
@app.route('/forum/event/<int:eid>/join', methods=['POST'])
@login_required
def join_event(eid):
    """Join an event"""
    try:        
        conn = get_conn()
        
        # Check if event exists and has capacity
        event = forum_db.get_event_capacity_info(conn, eid)
        
        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('forum'))
        
        # Check if event date has passed
        if event['date'] < datetime.now().date():
            flash('Cannot join past events', 'error')
            return redirect(url_for('view_event_forum', eid=eid))
        
        # Check if already joined
        if forum_db.is_user_participant(conn, eid, session['uid']):
            flash('You have already joined this event', 'error')
            return redirect(url_for('view_event_forum', eid=eid))
        
        # Attempt to add participant (checks capacity atomically)
        success = forum_db.add_participant(conn, eid, session['uid'])
        
        if success:
            flash('Successfully joined the event!', 'success')
        else:
            flash('Event is full', 'error')
            
        return redirect(url_for('view_event_forum', eid=eid))
    
    except Exception as ex:
        flash(f'Error joining event: {str(ex)}', 'error')
        return redirect(url_for('view_event_forum', eid=eid))
    
@app.route('/forum/event/<int:eid>/leave', methods=['POST'])
@login_required
def leave_event(eid):
    """Leave an event as a participant"""
    try:
        conn = get_conn()
        
        # Check if user is the event creator
        creator_uid = forum_db.get_event_creator(conn, eid)
        
        if creator_uid and creator_uid == session['uid']:
            flash('Event creators cannot leave their own events', 'error')
            return redirect(url_for('view_event_forum', eid=eid))
        
        # Remove participant
        forum_db.remove_participant(conn, eid, session['uid'])
        
        flash('Successfully left the event', 'success')
        return redirect(url_for('view_event_forum', eid=eid))
    
    except Exception as ex:
        flash(f'Error leaving event: {str(ex)}', 'error')
        return redirect(url_for('view_event_forum', eid=eid))

@app.route('/event/<int:eid>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(eid):
    """Edit an event (only for creator)"""
    conn = get_conn()

    #fetch category options for the drop down 
    categories = form.get_categories(conn)
    
    # Get event and check if user is the creator
    event = e.get_event_by_id(conn, eid)
    
    if not event:
        flash('Event not found', 'error')
        return redirect(url_for('forum'))
    
    if event['addedBy'] != session['uid']:
        flash('You can only edit your own events', 'error')
        return redirect(url_for('view_event_forum', eid=eid))
    
    if request.method == 'POST':
        # Handle the edit form submission, update event, and
        # redirect back to event page
        # Get form data
        title = request.form.get('title').strip()
        desc = request.form.get('desc').strip()
        date_str = request.form.get('date').strip()
        start_str = request.form.get('start').strip()
        end_str = request.form.get('end').strip()
        city = request.form.get('city').strip()
        state = request.form.get('state').strip()
        cap_str = request.form.get('cap').strip()
        flexible = request.form.get('flexible') == 'on'
        cid_str = request.form.get('cid').strip()

        error = False

        #required field checks 
        if not title:
            flash("Title is required.", 'error')
            error = True
        if not date_str:
            flash("Date is required.", 'error')
            error = True
        if not start_str:
            flash("Start time is required.", 'error')
            error = True
        if not end_str:
            flash("End time is required.", 'error')
            error = True
        if not city:
            flash("City is required.", 'error')
            error = True
        if not state:
            flash("State is required.", 'error')
            error = True
        if not cid_str:
            flash("Category is required.", 'error')
            error = True

        #capacity handling that defaults to 10 
        cap = None
        if cap_str:
            if cap_str.isnumeric():
                cap = int(cap_str)
                if cap < 0:
                    flash("Capacity must be non-negative.", 'error')
                    error = True
            else:
                flash("Capacity must be a non-negative integer.", 'error')
                error = True
        else:
            cap = 10

        #checking valid category 
        cid = None
        if cid_str:
            if cid_str.isnumeric():
                cid = int(cid_str)
            else:
                flash("Invalid category.", 'error')
                error = True

        #if any errors, re-render the form with previous values 
        if error:
            # Update event object with form data to preserve user input
            event['title'] = title
            event['desc'] = desc
            event['date'] = date_str
            event['start'] = start_str
            event['end'] = end_str
            event['city'] = city
            event['state'] = state
            event['cap'] = cap
            event['cid'] = cid

            return render_template(
                'edit_event.html', 
                page_title='Edit Event',
                categories=categories,
                event=event
            )
        
        # Update event in database
        e.update_event(conn, eid, title, desc, date_str, start_str, end_str, 
                       city, state, cap, flexible, cid)
        
        flash('Event updated successfully', 'success')
        return redirect(url_for('view_event_forum', eid=eid))
    
    # GET request - show edit form  
    return render_template('edit_event.html', 
                          page_title='Edit Event',
                          event=event, 
                          categories=categories)
    
@app.route('/forum/event/<int:eid>/delete', methods=['POST'])
@login_required
def delete_event(eid):
    """Delete an event (only for creator of event)"""
    try:        
        conn = get_conn()
        
        # Get event and check if user is the creator
        event = e.get_event_by_id(conn, eid)
        
        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('forum'))
        
        if event['addedBy'] != session['uid']:
            flash('You can only delete your own events', 'error')
            return redirect(url_for('view_event_forum', eid=event['eid']))
        
        # Delete event
        e.delete_event_by_id(conn, eid)
        
        flash('Event deleted successfully', 'success')
        return redirect(url_for('forum'))
    
    except Exception as ex:
        flash(f'Error deleting event: {str(ex)}', 'error')
        return redirect(url_for('forum'))

@app.route('/forum/comment/<int:commId>/delete', methods=['POST'])
@login_required
def delete_comment(commId):
    """Delete a comment (only by creator)"""
    try:        
        conn = get_conn()
        
        # Get comment and check if user is the creator
        comment = forum_db.get_comment_info(conn, commId)
        
        if not comment:
            flash('Comment not found', 'error')
            return redirect(url_for('forum'))
        
        if comment['addedBy'] != session['uid']:
            flash('You can only delete your own comments', 'error')
            return redirect(url_for('view_event_forum', eid=comment['eid']))
        
        # Delete comment
        forum_db.delete_comment_by_id(conn, commId)
        
        flash('Comment deleted successfully', 'success')
        return redirect(url_for('view_event_forum', eid=comment['eid']))
    
    except Exception as ex:
        flash(f'Error deleting comment: {str(ex)}', 'error')
        return redirect(url_for('forum'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return redirect(url_for('login'))
        
        try:
            conn = get_conn()
            
            # Get user by email
            user = password_db.get_user_by_email(conn, email)
            
            if user:
                # Check password using bcrypt
                stored_hash = user['pass']
                # Convert password to bytes if it's a string
                if isinstance(password, str):
                    password = password.encode('utf-8')
                # Convert stored hash to bytes if it's a string
                if isinstance(stored_hash, str):
                    stored_hash = stored_hash.encode('utf-8')
                
                if bcrypt.checkpw(password, stored_hash):
                    # Login successful
                    session['uid'] = user['uid']
                    session['name'] = user['name']
                    session['email'] = user['email']
                    flash(f'Welcome back, {user["name"]}!', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Invalid email or password', 'error')
                    return redirect(url_for('login'))
            else:
                flash('Invalid email or password', 'error')
                return redirect(url_for('login'))
        
        except Exception as ex:
            flash(f'Login error: {str(ex)}', 'error')
            return redirect(url_for('login'))
    
    # GET request - show login form
    return render_template('login.html', page_title='Login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        year = request.form.get('year')
        if year and year.strip():
            year = int(year)
        else:
            year = None
        pronouns = request.form.get('pronouns', None)
        bio = request.form.get('bio', '')
        
        # Validation
        if not all([name, email, password, confirm_password]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('signup'))
        
        # Check Wellesley email
        if not email.endswith('@wellesley.edu'):
            flash('Please use your Wellesley email address', 'error')
            return redirect(url_for('signup'))
        
        # Check password match
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
        
        # Check password length
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return redirect(url_for('signup'))
        
        try:
            conn = get_conn()
            
            # Hash password with bcrypt
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password_bytes, salt)
            
            # Insert new user - raises exception if email exists (thread-safe)
            # Exception caught per create_user() in password.py
            new_uid = password_db.create_user(conn, name, email, 
                                              hashed_password, 
                                             bio, year, pronouns)
            
            # Auto-login after signup
            session['uid'] = new_uid
            session['name'] = name
            session['email'] = email
            
            flash(f'Welcome to clump, {name}!', 'success')
            return redirect(url_for('index'))
        
        except Exception as ex:
            # MySQL duplicate entry error code
            is_mysql_duplicate = (
                hasattr(ex, 'args') 
                and len(ex.args) > 0 
                and ex.args[0] == 1062
            )

            if is_mysql_duplicate:
                flash('An account with this email already exists', 'error')
            else:
                flash(f'Signup error: {str(ex)}', 'error')

            return redirect(url_for('signup'))
    
    # GET request - show signup form
    return render_template('signup.html', page_title='Sign Up')

@app.route('/logout')
def logout():
    """Handle user logout"""
    name = session.get('name', 'User')
    session.clear()
    flash(f'Goodbye, {name}!', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """View user profile"""
    try:
        conn = get_conn()

        # Get show_past parameter (default False)
        show_past_created = request.args.get('show_past_created', 
                                             'false').lower() == 'true'
        show_past_joined = request.args.get('show_past_joined', 
                                            'false').lower() == 'true'
        
        # Get user info
        user = password_db.get_user_profile(conn, session['uid'])
        
        # Get user's events (as creator)
        created_events = password_db.get_user_created_events(conn, 
                                                             session['uid'],
                                                             show_past_created)
        
        # Get events user is participating in
        joined_events = password_db.get_user_joined_events(conn, 
                                                           session['uid'],
                                                           show_past_joined)

        # Format times for created events
        for evt in created_events:
            evt['start_formatted'] = e.format_time(evt.get('start'))
            evt['end_formatted'] = e.format_time(evt.get('end'))
        
        # Format times for joined events
        for evt in joined_events:
            evt['start_formatted'] = e.format_time(evt.get('start'))
            evt['end_formatted'] = e.format_time(evt.get('end'))
        
        return render_template('profile.html', 
                             page_title='Profile',
                             user=user,
                             created_events=created_events,
                             joined_events=joined_events,
                             show_past_created=show_past_created,
                             show_past_joined=show_past_joined)
    
    except Exception as ex:
        flash(f'Error loading profile: {str(ex)}', 'error')
        return redirect(url_for('forum'))
    
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    '''Similar to edit_event - show form and handle updates'''
    conn = get_conn()
    
    # Get current user info
    user = password_db.get_user_profile(conn, session['uid'])
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        bio = request.form.get('bio', '').strip()
        year = request.form.get('year', '').strip()
        pronouns = request.form.get('pronouns', '').strip()
        
        error = False
        
        # Validation
        if not name:
            flash('Name is required', 'error')
            error = True
        
        if len(name) > 30:
            flash('Name must be 30 characters or less', 'error')
            error = True
        
        if bio and len(bio) > 100:
            flash('Bio must be 100 characters or less', 'error')
            error = True

        if pronouns and len(pronouns) > 30:
            flash('Pronouns must be 30 characters or less', 'error')
            error = True
        
        # Convert year to int or None
        year_int = None
        if year:
            if year.isnumeric():
                year_int = int(year)
            else:
                flash('Year must be a number', 'error')
                error = True
        
        if error:
            # Re-render with current form data
            user['name'] = name
            user['bio'] = bio
            user['year'] = year
            user['pronouns'] = pronouns
            return render_template('edit_profile.html',
                                 page_title='Edit Profile',
                                 user=user)
        
        # Update user profile in database
        password_db.update_user_profile(conn, session['uid'], 
                                       name, bio, year_int, pronouns)
        
        # Update session with new name
        session['name'] = name
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
    
    # GET request - show edit form
    return render_template('edit_profile.html', 
                          page_title='Edit Profile',
                          user=user)

@app.route('/profile/delete', methods=['POST'])
@login_required
def delete_account():
    '''Delete user account (will cascade delete their events)'''
    try:
        conn = get_conn()
        uid = session['uid']
        name = session.get('name', 'User')
        
        # Delete user (CASCADE will handle events, participants, comments)
        password_db.delete_user(conn, uid)
        
        # Clear session
        session.clear()
        
        flash(f'Your account has been deleted. Goodbye, {name}!', 'success')
        return redirect(url_for('index'))
    
    except Exception as ex:
        flash(f'Error deleting account: {str(ex)}', 'error')
        return redirect(url_for('profile'))

# =======================
# API ENDPOINTS FOR AJAX
# =======================

@app.route('/api/event/<int:eid>')
def get_event_details(eid):
    """
    (Public) API endpoint to get full details of a specific event
    given and event eid. Displays full event details and participant info,
    returning JSON for the event side panel
    """
    conn = dbi.connect()
    
    # Get event details using event.py module
    event_data = e.get_event_by_id(conn, eid)
    
    if not event_data: # If event DNE
        return jsonify({'error': 'Event not found'}), 404
    
    # Get all participants for event
    participants = e.get_event_participants(conn, eid)
    
    # Get participant count
    current_count = e.get_participant_count(conn, eid)

    # Check if current user is logged in AND is creator
    logged_in = 'uid' in session
    is_creator = logged_in and session.get('uid') == event_data['addedBy']
    is_participant = False

    if logged_in:
        # Check if user is already a participant
        is_participant = any(p['uid'] == session['uid'] for p in participants)
    
    # Check if event has passed
    event_has_passed = event_data['date'] < datetime.now().date()
    
    # Format the response
    response = {
        'eid': event_data['eid'],
        'title': event_data['title'],
        'date': event_data['date'].strftime('%A, %B %d, %Y'),
        'start': e.format_time(event_data['start']),
        'end': e.format_time(event_data['end']),
        'desc': event_data['desc'],
        'city': event_data['city'],
        'state': event_data['state'],
        'cap': event_data['cap'],
        'current_participants': current_count,
        'flexible': event_data['flexible'],
        'category': event_data['category'],
        'creator_name': event_data['creator_name'],
        'addedBy': event_data['addedBy'],
        'logged_in': logged_in,
        'is_creator': is_creator,
        'is_participant': is_participant,
        'event_has_passed': event_has_passed,
        'participants': [{
                'uid': p['uid'],
                'name': p['name'],
                'year': p['year'],
                'pronouns': p['pronouns']
            } for p in participants
        ]
    }
    return jsonify(response)

@app.route('/api/event/<int:eid>/delete', methods=['DELETE'])
@login_required
def delete_event_api(eid):
    """API endpoint to delete an event"""
    try:        
        conn = get_conn()
        
        # Get event and check if user is the creator
        event = e.get_event_by_id(conn, eid)
        
        if not event:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        
        if event['addedBy'] != session['uid']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Delete event
        e.delete_event_by_id(conn, eid)
        
        return jsonify({'success': True})
    
    except Exception as ex:
        return jsonify({'success': False, 'error': str(ex)}), 500
    
@app.route('/api/event/<int:eid>/join', methods=['POST'])
@login_required
def api_join_event(eid):
    """API endpoint to join an event"""
    try:        
        conn = get_conn()
        
        # Check if event exists and has capacity
        event = forum_db.get_event_capacity_info(conn, eid)
        
        if not event:
            return jsonify({'success': False, 'error': 
                            'Event not found'}), 404
        
        # Check if event date has passed
        if event['date'] < datetime.now().date():
            return jsonify({'success': False, 'error': 
                            'Cannot join past events'}), 400
        
        # Check if already joined
        if forum_db.is_user_participant(conn, eid, session['uid']):
            return jsonify({'success': False, 'error': 
                            'Already joined'}), 400
        
        # Attempt to add participant (checks capacity atomically)
        success = forum_db.add_participant(conn, eid, session['uid'])
        
        if success:
            return jsonify({'success': True, 'message': 
                            'Successfully joined event'})
        else:
            return jsonify({'success': False, 'error': 
                            'Event is full'}), 400
    
    except Exception as ex:
        return jsonify({'success': False, 'error': str(ex)}), 500

@app.route('/api/event/<int:eid>/leave', methods=['POST'])
@login_required
def api_leave_event(eid):
    """API endpoint to leave an event"""
    try:
        conn = get_conn()
        
        # Check if user is the event creator
        creator_uid = forum_db.get_event_creator(conn, eid)
        
        if creator_uid and creator_uid == session['uid']:
            return jsonify({'success': False, 'error': 
                            'You  cannot leave your own event'}), 403
        
        # Remove participant
        forum_db.remove_participant(conn, eid, session['uid'])
        
        return jsonify({'success': True, 'message': 'Successfully left event'})
    
    except Exception as ex:
        return jsonify({'success': False, 'error': str(ex)}), 500

@app.route('/api/event/<int:eid>/forum')
def get_event_forum(eid):
    """
    API endpoint to get forum comments for an event
    Returns JSON with forum data
    """
    try:
        conn = get_conn()
        
        # Get the forum id for this event
        fid = forum_db.get_forum_id_by_event(conn, eid)
        
        if not fid:
            return jsonify({'error': 'Forum not found'}), 404
        
        # Get comments for this forum
        comments = forum_db.get_forum_comments(conn, fid)
        
        # Format comments for JSON response
        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                'commId': comment['commId'],
                'text': comment['text'],
                'author_name': comment['author_name'],
                'author_uid': comment['author_uid'],
                'postedAt': (comment['postedAt'].isoformat() 
                             if comment['postedAt'] else None)
            })
        
        # Check if user is logged in
        logged_in = 'uid' in session
        current_uid = session.get('uid') if logged_in else None
        
        return jsonify({
            'fid': fid,
            'comments': formatted_comments,
            'logged_in': logged_in,
            'current_uid': current_uid,
            'comment_count': len(formatted_comments)
        })
    
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500

@app.route('/api/event/<int:eid>/forum/comment', methods=['POST'])
@login_required
def api_add_comment(eid):
    """
    API endpoint to add a comment to an event's forum
    """
    try:        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Comment cannot be empty'}), 400
        
        conn = get_conn()
        
        # Get the forum id for this event
        fid = forum_db.get_forum_id_by_event(conn, eid)
        
        if not fid:
            return jsonify({'error': 'Forum not found'}), 404
        
        # Get the next comment ID and insert the comment
        new_commId = forum_db.insert_comment(conn, text, session['uid'], fid)
        
        return jsonify({
            'success': True,
            'message': 'Comment added successfully',
            'commId': new_commId
        })
    
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500

@app.route('/api/comment/<int:commId>/delete', methods=['DELETE'])
@login_required
def api_delete_comment(commId):
    """
    API endpoint to delete a comment
    """
    try:
        conn = get_conn()
        
        # Get comment and check if user is the creator
        comment = forum_db.get_comment_info(conn, commId)
        
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        if comment['addedBy'] != session['uid']:
            return jsonify({
                'error': 'You can only delete your own comments'
                }), 403
        
        # Delete comment
        forum_db.delete_comment_by_id(conn, commId)
        
        return jsonify({
            'success': True,
            'message': 'Comment deleted successfully'
        })
    
    except Exception as ex:
        return jsonify({'error': str(ex)}), 500

# ===========================
# HELPER FILTER FOR TEMPLATES
# ===========================

@app.template_filter('time_ago')
def time_ago_filter(timestamp):
    """Format timestamp as 'X hours ago', 'X days ago', etc."""
    if not timestamp:
        return 'just now'
    
    from datetime import datetime, timezone
    
    # Make sure both are timezone-aware or both are naive
    if timestamp.tzinfo is not None:
        now = datetime.now(timezone.utc)
    else:
        now = datetime.now()
    
    diff = now - timestamp
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    else:
        days = int(seconds / 86400)
        return f'{days} day{"s" if days != 1 else ""} ago'


if __name__ == '__main__':
    import sys, os
    if len(sys.argv) > 1:
        # arg, if any, is the desired port number
        port = int(sys.argv[1])
        assert(port>1024)
    else:
        port = os.getuid()
    app.debug = True
    app.run('0.0.0.0',port)
