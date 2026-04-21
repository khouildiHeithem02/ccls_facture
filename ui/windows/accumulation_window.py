import customtkinter as ctk
import os
import datetime
from tkinter import messagebox
from pdf_generator import generate_accumulation_pdf
from ui.windows.preview_window import InvoicePreviewWindow

class AccumulationWindow(ctk.CTkToplevel):
    def __init__(self, parent, data, grand_totals):
        super().__init__(parent)
        self.title("Rapport Financier d'Accumulation")
        self.geometry("1100x700")
        self.attributes("-topmost", True)
        
        self.accum_data = data
        self.grand_totals = grand_totals
        # Note: Access context from parent/master
        self.parent_app = parent.master if hasattr(parent, 'master') else parent
        
        # Screenshot protection
        try:
            from ctypes import windll
            windll.user32.SetWindowDisplayAffinity(self.winfo_id(), 0x00000011)
        except:
            pass
            
        header_font = ctk.CTkFont(family="Poppins", size=15, weight="bold")
        main_font = ctk.CTkFont(family="Poppins", size=14)
        summary_font = ctk.CTkFont(family="Poppins", size=18, weight="bold")
        
        # Table Scrollable Frame
        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Headers
        headers = ["Nature du Produit", "Agriculteurs", "Qte Totale", "Avant Taxes", "Bonification", "Réfaction", "Montant Brut"]
        for col, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=header_font, width=160).grid(row=0, column=col, padx=8, pady=15)
            
        # Data Rows
        row_idx = 1
        for row in data:
            ctk.CTkLabel(self.table_frame, text=row['nature'], font=main_font, width=160).grid(row=row_idx, column=0, padx=8, pady=8)
            ctk.CTkLabel(self.table_frame, text=str(row['farmer_count']), font=main_font, width=160).grid(row=row_idx, column=1, padx=8, pady=8)
            ctk.CTkLabel(self.table_frame, text=f"{row['qte']:,.2f}", font=main_font, width=160).grid(row=row_idx, column=2, padx=8, pady=8)
            ctk.CTkLabel(self.table_frame, text=f"{row['avant']:,.2f}", font=main_font, width=160).grid(row=row_idx, column=3, padx=8, pady=8)
            ctk.CTkLabel(self.table_frame, text=f"{row['bon']:,.2f}", font=main_font, width=160).grid(row=row_idx, column=4, padx=8, pady=8)
            ctk.CTkLabel(self.table_frame, text=f"{row['refac']:,.2f}", font=main_font, width=160).grid(row=row_idx, column=5, padx=8, pady=8)
            ctk.CTkLabel(self.table_frame, text=f"{row['net_prod']:,.2f}", font=main_font, width=160).grid(row=row_idx, column=6, padx=8, pady=8)
            row_idx += 1
            
        # 1. Spacer/Divider Line
        ctk.CTkFrame(self.table_frame, height=2, fg_color="gray").grid(row=row_idx, column=0, columnspan=7, sticky="ew", pady=10)
        row_idx += 1
        
        # 2. TOTAL GÉNÉRAL
        ctk.CTkLabel(self.table_frame, text="TOTAL GÉNÉRAL", font=header_font).grid(row=row_idx, column=0, padx=5, pady=5)
        total_farmers = sum(r['farmer_count'] for r in data)
        ctk.CTkLabel(self.table_frame, text=str(total_farmers), font=header_font).grid(row=row_idx, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(self.table_frame, text=f"{sum(r['qte'] for r in data):,.2f}", font=header_font).grid(row=row_idx, column=2, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_avant']:,.2f}", font=header_font).grid(row=row_idx, column=3, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_bon']:,.2f}", font=header_font).grid(row=row_idx, column=4, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_refac']:,.2f}", font=header_font).grid(row=row_idx, column=5, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_avant'] + grand_totals['total_bon'] - grand_totals['total_refac']:,.2f}", font=header_font).grid(row=row_idx, column=6, padx=5, pady=5)
        row_idx += 1
        
        # 3. TOTAL RETENUES
        ctk.CTkLabel(self.table_frame, text="TOTAL RETENUES (TAXES)", font=header_font, text_color="#E64A19").grid(row=row_idx, column=0, columnspan=6, sticky="e", padx=20, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"- {grand_totals['total_retenues']:,.2f}", font=header_font, text_color="#E64A19").grid(row=row_idx, column=6, padx=5, pady=5)
        row_idx += 1
        
        # 4. SPLIT NET TOTALS
        ctk.CTkLabel(self.table_frame, text=f"Total Déjà Payé:", font=summary_font, text_color="#2E7D32").grid(row=row_idx, column=4, columnspan=2, sticky="e", padx=5, pady=15)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_net_paye']:,.2f} DA", font=summary_font, text_color="#2E7D32").grid(row=row_idx, column=6, padx=5, pady=15)
        row_idx += 1
        
        ctk.CTkLabel(self.table_frame, text=f"Reste à Payer:", font=summary_font, text_color="#C62828").grid(row=row_idx, column=4, columnspan=2, sticky="e", padx=5, pady=15)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_net_non_paye']:,.2f} DA", font=summary_font, text_color="#C62828").grid(row=row_idx, column=6, padx=5, pady=15)
        row_idx += 1
        
        ctk.CTkLabel(self.table_frame, text=f"Total Général Net:", font=summary_font, text_color="#1f538d").grid(row=row_idx, column=4, columnspan=2, sticky="e", padx=5, pady=15)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_net']:,.2f} DA", font=summary_font, text_color="#1f538d").grid(row=row_idx, column=6, padx=5, pady=15)

        # Footer Button Frame
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", padx=20, pady=10)
        
        self.btn_print = ctk.CTkButton(footer_frame, text="🖨️ Imprimer Rapport", command=self.print_report,
                                       fg_color="#1976D2", font=ctk.CTkFont(family="Poppins", size=15, weight="bold"), height=45)
        self.btn_print.pack(side="right", padx=10)
        
        self.btn_close = ctk.CTkButton(footer_frame, text="Fermer", command=self.destroy,
                                       fg_color="gray", font=ctk.CTkFont(family="Poppins", size=15), height=45)
        self.btn_close.pack(side="right", padx=10)

    def print_report(self):
        filename = "temp_accumulation_report.pdf"
        # Since we moved script locations, we might need to adjust current dir expectations
        output_path = os.path.join(os.getcwd(), filename)
        
        try:
            date_val = datetime.datetime.now().strftime("%d/%m/%Y")
            # Get username from parent app context
            user_acc = getattr(self.parent_app, 'username', 'admin')
            
            generate_accumulation_pdf(self.accum_data, self.grand_totals, output_path, user_acc, date_val)
            InvoicePreviewWindow(self, output_path, mode="view")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'impression : {e}", parent=self)
