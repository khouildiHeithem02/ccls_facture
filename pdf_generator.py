import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def generate_facture_pdf(data, output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=0.5*cm,
        bottomMargin=0.5*cm,
    )

    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')

    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
        pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold')
        has_arial = True
    except:
        has_arial = False

    def reshaped_arabic(text):
        if not has_arial: return text
        return get_display(arabic_reshaper.reshape(text))

    font_name_bold = 'Arial-Bold' if has_arial else 'Helvetica-Bold'
    font_name_regular = 'Arial' if has_arial else 'Helvetica'

    center_style = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName=font_name_bold, fontSize=12)
    center_style_underlined = ParagraphStyle('CenterU', parent=styles['Normal'], alignment=1, fontName=font_name_bold, fontSize=11)
    
    fr_left_style = ParagraphStyle('FrLeft', parent=styles['Normal'], alignment=0, fontName=font_name_bold, fontSize=9)
    fr_left_style_regular = ParagraphStyle('FrLeftReg', parent=styles['Normal'], alignment=0, fontName=font_name_regular, fontSize=9)
    fr_right_style_regular = ParagraphStyle('FrRightReg', parent=styles['Normal'], alignment=2, fontName=font_name_regular, fontSize=11)
    ar_right_style = ParagraphStyle('ArRight', parent=styles['Normal'], alignment=2, fontName=font_name_bold, fontSize=10)

    # Top centered text
    elements.append(Paragraph(reshaped_arabic("الجمهورية الجزائرية الديمقراطية الشعبية"), center_style))
    elements.append(Paragraph("<u>REPUBLIQUE ALGERIENNE DEMOCRATIQUE ET POPULAIRE</u>", center_style_underlined))
    elements.append(Spacer(1, 5))

    # 3-Column Header Table
    fr_text = """Ministère de l'Agriculture et du Développement Rural<br/>
Office Algérien Interprofessionnel des Céréales<br/>
Coopérative des Céréales Et Légumes Secs<br/>
de Ouargla"""

    ar_text = f"""{reshaped_arabic("وزارة الفلاحة والتنمية الريفية")}<br/>
{reshaped_arabic("الديوان الجزائري المهني للحبوب")}<br/>
{reshaped_arabic("تعاونية الحبوب والبقول الجافة")}<br/>
{reshaped_arabic("ولاية ورقلة")}"""

    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')
    if os.path.exists(logo_path):
        header_logo = Image(logo_path, width=2.5*cm, height=3*cm)
    else:
        # Placeholder if no logo is found
        header_logo = Paragraph("<br/><b>[LOGO]</b><br/>O.A.I.C<br/>CCLS OUARGLA", center_style)

    header_table_data = [
        [Paragraph(fr_text, fr_left_style), header_logo, Paragraph(ar_text, ar_right_style)]
    ]
    
    header_t = Table(header_table_data, colWidths=[8*cm, 3*cm, 8*cm])
    header_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
    ]))
    
    elements.append(header_t)
    elements.append(Spacer(1, 0.3*cm))

    identity = data.get('identity', {})
    decompte_text = identity.get('decompte', '45465/2026')
    farmer_text = identity.get('farmer', '')
    address_text = identity.get('adresse', '')

    elements.append(Paragraph(f"<b>Decompte d'achat N° {decompte_text}</b>", center_style))
    elements.append(Spacer(1, 0.2*cm))
    
    nif_text = identity.get('nif', '')
    if not nif_text or str(nif_text).strip() == '':
        nif_text = 'Non'
    wilaya_text = identity.get('wilaya', '')
    elements.append(Paragraph(f"<b>Agriculteur:</b> {farmer_text}", fr_left_style_regular))
    if wilaya_text:
        elements.append(Paragraph(f"<b>Wilaya:</b> {wilaya_text}", fr_left_style_regular))
    elements.append(Paragraph(f"<b>L'adresse:</b> {address_text}", fr_left_style_regular))
    elements.append(Paragraph(f"<b>NIF:</b> {nif_text}", fr_left_style_regular))
    elements.append(Spacer(1, 0.3*cm))

    # Top Table Data
    # 7 columns
    products = data.get('products', [])
    
    header_data = [
        ['Nature de\nproduit', 'quantite', 'Prix\nunitaire', 'Montant\ntotal avant\ntax', 'Montant', '', 'Montant brut'],
        ['', '', '', '', 'bon', 'refac', '']
    ]
    
    global_brut = 0.0
    for p in products:
        qte = p.get('quantite', 0)
        prix = p.get('prix_u', 0)
        m_avant = p.get('montant_avant_tax', 0)
        bon = p.get('bon', 0)
        refac = p.get('refac', 0)
        m_brut = p.get('montant_brut', 0)
        global_brut += m_brut
        
        bon_str = f"{qte * bon:.2f}" if bon > 0 else "-"
        refac_str = f"{qte * refac:.2f}" if refac > 0 else "-"
        
        header_data.append([
            p.get('nature', ''), 
            f"{qte:.2f}", 
            f"{prix:.2f}", 
            f"{m_avant:.2f}", 
            bon_str, 
            refac_str, 
            f"{m_brut:.2f}"
        ])
    
    # Subtotal row
    header_data.append(['', '', '', '', '', 's/total', f"{global_brut:.2f}"])

    col_widths = [3.5*cm, 2*cm, 2.5*cm, 3*cm, 2*cm, 2*cm, 4*cm]
    t = Table(header_data, colWidths=col_widths)

    num_data_rows = len(products) if len(products) > 0 else 1
    last_row_idx = len(header_data) - 1
    
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (2, 1)),
        ('SPAN', (3, 0), (3, 1)),
        ('SPAN', (4, 0), (5, 0)),
        ('SPAN', (6, 0), (6, 1)),
        # Alignment
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (4, 1), (5, 1), 'CENTER'),
        # Borders
        ('GRID', (0, 0), (-1, last_row_idx - 1), 1, colors.black),
        ('BOX', (0, 0), (-1, last_row_idx), 1, colors.black), # outer box including s/total row
        ('LINEABOVE', (0, last_row_idx), (-1, last_row_idx), 1, colors.black), # line above s/total
        # Style all data rows slightly
        ('VALIGN', (0, 2), (-1, last_row_idx - 1), 'TOP'),
    ]))

    elements.append(t)
    elements.append(Spacer(1, 0.1*cm))

    # Bottom Sections
    # We will build a complex layout using a main borderless table with 2 columns corresponding to Left and Right
    
    # --- LEFT SIDE ---
    identity = data.get('identity', {})
    left_side_data = [
        [Paragraph(f"<b>Remis Par L'intéressé:</b>", normal_style)],
        [Paragraph(f"<b>N° identité:</b> {identity.get('piece_identite', '')}", normal_style)],
        [Paragraph(f"<b>Le:</b> {identity.get('date', '')}", normal_style)],
    ]
    
    left_top_table = Table(left_side_data, colWidths=[7*cm])
    left_top_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))

    # Signature Box (Observation)
    sig_box_data = [[Paragraph('<b>Observation</b>', normal_style)]]
    sig_table = Table(sig_box_data, colWidths=[6.5*cm], rowHeights=[2.5*cm])
    sig_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))

    # --- RIGHT SIDE ---
    retenues = data.get('retenues', [])
    right_cols = [4.5*cm, 2*cm, 2*cm, 2.5*cm]
    
    # Header for retenues
    right_data = [
        [Paragraph("<b>Retenues diverses</b>", normal_style), 
         "nbre", 
         "P.U", 
         ""]
    ]
    
    for r in retenues:
        nbre_str = f"{r.get('nbre', 0):.2f}" if r.get('nbre') else ""
        pu_val = r.get('pu', 0)
        pu_str = f"{pu_val:.2f}" if isinstance(pu_val, (int, float)) else str(pu_val)
        right_data.append([
            r['name'],
            nbre_str,
            pu_str,
            f"{r['amount']:.2f}"
        ])
    
    # Space before totals
    right_data.append(['', '', '', ''])
    
    # Totals
    totals = data.get('totals', {})
    
    # Build right table
    right_t = Table(right_data, colWidths=right_cols)
    right_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (3,-1), 'RIGHT'),
        ('FONTNAME', (1,0), (2,0), 'Helvetica-Bold'),
        ('RIGHTPADDING', (3,0), (3,-1), 15),
    ]))
    
    # Overall lower section: Left and Right side-by-side 
    # Top part: Identity (left), Retenues (right)
    # Bottom part: Signature (left), Totals (right)
    
    totals_data_inner = [
        [Paragraph("<b>Total de retenues</b>", normal_style), f"{totals.get('total_retenues', 0):.2f}"],
        [Spacer(1, 5), ""],
        [Paragraph("<b>Montant Net A Payer</b>", normal_style), f"{totals.get('montant_net', 0):.2f}"]
    ]
    totals_t = Table(totals_data_inner, colWidths=[7*cm, 4*cm])
    totals_t.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('RIGHTPADDING', (1,0), (1,-1), 15),
    ]))
    
    layout_data = [
        [left_top_table, right_t],
        [sig_table, totals_t]
    ]
    layout_t = Table(layout_data, colWidths=[8*cm, 11*cm])
    layout_t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,0), 'TOP'),
        ('VALIGN', (0,1), (-1,1), 'MIDDLE'),
        ('LINEABOVE', (0,1), (-1,1), 1, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    
    big_box_data = [
        [layout_t]
    ]
    
    # Width is 19cm = 8cm + 11cm
    big_box = Table(big_box_data, colWidths=[19*cm])
    big_box.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (0,0), 0),
    ]))
    
    # No elements.pop() needed since we didn't add layout_t yet.
    elements.append(big_box)
    
    elements.append(Spacer(1, 0.2*cm))
    
    import math
    from num2words import num2words
    net_amount = totals.get('montant_net', 0)
    entier = int(math.floor(net_amount))
    decimal = int(round((net_amount - entier) * 100))
    lettres = num2words(entier, lang='fr') + " Dinars Algériens"
    if decimal > 0:
        lettres += " " + num2words(decimal, lang='fr') + " Centimes"
    lettres = lettres.title()
    
    texte_final = f"<b>La présent décompte est arreté a la somme de : </b>{lettres}"
    elements.append(Paragraph(texte_final, fr_left_style_regular))
    
    elements.append(Spacer(1, 0.2*cm))
    user_acc = identity.get('user_account_name', '')
    if user_acc:
        elements.append(Paragraph(f"<b>Par :</b> {user_acc.upper()}", fr_right_style_regular))
        elements.append(Spacer(1, 0.2*cm))
    date_val = identity.get('date', '')
    elements.append(Paragraph(f"Ouargla le : {date_val}", fr_right_style_regular))
    elements.append(Spacer(1, 0.5*cm))

    # Signature Table
    sig_labels_style = ParagraphStyle('SigLabels', parent=styles['Normal'], alignment=1, fontName=font_name_bold, fontSize=10)
    
    sig_data = [
        [Paragraph("CHEF SCE COMMERCIAL", sig_labels_style), 
         Paragraph("CH.RECOUVREMENT", sig_labels_style), 
         Paragraph("LE TRESORIE", sig_labels_style)],
        [Spacer(1, 1.5*cm), Spacer(1, 1.5*cm), Spacer(1, 1.5*cm)],
        [Paragraph("AUDITEUR", sig_labels_style), 
         Paragraph("S/DIR/F.C", sig_labels_style), 
         Paragraph("LE DIRECTEUR", sig_labels_style)],
    ]
    
    sig_t = Table(sig_data, colWidths=[6.3*cm, 6.3*cm, 6.3*cm])
    sig_t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    
    elements.append(sig_t)
    
    doc.build(elements)
    
    return True

