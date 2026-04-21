import customtkinter as ctk
import os
import ctypes
from tkinter import messagebox
import database
from pdf_generator import generate_facture_pdf
from ui.windows.preview_window import InvoicePreviewWindow
from ui.windows.accumulation_window import AccumulationWindow
from ui.windows.dialogs import PasswordDialog

class HistoryFrame(ctk.CTkFrame):
    def __init__(self, master, username, on_back=None):
        super().__init__(master, fg_color="transparent")
        self.username = username
        self.on_back = on_back
        
        # Identity Search
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=20, pady=20)
        
        # BACK BUTTON
        btn_back = ctk.CTkButton(filter_frame, text="⬅ Retour", width=100, command=self._go_back, fg_color="#607D8B")
        btn_back.pack(side="left", padx=(0, 20))
        
        # Prevent screenshots for history too
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass

        # Filter Bar (Horizontal)
        filters_container = ctk.CTkFrame(self)
        filters_container.pack(fill="x", padx=20, pady=10)
        
        # Identity Search
        ctk.CTkLabel(filters_container, text="Recherche Nom/NIF:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(filters_container, placeholder_text="Mecheni...", width=250, height=35, font=ctk.CTkFont(family="Poppins", size=15))
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())
        self.search_entry.bind("<Return>", lambda e: self.refresh_list())
        
        # Wilaya Filter
        ctk.CTkLabel(filters_container, text="Wilaya:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        self.wilaya_var = ctk.StringVar(value="Tous")
        self.wilaya_menu = ctk.CTkOptionMenu(filters_container, values=["Tous", "Ouargla", "Tougourt", "Ilizi"], 
                                             variable=self.wilaya_var, command=lambda _: self.refresh_list(), 
                                             width=140, height=35, font=ctk.CTkFont(family="Poppins", size=14))
        self.wilaya_menu.pack(side="left", padx=5)
        
        # Product Filter
        ctk.CTkLabel(filters_container, text="Produit:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        all_prods = database.get_db_products()
        product_list = ["Tous"] + list(all_prods.keys())
        self.product_var = ctk.StringVar(value="Tous")
        self.product_menu = ctk.CTkOptionMenu(filters_container, values=product_list, 
                                              variable=self.product_var, command=lambda _: self.refresh_list(), 
                                              width=160, height=35, font=ctk.CTkFont(family="Poppins", size=14))
        self.product_menu.pack(side="left", padx=5)
        
        # Status Filter
        ctk.CTkLabel(filters_container, text="Statut:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        self.status_var = ctk.StringVar(value="Tous")
        self.status_menu = ctk.CTkOptionMenu(filters_container, values=["Tous", "Payé", "Non Payé"], 
                                              variable=self.status_var, command=lambda _: self.refresh_list(), 
                                              width=120, height=35, font=ctk.CTkFont(family="Poppins", size=14))
        self.status_menu.pack(side="left", padx=5)
        
        btn_refresh = ctk.CTkButton(filters_container, text="🔄 Actualiser", width=120, height=35, 
                                    command=self.refresh_list, fg_color="#37474F", font=ctk.CTkFont(family="Poppins", size=14))
        btn_refresh.pack(side="right", padx=5)
        
        # Header for the list
        header_frame = ctk.CTkFrame(self, fg_color="#e9ecef")
        header_frame.pack(fill="x", padx=20, pady=0)
        h_font = ctk.CTkFont(family="Poppins", size=15, weight="bold")
        ctk.CTkLabel(header_frame, text="Facture #", width=120, font=h_font).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(header_frame, text="Date", width=120, font=h_font).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(header_frame, text="Agriculteur", width=300, font=h_font).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(header_frame, text="Montant Net", width=150, font=h_font).grid(row=0, column=3, padx=5)
        ctk.CTkLabel(header_frame, text="Statut", width=120, font=h_font).grid(row=0, column=4, padx=5)
        ctk.CTkLabel(header_frame, text="Actions", width=180, font=h_font).grid(row=0, column=5, padx=5)
        
        # Scrollable list
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        
        # Accumulate area (Bottom)
        self.accum_frame = ctk.CTkFrame(self, fg_color="#f8f9fa")
        self.accum_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_accum = ctk.CTkButton(self.accum_frame, text="📊 Accumulate Totals", 
                                       command=self.accumulate_totals, height=45,
                                       fg_color="#FBC02D", text_color="black", font=ctk.CTkFont(family="Poppins", size=16, weight="bold"))
        self.btn_accum.pack(side="left", padx=20, pady=15)
        
        self.totals_label = ctk.CTkLabel(self.accum_frame, text="Cliquer pour calculer les totaux de la liste.", 
                                         font=ctk.CTkFont(family="Poppins", size=15), justify="left")
        self.totals_label.pack(side="left", padx=20)

        # Status Bar / Tooltip area
        self.status_bar = ctk.CTkLabel(self, text="Survoler un bouton pour voir son action...", 
                                       font=ctk.CTkFont(family="Poppins", size=14, slant="italic"), text_color="gray")
        self.status_bar.pack(pady=10)
        
        self.refresh_list()

    def _go_back(self):
        if self.on_back:
            self.on_back()

    def _set_status(self, text):
        self.status_bar.configure(text=text, text_color="#1f538d")

    def _clear_status(self, _=None):
        self.status_bar.configure(text="Survoler un bouton pour voir son action...", text_color="gray")

    def accumulate_totals(self):
        query = self.search_entry.get().strip()
        wilaya = self.wilaya_var.get()
        product = self.product_var.get()
        status = self.status_var.get()
        
        data_grouped = database.get_grouped_accumulation(query if query else None, wilaya, product, status)
        grand_totals = database.get_filtered_totals(query if query else None, wilaya, product, status)
        
        if not data_grouped:
            messagebox.showinfo("Information", "Aucune donnée à accumuler pour ces filtres.", parent=self)
            return
            
        AccumulationWindow(self, data_grouped, grand_totals)

    def refresh_list(self):
        """Fetches data and starts the chunked rendering process to keep UI responsive."""
        # Cancel any current background rendering loop
        self._current_render_id = getattr(self, "_current_render_id", 0) + 1
        render_id = self._current_render_id
        
        # Clear existing
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        # Loading Indicator
        self.loading_lbl = ctk.CTkLabel(self.list_frame, text="⏳ Chargement des données...", 
                                        font=ctk.CTkFont(family="Poppins", size=16, slant="italic"))
        self.loading_lbl.pack(pady=30)
        
        # Fetch data from DB
        query = self.search_entry.get().strip()
        wilaya = self.wilaya_var.get()
        product = self.product_var.get()
        status_filter = self.status_var.get()
        
        self.after(10, lambda: self._fetch_and_start_render(query, wilaya, product, status_filter, render_id))

    def _fetch_and_start_render(self, query, wilaya, product, status_filter, render_id):
        if render_id != self._current_render_id: return
        
        invoices = database.get_all_invoices(query if query else None, wilaya, product, status_filter)
        
        if hasattr(self, "loading_lbl") and self.loading_lbl.winfo_exists():
            self.loading_lbl.destroy()
        
        if not invoices:
            ctk.CTkLabel(self.list_frame, text="Aucune facture trouvée.", 
                         font=ctk.CTkFont(family="Poppins", size=16, slant="italic")).pack(pady=30)
            return

        self._render_chunk(invoices, 0, render_id)

    def _render_chunk(self, data, start_index, render_id):
        # Stop if a newer refresh started
        if render_id != self._current_render_id:
            return
            
        # Render 10 rows at a time
        chunk_size = 10
        end_index = min(start_index + chunk_size, len(data))
        
        r_font = ctk.CTkFont(family="Poppins", size=14)
        
        for i in range(start_index, end_index):
            inv = data[i]
            inv_id = inv["id"]
            dec = inv["decompte"]
            dt = inv["date"]
            name = inv["farmer_name"]
            net = inv["total_net"]
            status_val = inv["payment_status"]
            
            row_frame = ctk.CTkFrame(self.list_frame, fg_color="white", border_width=1, border_color="#eeeeee")
            row_frame.pack(fill="x", pady=4, padx=5)
            
            ctk.CTkLabel(row_frame, text=dec, width=120, font=r_font).grid(row=0, column=0, padx=5)
            ctk.CTkLabel(row_frame, text=dt, width=120, font=r_font).grid(row=0, column=1, padx=5)
            ctk.CTkLabel(row_frame, text=name, width=300, anchor="w", font=r_font).grid(row=0, column=2, padx=5)
            ctk.CTkLabel(row_frame, text=f"{net:,.2f} DA", width=150, text_color="#2E7D32", font=ctk.CTkFont(family="Poppins", size=14, weight="bold")).grid(row=0, column=3, padx=5)
            
            status_color = "#2E7D32" if status_val == "Payé" else "#C62828"
            display_stat = f"🟢 {status_val}" if status_val == "Payé" else f"🔴 {status_val}"
            status_lbl = ctk.CTkLabel(row_frame, text=display_stat, width=120, text_color=status_color, font=r_font)
            status_lbl.grid(row=0, column=4, padx=5)
            
            actions_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            actions_frame.grid(row=0, column=5, padx=5)
            
            btn_view = ctk.CTkButton(actions_frame, text="👁️ Voir", width=80, height=32, 
                                     font=ctk.CTkFont(family="Poppins", size=13),
                                     command=lambda i_id=inv_id: self.view_pdf(i_id))
            btn_view.pack(side="left", padx=5)
            
            toggle_text = "💳 Payer" if status_val != "Payé" else "❌ Annuler"
            toggle_color = "#1976D2" if status_val != "Payé" else "#757575"
            btn_toggle = ctk.CTkButton(actions_frame, text=toggle_text, width=80, height=32, 
                                       fg_color=toggle_color, font=ctk.CTkFont(family="Poppins", size=13))
            btn_toggle.configure(command=lambda i_id=inv_id, s_lbl=status_lbl, btn=btn_toggle: self.toggle_status(i_id, s_lbl, btn))
            btn_toggle.pack(side="left", padx=5)

        # Schedule next chunk if there's more data
        if end_index < len(data):
            self.after(5, lambda: self._render_chunk(data, end_index, render_id))

    def toggle_status(self, inv_id, status_lbl, btn_toggle):
        def do_toggle():
            current_status = "Payé" if "🟢 Payé" in status_lbl.cget("text") else "Non Payé"
            new_status = "Payé" if current_status != "Payé" else "Non Payé"
            if database.update_payment_status(inv_id, new_status):
                new_color = "#2E7D32" if new_status == "Payé" else "#C62828"
                new_display = f"🟢 {new_status}" if new_status == "Payé" else f"🔴 {new_status}"
                status_lbl.configure(text=new_display, text_color=new_color)
                btn_toggle.configure(text="❌ Annuler" if new_status == "Payé" else "💳 Payer", 
                                     fg_color="#757575" if new_status == "Payé" else "#1976D2")
        PasswordDialog(self, title="Validation Requise", on_success=do_toggle)

    def view_pdf(self, inv_id):
        data = database.get_invoice_details(inv_id)
        if data:
            filename = "temp_history_view.pdf"
            output_path = os.path.join(os.getcwd(), filename)
            try:
                generate_facture_pdf(data, output_path)
                InvoicePreviewWindow(self, output_path, mode="view")
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de l'aperçu: {e}", parent=self)
        else:
            messagebox.showerror("Erreur", "Données introuvables.", parent=self)
