import customtkinter as ctk
import tkinter as tk
import os
import ctypes
from tkinter import messagebox
import database
from pdf_generator import generate_facture_pdf
from ui.windows.preview_window import InvoicePreviewWindow
from ui.windows.dialogs import PasswordDialog, DownloadSelectionDialog
from excel_exporter import export_invoice_to_excel
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None
import datetime

class HistoryFrame(ctk.CTkFrame):
    def __init__(self, master, username, on_back=None):
        super().__init__(master, fg_color="transparent")
        self.username = username
        self.on_back = on_back
        self.current_page = 0
        self.page_size = 15
        self.all_invoices = []
        self._search_after_id = None  # Debounce timer for search entry
        
        # Identity Search
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=20, pady=20)
        
        # BACK BUTTON
        btn_back = ctk.CTkButton(filter_frame, text="⬅ Retour", width=100, command=self._go_back, fg_color="#607D8B")
        btn_back.pack(side="left", padx=(0, 20))
        
        # Filter Bar (Horizontal)
        self.filters_container = ctk.CTkFrame(self)
        self.filters_container.pack(fill="x", padx=20, pady=10)
        
        # Identity Search
        ctk.CTkLabel(self.filters_container, text="Recherche Nom/NIF:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(self.filters_container, placeholder_text="Mecheni...", width=250, height=35, font=ctk.CTkFont(family="Poppins", size=15))
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self._schedule_refresh)
        self.search_entry.bind("<Return>", lambda e: self.refresh_list())
        
        # Wilaya Filter
        ctk.CTkLabel(self.filters_container, text="Wilaya:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        self.wilaya_var = ctk.StringVar(value="Tous")
        self.wilaya_menu = ctk.CTkOptionMenu(self.filters_container, values=["Tous", "Ouargla", "Tougourt", "Ilizi"], 
                                             variable=self.wilaya_var, command=lambda _: self.refresh_list(), 
                                             width=140, height=35, font=ctk.CTkFont(family="Poppins", size=14))
        self.wilaya_menu.pack(side="left", padx=5)
        
        # Product Filter
        ctk.CTkLabel(self.filters_container, text="Produit:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        all_prods = database.get_db_products()
        product_list = ["Tous"] + list(all_prods.keys())
        self.product_var = ctk.StringVar(value="Tous")
        self.product_menu = ctk.CTkOptionMenu(self.filters_container, values=product_list, 
                                              variable=self.product_var, command=lambda _: self.refresh_list(), 
                                              width=160, height=35, font=ctk.CTkFont(family="Poppins", size=14))
        self.product_menu.pack(side="left", padx=5)
        
        # Status Filter
        ctk.CTkLabel(self.filters_container, text="Statut:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=5)
        self.status_var = ctk.StringVar(value="Tous")
        self.status_menu = ctk.CTkOptionMenu(self.filters_container, values=["Tous", "Payé", "Non Payé"], 
                                              variable=self.status_var, command=lambda _: self.refresh_list(), 
                                              width=120, height=35, font=ctk.CTkFont(family="Poppins", size=14))
        self.status_menu.pack(side="left", padx=5)
        
        btn_refresh = ctk.CTkButton(self.filters_container, text="🔄 Actualiser", width=120, height=35, 
                                    command=self.refresh_list, fg_color="#37474F", font=ctk.CTkFont(family="Poppins", size=14))
        btn_refresh.pack(side="right", padx=5)

        # Additional Filter Toggle
        ctk.CTkLabel(self.filters_container, text="Extra Filter:", font=ctk.CTkFont(family="Poppins", size=15)).pack(side="left", padx=(15, 5))
        self.extra_filter_var = ctk.StringVar(value="Aucun")
        self.extra_filter_menu = ctk.CTkOptionMenu(self.filters_container, values=["Aucun", "Par Date"], 
                                                 variable=self.extra_filter_var, command=self._toggle_extra_filters,
                                                 width=130, height=35, font=ctk.CTkFont(family="Poppins", size=14))
        self.extra_filter_menu.pack(side="left", padx=5)

        # Container for Date Fields (Hidden by default, parent is self for new line)
        self.date_fields_frame = ctk.CTkFrame(self, fg_color="#e3e8ed", corner_radius=12, border_width=1, border_color="#ccd6e0")
        # Internal container for centering
        date_inner = ctk.CTkFrame(self.date_fields_frame, fg_color="transparent")
        date_inner.pack(pady=10)
        
        ctk.CTkLabel(date_inner, text="Du:", font=ctk.CTkFont(family="Poppins", size=15, weight="bold")).pack(side="left", padx=5)
        if DateEntry:
            # Rounded container for start date
            self.start_date_container = ctk.CTkFrame(date_inner, fg_color="white", corner_radius=10, border_width=1, border_color="#1976D2")
            self.start_date_container.pack(side="left", padx=5)
            
            self.start_date_en = DateEntry(self.start_date_container, width=16, background='#1976D2',
                                         foreground='black', borderwidth=0, date_pattern='dd/mm/yyyy',
                                         font=("Poppins", 16),
                                         headersbackground='#1565C0',
                                         headersforeground='white',
                                         selectbackground='#00ACC1',
                                         selectforeground='white',
                                         normalbackground='white',
                                         normalforeground='#37474F',
                                         weekendbackground='#f5f7f9',
                                         weekendforeground='#C62828',
                                         othermonthbackground='#f8f9fa',
                                         othermonthforeground='gray',
                                         othermonthwebackground='#f8f9fa',
                                         othermonthweforeground='gray')
            self.start_date_en.pack(padx=8, pady=5)
            self.start_date_en.set_date(datetime.datetime.now().replace(day=1))
            self.start_date_en.bind("<<DateEntrySelected>>", lambda e: self.refresh_list())
            self.start_date_en.bind("<Button-1>", lambda e: self.start_date_en.drop_down())
        else:
            self.start_date_en = ctk.CTkEntry(date_inner, width=180, height=45, font=("Poppins", 16))
            self.start_date_en.pack(side="left", padx=5)

        ctk.CTkLabel(date_inner, text="Au:", font=ctk.CTkFont(family="Poppins", size=15, weight="bold")).pack(side="left", padx=5)
        if DateEntry:
            # Rounded container for end date
            self.end_date_container = ctk.CTkFrame(date_inner, fg_color="white", corner_radius=10, border_width=1, border_color="#1976D2")
            self.end_date_container.pack(side="left", padx=5)
            
            self.end_date_en = DateEntry(self.end_date_container, width=16, background='#1976D2',
                                       foreground='black', borderwidth=0, date_pattern='dd/mm/yyyy',
                                       font=("Poppins", 16),
                                       headersbackground='#1565C0',
                                       headersforeground='white',
                                       selectbackground='#00ACC1',
                                       selectforeground='white',
                                       normalbackground='white',
                                       normalforeground='#37474F',
                                       weekendbackground='#f5f7f9',
                                       weekendforeground='#C62828',
                                       othermonthbackground='#f8f9fa',
                                       othermonthforeground='gray',
                                       othermonthwebackground='#f8f9fa',
                                       othermonthweforeground='gray')
            self.end_date_en.pack(padx=8, pady=5)
            self.end_date_en.set_date(datetime.datetime.now())
            self.end_date_en.bind("<<DateEntrySelected>>", lambda e: self.refresh_list())
            self.end_date_en.bind("<Button-1>", lambda e: self.end_date_en.drop_down())
        else:
            self.end_date_en = ctk.CTkEntry(date_inner, width=180, height=45, font=("Poppins", 16))
            self.end_date_en.pack(side="left", padx=5)

        self.btn_clear_dates = ctk.CTkButton(date_inner, text="🧹", width=45, height=45, 
                                             command=self.clear_date_filters, fg_color="#78909C", font=ctk.CTkFont(family="Poppins", size=16))
        self.btn_clear_dates.pack(side="left", padx=5)
        
        # Header for the list
        self.header_frame = ctk.CTkFrame(self, fg_color="#e9ecef")
        self.header_frame.pack(fill="x", padx=20, pady=0)
        h_font = ctk.CTkFont(family="Poppins", size=15, weight="bold")
        ctk.CTkLabel(self.header_frame, text="Facture #", width=120, font=h_font).grid(row=0, column=0, padx=5)
        ctk.CTkLabel(self.header_frame, text="Date", width=120, font=h_font).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(self.header_frame, text="Agriculteur", width=300, font=h_font).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(self.header_frame, text="Montant Net", width=150, font=h_font).grid(row=0, column=3, padx=5)
        ctk.CTkLabel(self.header_frame, text="Statut", width=120, font=h_font).grid(row=0, column=4, padx=5)
        ctk.CTkLabel(self.header_frame, text="Actions", width=180, font=h_font).grid(row=0, column=5, padx=5)
        
        # Scrollable list
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        
        # Pagination Bar (Guarantees zero lag by limiting widget count)
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.pack(fill="x", padx=20, pady=5)
        
        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="⬅ Précédent", width=120, height=35,
                                      command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left", padx=10)
        
        self.page_info_lbl = ctk.CTkLabel(self.pagination_frame, text="Page 1 / 1", 
                                          font=ctk.CTkFont(family="Poppins", size=14, weight="bold"))
        self.page_info_lbl.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.pagination_frame, text="Suivant ➡", width=120, height=35,
                                      command=self.next_page, state="disabled")
        self.btn_next.pack(side="right", padx=10)
        
        # Status Bar / Tooltip area
        self.status_bar = ctk.CTkLabel(self, text="Survoler un bouton pour voir son action...", 
                                       font=ctk.CTkFont(family="Poppins", size=14, slant="italic"), text_color="gray")
        self.status_bar.pack(pady=10)
        
        self.after(50, self.refresh_list)

    def _toggle_extra_filters(self, choice):
        if choice == "Par Date":
            # Pack after filters_container (which is at the top)
            self.date_fields_frame.pack(fill="x", padx=20, pady=(0, 10))
            # Adjust packing order to stay before header_frame
            self.header_frame.pack_forget()
            self.list_frame.pack_forget()
            self.pagination_frame.pack_forget()
            self.accum_frame.pack_forget()
            self.status_bar.pack_forget()
            
            self.header_frame.pack(fill="x", padx=20, pady=0)
            self.list_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))
            self.pagination_frame.pack(fill="x", padx=20, pady=5)
            self.accum_frame.pack(fill="x", padx=20, pady=10)
            self.status_bar.pack(pady=10)
        else:
            self.date_fields_frame.pack_forget()
        self.refresh_list()

    def _go_back(self):
        if self.on_back:
            self.on_back()

    def start_edit(self, inv_id):
        """Loads an invoice for editing and switches to the dashboard."""
        if hasattr(self.master, 'load_invoice_for_edit'):
            self.master.load_invoice_for_edit(inv_id)
        elif hasattr(self.master.master, 'load_invoice_for_edit'):
            # In case of nested frames in MainApplication
            self.master.master.load_invoice_for_edit(inv_id)
        
        if self.on_back:
            self.on_back()

    def _set_status(self, text):
        self.status_bar.configure(text=text, text_color="#1f538d")

    def _clear_status(self, _=None):
        self.status_bar.configure(text="Survoler un bouton pour voir son action...", text_color="gray")

    def _validate_date_mask(self, P, S, d, i, entry):
        if d == '0': return True # Deletion
        if not S.isdigit(): return False # Digits only
        l = len(P)
        if l > 10: return False
        if i == str(l-1): # Typing at the end
            if l in [2, 5]:
                entry.insert(int(i), '/')
        if l == 10: 
            if self._search_after_id: self.after_cancel(self._search_after_id)
            self._search_after_id = self.after(100, self.refresh_list)
        return True

    def _schedule_refresh(self, event=None):
        """Debounce search: wait 300ms after last keystroke before refreshing."""
        if self._search_after_id is not None:
            try:
                self.after_cancel(self._search_after_id)
            except: pass
        self._search_after_id = self.after(300, self.refresh_list)

    def clear_date_filters(self):
        if DateEntry and isinstance(self.start_date_en, DateEntry):
             self.start_date_en.set_date(datetime.datetime.now().replace(day=1))
             self.end_date_en.set_date(datetime.datetime.now())
        else:
            self.start_date_en.delete(0, 'end')
            self.end_date_en.delete(0, 'end')
        self.refresh_list()

    def _get_iso_dates(self):
        """Converts JJ / MM / AAAA to YYYY-MM-DD for SQLite."""
        if self.extra_filter_var.get() != "Par Date":
            return None, None
            
        if DateEntry and isinstance(self.start_date_en, DateEntry):
            d1 = self.start_date_en.get_date()
            d2 = self.end_date_en.get_date()
            if d1 > d2:
                # Silently auto-correct or show warning? Let's just return to avoid crash
                return d1.strftime("%Y-%m-%d"), d1.strftime("%Y-%m-%d")
            return d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d")
            
        def to_iso(s):
            s = s.replace(" ", "")
            if len(s) == 10: # DD/MM/YYYY
                d, m, y = s.split("/")
                return f"{y}-{m}-{d}"
            return None
        return to_iso(self.start_date_en.get()), to_iso(self.end_date_en.get())

    def accumulate_totals(self):
        query = self.search_entry.get().strip()
        wilaya = self.wilaya_var.get()
        product = self.product_var.get()
        status = self.status_var.get()
        start_iso, end_iso = self._get_iso_dates()
        
        data_grouped = database.get_grouped_accumulation(query if query else None, wilaya, product, status, start_iso, end_iso)
        grand_totals = database.get_filtered_totals(query if query else None, wilaya, product, status, start_iso, end_iso)
        
        if not data_grouped:
            messagebox.showinfo("Information", "Aucune donnée à accumuler pour ces filtres.", parent=self)
            return
            
        AccumulationWindow(self, data_grouped, grand_totals)

    def refresh_list(self, reset_page=True):
        """Fetches data and starts the chunked rendering process to keep UI responsive."""
        if reset_page:
            self.current_page = 0
            
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
        start_iso, end_iso = self._get_iso_dates()
        
        self._search_after_id = self.after(10, lambda: self._fetch_and_start_render(query, wilaya, product, status_filter, render_id, start_iso, end_iso))

    def _fetch_and_start_render(self, query, wilaya, product, status_filter, render_id, start_iso, end_iso):
        self.all_invoices = database.get_all_invoices(query if query else None, wilaya, product, status_filter, start_iso, end_iso)
        
        if hasattr(self, "loading_lbl") and self.loading_lbl.winfo_exists():
            self.loading_lbl.destroy()
        
        if not self.all_invoices:
            tk.Label(self.list_frame, text="Aucune facture trouvée.", bg="white",
                     font=("Poppins", 14), fg="gray").pack(pady=30)
            self._update_pagination_buttons(0)
            return

        self._update_pagination_buttons(len(self.all_invoices))
        self._render_page(render_id)

    def _update_pagination_buttons(self, total_count):
        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        self.page_info_lbl.configure(text=f"Page {self.current_page + 1} / {total_pages} ({total_count} invoices)")
        
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if (self.current_page + 1) * self.page_size < total_count else "disabled")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_list(reset_page=False)

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.all_invoices):
            self.current_page += 1
            self.refresh_list(reset_page=False)

    def _render_page(self, render_id):
        if render_id != self._current_render_id: return
        
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.all_invoices))
        
        self._render_chunk(self.all_invoices, start_idx, end_idx, render_id)

    def _render_chunk(self, data, start_index, page_end, render_id):
        # Stop if a newer refresh started
        if render_id != self._current_render_id:
            return
            
        # Render a small sub-chunk to keep UI responsive
        chunk_size = 5
        end_index = min(start_index + chunk_size, page_end)
        
        for i in range(start_index, end_index):
            inv = data[i]
            inv_id = inv["id"]
            dec = inv["decompte"]
            dt = inv["date"]
            name = inv["farmer_name"]
            net = inv["total_net"]
            status_val = inv["payment_status"]
            
            # Use native tk.Frame for the row container (ultra-lightweight)
            row_frame = tk.Frame(self.list_frame, bg="white", highlightthickness=1, highlightbackground="#eeeeee")
            row_frame.pack(fill="x", pady=1, padx=5)
            
            # Use native tk.Label with fixed widths for ultra-smooth scrolling
            tk.Label(row_frame, text=dec, width=15, font=("Poppins", 10), bg="white", fg="black").grid(row=0, column=0, padx=5, pady=5)
            tk.Label(row_frame, text=dt, width=15, font=("Poppins", 10), bg="white", fg="black").grid(row=0, column=1, padx=5, pady=5)
            tk.Label(row_frame, text=name, width=40, anchor="w", font=("Poppins", 10), bg="white", fg="black").grid(row=0, column=2, padx=5, pady=5)
            tk.Label(row_frame, text=f"{net:,.2f} DA", width=18, font=("Poppins", 10, "bold"), bg="white", fg="#2E7D32").grid(row=0, column=3, padx=5, pady=5)
            
            status_color = "#2E7D32" if status_val == "Payé" else "#C62828"
            display_stat = f"🟢 {status_val}" if status_val == "Payé" else f"🔴 {status_val}"
            status_lbl = tk.Label(row_frame, text=display_stat, width=15, font=("Poppins", 10), bg="white", fg=status_color)
            status_lbl.grid(row=0, column=4, padx=5, pady=5)
            
            # Pack buttons directly into row_frame to reduce widget count
            btn_view = ctk.CTkButton(row_frame, text="👁️ Voir", width=80, height=30, 
                                     font=ctk.CTkFont(family="Poppins", size=13),
                                     command=lambda i_id=inv_id: self.view_pdf(i_id))
            btn_view.grid(row=0, column=5, padx=5, pady=2, sticky="w")
            
            toggle_text = "💳 Payer" if status_val != "Payé" else "❌ Annuler"
            toggle_color = "#1976D2" if status_val != "Payé" else "#757575"
            btn_toggle = ctk.CTkButton(row_frame, text=toggle_text, width=80, height=30, 
                                       fg_color=toggle_color, font=ctk.CTkFont(family="Poppins", size=13))
            btn_toggle.configure(command=lambda i_id=inv_id, s_lbl=status_lbl, btn=btn_toggle: self.toggle_status(i_id, s_lbl, btn))
            btn_toggle.grid(row=0, column=6, padx=5, pady=2, sticky="w")
            
            # Unified Download Button
            btn_dl = ctk.CTkButton(row_frame, text="📥", width=40, height=30, 
                                   fg_color="#3B8ED0", font=ctk.CTkFont(size=14, weight="bold"),
                                   command=lambda i_id=inv_id: self.open_download_options(i_id))
            btn_dl.grid(row=0, column=7, padx=5, pady=2, sticky="w")
            btn_dl.bind("<Enter>", lambda e: self._set_status("📥 Télécharger la facture (PDF ou Excel)."))
            btn_dl.bind("<Leave>", self._clear_status)

            btn_edit = ctk.CTkButton(row_frame, text="✏️+", width=40, height=30, 
                                     fg_color="#FBC02D", text_color="black", font=ctk.CTkFont(size=14, weight="bold"),
                                     command=lambda i_id=inv_id: self.start_edit(i_id))
            btn_edit.grid(row=0, column=8, padx=(5, 10), pady=2, sticky="w")
            btn_edit.bind("<Enter>", lambda e: self._set_status("✏️+ Charger pour modification (Mise à jour)."))
            btn_edit.bind("<Leave>", self._clear_status)

        # Schedule next sub-chunk if within the same page
        if end_index < page_end:
            if self.winfo_exists():
                self.after(2, lambda: self._render_chunk(data, end_index, page_end, render_id))

    def toggle_status(self, inv_id, status_lbl, btn_toggle):
        def do_toggle():
            current_status = "Payé" if "🟢 Payé" in status_lbl.cget("text") else "Non Payé"
            new_status = "Payé" if current_status != "Payé" else "Non Payé"
            if database.update_payment_status(inv_id, new_status):
                new_color = "#2E7D32" if new_status == "Payé" else "#C62828"
                new_display = f"🟢 {new_status}" if new_status == "Payé" else f"🔴 {new_status}"
                status_lbl.configure(text=new_display, fg=new_color)
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

    def export_to_excel(self, inv_id):
        data = database.get_invoice_details(inv_id)
        if data:
            export_invoice_to_excel(data)
        else:
            messagebox.showerror("Erreur", "Impossible de récupérer les détails de la facture.", parent=self)

    def open_download_options(self, inv_id):
        """Opens a dialog to choose between PDF and Excel."""
        DownloadSelectionDialog(self, on_select=lambda fmt: self.process_download(inv_id, fmt))

    def process_download(self, inv_id, format_type):
        if format_type == "excel":
            self.export_to_excel(inv_id)
        else:
            # Handle PDF Download (Save As dialog)
            data = database.get_invoice_details(inv_id)
            if data:
                # Custom naming: FarmerName_DecNum_Year.pdf
                ident = data.get('identity', {})
                farmer_name = ident.get('farmer', 'Agriculteur').replace(' ', '_')
                dec_num = ident.get('decompte', 'Unknown').replace('/', '_')
                default_name = f"{farmer_name}_{dec_num}.pdf"
                
                from tkinter import filedialog
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF Files", "*.pdf")],
                    initialfile=default_name,
                    title="Enregistrer la facture PDF"
                )
                if file_path:
                    from pdf_generator import generate_facture_pdf
                    generate_facture_pdf(data, file_path)
                    messagebox.showinfo("Succès", f"Facture PDF enregistrée :\n{os.path.basename(file_path)}")
            else:
                messagebox.showerror("Erreur", "Données introuvables.", parent=self)
