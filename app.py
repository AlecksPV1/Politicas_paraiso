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
    get_equipos_by_folio_politica,
    get_equipos_pendientes_by_folio_politica,
    get_next_folio_entrega,
    save_entrega,
    get_all_entregas,
    get_entrega_by_folio,
    get_entrega_by_folio_politica,
    get_entregas_by_folio_politica,
    get_equipos_by_folio_entrega,
    get_politicas_with_dev_status,
    get_politicas_disponibles_para_devolucion,
    update_nombre_empleado
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
        nombre_empleado = request.form.get('nombre_empleado', '').strip()
        fecha_entrega = request.form.get('fecha_entrega', '').strip()
        signature_data = request.form.get('signature_data', '').strip()

        # Multi-equipment support
        equipos_asignados = request.form.getlist('equipo_asignado') or request.form.getlist('equipo_asignado[]')
        marcas = request.form.getlist('marca') or request.form.getlist('marca[]')
        modelos = request.form.getlist('modelo') or request.form.getlist('modelo[]')
        estados_fisicos = request.form.getlist('estado_fisico') or request.form.getlist('estado_fisico[]')
        notas_list = request.form.getlist('notas') or request.form.getlist('notas[]')

        if not nombre_empleado or not fecha_entrega:
            flash('El nombre del colaborador y la fecha de entrega son obligatorios.', 'error')
            return redirect(url_for('nueva_politica'))

        if not equipos_asignados or len(equipos_asignados) == 0:
            flash('Debe asignar al menos un equipo de cómputo o dispositivo.', 'error')
            return redirect(url_for('nueva_politica'))

        equipos = []
        for i in range(len(equipos_asignados)):
            eq = equipos_asignados[i].strip()
            ma = marcas[i].strip() if i < len(marcas) else ''
            mo = modelos[i].strip() if i < len(modelos) else ''
            ef = estados_fisicos[i].strip() if i < len(estados_fisicos) else ''
            nt = notas_list[i].strip() if i < len(notas_list) else ''

            if not all([eq, ma, mo, ef]):
                flash(f'Por favor completa todos los campos del equipo #{i+1} (*).', 'error')
                return redirect(url_for('nueva_politica'))

            equipos.append({
                'equipo_asignado': eq,
                'marca': ma,
                'modelo': mo,
                'estado_fisico': ef,
                'notas': nt
            })

        # Generate folio
        folio = get_next_folio()

        # Handle digital signature if captured
        signature_path = None
        signature_filename = None
        if signature_data and signature_data.startswith('data:image'):
            try:
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

        # Summary strings for legacy/list views
        equipo_summary = " + ".join([eq['equipo_asignado'] for eq in equipos]) if len(equipos) > 1 else equipos[0]['equipo_asignado']
        marca_summary = ", ".join([eq['marca'] for eq in equipos]) if len(equipos) > 1 else equipos[0]['marca']
        modelo_summary = ", ".join([eq['modelo'] for eq in equipos]) if len(equipos) > 1 else equipos[0]['modelo']
        estado_summary = ", ".join(list(dict.fromkeys([eq['estado_fisico'] for eq in equipos])))
        notas_summary = " | ".join([f"[{eq['equipo_asignado']}]: {eq['notas']}" for eq in equipos if eq['notas']]) or (equipos[0]['notas'] if equipos else '')

        data = {
            'folio': folio,
            'nombre_empleado': nombre_empleado,
            'equipo_asignado': equipo_summary,
            'marca': marca_summary,
            'modelo': modelo_summary,
            'fecha_entrega': fecha_entrega,
            'estado_fisico': estado_summary,
            'notas': notas_summary,
            'equipos': equipos
        }

        # Generate PDF
        try:
            pdf_filename, _ = generate_policy_pdf(data, signature_path=signature_path)
        except Exception as e:
            flash(f'Error al generar el documento PDF: {str(e)}', 'error')
            return redirect(url_for('nueva_politica'))

        # Save to SQLite
        save_politica(data, pdf_filename, signature_filename, equipos=equipos)

        flash(f'¡Política creada con éxito bajo el folio {folio}! Documento PDF generado con {len(equipos)} equipo(s) consignado(s).', 'success')
        return redirect(url_for('dashboard'))

    # GET Request
    next_folio = get_next_folio()
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('form.html', next_folio=next_folio, today_date=today_date)


