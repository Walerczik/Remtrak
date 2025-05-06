import sqlite3
from sqlite3 import Error

# Подключение к базе данных
def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('wagon_repair.db')
    except Error as e:
        print(e)
    return conn

# Создание таблиц
def create_tables():
    conn = create_connection()
    cursor = conn.cursor()

    # Таблица для вагона и поломок
    cursor.execute('''CREATE TABLE IF NOT EXISTS wagons (
                        id INTEGER PRIMARY KEY,
                        wagon_number TEXT NOT NULL,
                        type TEXT NOT NULL)''')
    
    # Таблица для поломок
    cursor.execute('''CREATE TABLE IF NOT EXISTS faults (
                        id INTEGER PRIMARY KEY,
                        wagon_id INTEGER,
                        fault_description TEXT,
                        status BOOLEAN DEFAULT 0,
                        completed_by TEXT,
                        completed_at DATETIME,
                        FOREIGN KEY (wagon_id) REFERENCES wagons (id))''')
    
    conn.commit()
    conn.close()

# Функция для добавления вагона
def add_wagon(wagon_number, type_):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO wagons (wagon_number, type) VALUES (?, ?)''', (wagon_number, type_))
    conn.commit()
    conn.close()

# Функция для добавления поломки
def add_fault(wagon_id, fault_description):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO faults (wagon_id, fault_description) VALUES (?, ?)''', (wagon_id, fault_description))
    conn.commit()
    conn.close()

# Функция для получения всех поломок для вагона
def get_faults(wagon_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM faults WHERE wagon_id = ?''', (wagon_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# Функция для обновления статуса поломки
def mark_fault_done(fault_id, completed_by):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''UPDATE faults SET status = 1, completed_by = ?, completed_at = ? WHERE id = ?''',
                   (completed_by, sqlite3.datetime.datetime.now(), fault_id))
    conn.commit()
    conn.close()

# Вызов функции для создания таблиц при старте
create_tables()
