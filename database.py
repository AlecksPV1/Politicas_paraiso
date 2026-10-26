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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio_entrega TEXT UNIQUE NOT NULL,
            folio_politica TEXT NOT NULL,
            nombre_empleado TEXT NOT NULL,
            puesto_departamento TEXT,
            equipo_asignado TEXT NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            motivo_entrega TEXT NOT NULL,
            fecha_devolucion TEXT NOT NULL,
            estado_fisico_entrega TEXT NOT NULL,
            operatividad TEXT NOT NULL,
            dictamen_no_adeudo TEXT NOT NULL,
            monto_retencion TEXT,
            accesorios_devueltos TEXT,
            accesorios_faltantes TEXT,
            observaciones TEXT,
            responsable_sistemas TEXT NOT NULL,
            fecha_creacion TEXT NOT NULL,
            estado_firma TEXT NOT NULL DEFAULT 'Firma Física',
            pdf_path TEXT NOT NULL,
            signature_path TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS politica_equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio_politica TEXT NOT NULL,
            equipo_asignado TEXT NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            estado_fisico TEXT NOT NULL,
            notas TEXT,
            estado_devolucion TEXT NOT NULL DEFAULT 'En Resguardo',
            folio_entrega TEXT,
            fecha_devolucion TEXT,
            FOREIGN KEY (folio_politica) REFERENCES politicas (folio)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entrega_equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio_entrega TEXT NOT NULL,
            politica_equipo_id INTEGER,
            equipo_asignado TEXT NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            estado_fisico_entrega TEXT NOT NULL,
            operatividad TEXT NOT NULL,
            accesorios_devueltos TEXT,
            accesorios_faltantes TEXT,
            FOREIGN KEY (folio_entrega) REFERENCES entregas (folio_entrega)
        )
    ''')

    # Automatic migration for existing data
    cursor.execute('SELECT COUNT(*) FROM politica_equipos')
    count_equipos = cursor.fetchone()[0]
    if count_equipos == 0:
        cursor.execute('SELECT * FROM politicas')
        existing_politicas = cursor.fetchall()
        for pol in existing_politicas:
            cursor.execute('SELECT * FROM entregas WHERE folio_politica = ?', (pol['folio'],))
            ent = cursor.fetchone()
            if ent:
                cursor.execute('''
                    INSERT INTO politica_equipos (
                        folio_politica, equipo_asignado, marca, modelo, estado_fisico, notas, estado_devolucion, folio_entrega, fecha_devolucion
                    ) VALUES (?, ?, ?, ?, ?, ?, 'Devuelto', ?, ?)
                ''', (
                    pol['folio'], pol['equipo_asignado'], pol['marca'], pol['modelo'],
                    pol['estado_fisico'], pol['notas'], ent['folio_entrega'], ent['fecha_devolucion']
                ))
                pe_id = cursor.lastrowid
                cursor.execute('''
                    INSERT INTO entrega_equipos (
                        folio_entrega, politica_equipo_id, equipo_asignado, marca, modelo, estado_fisico_entrega, operatividad, accesorios_devueltos, accesorios_faltantes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ent['folio_entrega'], pe_id, ent['equipo_asignado'], ent['marca'], ent['modelo'],
                    ent['estado_fisico_entrega'], ent['operatividad'], ent['accesorios_devueltos'], ent['accesorios_faltantes']
                ))
            else:
                cursor.execute('''
                    INSERT INTO politica_equipos (
                        folio_politica, equipo_asignado, marca, modelo, estado_fisico, notas, estado_devolucion
                    ) VALUES (?, ?, ?, ?, ?, ?, 'En Resguardo')
                ''', (
                    pol['folio'], pol['equipo_asignado'], pol['marca'], pol['modelo'],
                    pol['estado_fisico'], pol['notas']
                ))

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