@app.route('/editar-nombre/<folio>', methods=['POST'])
@login_required
def editar_nombre(folio):
    record = get_politica_by_folio(folio)
    if not record:
        abort(404, description="Política no encontrada")

    nuevo_nombre = request.form.get('nombre_empleado', '').strip()
    if not nuevo_nombre:
        flash('El nombre del colaborador no puede quedar vacío.', 'error')
        return redirect(url_for('dashboard'))

    if nuevo_nombre == record['nombre_empleado']:
        flash(f'El nombre de la política {folio} no tuvo cambios.', 'info')
        return redirect(url_for('dashboard'))

    nombre_anterior = record['nombre_empleado']
    update_nombre_empleado(folio, nuevo_nombre)

    # Regenerate PDFs so the printed name matches; folio and file names stay the same
    try:
        equipos = get_equipos_by_folio_politica(folio)
        data = dict(get_politica_by_folio(folio))
        data['equipos'] = equipos
        sig_path = os.path.join(config.SIGNATURE_STORAGE_DIR, data['signature_path']) if data['signature_path'] else None
        generate_policy_pdf(data, signature_path=sig_path)

        entregas = sorted(get_entregas_by_folio_politica(folio), key=lambda e: e['id'])
        entrega_ids = {e['folio_entrega']: e['id'] for e in entregas}
        for ent in entregas:
            # Partial if some equipment was still pending after this acta was issued
            restantes = [
                eq for eq in equipos
                if not eq['folio_entrega'] or entrega_ids.get(eq['folio_entrega'], 0) > ent['id']
            ]
            ent['es_parcial'] = len(restantes) > 0
            ent['equipos_devueltos'] = get_equipos_by_folio_entrega(ent['folio_entrega'])
            ent_sig_path = os.path.join(config.SIGNATURE_STORAGE_DIR, ent['signature_path']) if ent['signature_path'] else None
            generate_entrega_pdf(ent, signature_path=ent_sig_path)
    except Exception as e:
        flash(f'El nombre se actualizó, pero hubo un error al regenerar los documentos PDF: {str(e)}', 'warning')
        return redirect(url_for('dashboard'))

    flash(f'Nombre de la política {folio} corregido: "{nombre_anterior}" → "{nuevo_nombre}". Documentos PDF actualizados con el mismo folio.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/devoluciones')
