"""
password.py - Database query functions for authentication
authors: Beatrix Kim, Bessie Li, Samiksha Singh 
"""
import cs304dbi as dbi


def get_user_by_email(conn, email):
    """Get user information by email"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT uid, name, email, pass
        FROM person
        WHERE email = %s
    ''', [email])
    return curs.fetchone()


def email_exists(conn, email):
    """Check if an email is already registered"""
    curs = dbi.dict_cursor(conn)
    curs.execute('SELECT uid FROM person WHERE email = %s', [email])
    return curs.fetchone() is not None


def create_user(conn, name, email, hashed_password, bio, year, pronouns):
    """Insert a new user into the database and return the new uid

    Raises:
        Exception: If email already exists (duplicate key error).
                   Caller should handle this with try/except.
                   Currently caught in app.py > signup() route.
    
    Note: Uses database UNIQUE constraint for thread-safe duplicate detection.
          Checking email_exists() before insert would have a race condition:
          Thread A checks -> email doesn't exist
          Thread B checks -> email doesn't exist
          Thread A inserts -> success
          Thread B inserts -> duplicate error!
          By relying on the database constraint, the duplicate check and insert
          happen atomically at the database level.
    """
    curs = dbi.dict_cursor(conn)
    try:
        curs.execute('''
            INSERT INTO person (name, email, pass, bio, year, pronouns)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', [name, email, hashed_password, bio, year, pronouns])
        conn.commit()
        # Get the auto-generated uid
        return curs.lastrowid
    except Exception as e:
        # Duplicate email will raise an exception due to UNIQUE constraint
        # Let it bubble up to caller (app.py > signup route)
        raise

def update_user_profile(conn, uid, name, bio, year, pronouns):
    """Update user profile information"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        UPDATE person 
        SET name=%s, bio=%s, year=%s, pronouns=%s
        WHERE uid=%s
    ''', [name, bio, year, pronouns, uid])
    conn.commit()

def delete_user(conn, uid):
    """Delete a user account from the database"""
    curs = dbi.dict_cursor(conn)
    curs.execute('DELETE FROM person WHERE uid = %s', [uid])
    conn.commit()

def get_user_profile(conn, uid):
    """Get user profile information"""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT uid, name, email, bio, year, pronouns, profile_filename
        FROM person
        WHERE uid = %s
    ''', [uid])
    return curs.fetchone()


def get_user_created_events(conn, uid, show_past=False):
    """Get events created by a user"""
    curs = dbi.dict_cursor(conn)
    if show_past:
        # Show all events
        query = '''
            SELECT e.eid, e.title, e.date, e.start,e.end, c.category,
                COUNT(p.uid) as participant_count
            FROM events e
            JOIN calendar c ON e.cid = c.cid
            LEFT JOIN participants p ON e.eid = p.eid
            WHERE e.addedBy = %s
            GROUP BY e.eid
            ORDER BY e.date DESC
        '''
    else:
        # Show only upcoming events
        query = '''
            SELECT e.eid, e.title, e.date, e.start, e.end, c.category,
                   COUNT(p.uid) as participant_count
            FROM events e
            JOIN calendar c ON e.cid = c.cid
            LEFT JOIN participants p ON e.eid = p.eid
            WHERE e.addedBy = %s AND e.date >= CURDATE()
            GROUP BY e.eid
            ORDER BY e.date, e.start
        '''
    curs.execute(query, [uid])
    return curs.fetchall()


def get_user_joined_events(conn, uid, show_past=False):
    """Get events a user is participating in,
    excluding their own (visible in created events!)"""
    curs = dbi.dict_cursor(conn)

    if show_past:
        # Show all events
        query = '''
            SELECT e.eid, e.title, e.date, e.start, c.category,
                p2.name as creator_name
            FROM participants part
            JOIN events e ON part.eid = e.eid
            JOIN calendar c ON e.cid = c.cid
            JOIN person p2 ON e.addedBy = p2.uid
            WHERE part.uid = %s AND e.addedBy != %s
            ORDER BY e.date DESC
        '''
        curs.execute(query, [uid, uid])
    else: 
        # Show only upcoming events
        query = '''
            SELECT e.eid, e.title, e.date, e.start, e.end, c.category,
                   p2.name as creator_name
            FROM participants pa
            JOIN events e ON pa.eid = e.eid
            JOIN calendar c ON e.cid = c.cid
            JOIN person p2 ON e.addedBy = p2.uid
            WHERE pa.uid = %s AND e.addedBy != %s AND e.date >= CURDATE()
            ORDER BY e.date, e.start
        '''
        curs.execute(query, [uid, uid])

    return curs.fetchall()