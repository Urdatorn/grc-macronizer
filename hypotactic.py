import sqlite3

from format_macrons import macron_integrate_markup

def hypotactic(word, hypotactic_db_path='db/hypotactic.db'):
    '''
    >>> hypotactic('ἀγαθῆς')
    >>> ἀ^γα^θῆς
    '''
    try:
        conn = sqlite3.connect(hypotactic_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT macrons FROM annotated_tokens WHERE token = ?", (word,)) # important to include table name
        result = cursor.fetchone()
        conn.close()
        if result:
            return macron_integrate_markup(word, result[0])  # Return first column of the result (macrons)
        return word
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return word


