import os
import re
import base64
import datetime
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory,
    jsonify,
    abort
)
import config
from database import (
    init_db,
    get_next_folio,
    save_politica,
    get_all_politicas,
    get_politica_by_folio,
    get_next_folio_entrega,
    save_entrega,
    get_all_entregas,
    get_entrega_by_folio,
    get_entrega_by_folio_politica,
    get_politicas_with_dev_status
)
from pdf_generator import generate_policy_pdf, generate_entrega_pdf

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Initialize database tables on startup
init_db()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Por favor ingresa la contraseña maestra para acceder.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        entered_password = request.form.get('password', '').strip()
        if entered_password == config.MASTER_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            flash('¡Bienvenido al Sistema de Gestión de Políticas!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Contraseña maestra incorrecta. Acceso denegado.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))


@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    records = get_politicas_with_dev_status()
    total_count = len(records)
    signed_count = sum(1 for r in records if 'Digitalmente' in r['estado_firma'] or 'Digital' in r['estado_firma'])
    pending_count = total_count - signed_count
    last_folio = records[0]['folio'] if records else None

    # Devoluciones stats
    entregas = get_all_entregas()
    total_entregas = len(entregas)
    liberados_count = sum(1 for e in entregas if 'LIBERADO' in e['dictamen_no_adeudo'].upper())
    retenciones_count = total_entregas - liberados_count

    return render_template(
        'dashboard.html',
        politicas=records,
        total_count=total_count,
        signed_count=signed_count,
        pending_count=pending_count,
        last_folio=last_folio,
        total_entregas=total_entregas,
        liberados_count=liberados_count,
        retenciones_count=retenciones_count
    )


@app.route('/nueva-politica', methods=['GET', 'POST'])
@login_required
def nueva_politica():
    if request.method == 'POST':
        # Mandatory fields
        nombre_empleado = request.form.get('nombre_empleado', '').strip()
        equipo_asignado = request.form.get('equipo_asignado', '').strip()
        marca = request.form.get('marca', '').strip()
        modelo = request.form.get('modelo', '').strip()
        fecha_entrega = request.form.get('fecha_entrega', '').strip()
        estado_fisico = request.form.get('estado_fisico', '').strip()
        notas = request.form.get('notas', '').strip()
        signature_data = request.form.get('signature_data', '').strip()

        # Validation
        if not all([nombre_empleado, equipo_asignado, marca, modelo, fecha_entrega, estado_fisico, notas]):
            flash('Todos los campos marcados con asterisco (*) son obligatorios.', 'error')
            return redirect(url_for('nueva_politica'))

        # Generate folio
        folio = get_next_folio()

        # Handle digital signature if captured
        signature_path = None
        signature_filename = None
        if signature_data and signature_data.startswith('data:image'):
            try:
                # Remove header like data:image/png;base64,
                img_data_str = re.sub('^data:image/.+;base64,', '', signature_data)
                img_bytes = base64.b64decode(img_data_str)
                signature_filename = f"{folio}_signature.png"
                signature_path = os.path.join(config.SIGNATURE_STORAGE_DIR, signature_filename)
                with open(signature_path, 'wb') as f:
                    f.write(img_bytes)
            except Exception as e:
                print(f"Error procesando firma base64: {e}")
                signature_path = None
                signature_filename = None

        data = {
            'folio': folio,
            'nombre_empleado': nombre_empleado,
            'equipo_asignado': equipo_asignado,
            'marca': marca,
            'modelo': modelo,
            'fecha_entrega': fecha_entrega,
            'estado_fisico': estado_fisico,
            'notas': notas
        }

        # Generate PDF
        try:
            pdf_filename, _ = generate_policy_pdf(data, signature_path=signature_path)
        except Exception as e:
            flash(f'Error al generar el documento PDF: {str(e)}', 'error')
            return redirect(url_for('nueva_politica'))

        # Save to SQLite
        save_politica(data, pdf_filename, signature_filename)

        flash(f'¡Política creada con éxito bajo el folio {folio}! Documento PDF generado y listo para su descarga.', 'success')
        return redirect(url_for('dashboard'))

    # GET Request
    next_folio = get_next_folio()
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('form.html', next_folio=next_folio, today_date=today_date)


@app.route('/devoluciones')
@login_required
def devoluciones():
    entregas = get_all_entregas()
    total_entregas = len(entregas)
    liberados_count = sum(1 for e in entregas if 'LIBERADO' in e['dictamen_no_adeudo'].upper())
    retenciones_count = total_entregas - liberados_count
    last_folio = entregas[0]['folio_entrega'] if entregas else None

    return render_template(
        'entregas_list.html',
        entregas=entregas,
        total_entregas=total_entregas,
        liberados_count=liberados_count,
        retenciones_count=retenciones_count,
        last_folio=last_folio
    )


@app.route('/nueva-devolucion', methods=['GET', 'POST'])
@app.route('/nueva-devolucion/<folio_politica>', methods=['GET', 'POST'])
@login_required
def nueva_devolucion(folio_politica=None):
    if request.method == 'POST':
        folio_politica = request.form.get('folio_politica', '').strip()
        nombre_empleado = request.form.get('nombre_empleado', '').strip()
        puesto_departamento = request.form.get('puesto_departamento', '').strip()
        equipo_asignado = request.form.get('equipo_asignado', '').strip()
        marca = request.form.get('marca', '').strip()
        modelo = request.form.get('modelo', '').strip()
        motivo_entrega = request.form.get('motivo_entrega', '').strip()
        fecha_devolucion = request.form.get('fecha_devolucion', '').strip()
        estado_fisico_entrega = request.form.get('estado_fisico_entrega', '').strip()
        operatividad = request.form.get('operatividad', '').strip()
        dictamen_no_adeudo = request.form.get('dictamen_no_adeudo', '').strip()
        monto_retencion = request.form.get('monto_retencion', '$0.00').strip()
        accesorios_devueltos = request.form.get('accesorios_devueltos', '').strip()
        accesorios_faltantes = request.form.get('accesorios_faltantes', 'Ninguno').strip()
        observaciones = request.form.get('observaciones', '').strip()
        responsable_sistemas = request.form.get('responsable_sistemas', '').strip()
        signature_data = request.form.get('signature_data', '').strip()

        if not all([folio_politica, nombre_empleado, equipo_asignado, marca, modelo, motivo_entrega, fecha_devolucion, estado_fisico_entrega, dictamen_no_adeudo, responsable_sistemas]):
            flash('Por favor completa todos los campos requeridos (*).', 'error')
            return redirect(url_for('nueva_devolucion', folio_politica=folio_politica))

        folio_entrega = get_next_folio_entrega()

        signature_path = None
        signature_filename = None
        if signature_data and signature_data.startswith('data:image'):
            try:
                img_data_str = re.sub('^data:image/.+;base64,', '', signature_data)
                img_bytes = base64.b64decode(img_data_str)
                signature_filename = f"{folio_entrega}_signature.png"
                signature_path = os.path.join(config.SIGNATURE_STORAGE_DIR, signature_filename)
                with open(signature_path, 'wb') as f:
                    f.write(img_bytes)
            except Exception as e:
                print(f"Error procesando firma base64 entrega: {e}")
                signature_path = None
                signature_filename = None

        data = {
            'folio_entrega': folio_entrega,
            'folio_politica': folio_politica,
            'nombre_empleado': nombre_empleado,
            'puesto_departamento': puesto_departamento,
            'equipo_asignado': equipo_asignado,
            'marca': marca,
            'modelo': modelo,
            'motivo_entrega': motivo_entrega,
            'fecha_devolucion': fecha_devolucion,
            'estado_fisico_entrega': estado_fisico_entrega,
            'operatividad': operatividad,
            'dictamen_no_adeudo': dictamen_no_adeudo,
            'monto_retencion': monto_retencion,
            'accesorios_devueltos': accesorios_devueltos,
            'accesorios_faltantes': accesorios_faltantes,
            'observaciones': observaciones,
            'responsable_sistemas': responsable_sistemas
        }

        try:
            pdf_filename, _ = generate_entrega_pdf(data, signature_path=signature_path)
        except Exception as e:
            flash(f'Error al generar el documento PDF de devolución: {str(e)}', 'error')
            return redirect(url_for('nueva_devolucion', folio_politica=folio_politica))

        save_entrega(data, pdf_filename, signature_filename)

        flash(f'¡Acta de Entrega y Carta de No Adeudo {folio_entrega} generada con éxito para {nombre_empleado}!', 'success')
        return redirect(url_for('devoluciones'))

    # GET Request
    next_folio_entrega = get_next_folio_entrega()
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    politicas_disponibles = get_all_politicas()

    politica_seleccionada = None
    if folio_politica:
        politica_seleccionada = get_politica_by_folio(folio_politica)

    return render_template(
        'entrega_form.html',
        next_folio_entrega=next_folio_entrega,
        today_date=today_date,
        politicas=politicas_disponibles,
        politica_seleccionada=politica_seleccionada
    )


@app.route('/descargar-devolucion/<folio_entrega>')
@login_required
def descargar_devolucion_pdf(folio_entrega):
    record = get_entrega_by_folio(folio_entrega)
    if not record:
        abort(404, description="Acta de entrega no encontrada")

    pdf_filename = record['pdf_path']
    return send_from_directory(
        config.PDF_STORAGE_DIR,
        pdf_filename,
        as_attachment=True,
        download_name=f"NoAdeudo_{folio_entrega}.pdf"
    )


@app.route('/descargar/<folio>')
@login_required
def descargar_pdf(folio):
    record = get_politica_by_folio(folio)
    if not record:
        abort(404, description="Documento no encontrado")

    pdf_filename = record['pdf_path']
    return send_from_directory(
        config.PDF_STORAGE_DIR,
        pdf_filename,
        as_attachment=True,
        download_name=f"Politica_{folio}.pdf"
    )


@app.route('/api/politica/<folio>')
@login_required
def api_politica(folio):
    record = get_politica_by_folio(folio)
    if not record:
        return jsonify({'error': 'No encontrado'}), 404
    return jsonify(dict(record))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
