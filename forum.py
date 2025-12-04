"""
forum.py - Database query functions for forum functionality
authors: clump
"""
import cs304dbi as dbi


def get_all_events_with_forums(conn, show_past=False):
    """Get all events with their creator info, 
    forum info, and participant counts
    Args: show_past (bool): If True, include past events. 
    If False, only show upcoming/current events
    """
    curs = dbi.dict_cursor(conn)

    # Build query with optional date filter
    query = '''
        SELECT e.eid, e.title, e.desc, e.date, e.start, e.end,
               e.city, e.state, e.cap,
               p.name as creator_name, p.uid as creator_uid,
               c.category,
               f.fid,
               COUNT(DISTINCT part.uid) as participant_count
        FROM events e
        JOIN person p ON e.addedBy = p.uid
        JOIN calendar c ON e.cid = c.cid
        JOIN forum f ON e.eid = f.eid
        LEFT JOIN participants part ON e.eid = part.eid
    '''

    if not show_past:
        query += ' WHERE e.date >= CURDATE()'
    
    query += '''
        GROUP BY e.eid
        ORDER BY e.date ASC, e.start ASC
    '''
    
    curs.execute(query)
    return curs.fetchall()


def get_comment_count(conn, fid):
    """Get the number of comments for a forum"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT COUNT(*) as comment_count
        FROM comments
        WHERE fid = %s
    ''', [fid])
    result = curs.fetchone()
    return result['comment_count']


def get_event_details(conn, eid):
    """Get detailed information about a specific event"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT e.eid, e.title, e.desc, e.date, e.start, e.end,
               e.city, e.state, e.cap, e.flexible,
               p.name as creator_name, p.uid as creator_uid,
               c.category,
               f.fid
        FROM events e
        JOIN person p ON e.addedBy = p.uid
        JOIN calendar c ON e.cid = c.cid
        JOIN forum f ON e.eid = f.eid
        WHERE e.eid = %s
    ''', [eid])
    return curs.fetchone()


def get_event_participants(conn, eid):
    """Get all participants for an event"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT p.name, p.uid
        FROM participants part
        JOIN person p ON part.uid = p.uid
        WHERE part.eid = %s
    ''', [eid])
    return curs.fetchall()


def get_forum_comments(conn, fid):
    """Get all comments for a forum, ordered by posting time"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT co.commId, co.text, co.postedAt,
               p.name as author_name, p.uid as author_uid
        FROM comments co
        JOIN person p ON co.addedBy = p.uid
        WHERE co.fid = %s
        ORDER BY co.postedAt ASC
    ''', [fid])
    return curs.fetchall()


def get_forum_id_by_event(conn, eid):
    """Get the forum ID for a specific event"""
    curs = dbi.dict_cursor(conn)
    curs.execute('SELECT fid FROM forum WHERE eid = %s', [eid])
    result = curs.fetchone()
    return result['fid'] if result else None


def insert_comment(conn, text, uid, fid):
    """Insert a new comment into the database
    and return the auto-generated commId"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        INSERT INTO comments (text, addedBy, fid, postedAt)
        VALUES (%s, %s, %s, NOW())
    ''', [text, uid, fid])
    conn.commit()
    return curs.lastrowid


def get_comment_info(conn, comm_id):
    """Get comment information including the associated event ID"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT co.addedBy, f.eid
        FROM comments co
        JOIN forum f ON co.fid = f.fid
        WHERE co.commId = %s
    ''', [comm_id])
    return curs.fetchone()


def delete_comment_by_id(conn, comm_id):
    """Delete a comment from the database"""
    curs = dbi.dict_cursor(conn)
    curs.execute('DELETE FROM comments WHERE commId = %s', [comm_id])
    conn.commit()


def get_event_capacity_info(conn, eid):
    """Get event capacity and current participant count"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT e.eid, e.cap, e.date, COUNT(p.uid) as current_count
        FROM events e
        LEFT JOIN participants p ON e.eid = p.eid
        WHERE e.eid = %s
        GROUP BY e.eid, e.cap
    ''', [eid])
    return curs.fetchone()


def is_user_participant(conn, eid, uid):
    """Check if a user is already a participant in an event"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT uid FROM participants
        WHERE eid = %s AND uid = %s
    ''', [eid, uid])
    return curs.fetchone() is not None


def add_participant(conn, eid, uid):
    """Add a user as a participant to an event

    Returns:
        True if successfully added
        False if event is full 
        
    Raises:
        Exception for other database errors

    Note: Already-joined check should be done before calling this function
          for better error messages. This function focuses on capacity check.
    """
    curs = dbi.dict_cursor(conn)
    try:
        # Start transaction and lock the event row
        curs.execute('START TRANSACTION')

        # Lock the event and check capacity atomically
        curs.execute('''
            SELECT e.cap, COUNT(p.uid) as current_count
            FROM events e
            LEFT JOIN participants p ON e.eid = p.eid
            WHERE e.eid = %s
            GROUP BY e.eid, e.cap
            FOR UPDATE
        ''', [eid])

        result = curs.fetchone()
        if not result:
            conn.rollback()
            return False  # Event not found
            
        if result['current_count'] >= result['cap']:
            conn.rollback()
            return False  # Event is full
        
        # Add participant
        curs.execute('''
            INSERT INTO participants (eid, uid)
            VALUES (%s, %s)
        ''', [eid, uid])
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        raise


def get_event_creator(conn, eid):
    """Get the creator UID of an event"""
    curs = dbi.cursor(conn)
    curs.execute('SELECT addedBy FROM events WHERE eid = %s', [eid])
    result = curs.fetchone()
    return result[0] if result else None


def remove_participant(conn, eid, uid):
    """Remove a user as a participant from an event"""
    curs = dbi.cursor(conn)
    curs.execute('''
        DELETE FROM participants
        WHERE eid = %s AND uid = %s
    ''', [eid, uid])
    conn.commit()