@login_required
def devoluciones():
    entregas_raw = get_all_entregas()
    entregas = [dict(e) for e in entregas_raw]
    for e in entregas:
        e['equipos'] = get_equipos_by_folio_entrega(e['folio_entrega'])
        e['total_devueltos'] = len(e['equipos'])

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
        motivo_entrega = request.form.get('motivo_entrega', '').strip()
        fecha_devolucion = request.form.get('fecha_devolucion', '').strip()
        dictamen_no_adeudo = request.form.get('dictamen_no_adeudo', '').strip()
        monto_retencion = request.form.get('monto_retencion', '$0.00').strip()
        observaciones = request.form.get('observaciones', '').strip()
        responsable_sistemas = request.form.get('responsable_sistemas', '').strip()
        signature_data = request.form.get('signature_data', '').strip()

        # Selected equipment IDs from checkboxes
        selected_ids = request.form.getlist('selected_equipos') or request.form.getlist('selected_equipos[]')

        if not all([folio_politica, nombre_empleado, motivo_entrega, fecha_devolucion, dictamen_no_adeudo, responsable_sistemas]):
            flash('Por favor completa todos los campos requeridos (*).', 'error')
            return redirect(url_for('nueva_devolucion', folio_politica=folio_politica))

        # Check pending equipments for this policy
        pendientes = get_equipos_pendientes_by_folio_politica(folio_politica)
        if not pendientes:
            flash(f'La política {folio_politica} ya no cuenta con equipos pendientes de devolución.', 'warning')
            return redirect(url_for('devoluciones'))

        # If no specific equipment checkboxes were selected, check if there's a fallback single equipment
        equipos_devueltos = []
        if selected_ids:
            # Match selected IDs with pending items
            pendientes_map = {str(eq['id']): eq for eq in pendientes}
            for sid in selected_ids:
                if sid in pendientes_map:
                    base_eq = pendientes_map[sid]
                    ef = request.form.get(f'estado_fisico_entrega_{sid}') or request.form.get('estado_fisico_entrega', 'Excelente / Sin daños ni rayaduras')
                    op = request.form.get(f'operatividad_{sid}') or request.form.get('operatividad', '100% Operativo y Verificado (Sin bloqueos ni contraseñas)')
                    acc_dev = request.form.get(f'accesorios_devueltos_{sid}') or request.form.get('accesorios_devueltos', 'Completos')
                    acc_fal = request.form.get(f'accesorios_faltantes_{sid}') or request.form.get('accesorios_faltantes', 'Ninguno')

                    equipos_devueltos.append({
                        'politica_equipo_id': base_eq['id'],
                        'equipo_asignado': base_eq['equipo_asignado'],
                        'marca': base_eq['marca'],
                        'modelo': base_eq['modelo'],
                        'estado_fisico_entrega': ef,
                        'operatividad': op,
                        'accesorios_devueltos': acc_dev,
                        'accesorios_faltantes': acc_fal
                    })
        else:
            # Fallback for single equipment return or direct form post
            ef = request.form.get('estado_fisico_entrega', 'Excelente / Sin daños ni rayaduras')
            op = request.form.get('operatividad', '100% Operativo y Verificado (Sin bloqueos ni contraseñas)')
            acc_dev = request.form.get('accesorios_devueltos', 'Completos')
            acc_fal = request.form.get('accesorios_faltantes', 'Ninguno')
            eq_name = request.form.get('equipo_asignado') or (pendientes[0]['equipo_asignado'] if pendientes else 'Equipo')
            eq_marca = request.form.get('marca') or (pendientes[0]['marca'] if pendientes else '')
            eq_modelo = request.form.get('modelo') or (pendientes[0]['modelo'] if pendientes else '')
            pe_id = pendientes[0]['id'] if pendientes else None

            equipos_devueltos.append({
                'politica_equipo_id': pe_id,
                'equipo_asignado': eq_name,
                'marca': eq_marca,
                'modelo': eq_modelo,
                'estado_fisico_entrega': ef,
                'operatividad': op,
                'accesorios_devueltos': acc_dev,
                'accesorios_faltantes': acc_fal
            })

        if not equipos_devueltos:
            flash('Debe seleccionar al menos un equipo para procesar la entrega.', 'error')
            return redirect(url_for('nueva_devolucion', folio_politica=folio_politica))

        # Check if partial return (some equipments will still remain pending)
        es_parcial = len(equipos_devueltos) < len(pendientes)

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

        equipo_summary = ", ".join([eq['equipo_asignado'] for eq in equipos_devueltos])
        marca_summary = ", ".join([eq['marca'] for eq in equipos_devueltos])
        modelo_summary = ", ".join([eq['modelo'] for eq in equipos_devueltos])
        ef_summary = ", ".join(list(dict.fromkeys([eq['estado_fisico_entrega'] for eq in equipos_devueltos])))
        op_summary = ", ".join(list(dict.fromkeys([eq['operatividad'] for eq in equipos_devueltos])))
        acc_dev_summary = " | ".join([f"[{eq['equipo_asignado']}]: {eq['accesorios_devueltos']}" for eq in equipos_devueltos]) if len(equipos_devueltos) > 1 else equipos_devueltos[0]['accesorios_devueltos']
        acc_fal_summary = " | ".join([f"[{eq['equipo_asignado']}]: {eq['accesorios_faltantes']}" for eq in equipos_devueltos if eq['accesorios_faltantes'] and eq['accesorios_faltantes'] != 'Ninguno']) or 'Ninguno'

        data = {
            'folio_entrega': folio_entrega,
            'folio_politica': folio_politica,
            'nombre_empleado': nombre_empleado,
            'puesto_departamento': puesto_departamento,
            'equipo_asignado': equipo_summary,
            'marca': marca_summary,
            'modelo': modelo_summary,
            'motivo_entrega': motivo_entrega,
            'fecha_devolucion': fecha_devolucion,
            'estado_fisico_entrega': ef_summary,
            'operatividad': op_summary,
            'dictamen_no_adeudo': dictamen_no_adeudo,
            'monto_retencion': monto_retencion,
            'accesorios_devueltos': acc_dev_summary,
            'accesorios_faltantes': acc_fal_summary,
            'observaciones': observaciones,
            'responsable_sistemas': responsable_sistemas,
            'es_parcial': es_parcial,
            'equipos_devueltos': equipos_devueltos
        }

        try:
            pdf_filename, _ = generate_entrega_pdf(data, signature_path=signature_path)
        except Exception as e:
            flash(f'Error al generar el documento PDF de devolución: {str(e)}', 'error')
            return redirect(url_for('nueva_devolucion', folio_politica=folio_politica))

        save_entrega(data, pdf_filename, signature_filename, equipos_devueltos=equipos_devueltos)

        if es_parcial:
            pendientes_restantes = len(pendientes) - len(equipos_devueltos)
            flash(f'¡Acta de Entrega Parcial {folio_entrega} generada con éxito! Se devolvieron {len(equipos_devueltos)} equipo(s). Quedan {pendientes_restantes} equipo(s) en resguardo bajo la política {folio_politica}.', 'info')
        else:
            flash(f'¡Acta de Entrega y Carta de No Adeudo Total {folio_entrega} generada con éxito para {nombre_empleado}! Todos los equipos han sido devueltos.', 'success')

        return redirect(url_for('devoluciones'))

    # GET Request
    target_folio = folio_politica or request.args.get('folio_politica')
    politica_seleccionada = None
    equipos_politica = []

    if target_folio:
        politica_seleccionada = get_politica_by_folio(target_folio)
        if politica_seleccionada:
            equipos_politica = get_equipos_by_folio_politica(target_folio)
            pendientes = [eq for eq in equipos_politica if eq['estado_devolucion'] == 'En Resguardo']
            if not pendientes:
                flash(f'Todos los equipos consignados bajo la política {target_folio} ya han sido devueltos formalmente.', 'warning')
                return redirect(url_for('devoluciones'))
        else:
            flash(f'No se encontró la política con folio {target_folio}.', 'error')

    next_folio_entrega = get_next_folio_entrega()
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    politicas_disponibles = get_politicas_disponibles_para_devolucion()

    return render_template(
        'entrega_form.html',
        next_folio_entrega=next_folio_entrega,
        today_date=today_date,
        politicas=politicas_disponibles,
        politica_seleccionada=politica_seleccionada,
        equipos_politica=equipos_politica
    )