def generate_accumulation_pdf(data, grand_totals, output_path, user_acc, date_val):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=0.5*cm,
        bottomMargin=0.5*cm,
    )

    elements = []
    styles = getSampleStyleSheet()
    
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
        pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold')
        has_arial = True
    except:
        has_arial = False

    def reshaped_arabic(text):
        if not has_arial: return text
        return get_display(arabic_reshaper.reshape(text))

    font_name_bold = 'Arial-Bold' if has_arial else 'Helvetica-Bold'
    font_name_regular = 'Arial' if has_arial else 'Helvetica'

    center_style = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName=font_name_bold, fontSize=12)
    center_style_underlined = ParagraphStyle('CenterU', parent=styles['Normal'], alignment=1, fontName=font_name_bold, fontSize=11)
    fr_left_style = ParagraphStyle('FrLeft', parent=styles['Normal'], alignment=0, fontName=font_name_bold, fontSize=9)
    fr_left_style_regular = ParagraphStyle('FrLeftReg', parent=styles['Normal'], alignment=0, fontName=font_name_regular, fontSize=9)
    fr_right_style_regular = ParagraphStyle('FrRightReg', parent=styles['Normal'], alignment=2, fontName=font_name_regular, fontSize=11)
    ar_right_style = ParagraphStyle('ArRight', parent=styles['Normal'], alignment=2, fontName=font_name_bold, fontSize=10)

    # Header
    elements.append(Paragraph(reshaped_arabic("الجمهورية الجزائرية الديمقراطية الشعبية"), center_style))
    elements.append(Paragraph("<u>REPUBLIQUE ALGERIENNE DEMOCRATIQUE ET POPULAIRE</u>", center_style_underlined))
    elements.append(Spacer(1, 10))

    fr_text = "Ministère de l'Agriculture et du Développement Rural<br/>Office Algérien Interprofessionnel des Céréales<br/>Coopérative des Céréales Et Légumes Secs<br/>de Ouargla"
    ar_text = f"{reshaped_arabic('وزارة الفلاحة والتنمية الريفية')}<br/>{reshaped_arabic('الديوان الجزائري المهني للحبوب')}<br/>{reshaped_arabic('تعاونية الحبوب والبقول الجافة')}<br/>{reshaped_arabic('ولاية ورقلة')}"
    
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')
    header_logo = Image(logo_path, width=2.5*cm, height=3*cm) if os.path.exists(logo_path) else Paragraph("<b>OAIC</b>", center_style)
    
    header_t = Table([[Paragraph(fr_text, fr_left_style), header_logo, Paragraph(ar_text, ar_right_style)]], colWidths=[8*cm, 3*cm, 8*cm])
    header_t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'CENTER')]))
    elements.append(header_t)
    elements.append(Spacer(1, 0.5*cm))

    # Report Title
    elements.append(Paragraph("<b>RAPPORT D'ACCUMULATION FINANCIERE</b>", center_style))
    elements.append(Spacer(1, 0.5*cm))

    # Main Data Table
    table_data = [["Nature du Produit", "Agriculteurs", "Qte Totale", "Avant Taxes", "Bonification", "Réfaction", "Montant Brut"]]
    for row in data:
        table_data.append([
            row['nature'],
            str(row['farmer_count']),
            f"{row['qte']:,.2f}",
            f"{row['avant']:,.2f}",
            f"{row['bon']:,.2f}",
            f"{row['refac']:,.2f}",
            f"{row['net_prod']:,.2f}"
        ])
    
    # Grand Totals Row
    table_data.append([
        "TOTAL GÉNÉRAL",
        str(sum(r['farmer_count'] for r in data)),
        f"{sum(r['qte'] for r in data):,.2f}",
        f"{grand_totals['total_avant']:,.2f}",
        f"{grand_totals['total_bon']:,.2f}",
        f"{grand_totals['total_refac']:,.2f}",
        f"{grand_totals['total_avant'] + grand_totals['total_bon'] - grand_totals['total_refac']:,.2f}"
    ])

    col_widths = [4*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), font_name_bold),
        ('FONTNAME', (0,-1), (-1,-1), font_name_bold),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))

    # Financial Summary Section
    summary_data = [
        [Paragraph("<b>TOTAL RETENUES (TAXES) :</b>", fr_left_style_regular), f"- {grand_totals['total_retenues']:,.2f} DA"],
        [Paragraph("<b>Montant Déjà Payé :</b>", fr_left_style_regular), f"{grand_totals['total_net_paye']:,.2f} DA"],
        [Paragraph("<b>Reste à Payer :</b>", fr_left_style_regular), f"{grand_totals['total_net_non_paye']:,.2f} DA"],
        [Paragraph("<b>TOTAL GÉNÉRAL NET :</b>", center_style), f"{grand_totals['total_net']:,.2f} DA"]
    ]
    summary_t = Table(summary_data, colWidths=[10*cm, 5*cm])
    summary_t.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(summary_t)
    elements.append(Spacer(1, 1*cm))

    # Footer Info
    if user_acc:
        elements.append(Paragraph(f"<b>Par :</b> {user_acc.upper()}", fr_right_style_regular))
        elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(f"Ouargla le : {date_val}", fr_right_style_regular))
    elements.append(Spacer(1, 0.5*cm))

    # Signatures
    sig_labels_style = ParagraphStyle('SigLabels', parent=styles['Normal'], alignment=1, fontName=font_name_bold, fontSize=10)
    sig_data = [
        [Paragraph("CHEF SCE COMMERCIAL", sig_labels_style), Paragraph("CH.RECOUVREMENT", sig_labels_style), Paragraph("LE TRESORIE", sig_labels_style)],
        [Spacer(1, 1.5*cm), Spacer(1, 1.5*cm), Spacer(1, 1.5*cm)],
        [Paragraph("AUDITEUR", sig_labels_style), Paragraph("S/DIR/F.C", sig_labels_style), Paragraph("LE DIRECTEUR", sig_labels_style)],
    ]
    sig_t = Table(sig_data, colWidths=[6.3*cm, 6.3*cm, 6.3*cm])
    sig_t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(sig_t)

    doc.build(elements)
    return True

