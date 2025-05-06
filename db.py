# db.py
import sqlite3
from datetime import datetime

DATABASE = 'repairs.db'

def create_table():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY,
            wagon_number TEXT NOT NULL,
            defect TEXT NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,
            worker TEXT,
            completion_date TEXT
        )
    ''')
    connection.commit()
    connection.close()

def add_repair(wagon_number, defect):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute('''
        INSERT INTO repairs (wagon_number, defect, is_done)
        VALUES (?, ?, ?)
    ''', (wagon_number, defect, 0))
    connection.commit()
    connection.close()

def get_repairs_by_wagon(wagon_number):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute('''
        SELECT * FROM repairs WHERE wagon_number = ?
    ''', (wagon_number,))
    repairs = cursor.fetchall()
    connection.close()
    return repairs

def mark_repair_done(repair_id, worker):
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute('''
        UPDATE repairs
        SET is_done = 1, worker = ?, completion_date = ?
        WHERE id = ?
    ''', (worker, datetime.now(), repair_id))
    connection.commit()
    connection.close()
