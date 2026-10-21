import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable
)
from reportlab.pdfgen import canvas
from PIL import Image as PILImage
from config import LOGO_PATH, TEMPLATE_PATH, PDF_STORAGE_DIR

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6c757d"))
        
        # Footer line
        self.setStrokeColor(colors.HexColor("#dee2e6"))
        self.setLineWidth(0.5)
        self.line(36, 32, letter[0] - 36, 32)
        
        # Footer text
        footer_text = f"Documento confidencial generado por el Sistema de Gestión de Políticas | Página {self._pageNumber} de {page_count}"
        self.drawString(36, 20, footer_text)
        self.restoreState()


def get_scaled_image(path, max_width=140, max_height=50):
    if not os.path.exists(path):
        return None
    try:
        with PILImage.open(path) as img:
            w, h = img.size
            aspect = h / float(w)
            
            calc_w = max_width
            calc_h = calc_w * aspect
            
            if calc_h > max_height:
                calc_h = max_height
                calc_w = calc_h / aspect
                
            return RLImage(path, width=calc_w, height=calc_h)
    except Exception as e:
        print(f"Error loading image {path}: {e}")
        return None


def generate_policy_pdf(data, signature_path=None):
    """
    Generates a PDF using the policy template and form data.
    Supports single or multiple equipment assignments.
    """
    folio = data['folio']
    pdf_filename = f"{folio}.pdf"
    pdf_filepath = os.path.join(PDF_STORAGE_DIR, pdf_filename)

    # Read template text
    raw_template = ""
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            raw_template = f.read()
    else:
        raw_template = "POLÍTICA DE USO Y ASIGNACIÓN DE EQUIPO\nFolio: {folio}\nEmpleado: {nombre_empleado}"

    equipos = data.get('equipos') or [{
        'equipo_asignado': data.get('equipo_asignado', ''),
        'marca': data.get('marca', ''),
        'modelo': data.get('modelo', ''),
        'estado_fisico': data.get('estado_fisico', ''),
        'notas': data.get('notas', '')
    }]

    # Replace placeholders in template text
    replacements = {
        "{folio}": data.get("folio", ""),
        "{nombre_empleado}": data.get("nombre_empleado", ""),
        "{equipo_asignado}": data.get("equipo_asignado", ""),
        "{marca}": data.get("marca", ""),
        "{modelo}": data.get("modelo", ""),
        "{fecha_entrega}": data.get("fecha_entrega", ""),
        "{estado_fisico}": data.get("estado_fisico", ""),
        "{notas}": data.get("notas", "") or "Sin notas adicionales"
    }
    
    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1B4D3E'),
        alignment=1 # Center
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#53635B'),
        alignment=1
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1B4D3E'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1A2421')
    )

    table_label_style = ParagraphStyle(
        'TableLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1B4D3E')
    )

    table_value_style = ParagraphStyle(
        'TableValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#1A2421')
    )

    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    tb_val_center = ParagraphStyle(
        'TableValCenter',
        parent=table_value_style,
        fontSize=8,
        leading=10,
        alignment=1
    )

    tb_val_small = ParagraphStyle(
        'TableValSmall',
        parent=table_value_style,
        fontSize=8,
        leading=10
    )

    story = []

    # 1. HEADER WITH LOGO AND METADATA
    logo_img = get_scaled_image(LOGO_PATH, max_width=150, max_height=55)
    
    header_info = [
        [
            logo_img if logo_img else Paragraph("<b>PARAÍSO COUNTRY CLUB</b>", subtitle_style),
            Paragraph(
                "<b>POLÍTICA DE USO Y CONSIGNACIÓN DE EQUIPO DE CÓMPUTO</b><br/>"
                "<font size=7 color='#53635B'>CÓDIGO: AP-RH-PO-001 | VERSIÓN 3.0 | ÁREA DE SISTEMAS</font>",
                title_style
            ),
            Paragraph(
                f"<font size=8 color='#53635B'>FOLIO OFICIAL</font><br/>"
                f"<font size=12 color='#1B4D3E'><b>{folio}</b></font><br/>"
                f"<font size=7 color='#53635B'>Fecha: {data.get('fecha_entrega')}</font>",
                subtitle_style
            )
        ]
    ]

    header_table = Table(header_info, colWidths=[130, 290, 120])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FDFBF7')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 2. CAPTURED EQUIPMENT DATA TABLE
    story.append(Paragraph("1. DATOS DEL RESGUARDO Y ESPECIFICACIONES DE LOS EQUIPOS", section_heading))
    
    # Overview table
    overview_data = [
        [
            Paragraph("Nombre del Colaborador:", table_label_style),
            Paragraph(f"<b>{data.get('nombre_empleado', '')}</b>", table_value_style),
            Paragraph("Fecha de Asignación:", table_label_style),
            Paragraph(data.get('fecha_entrega', ''), table_value_style)
        ],
        [
            Paragraph("Total de Equipos:", table_label_style),
            Paragraph(f"<b>{len(equipos)} activo(s) consignado(s)</b>", table_value_style),
            Paragraph("Modalidad de Firma:", table_label_style),
            Paragraph("<font color='#1B4D3E'><b>Registrada Digitalmente</b></font>" if signature_path else "<font color='#B3924C'><b>Firma Física</b></font>", table_value_style)
        ]
    ]

    overview_table = Table(overview_data, colWidths=[130, 160, 120, 130])
    overview_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F4EFE6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F4EFE6')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 5))

    # Detailed items table
    eq_table_data = [
        [
            Paragraph("#", th_style),
            Paragraph("Equipo Asignado", th_style),
            Paragraph("Marca &bull; Modelo", th_style),
            Paragraph("Estado Físico", th_style),
            Paragraph("Notas / Accesorios / Serie", th_style)
        ]
    ]

    for idx, eq in enumerate(equipos, start=1):
        notas_txt = eq.get('notas', '').strip() or "Sin observaciones adicionales"
        eq_table_data.append([
            Paragraph(str(idx), tb_val_center),
            Paragraph(f"<b>{eq.get('equipo_asignado', '')}</b>", tb_val_small),
            Paragraph(f"{eq.get('marca', '')}<br/><font color='#53635B'>{eq.get('modelo', '')}</font>", tb_val_small),
            Paragraph(f"<b>{eq.get('estado_fisico', '')}</b>", tb_val_small),
            Paragraph(notas_txt, tb_val_small)
        ])

    eq_table = Table(eq_table_data, colWidths=[25, 125, 125, 115, 150])
    eq_style = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4D3E')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    # Alternating row colors
    for r in range(1, len(eq_table_data)):
        bg = colors.HexColor('#FFFFFF') if r % 2 != 0 else colors.HexColor('#FDFBF7')
        eq_style.append(('BACKGROUND', (0, r), (-1, r), bg))

    eq_table.setStyle(TableStyle(eq_style))
    story.append(eq_table)
    story.append(Spacer(1, 10))

    # 3. POLICY TEXT FROM TEMPLATE
    story.append(Paragraph("2. TÉRMINOS, CONDICIONES Y RESPONSIVA DE CONSIGNACIÓN", section_heading))

    # Parse template content blocks
    paragraphs_raw = raw_template.split('\n\n')
    for block in paragraphs_raw:
        block = block.strip()
        if not block:
            continue
        # Skip repetitive headers that we already formatted above
        if "POLÍTICA DE USO" in block or "DATOS DEL EQUIPO" in block or block.startswith("CÓDIGO:"):
            continue
        
        # Apply placeholder replacements
        for placeholder, val in replacements.items():
            block = block.replace(placeholder, str(val))
            
        clean_html = block.replace("\n", "<br/>")
        
        # Detect section headings (numbered 1-9) and RESPONSIVA
        is_heading = False
        for n in range(1, 10):
            if clean_html.startswith(f"{n}."):
                is_heading = True
                break
        if "RESPONSIVA" in clean_html:
            is_heading = True
        
        if is_heading:
            story.append(Paragraph(f"<b>{clean_html}</b>", body_style))
        else:
            story.append(Paragraph(clean_html, body_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))

    # 4. SIGNATURE SECTION
    story.append(Paragraph("3. CONFORMIDAD Y FIRMAS DE ENTREGA - RECEPCIÓN", section_heading))
    story.append(Paragraph("<font size=7 color='#6c757d'>El colaborador manifiesta haber recibido los equipos detallados a entera satisfacción y bajo las condiciones descritas en este instrumento.</font>", subtitle_style))
    story.append(Spacer(1, 6))

    sig_img_flowable = None
    if signature_path and os.path.exists(signature_path):
        sig_img_flowable = get_scaled_image(signature_path, max_width=180, max_height=65)

    if not sig_img_flowable:
        sig_box_employee = Paragraph("<br/><br/><br/>", body_style)
    else:
        sig_box_employee = sig_img_flowable

    sig_box_company = Paragraph("<br/><br/><br/>", body_style)

    signatures_matrix = [
        [
            sig_box_employee,
            sig_box_company
        ],
        [
            Paragraph(
                f"_______________________________________<br/>"
                f"<b>{data.get('nombre_empleado', 'EMPLEADO').upper()}</b><br/>"
                f"<font size=7 color='#495057'>Nombre y Firma de Conformidad (Receptor)</font><br/>"
                f"<font size=7 color='#198754'>Firma Digital Registrada en Sistema</font>" if signature_path else
                f"_______________________________________<br/>"
                f"<b>{data.get('nombre_empleado', 'EMPLEADO').upper()}</b><br/>"
                f"<font size=7 color='#495057'>Nombre y Firma Autógrafa (Receptor)</font>",
                subtitle_style
            ),
            Paragraph(
                "_______________________________________<br/>"
                "<b>ÁREA DE SISTEMAS E INFRAESTRUCTURA</b><br/>"
                "<font size=7 color='#495057'>Entrega y Validación de Inventario (Emisor)</font><br/>"
                f"<font size=7 color='#6c757d'>Fecha: {data.get('fecha_entrega')}</font>",
                subtitle_style
            )
        ]
    ]

    sig_table = Table(signatures_matrix, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
    ]))

    story.append(KeepTogether([sig_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return pdf_filename, pdf_filepath


def generate_entrega_pdf(data, signature_path=None):
    """
    Genera el documento formal:
    'Acta de Entrega-Recepción y Carta de No Adeudo de Equipo de Cómputo'
    Vinculado al Folio de Asignación de la Política original.
    Soporta devolución única, parcial o múltiple.
    """
    folio_entrega = data['folio_entrega']
    folio_politica = data['folio_politica']
    pdf_filename = f"{folio_entrega}.pdf"
    pdf_filepath = os.path.join(PDF_STORAGE_DIR, pdf_filename)

    equipos_devueltos = data.get('equipos_devueltos') or [{
        'equipo_asignado': data.get('equipo_asignado', ''),
        'marca': data.get('marca', ''),
        'modelo': data.get('modelo', ''),
        'estado_fisico_entrega': data.get('estado_fisico_entrega', ''),
        'operatividad': data.get('operatividad', '100% Operativo y Funcional'),
        'accesorios_devueltos': data.get('accesorios_devueltos', 'Completos'),
        'accesorios_faltantes': data.get('accesorios_faltantes', 'Ninguno')
    }]

    es_parcial = data.get('es_parcial', False)

    doc = SimpleDocTemplate(
        pdf_filepath,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitleDev',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1B4D3E'),
        alignment=1
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitleDev',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#53635B'),
        alignment=1
    )

    section_heading = ParagraphStyle(
        'SectionHeadingDev',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1B4D3E'),
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'DocBodyDev',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor('#1A2421')
    )

    table_label_style = ParagraphStyle(
        'TableLabelDev',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1B4D3E')
    )

    table_value_style = ParagraphStyle(
        'TableValueDev',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1A2421')
    )

    th_style = ParagraphStyle(
        'ThDev',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
        alignment=1
    )

    tb_val_center = ParagraphStyle(
        'TbValCenterDev',
        parent=table_value_style,
        fontSize=7.5,
        leading=9.5,
        alignment=1
    )

    tb_val_small = ParagraphStyle(
        'TbValSmallDev',
        parent=table_value_style,
        fontSize=7.5,
        leading=9.5
    )

    story = []

    # 1. ENCABEZADO OFICIAL CON LOGOTIPO
    logo_img = get_scaled_image(LOGO_PATH, max_width=140, max_height=52)

    subtitulo_acta = "<font size=6.5 color='#B3924C'><b>CONSTANCIA OFICIAL DE DEVOLUCIÓN PARCIAL DE ACTIVOS TI</b></font>" if es_parcial else "<font size=6.5 color='#B3924C'><b>CONSTANCIA OFICIAL DE FINIQUITO TOTAL DE RESGUARDO TECNOLÓGICO</b></font>"

    header_info = [
        [
            logo_img if logo_img else Paragraph("<b>PARAÍSO COUNTRY CLUB</b>", subtitle_style),
            Paragraph(
                "<b>ACTA DE ENTREGA - RECEPCIÓN Y CARTA DE NO ADEUDO DE EQUIPO</b><br/>"
                "<font size=6.5 color='#53635B'>CÓDIGO: AP-RH-FO-002 | VERSIÓN 3.0 | DIRECCIÓN DE TECNOLOGÍA E INFRAESTRUCTURA</font><br/>"
                f"{subtitulo_acta}",
                title_style
            ),
            Paragraph(
                f"<font size=7 color='#53635B'>FOLIO DEVOLUCIÓN</font><br/>"
                f"<font size=11 color='#1B4D3E'><b>{folio_entrega}</b></font><br/>"
                f"<font size=7 color='#53635B'>FOLIO ORIGEN:</font> <font size=7.5 color='#B3924C'><b>{folio_politica}</b></font><br/>"
                f"<font size=6.5 color='#53635B'>Fecha: {data.get('fecha_devolucion')}</font>",
                subtitle_style
            )
        ]
    ]

    header_table = Table(header_info, colWidths=[120, 305, 115])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FDFBF7')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 7))

    # 2. DATOS DEL COLABORADOR Y VINCULACIÓN
    story.append(Paragraph("1. DATOS DEL COLABORADOR Y ANTECEDENTES DE ASIGNACIÓN", section_heading))

    datos_colaborador = [
        [
            Paragraph("Nombre del Colaborador:", table_label_style),
            Paragraph(f"<b>{data.get('nombre_empleado', '')}</b>", table_value_style),
            Paragraph("Folio Asignación Original:", table_label_style),
            Paragraph(f"<b>{folio_politica}</b>", table_value_style)
        ],
        [
            Paragraph("Puesto / Área:", table_label_style),
            Paragraph(data.get('puesto_departamento', '') or "No especificado", table_value_style),
            Paragraph("Fecha de Devolución:", table_label_style),
            Paragraph(data.get('fecha_devolucion', ''), table_value_style)
        ],
        [
            Paragraph("Motivo de la Entrega:", table_label_style),
            Paragraph(f"<b>{data.get('motivo_entrega', '')}</b>", table_value_style),
            Paragraph("Responsable TI que Recibe:", table_label_style),
            Paragraph(data.get('responsable_sistemas', ''), table_value_style)
        ]
    ]

    t_colab = Table(datos_colaborador, colWidths=[125, 155, 125, 135])
    t_colab.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F4EFE6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F4EFE6')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_colab)
    story.append(Spacer(1, 7))

    # 3. VERIFICACIÓN FÍSICA Y TÉCNICA DEL EQUIPO
    story.append(Paragraph("2. DICTAMEN DE INSPECCIÓN FÍSICA, TÉCNICA Y ACCESORIOS DE LOS EQUIPOS", section_heading))

    estado_dictamen = data.get('dictamen_no_adeudo', 'LIBERADO (NO ADEUDO)')
    es_liberado = 'LIBERADO' in estado_dictamen.upper()

    # Table of returned items
    eq_dev_table_data = [
        [
            Paragraph("#", th_style),
            Paragraph("Equipo Recibido", th_style),
            Paragraph("Marca &bull; Modelo", th_style),
            Paragraph("Estado Físico", th_style),
            Paragraph("Operatividad", th_style),
            Paragraph("Accesorios Devueltos / Faltantes", th_style)
        ]
    ]

    for idx, eq in enumerate(equipos_devueltos, start=1):
        faltantes = eq.get('accesorios_faltantes', 'Ninguno')
        faltantes_html = "<font color='#1B4D3E'>Completo</font>" if faltantes in ['Ninguno', '', None] else f"<font color='#B94A48'><b>Faltan: {faltantes}</b></font>"
        acc_txt = f"{eq.get('accesorios_devueltos', 'Completos')}<br/>{faltantes_html}"

        eq_dev_table_data.append([
            Paragraph(str(idx), tb_val_center),
            Paragraph(f"<b>{eq.get('equipo_asignado', '')}</b>", tb_val_small),
            Paragraph(f"{eq.get('marca', '')} / {eq.get('modelo', '')}", tb_val_small),
            Paragraph(f"<b>{eq.get('estado_fisico_entrega', '')}</b>", tb_val_small),
            Paragraph(eq.get('operatividad', '100% Funcional'), tb_val_small),
            Paragraph(acc_txt, tb_val_small)
        ])

    t_eq_dev = Table(eq_dev_table_data, colWidths=[20, 115, 105, 95, 95, 110])
    eq_dev_style = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B4D3E')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]
    for r in range(1, len(eq_dev_table_data)):
        bg = colors.HexColor('#FFFFFF') if r % 2 != 0 else colors.HexColor('#FDFBF7')
        eq_dev_style.append(('BACKGROUND', (0, r), (-1, r), bg))

    t_eq_dev.setStyle(TableStyle(eq_dev_style))
    story.append(t_eq_dev)
    story.append(Spacer(1, 5))

    # Dictamen summary row table
    dictamen_data = [
        [
            Paragraph("Dictamen de No Adeudo:", table_label_style),
            Paragraph(
                "<font color='#1B4D3E'><b>LIBERADO (SIN ADEUDOS)</b></font>" if es_liberado
                else "<font color='#B94A48'><b>CON OBSERVACIONES / RETENCIÓN</b></font>",
                table_value_style
            ),
            Paragraph("Monto Cargo / Retención:", table_label_style),
            Paragraph(f"<b>{data.get('monto_retencion', '$0.00')}</b>", table_value_style)
        ],
        [
            Paragraph("Observaciones Técnicas:", table_label_style),
            Paragraph(data.get('observaciones', '') or "Sin incidencias ni faltantes registrados durante la revisión.", table_value_style),
            Paragraph("Modalidad de Firma:", table_label_style),
            Paragraph("<font color='#1B4D3E'><b>Registrada Digitalmente</b></font>" if signature_path else "<font color='#B3924C'><b>Firma Física Autógrafa</b></font>", table_value_style)
        ]
    ]

    t_dictamen = Table(dictamen_data, colWidths=[125, 155, 125, 135])
    t_dictamen.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F4EFE6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F4EFE6')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_dictamen)
    story.append(Spacer(1, 7))

    # 4. CERTIFICACIÓN LEGAL Y DECLARATORIA DE NO ADEUDO
    story.append(Paragraph("3. CERTIFICACIÓN RIGUROSA DE NO ADEUDO Y DESLINDE DE RESPONSABILIDAD", section_heading))

    if es_liberado:
        if es_parcial:
            declaracion_html = (
                "<b>CONSTANCIA OFICIAL DE DEVOLUCIÓN PARCIAL Y LIBERACIÓN DE ACTIVOS:</b><br/>"
                f"En cumplimiento con lo estipulado en la <b>POLÍTICA DE USO Y ASIGNACIÓN DE EQUIPO (Código AP-RH-PO-001)</b>, "
                f"numeral 9 (RETIRO DEL EQUIPO), se hace constar que en la fecha indicada el colaborador <b>{data.get('nombre_empleado', '')}</b> "
                f"ha comparecido ante el Área de Sistemas e Infraestructura para realizar la entrega material y formal de los equipos arriba descritos, "
                f"amparados bajo el <b>Folio de Asignación {folio_politica}</b>.<br/><br/>"
                "Tras la rigurosa revisión técnica y funcional de los componentes entregados, se determina que dichos equipos han sido devueltos "
                "íntegros, en óptimas condiciones operativas y sin anomalías imputables por mal uso. Por lo anterior, el Área de Sistemas e Infraestructura "
                "<b>CERTIFICA QUE EL COLABORADOR NO PRESENTA ADEUDO RESPECTO A ESTOS ACTIVOS DEVUELTOS</b>.<br/><br/>"
                f"<i>NOTA IMPORTANTE: La presente acta formaliza una entrega parcial. Los equipos restantes asignados originalmente bajo el folio "
                f"<b>{folio_politica}</b> continúan en posesión y resguardo activo del colaborador hasta su entrega y dictamen posterior.</i>"
            )
            box_bg = colors.HexColor('#F2F7E6')
            box_border = colors.HexColor('#8BAE23')
        else:
            declaracion_html = (
                "<b>CONSTANCIA OFICIAL DE NO ADEUDO TOTAL DE ACTIVOS TECNOLÓGICOS:</b><br/>"
                f"En cumplimiento con lo estipulado en la <b>POLÍTICA DE USO Y ASIGNACIÓN DE EQUIPO (Código AP-RH-PO-001)</b>, "
                f"numeral 9 (RETIRO DEL EQUIPO), se hace constar que en la fecha indicada el colaborador <b>{data.get('nombre_empleado', '')}</b> "
                f"ha comparecido ante el Área de Sistemas e Infraestructura para realizar la entrega material y formal de la totalidad de equipos "
                f"amparados bajo el <b>Folio de Asignación {folio_politica}</b>.<br/><br/>"
                "Tras la rigurosa revisión técnica y funcional de los componentes físicos, sistemas lógicos, licencias, puertos y accesorios, "
                "se determina que el equipo ha sido devuelto íntegro, en óptimas condiciones operativas y sin anomalías imputables por mal uso. "
                "Por lo anterior, el Área de Sistemas e Infraestructura <b>CERTIFICA QUE EL COLABORADOR NO PRESENTA ADEUDO ALGUNO</b> por concepto "
                "de herramientas de cómputo, dispositivos móviles ni accesorios de TI propiedad de Paraíso Country Club.<br/><br/>"
                "En consecuencia, se extiende la presente <b>CARTA DE NO ADEUDO TOTAL DE EQUIPO</b>, liberándolo formalmente de toda responsabilidad civil, laboral "
                "o patrimonial respecto a los bienes descritos, autorizando la continuación de sus trámites administrativos de finiquito o reasignación ante el "
                "Departamento de Recursos Humanos."
            )
            box_bg = colors.HexColor('#F2F7E6')
            box_border = colors.HexColor('#8BAE23')
    else:
        declaracion_html = (
            "<b>DICTAMEN CON SALVEDAD / RETENCIÓN DE FINIQUITO:</b><br/>"
            f"En la revisión técnica de los equipos correspondientes al <b>Folio de Asignación {folio_politica}</b>, a cargo del colaborador "
            f"<b>{data.get('nombre_empleado', '')}</b>, se identificaron anomalías físicas, daños por negligencia o faltantes de accesorios "
            f"detallados en el apartado 2 del presente instrumento.<br/><br/>"
            f"Conforme a la carta responsiva previamente aceptada, se notifica formalmente al Departamento de Recursos Humanos la retención / deducción "
            f"en finiquito por el importe estimado de <b>{data.get('monto_retencion', '$0.00')}</b>, amparando los costos de reparación, reposición o restitución "
            "del equipo o accesorios faltantes."
        )
        box_bg = colors.HexColor('#FAF6ED')
        box_border = colors.HexColor('#B3924C')

    declaracion_p = Paragraph(declaracion_html, body_style)
    dec_table = Table([[declaracion_p]], colWidths=[540])
    dec_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, box_border),
        ('BACKGROUND', (0, 0), (-1, -1), box_bg),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(dec_table)
    story.append(Spacer(1, 8))

    # 5. BLOQUE DE FIRMAS (Colaborador que entrega y Sistemas que recibe)
    story.append(Paragraph("4. CONFORMIDAD Y FIRMAS DE ENTREGA - RECEPCIÓN", section_heading))
    story.append(Paragraph("<font size=7 color='#53635B'>Las partes suscriben la presente acta en señal de conformidad sobre el estado del equipo y la liberación de adeudo asentada.</font>", subtitle_style))
    story.append(Spacer(1, 6))

    sig_img_flowable = None
    if signature_path and os.path.exists(signature_path):
        sig_img_flowable = get_scaled_image(signature_path, max_width=180, max_height=65)

    sig_box_employee = sig_img_flowable if sig_img_flowable else Paragraph("<br/><br/><br/>", body_style)
    sig_box_sistemas = Paragraph("<br/><br/><br/>", body_style)

    signatures_matrix = [
        [
            sig_box_employee,
            sig_box_sistemas
        ],
        [
            Paragraph(
                f"_______________________________________<br/>"
                f"<b>{data.get('nombre_empleado', 'COLABORADOR').upper()}</b><br/>"
                f"<font size=7 color='#53635B'>Entrega de Equipo (Colaborador)</font><br/>"
                f"<font size=7 color='#1B4D3E'>Firma Digital Registrada en Sistema</font>" if signature_path else
                f"_______________________________________<br/>"
                f"<b>{data.get('nombre_empleado', 'COLABORADOR').upper()}</b><br/>"
                f"<font size=7 color='#53635B'>Nombre y Firma Autógrafa de Conformidad</font>",
                subtitle_style
            ),
            Paragraph(
                f"_______________________________________<br/>"
                f"<b>{data.get('responsable_sistemas', 'ÁREA DE SISTEMAS').upper()}</b><br/>"
                f"<font size=7 color='#53635B'>Recepción e Inspección Técnica</font><br/>"
                f"<font size=7 color='#1B4D3E'>Sistemas e Infraestructura</font><br/>"
                f"<font size=6.5 color='#6c757d'>Fecha: {data.get('fecha_devolucion')}</font>",
                subtitle_style
            )
        ]
    ]

    sig_table = Table(signatures_matrix, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
    ]))

    story.append(KeepTogether([sig_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    return pdf_filename, pdf_filepath
