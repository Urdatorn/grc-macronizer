import sqlite3

def hypotactic(word, hypotactic_db_path='db/hypotactic.db'):
    try:
        conn = sqlite3.connect(hypotactic_db_path)
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

