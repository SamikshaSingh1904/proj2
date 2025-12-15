"""
profile.py - Database query functions for profile photos
authors: Bessie Li
"""
import cs304dbi as dbi


def get_profile_photo_filename(conn, uid):
    """Return filename for user's profile photo, or None if user not found."""
    curs = dbi.dict_cursor(conn)
    n = curs.execute('''
        SELECT profile_filename
        FROM person
        WHERE uid = %s
    ''', [uid])
    if n == 0:
        return None  # user not found
    row = curs.fetchone()
    return row['profile_filename']  # may be None


def upsert_profile_photo(conn, uid, filename):
    """Update the filename for this user's profile photo."""
    curs = dbi.dict_cursor(conn)
    curs.execute('''
        UPDATE person
        SET profile_filename = %s
        WHERE uid = %s
    ''', [filename, uid])
    conn.commit()
