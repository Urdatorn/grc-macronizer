import sqlite3

def hypotactic(word, db_path='db/hypotactic.db'):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT macrons FROM annotated_tokens WHERE token = ?", (word,)) # important to include table name
        
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]  # Return first column of the result (macrons)
        return word
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return word

# Example usage:
print(hypotactic("ἀγαθῆς"))  # Uses default db_path='hypotactic.db'
# print(hypotactic("test", db_path='/path/to/your/hypotactic.db'))  # Specify custom path

from greek_accentuation.characters import add_diacritic

add_diacritic('ι', SHORT)