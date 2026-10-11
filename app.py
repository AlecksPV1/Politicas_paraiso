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
    get_politica_by_folio
)
from pdf_generator import generate_policy_pdf

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
    records = get_all_politicas()
    total_count = len(records)
    signed_count = sum(1 for r in records if 'Digitalmente' in r['estado_firma'])
    pending_count = total_count - signed_count
    last_folio = records[0]['folio'] if records else None

    return render_template(
        'dashboard.html',
        politicas=records,
        total_count=total_count,
        signed_count=signed_count,
        pending_count=pending_count,
        last_folio=last_folio
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