def save_politica(data, pdf_filename, signature_filename=None, equipos=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_firma = "Firmado Digitalmente" if signature_filename else "Firma Física"
    
    if not equipos:
        equipos = [{
            'equipo_asignado': data['equipo_asignado'],
            'marca': data['marca'],
            'modelo': data['modelo'],
            'estado_fisico': data['estado_fisico'],
            'notas': data.get('notas', '')
        }]

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
    new_id = cursor.lastrowid

    for eq in equipos:
        cursor.execute('''
            INSERT INTO politica_equipos (
                folio_politica,
                equipo_asignado,
                marca,
                modelo,
                estado_fisico,
                notas,
                estado_devolucion
            ) VALUES (?, ?, ?, ?, ?, ?, 'En Resguardo')
        ''', (
            data['folio'],
            eq['equipo_asignado'],
            eq['marca'],
            eq['modelo'],
            eq['estado_fisico'],
            eq.get('notas', '')
        ))

    conn.commit()
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

def get_equipos_by_folio_politica(folio_politica):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM politica_equipos WHERE folio_politica = ? ORDER BY id ASC', (folio_politica,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_equipos_pendientes_by_folio_politica(folio_politica):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM politica_equipos WHERE folio_politica = ? AND estado_devolucion = "En Resguardo" ORDER BY id ASC', (folio_politica,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_next_folio_entrega():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM entregas')
    row = cursor.fetchone()
    last_id = row[0] if row and row[0] is not None else 0
    conn.close()
    next_id = last_id + 1
    return f"DEV-{next_id:04d}"

def save_entrega(data, pdf_filename, signature_filename=None, equipos_devueltos=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_firma = "Firmado Digitalmente" if signature_filename else "Firma Física"

    cursor.execute('''
        INSERT INTO entregas (
            folio_entrega,
            folio_politica,
            nombre_empleado,
            puesto_departamento,
            equipo_asignado,
            marca,
            modelo,
            motivo_entrega,
            fecha_devolucion,
            estado_fisico_entrega,
            operatividad,
            dictamen_no_adeudo,
            monto_retencion,
            accesorios_devueltos,
            accesorios_faltantes,
            observaciones,
            responsable_sistemas,
            fecha_creacion,
            estado_firma,
            pdf_path,
            signature_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['folio_entrega'],
        data['folio_politica'],
        data['nombre_empleado'],
        data.get('puesto_departamento', ''),
        data['equipo_asignado'],
        data['marca'],
        data['modelo'],
        data['motivo_entrega'],
        data['fecha_devolucion'],
        data['estado_fisico_entrega'],
        data.get('operatividad', '100% Operativo y Funcional'),
        data['dictamen_no_adeudo'],
        data.get('monto_retencion', '$0.00'),
        data.get('accesorios_devueltos', 'Completos'),
        data.get('accesorios_faltantes', 'Ninguno'),
        data.get('observaciones', ''),
        data['responsable_sistemas'],
        now_str,
        estado_firma,
        pdf_filename,
        signature_filename
    ))
    new_id = cursor.lastrowid

    if equipos_devueltos:
        for eq in equipos_devueltos:
            pe_id = eq.get('politica_equipo_id')
            cursor.execute('''
                INSERT INTO entrega_equipos (
                    folio_entrega,
                    politica_equipo_id,
                    equipo_asignado,
                    marca,
                    modelo,
                    estado_fisico_entrega,
                    operatividad,
                    accesorios_devueltos,
                    accesorios_faltantes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['folio_entrega'],
                pe_id,
                eq['equipo_asignado'],
                eq['marca'],
                eq['modelo'],
                eq.get('estado_fisico_entrega', data['estado_fisico_entrega']),
                eq.get('operatividad', data.get('operatividad', '100% Operativo y Funcional')),
                eq.get('accesorios_devueltos', data.get('accesorios_devueltos', '')),
                eq.get('accesorios_faltantes', data.get('accesorios_faltantes', 'Ninguno'))
            ))

            if pe_id:
                cursor.execute('''
                    UPDATE politica_equipos
                    SET estado_devolucion = 'Devuelto',
                        folio_entrega = ?,
                        fecha_devolucion = ?
                    WHERE id = ?
                ''', (data['folio_entrega'], data['fecha_devolucion'], pe_id))
            else:
                cursor.execute('''
                    UPDATE politica_equipos
                    SET estado_devolucion = 'Devuelto',
                        folio_entrega = ?,
                        fecha_devolucion = ?
                    WHERE folio_politica = ? AND equipo_asignado = ? AND estado_devolucion = 'En Resguardo'
                ''', (data['folio_entrega'], data['fecha_devolucion'], data['folio_politica'], eq['equipo_asignado']))

    conn.commit()
    conn.close()
    return new_id

def get_all_entregas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entregas ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_entrega_by_folio(folio_entrega):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entregas WHERE folio_entrega = ?', (folio_entrega,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_entrega_by_folio_politica(folio_politica):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entregas WHERE folio_politica = ? ORDER BY id DESC', (folio_politica,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_entregas_by_folio_politica(folio_politica):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entregas WHERE folio_politica = ? ORDER BY id DESC', (folio_politica,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_equipos_by_folio_entrega(folio_entrega):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entrega_equipos WHERE folio_entrega = ? ORDER BY id ASC', (folio_entrega,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_politicas_with_dev_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM politicas ORDER BY id DESC')
    politicas = [dict(row) for row in cursor.fetchall()]

    for pol in politicas:
        cursor.execute('SELECT * FROM politica_equipos WHERE folio_politica = ? ORDER BY id ASC', (pol['folio'],))
        equipos = [dict(eq) for eq in cursor.fetchall()]
        pol['equipos'] = equipos
        pol['total_equipos'] = len(equipos)
        pol['devueltos_count'] = sum(1 for eq in equipos if eq['estado_devolucion'] == 'Devuelto')
        pol['pendientes_count'] = pol['total_equipos'] - pol['devueltos_count']

        cursor.execute('SELECT * FROM entregas WHERE folio_politica = ? ORDER BY id DESC', (pol['folio'],))
        entregas = [dict(e) for e in cursor.fetchall()]
        pol['entregas'] = entregas

        if entregas:
            pol['folio_entrega'] = entregas[0]['folio_entrega']
            pol['dictamen_no_adeudo'] = entregas[0]['dictamen_no_adeudo']
            pol['fecha_devolucion'] = entregas[0]['fecha_devolucion']
        else:
            pol['folio_entrega'] = None
            pol['dictamen_no_adeudo'] = None
            pol['fecha_devolucion'] = None

        if pol['total_equipos'] > 0 and pol['pendientes_count'] == 0:
            pol['estado_resguardo'] = 'Devuelto Total'
        elif pol['devueltos_count'] > 0 and pol['pendientes_count'] > 0:
            pol['estado_resguardo'] = 'Devolución Parcial'
        else:
            pol['estado_resguardo'] = 'En Resguardo'

    conn.close()
    return politicas

def get_politicas_disponibles_para_devolucion():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT p.* FROM politicas p
        JOIN politica_equipos pe ON p.folio = pe.folio_politica
        WHERE pe.estado_devolucion = 'En Resguardo'
        ORDER BY p.id DESC
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    for pol in rows:
        cursor.execute('SELECT * FROM politica_equipos WHERE folio_politica = ? AND estado_devolucion = "En Resguardo" ORDER BY id ASC', (pol['folio'],))
        pol['equipos_pendientes'] = [dict(eq) for eq in cursor.fetchall()]
    conn.close()
    return rows

def update_nombre_empleado(folio, nuevo_nombre):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE politicas SET nombre_empleado = ? WHERE folio = ?', (nuevo_nombre, folio))
    cursor.execute('UPDATE entregas SET nombre_empleado = ? WHERE folio_politica = ?', (nuevo_nombre, folio))
    conn.commit()
    conn.close()
