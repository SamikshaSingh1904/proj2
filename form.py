"""
form.py - Database functions for create event form operations
authors: clump
"""
import cs304dbi as dbi

def get_categories(conn):
    """Return all calendar categories (cid, category)."""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        SELECT cid, category
        FROM calendar
        ORDER BY category
    ''')
    return curs.fetchall()

def insert_event(conn, title, date_str, start_str, end_str,
                 desc, uid, city, state, cap,
                 flexible, cid):
    """
    Insert a new event into the events table and return its eid.

    - date_str: 'YYYY-MM-DD'
    - start_str / end_str: 'HH:MM' or '' (we'll pass None if blank)
    - cap: int (already validated) or None
    - flexible: boolean
    """
    curs = dbi.cursor(conn)

    sql = '''
        INSERT INTO events
            (title, `start`, `end`, `date`, `desc`,
             addedBy, city, state, cap, flexible, cid)
        VALUES
            (%s, %s, %s, %s, %s,
             %s, %s, %s, %s, %s, %s)
    '''

    # If start_str / end_str are empty strings, convert to None so MySQL
    # will store NULL instead of '0000-00-00' or erroring.
    start_val = start_str or None
    end_val = end_str or None

    curs.execute(sql, [
        title,
        start_val,
        end_val,
        date_str,
        desc,
        uid,
        city,
        state,
        cap,
        flexible,
        cid
    ])
    conn.commit()
    eid = curs.lastrowid
    
    # Create forum for the new event
    curs.execute('INSERT INTO forum (eid) VALUES (%s)', [eid])
    conn.commit()
    
    return eid

def add_participant(conn, eid, uid):
    """Insert a row into participants for (eid, uid)."""
    curs = dbi.cursor(conn)
    curs.execute(
        '''
        INSERT INTO participants (eid, uid)
        VALUES (%s, %s)
        ''',
        [eid, uid]
    )
    conn.commit()