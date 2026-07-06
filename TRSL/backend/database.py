import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime

class RSLDatabase:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'root',  # Changed to root for XAMPP
            'password': '',  # XAMPP MySQL usually has empty password
            'database': 'RSL_db',
            'raise_on_warnings': True
        }
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(**self.config)
            print("✅ MySQL Database connection successful")
            return True
        except Error as e:
            print(f"❌ Error connecting to MySQL: {e}")
            print(f"Trying with port 3307...")
            # Try with port 3307 (common for XAMPP)
            try:
                self.config['port'] = 3307
                self.connection = mysql.connector.connect(**self.config)
                print("✅ MySQL Database connection successful on port 3307")
                return True
            except Error as e2:
                print(f"❌ Error connecting to MySQL: {e2}")
                self.connection = None
                return False
    
    def get_cursor(self):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        return self.connection.cursor(dictionary=True)
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    # Create tables if they don't exist
    def create_tables(self):
        cursor = self.get_cursor()
        
        # Words table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id INT PRIMARY KEY AUTO_INCREMENT,
                word VARCHAR(100) UNIQUE NOT NULL,
                filename VARCHAR(255) NOT NULL,
                type ENUM('word', 'phrase') DEFAULT 'word',
                description TEXT,
                category VARCHAR(50),
                difficulty_level ENUM('beginner', 'intermediate', 'advanced') DEFAULT 'beginner',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_word (word),
                INDEX idx_category (category)
            )
        """)
        
        # Phrases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phrases (
                id INT PRIMARY KEY AUTO_INCREMENT,
                phrase VARCHAR(200) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_phrase (phrase)
            )
        """)
        
        # Phrase components (junction table for phrase-word relationships)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phrase_components (
                id INT PRIMARY KEY AUTO_INCREMENT,
                phrase_id INT NOT NULL,
                word_id INT NOT NULL,
                position INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (phrase_id) REFERENCES phrases(id) ON DELETE CASCADE,
                FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE,
                UNIQUE KEY unique_phrase_word (phrase_id, word_id, position),
                INDEX idx_phrase_id (phrase_id),
                INDEX idx_word_id (word_id)
            )
        """)
        
        # Videos metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INT PRIMARY KEY AUTO_INCREMENT,
                word_id INT,
                filename VARCHAR(255) UNIQUE NOT NULL,
                original_filename VARCHAR(255),
                file_path VARCHAR(500),
                file_size BIGINT,
                duration FLOAT,
                resolution VARCHAR(20),
                format VARCHAR(10),
                source ENUM('upload', 'camera', 'external') DEFAULT 'upload',
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status ENUM('active', 'pending', 'deleted') DEFAULT 'active',
                view_count INT DEFAULT 0,
                last_used TIMESTAMP NULL,
                FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE SET NULL,
                INDEX idx_filename (filename),
                INDEX idx_status (status),
                INDEX idx_upload_date (upload_date)
            )
        """)
        
        self.connection.commit()
        cursor.close()
        print("✅ Database tables created successfully")
        
        # Insert default data if empty
        self.insert_default_data()
    
    def insert_default_data(self):
        cursor = self.get_cursor()
        
        # Check if words table is empty
        cursor.execute("SELECT COUNT(*) as count FROM words")
        if cursor.fetchone()['count'] == 0:
            print("📝 Inserting default words...")
            
            default_words = [
                ('hello', 'hello.mp4', 'greeting'),
                ('thank you', 'thank_you.mp4', 'courtesy'),
                ('please', 'please.mp4', 'courtesy'),
                ('yes', 'yes.mp4', 'basic'),
                ('no', 'no.mp4', 'basic'),
                ('water', 'water.mp4', 'basic_needs'),
                ('food', 'food.mp4', 'basic_needs'),
                ('help', 'help.mp4', 'emergency'),
                ('name', 'name.mp4', 'personal'),
                ('how', 'how.mp4', 'question'),
                ('you', 'you.mp4', 'pronoun'),
                ('i', 'i.mp4', 'pronoun'),
                ('good', 'good.mp4', 'adjective'),
                ('morning', 'morning.mp4', 'time'),
                ('evening', 'evening.mp4', 'time'),
                ('my', 'my.mp4', 'pronoun'),
                ('what', 'what.mp4', 'question')
            ]
            
            for word, filename, category in default_words:
                try:
                    cursor.execute(
                        "INSERT IGNORE INTO words (word, filename, category) VALUES (%s, %s, %s)",
                        (word, filename, category)
                    )
                except Exception as e:
                    print(f"Error inserting {word}: {e}")
            
            self.connection.commit()
            print(f"✅ Inserted {len(default_words)} default words")
        
        # Check if phrases table is empty
        cursor.execute("SELECT COUNT(*) as count FROM phrases")
        if cursor.fetchone()['count'] == 0:
            print("📝 Inserting default phrases...")
            
            default_phrases = [
                ('good morning', ['good', 'morning']),
                ('thank you very much', ['thank', 'you', 'very', 'much']),
                ('my name is', ['my', 'name', 'is']),
                ('how are you', ['how', 'are', 'you'])
            ]
            
            for phrase, words in default_phrases:
                try:
                    # Insert phrase
                    cursor.execute("INSERT IGNORE INTO phrases (phrase) VALUES (%s)", (phrase,))
                    
                    # Get phrase_id
                    cursor.execute("SELECT id FROM phrases WHERE phrase = %s", (phrase,))
                    phrase_result = cursor.fetchone()
                    
                    if phrase_result:
                        phrase_id = phrase_result['id']
                        
                        # Add phrase components
                        for position, word in enumerate(words, 1):
                            # Get word_id
                            cursor.execute("SELECT id FROM words WHERE word = %s", (word,))
                            word_result = cursor.fetchone()
                            
                            if word_result:
                                cursor.execute(
                                    "INSERT IGNORE INTO phrase_components (phrase_id, word_id, position) VALUES (%s, %s, %s)",
                                    (phrase_id, word_result['id'], position)
                                )
                except Exception as e:
                    print(f"Error inserting phrase {phrase}: {e}")
            
            self.connection.commit()
            print(f"✅ Inserted {len(default_phrases)} default phrases")
        
        cursor.close()
    
    # Word operations
    def get_word(self, word):
        cursor = self.get_cursor()
        query = "SELECT * FROM words WHERE word = %s"
        cursor.execute(query, (word.lower(),))
        result = cursor.fetchone()
        cursor.close()
        return result
    
    def get_all_words(self):
        cursor = self.get_cursor()
        query = "SELECT * FROM words ORDER BY word"
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result
    
    def add_word(self, word, filename, word_type='word', description=None, category=None):
        cursor = self.get_cursor()
        query = """
        INSERT INTO words (word, filename, type, description, category) 
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            filename = VALUES(filename),
            type = VALUES(type),
            description = VALUES(description),
            category = VALUES(category)
        """
        cursor.execute(query, (word.lower(), filename, word_type, description, category))
        self.connection.commit()
        word_id = cursor.lastrowid
        cursor.close()
        return word_id
    
    def delete_word(self, word):
        cursor = self.get_cursor()
        query = "DELETE FROM words WHERE word = %s"
        cursor.execute(query, (word.lower(),))
        self.connection.commit()
        affected = cursor.rowcount
        cursor.close()
        return affected > 0
    
    # Phrase operations
    def add_phrase(self, phrase, words_list):
        cursor = self.get_cursor()
        
        try:
            # Add phrase
            query = "INSERT INTO phrases (phrase) VALUES (%s) ON DUPLICATE KEY UPDATE id=id"
            cursor.execute(query, (phrase.lower(),))
            
            if cursor.lastrowid == 0:
                # Phrase already exists, get its id
                cursor.execute("SELECT id FROM phrases WHERE phrase = %s", (phrase.lower(),))
                result = cursor.fetchone()
                phrase_id = result['id'] if result else None
            else:
                phrase_id = cursor.lastrowid
            
            if phrase_id:
                # Clear existing components
                cursor.execute("DELETE FROM phrase_components WHERE phrase_id = %s", (phrase_id,))
                
                # Add new components
                for position, word in enumerate(words_list, 1):
                    # Get word_id
                    cursor.execute("SELECT id FROM words WHERE word = %s", (word.lower(),))
                    word_result = cursor.fetchone()
                    
                    if word_result:
                        cursor.execute(
                            "INSERT INTO phrase_components (phrase_id, word_id, position) VALUES (%s, %s, %s)",
                            (phrase_id, word_result['id'], position)
                        )
                    else:
                        # Word doesn't exist, create it
                        word_id = self.add_word(word, f"{word}.mp4")
                        cursor.execute(
                            "INSERT INTO phrase_components (phrase_id, word_id, position) VALUES (%s, %s, %s)",
                            (phrase_id, word_id, position)
                        )
            
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"Error adding phrase: {e}")
            self.connection.rollback()
            cursor.close()
            return False
    
    def get_phrase(self, phrase):
        cursor = self.get_cursor()
        query = """
        SELECT p.*, 
               GROUP_CONCAT(w.word ORDER BY pc.position) as component_words,
               GROUP_CONCAT(w.filename ORDER BY pc.position) as component_filenames
        FROM phrases p
        LEFT JOIN phrase_components pc ON p.id = pc.phrase_id
        LEFT JOIN words w ON pc.word_id = w.id
        WHERE p.phrase = %s
        GROUP BY p.id
        """
        cursor.execute(query, (phrase.lower(),))
        result = cursor.fetchone()
        cursor.close()
        
        if result and result['component_words']:
            result['words'] = result['component_words'].split(',')
            result['filenames'] = result['component_filenames'].split(',')
        elif result:
            result['words'] = []
            result['filenames'] = []
        
        return result
    
    def get_all_phrases(self):
        cursor = self.get_cursor()
        query = """
        SELECT p.*, 
               GROUP_CONCAT(w.word ORDER BY pc.position) as component_words
        FROM phrases p
        LEFT JOIN phrase_components pc ON p.id = pc.phrase_id
        LEFT JOIN words w ON pc.word_id = w.id
        GROUP BY p.id
        ORDER BY p.phrase
        """
        cursor.execute(query)
        results = cursor.fetchall()
        
        for result in results:
            if result['component_words']:
                result['words'] = result['component_words'].split(',')
            else:
                result['words'] = []
        
        cursor.close()
        return results
    
    # Statistics
    def get_stats(self):
        cursor = self.get_cursor()
        
        try:
            # Word count
            cursor.execute("SELECT COUNT(*) as count FROM words")
            total_words = cursor.fetchone()['count']
            
            # Phrase count
            cursor.execute("SELECT COUNT(*) as count FROM phrases")
            total_phrases = cursor.fetchone()['count']
            
            # Video count from words table
            cursor.execute("SELECT COUNT(DISTINCT filename) as count FROM words")
            total_videos = cursor.fetchone()['count']
            
            # Get list of all video files in videos directory
            import os
            video_dir = 'videos'
            video_files = []
            if os.path.exists(video_dir):
                video_files = [f for f in os.listdir(video_dir) 
                             if os.path.isfile(os.path.join(video_dir, f))]
            
            # Get used filenames from database
            cursor.execute("SELECT filename FROM words")
            used_files = [row['filename'] for row in cursor.fetchall()]
            
            # Find unused videos
            unused_files = [f for f in video_files if f not in used_files]
            
            cursor.close()
            
            return {
                'total_words': total_words,
                'total_phrases': total_phrases,
                'total_videos': len(video_files),
                'unused_videos': len(unused_files),
                'unused_video_list': unused_files
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            cursor.close()
            return {
                'total_words': 0,
                'total_phrases': 0,
                'total_videos': 0,
                'unused_videos': 0,
                'unused_video_list': []
            }

# Initialize database
db_instance = RSLDatabase()