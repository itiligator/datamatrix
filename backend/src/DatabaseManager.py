import logging
import os
import sqlite3
import datetime
from typing import List


class DatabaseManager:
    def __init__(self, db_path: str = 'codes_database.db'):
        """Initialize the database manager with the specified database path."""
        os.makedirs(os.path.join('results', 'database'), exist_ok=True)
        self.db_path = os.path.join('results', 'database', db_path)
        self.conn = None
        self.cursor = None
        self._initialize_database()

    def _initialize_database(self):
        """Create the database and tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Create tables for individual codes, group codes, and their relationships
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS individual_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS code_relationships (
                    group_code_id INTEGER,
                    individual_code_id INTEGER,
                    PRIMARY KEY (group_code_id, individual_code_id),
                    FOREIGN KEY (group_code_id) REFERENCES group_codes(id),
                    FOREIGN KEY (individual_code_id) REFERENCES individual_codes(id)
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_sequence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    sequence INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (group_code_id) REFERENCES group_codes(id)
                )
            ''')

            self.conn.commit()
            logging.info("Database initialized successfully")
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            if self.conn:
                self.conn.close()
            raise

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def is_individual_code_exists(self, code: str) -> bool:
        """Check if an individual code already exists in the database."""
        try:
            self.cursor.execute("SELECT 1 FROM individual_codes WHERE code = ?", (code,))
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logging.error(f"Error checking individual code: {e}")
            return False

    def is_group_code_exists(self, code: str) -> bool:
        """Check if a group code already exists in the database."""
        try:
            self.cursor.execute("SELECT 1 FROM group_codes WHERE code = ?", (code,))
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logging.error(f"Error checking group code: {e}")
            return False

    def save_codes(self, individual_codes: List[str], group_code: str) -> int:
        """Save individual codes and group code to the database with their relationship."""
        try:
            # Begin transaction
            self.conn.execute("BEGIN TRANSACTION")
            # Insert group code
            self.cursor.execute("INSERT INTO group_codes (code) VALUES (?)", (group_code,))
            group_code_id = self.cursor.lastrowid

            # Insert individual codes and create relationships
            for code in individual_codes:
                self.cursor.execute("INSERT INTO individual_codes (code) VALUES (?)", (code,))
                individual_code_id = self.cursor.lastrowid

                # Create relationship
                self.cursor.execute(
                    "INSERT INTO code_relationships (group_code_id, individual_code_id) VALUES (?, ?)",
                    (group_code_id, individual_code_id)
                )

            # Get the current date
            current_date = datetime.date.today()

            # Check if the current date exists in the daily_sequence table
            self.cursor.execute("SELECT sequence FROM daily_sequence WHERE date = ?", (current_date,))
            result = self.cursor.fetchone()

            if result is None:
                # If the current date does not exist in the daily_sequence table, insert a new record with the current date and sequence number 1
                self.cursor.execute("INSERT INTO daily_sequence (date, sequence) VALUES (?, 1)", (current_date,))
                sequence_number = 1
            else:
                # If the current date exists in the daily_sequence table, increment the sequence number by 1
                sequence_number = result[0] + 1
                self.cursor.execute("UPDATE daily_sequence SET sequence = ? WHERE date = ?", (sequence_number, current_date))

            # Commit transaction
            self.conn.commit()
            logging.info(f"Saved {len(individual_codes)} individual codes and 1 group code to database")
            return sequence_number
        except sqlite3.Error as e:
            logging.error(f"Error saving codes to database: {e}")
            self.conn.rollback()
            return -1

    def check_duplicate_codes(self, individual_codes: List[str]) -> List[str]:
        """Check if any individual codes already exist in the database and return the duplicates."""
        duplicates = []
        try:
            for code in individual_codes:
                if self.is_individual_code_exists(code):
                    duplicates.append(code)
            return duplicates
        except sqlite3.Error as e:
            logging.error(f"Error checking duplicate codes: {e}")
            return []
