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
    story.append(Spacer(1, 10))

    # 2. CAPTURED EQUIPMENT DATA TABLE
    story.append(Paragraph("1. DATOS DEL RESGUARDO Y ESPECIFICACIONES DEL EQUIPO", section_heading))
    
    details_data = [
        [
            Paragraph("Nombre del Empleado:", table_label_style),
            Paragraph(f"<b>{data.get('nombre_empleado', '')}</b>", table_value_style),
            Paragraph("Fecha de Asignación:", table_label_style),
            Paragraph(data.get('fecha_entrega', ''), table_value_style)
        ],
        [
            Paragraph("Equipo Asignado:", table_label_style),
            Paragraph(data.get('equipo_asignado', ''), table_value_style),
            Paragraph("Estado Físico:", table_label_style),
            Paragraph(f"<b>{data.get('estado_fisico', '')}</b>", table_value_style)
        ],
        [
            Paragraph("Marca:", table_label_style),
            Paragraph(data.get('marca', ''), table_value_style),
            Paragraph("Modelo:", table_label_style),
            Paragraph(data.get('modelo', ''), table_value_style)
        ],
        [
            Paragraph("Notas / Accesorios:", table_label_style),
            Paragraph(data.get('notas') if data.get('notas') else "Sin observaciones adicionales", table_value_style),
            Paragraph("Estado de Firma:", table_label_style),
            Paragraph("<font color='#1B4D3E'><b>Registrada Digitalmente</b></font>" if signature_path else "<font color='#B3924C'><b>Pendiente</b></font>", table_value_style)
        ]
    ]

    details_table = Table(details_data, colWidths=[120, 160, 120, 140])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F4EFE6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#F4EFE6')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D8CDBD')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8DFD0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(details_table)
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
            
        # Clean inline line breaks to standard html breaks
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

    # 4. SIGNATURE SECTION (Digital + Physical printing support)
    story.append(Paragraph("3. CONFORMIDAD Y FIRMAS DE ENTREGA - RECEPCIÓN", section_heading))
    story.append(Paragraph("<font size=7 color='#6c757d'>El colaborador manifiesta haber recibido el equipo a entera satisfacción y bajo las condiciones descritas en este instrumento.</font>", subtitle_style))
    story.append(Spacer(1, 6))

    # Employee signature image if present
    sig_img_flowable = None
    if signature_path and os.path.exists(signature_path):
        sig_img_flowable = get_scaled_image(signature_path, max_width=180, max_height=65)

    if not sig_img_flowable:
        sig_box_employee = Paragraph("<br/><br/><br/>", body_style)
    else:
        sig_box_employee = sig_img_flowable

    sig_box_company = Paragraph("<br/><font size=7 color='#6c757d'>Sello y Validación de Soporte TI</font><br/><br/>", subtitle_style)

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

    # Build PDF with custom canvas for page numbering
    doc.build(story, canvasmaker=NumberedCanvas)
    return pdf_filename, pdf_filepath