@app.route('/descargar-devolucion/<folio_entrega>')
@login_required
def descargar_devolucion_pdf(folio_entrega):
    record = get_entrega_by_folio(folio_entrega)
    if not record:
        abort(404, description="Acta de entrega no encontrada")

    pdf_filename = record['pdf_path']
    force_download = request.args.get('download') == '1'

    return send_from_directory(
        config.PDF_STORAGE_DIR,
        pdf_filename,
        as_attachment=force_download,
        download_name=f"NoAdeudo_{folio_entrega}.pdf",
        mimetype='application/pdf'
    )


@app.route('/descargar/<folio>')
@login_required
def descargar_pdf(folio):
    record = get_politica_by_folio(folio)
    if not record:
        abort(404, description="Documento no encontrado")

    pdf_filename = record['pdf_path']
    force_download = request.args.get('download') == '1'

    return send_from_directory(
        config.PDF_STORAGE_DIR,
        pdf_filename,
        as_attachment=force_download,
        download_name=f"Politica_{folio}.pdf",
        mimetype='application/pdf'
    )


@app.route('/api/politica/<folio>')
@login_required
def api_politica(folio):
    record = get_politica_by_folio(folio)
    if not record:
        return jsonify({'error': 'No encontrado'}), 404
    data = dict(record)
    data['equipos'] = get_equipos_by_folio_politica(folio)
    data['equipos_pendientes'] = get_equipos_pendientes_by_folio_politica(folio)
    data['entregas'] = get_entregas_by_folio_politica(folio)
    return jsonify(data)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
