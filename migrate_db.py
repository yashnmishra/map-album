import sqlite3
import os
import sys

def migrate():
    # It is in the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'database.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE maps ADD COLUMN preview_path VARCHAR(500)")
        print("Added preview_path")
    except sqlite3.OperationalError as e:
        print(f"preview_path already exists or error: {e}")
        
    try:
        cursor.execute("ALTER TABLE maps ADD COLUMN has_tiles BOOLEAN DEFAULT 0")
        print("Added has_tiles")
    except sqlite3.OperationalError as e:
        print(f"has_tiles already exists or error: {e}")
        
    try:
        cursor.execute("ALTER TABLE maps ADD COLUMN tile_dir_path VARCHAR(500)")
        print("Added tile_dir_path")
    except sqlite3.OperationalError as e:
        print(f"tile_dir_path already exists or error: {e}")
        
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == '__main__':
    migrate()
