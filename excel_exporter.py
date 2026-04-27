import pandas as pd
import os
from tkinter import filedialog, messagebox
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Border, Side, PatternFill
from config import TAXES_LIST

def export_invoice_to_excel(data):
    """Exports single invoice data to a highly formatted Excel file mirroring the PDF layout."""
    try:
        ident = data.get('identity', {})
        totals = data.get('totals', {})
        products = data.get('products', [])
        retenues = data.get('retenues', [])
        provided_retenues = {r['name']: r for r in retenues}

        # 1. File Dialog - Custom naming: FarmerName_DecNum_Year.xlsx
        farmer_name = ident.get('farmer', 'Agriculteur').replace(' ', '_')
        dec_num = ident.get('decompte', 'Unknown').replace('/', '_')
        default_name = f"{farmer_name}_{dec_num}.xlsx"
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=default_name,
            title="Exporter vers Excel"
        )
        if not file_path: return False

        # 2. Create Workbook and Styles
        wb = Workbook()
        ws = wb.active
        ws.title = "Facture"

        # Define Styles
        bold_font = Font(bold=True, size=11)
        header_font = Font(bold=True, size=12, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align = Alignment(horizontal="left", vertical="center")
        right_align = Alignment(horizontal="right", vertical="center")
        
        thin_border = Border(
            left=Side(style='thin'), 
            right=Side(style='thin'), 
            top=Side(style='thin'), 
            bottom=Side(style='thin')
        )
        
        header_fill = PatternFill(start_color="3B8ED0", end_color="3B8ED0", fill_type="solid")
        subtotal_fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")

        # 3. Header Section (Logo/Ministry Info Placeholder)
        ws.merge_cells('A1:G1')
        ws['A1'] = "REPUBLIQUE ALGERIENNE DEMOCRATIQUE ET POPULAIRE"
        ws['A1'].alignment = center_align
        ws['A1'].font = Font(bold=True, size=14)

        ws.merge_cells('A2:C5')
        ws['A2'] = "Ministère de l'Agriculture\nOAIC / CCLS Ouargla"
        ws['A2'].alignment = left_align
        
        ws.merge_cells('E2:G5')
        ws['E2'] = "وزارة الفلاحة والتنمية الريفية\nالديوان المهني للحبوب"
        ws['E2'].alignment = right_align

        # 4. Invoice Metadata
        ws['A7'] = "Decompte d'achat N°:"
        ws['B7'] = ident.get('decompte')
        ws['A7'].font = bold_font
        
        ws['A9'] = "Agriculteur:"
        ws['B9'] = ident.get('farmer')
        ws['A9'].font = bold_font

        ws['A10'] = "Wilaya:"
        ws['B10'] = ident.get('wilaya')
        ws['A10'].font = bold_font

        ws['A11'] = "Adresse:"
        ws['B11'] = ident.get('adresse')
        ws['A11'].font = bold_font

        ws['E11'] = "NIF:"
        ws['F11'] = ident.get('nif') or "Non"
        ws['E11'].font = bold_font

        # 5. Products Table
        start_row = 13
        headers = ['Nature de produit', 'Quantité', 'P.U', 'Total Avant Tax', 'Bonification', 'Réfaction', 'Montant Brut']
        for col, text in enumerate(headers, 1):
            cell = ws.cell(row=start_row, column=col, value=text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border

        curr_row = start_row + 1
        global_brut = 0
        for p in products:
            qte = p.get('quantite', 0)
            pu = p.get('prix_u', 0)
            m_avant = qte * pu
            bon = p.get('bon', 0) * qte
            refac = p.get('refac', 0) * qte
            brut = p.get('montant_brut', 0)
            global_brut += brut

            row_data = [p.get('nature'), qte, pu, m_avant, bon, refac, brut]
            for col, val in enumerate(row_data, 1):
                cell = ws.cell(row=curr_row, column=col, value=val)
                cell.border = thin_border
                cell.alignment = center_align
                if col > 1: cell.number_format = '#,##0.00'
            curr_row += 1

        # Subtotal Row
        ws.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=6)
        ws.cell(row=curr_row, column=1, value="SOUS-TOTAL BRUT").alignment = right_align
        ws.cell(row=curr_row, column=1).font = bold_font
        
        brut_cell = ws.cell(row=curr_row, column=7, value=global_brut)
        brut_cell.font = bold_font
        brut_cell.fill = subtotal_fill
        brut_cell.border = thin_border
        brut_cell.number_format = '#,##0.00'
        
        curr_row += 2

        # 6. Retenues Table (Side-by-side Layout)
        ws.cell(row=curr_row, column=1, value="RETENUES DIVERSES").font = Font(bold=True, underline="single")
        curr_row += 1
        
        tax_headers = ["Taxe", "Nombre", "P.U", "Montant"]
        for col, text in enumerate(tax_headers, 4): # Start from column D (4)
            cell = ws.cell(row=curr_row, column=col, value=text)
            cell.font = bold_font
            cell.border = thin_border
            cell.alignment = center_align

        curr_row += 1
        for tax_name in TAXES_LIST:
            r = provided_retenues.get(tax_name, {})
            ws.cell(row=curr_row, column=4, value=tax_name).border = thin_border
            ws.cell(row=curr_row, column=5, value=r.get('nbre', '')).border = thin_border
            ws.cell(row=curr_row, column=6, value=r.get('pu', '')).border = thin_border
            amt_cell = ws.cell(row=curr_row, column=7, value=r.get('amount', 0))
            amt_cell.border = thin_border
            amt_cell.number_format = '#,##0.00'
            curr_row += 1

        # 7. Final Totals
        curr_row += 1
        ws.cell(row=curr_row, column=6, value="TOTAL RETENUES").font = bold_font
        ws.cell(row=curr_row, column=7, value=totals.get('total_retenues', 0)).number_format = '#,##0.00'
        ws.cell(row=curr_row, column=7).font = bold_font
        
        curr_row += 1
        net_label = ws.cell(row=curr_row, column=6, value="MONTANT NET A PAYER")
        net_label.font = Font(bold=True, size=12)
        net_val = ws.cell(row=curr_row, column=7, value=totals.get('montant_net', 0))
        net_val.font = Font(bold=True, size=12, color="FF0000")
        net_val.number_format = '#,##0.00'
        
        # 8. Adjust Column Widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 15
        ws.column_dimensions['G'].width = 20

        wb.save(file_path)
        messagebox.showinfo("Succès", f"Fichier Excel stylisé exporté :\n{os.path.basename(file_path)}")
        return True

    except Exception as e:
        messagebox.showerror("Erreur Export", f"Une erreur est survenue lors de l'export Excel :\n{str(e)}")
        import traceback
        traceback.print_exc()
        return False
