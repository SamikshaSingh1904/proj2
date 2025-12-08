"""
forum.py - Database query functions for forum functionality
authors: Samiksha Singh
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
               COUNT(DISTINCT part.uid) as participant_count,
               COUNT(DISTINCT co.commId) as comment_count
        FROM events e
        JOIN person p ON e.addedBy = p.uid
        JOIN calendar c ON e.cid = c.cid
        JOIN forum f ON e.eid = f.eid
        LEFT JOIN participants part ON e.eid = part.eid
        LEFT JOIN comments co ON f.fid = co.fid
    '''

    if not show_past:
        query += ' WHERE e.date >= CURDATE()'
    
    query += '''
        GROUP BY e.eid, e.title, e.desc, e.date, e.start, e.end,
                e.city, e.state, e.cap, p.name, p.uid, c.category, f.fid
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
    """Get information about a specific event to be
    displayed on an event's individual page (as opposed
    to the calendar view's event side panel)"""
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
               co.parent_commId, 
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

def insert_reply(conn, text, uid, fid, parent_commId):
    """Insert a reply to an existing comment"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        INSERT INTO comments (text, addedBy, fid, parent_commId, postedAt)
        VALUES (%s, %s, %s, %s, NOW())
    ''', [text, uid, fid, parent_commId])
    conn.commit()
    return curs.lastrowid


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
    
    THREAD SAFETY:
        Uses SELECT ... FOR UPDATE to lock the event row, 
        preventing race conditions. Without the lock, this could happen:
        Thread A reads current_count=9, cap=10 -> has space
        Thread B reads current_count=9, cap=10 -> has space
        Thread A inserts -> current_count now 10
        Thread B inserts -> current_count now 11 (OVER CAPACITY!)
        
        FOR UPDATE lock ensures only one thread can read and modify at a time.
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