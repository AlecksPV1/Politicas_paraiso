import sqlite3
import datetime
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS politicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio TEXT UNIQUE NOT NULL,
            nombre_empleado TEXT NOT NULL,
            equipo_asignado TEXT NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            fecha_entrega TEXT NOT NULL,
            estado_fisico TEXT NOT NULL,
            notas TEXT,
            fecha_creacion TEXT NOT NULL,
            estado_firma TEXT NOT NULL DEFAULT 'Firmado Digitalmente',
            pdf_path TEXT NOT NULL,
            signature_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_next_folio():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM politicas')
    row = cursor.fetchone()
    last_id = row[0] if row and row[0] is not None else 0
    conn.close()
    next_id = last_id + 1
    return f"POL-{next_id:04d}"

def save_politica(data, pdf_filename, signature_filename=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_firma = "Firmado Digitalmente" if signature_filename else "Pendiente de Firma"
    
    cursor.execute('''
        INSERT INTO politicas (
            folio,
            nombre_empleado,
            equipo_asignado,
            marca,
            modelo,
            fecha_entrega,
            estado_fisico,
            notas,
            fecha_creacion,
            estado_firma,
            pdf_path,
            signature_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['folio'],
        data['nombre_empleado'],
        data['equipo_asignado'],
        data['marca'],
        data['modelo'],
        data['fecha_entrega'],
        data['estado_fisico'],
        data.get('notas', ''),
        now_str,
        estado_firma,
        pdf_filename,
        signature_filename
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_all_politicas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM politicas ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_politica_by_id(politica_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM politicas WHERE id = ?', (politica_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_politica_by_folio(folio):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM politicas WHERE folio = ?', (folio,))
    row = cursor.fetchone()
    conn.close()
    return row
