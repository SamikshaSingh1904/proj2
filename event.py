"""
event.py - Database functions for event operations
authors: clump
"""
import cs304dbi as dbi

def format_time(time_delta):
    """Convert timedelta (from MySQL TIME) to time string"""
    if time_delta is None:
        return 'TBD'
    total_seconds = int(time_delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    period = 'AM' if hours < 12 else 'PM'
    display_hours = hours % 12
    if display_hours == 0:
        display_hours = 12
    return f'{display_hours:02d}:{minutes:02d} {period}'

def get_week_events(conn, start_date, end_date):
    """
    Fetch all events for a given week
    Returns list of event dictionaries with formatted times
    """
    curs = dbi.dict_cursor(conn)
    
    query = '''
        SELECT e.eid, e.title, e.start, e.end, e.date, e.desc,
               e.city, e.state, e.cap, c.category
        FROM events e
        JOIN calendar c ON e.cid = c.cid
        WHERE e.date BETWEEN %s AND %s
        ORDER BY e.date, e.start
    '''

    print(
        f"DEBUG event.py: Querying events between {start_date} and {end_date}"
    )
    curs.execute(query, (start_date, end_date))
    events = curs.fetchall()
    
    # Format times for display
    for event in events:
        event['start_formatted'] = format_time(event['start'])
        event['end_formatted'] = format_time(event['end'])
    
    return events

def get_event_by_id(conn, eid):
    """
    Get full details of a specific event including creator info
    Returns event dictionary or None if not found
    """
    curs = dbi.dict_cursor(conn)
    
    query = '''
        SELECT e.eid, e.title, e.start, e.end, e.date, e.desc,
               e.city, e.state, e.cap, e.flexible, e.addedBy,
               p.name as creator_name, c.category
        FROM events e
        JOIN person p ON e.addedBy = p.uid
        JOIN calendar c ON e.cid = c.cid
        WHERE e.eid = %s
    '''
    
    curs.execute(query, (eid,))
    return curs.fetchone()

def get_event_participants(conn, eid):
    """
    Get all participants for a specific event
    Returns list of participant dictionaries
    """
    curs = dbi.dict_cursor(conn)
    
    query = '''
        SELECT p.uid, p.name, p.year, p.pronouns
        FROM participants pa
        JOIN person p ON pa.uid = p.uid
        WHERE pa.eid = %s
        ORDER BY p.name
    '''
    
    curs.execute(query, (eid,))
    return curs.fetchall()

def delete_event_by_id(conn, eid):
    """Delete an event from the database"""
    curs = dbi.dict_cursor(conn)
    curs.execute('DELETE FROM events WHERE eid = %s', [eid])
    conn.commit()

def update_event(conn, eid, title, desc, date, start, 
                 end, city, state, cap, flexible, cid):
    """Update an existing event in the database"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        UPDATE events 
        SET title=%s, `desc`=%s, date=%s, start=%s, end=%s, 
            city=%s, state=%s, cap=%s, flexible=%s, cid=%s
        WHERE eid=%s
    ''', [title, desc, date, start, end, city, state, cap, flexible, cid, eid])
    conn.commit()

def get_participant_count(conn, eid):
    """
    Get current number of participants for an event
    Returns integer count
    """
    curs = dbi.cursor(conn)
    
    query = 'SELECT COUNT(*) FROM participants WHERE eid = %s'
    curs.execute(query, (eid,))
    return curs.fetchone()[0]