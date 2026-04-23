import customtkinter as ctk
import os
import datetime
import fitz  # PyMuPDF
import ctypes
from PIL import Image
import tkinter as tk
from tkinter import messagebox
from pdf_generator import generate_facture_pdf
import database

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")



TAXES_LIST = [
    "taxe pour compte CNA",
    "taxe pour chambre agricole",
    "redevance CH AGP",
    "sacherie",
    "Credit semence",
    "Credit engrais",
    "Fongicide",
    "Kit aspersion/Oniouleur",
    "pivot",
    "Préstation Motoculture"
]

class InvoicePreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, pdf_path, on_confirm=None, mode="creation"):
        super().__init__(parent)
        self.title("Invoice Preview (Exact Layout)")
        self.geometry("850x700")
        self.lift()
        self.on_confirm = on_confirm
        self.pdf_path = pdf_path
        self.mode = mode
        
        # Make top level modal
        self.grab_set()
        
        # Prevent screenshots specifically for the preview
        self.after(100, lambda: self._apply_protection())

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- ACTION BUTTONS (Pack these FIRST at the bottom) ---
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=10)
        
        if self.mode == "creation":
            self.btn_print = ctk.CTkButton(btn_frame, text="✅ CONFIRM & SAVE PDF", command=self.confirm_and_close,
                                           fg_color="green", font=ctk.CTkFont(size=14, weight="bold"), height=40)
            self.btn_print.pack(side="left", expand=True, padx=10)
            
            self.btn_cancel = ctk.CTkButton(btn_frame, text="❌ CANCEL", command=self.on_cancel,
                                            fg_color="#C62828", font=ctk.CTkFont(size=14), height=40)
            self.btn_cancel.pack(side="right", expand=True, padx=10)
        else:
            # View-only / History mode
            self.btn_print = ctk.CTkButton(btn_frame, text="🖨️ PRINT / OPEN FILE", command=lambda: os.startfile(self.pdf_path),
                                           fg_color="#1976D2", font=ctk.CTkFont(size=14, weight="bold"), height=40)
            self.btn_print.pack(side="left", expand=True, padx=10)
            
            self.btn_close = ctk.CTkButton(btn_frame, text="Fermer", command=self.destroy,
                                           fg_color="gray", font=ctk.CTkFont(size=14), height=40)
            self.btn_close.pack(side="right", expand=True, padx=10)

        # Scrollable area for the image (Takes remaining space)
        self.scroll_canvas = ctk.CTkScrollableFrame(main_frame, fg_color="gray20")
        self.scroll_canvas.pack(side="top", fill="both", expand=True, pady=(0, 10))
        
        # Render the PDF to an image
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)  # Load first page
            
            # Increase resolution for sharpness (zoom=2.0)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert pixmap to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert to CTkImage
            self.preview_image = ctk.CTkImage(light_image=img, dark_image=img, size=(pix.width//2.5, pix.height//2.5))
            
            # Display image centered
            self.image_label = ctk.CTkLabel(self.scroll_canvas, image=self.preview_image, text="")
            self.image_label.pack(expand=True, padx=20, pady=20)
            doc.close()
        except Exception as e:
            ctk.CTkLabel(self.scroll_canvas, text=f"Error rendering preview: {e}").pack(pady=50)
        
    def on_cancel(self):
        try:
            # Only delete the file in creation mode if cancelled
            if self.mode == "creation" and os.path.exists(self.pdf_path):
                os.remove(self.pdf_path)
        except:
            pass
        self.destroy()

    def _apply_protection(self):
        """Internal helper for Windows screenshot protection."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            # WDA_EXCLUDEFROMCAPTURE = 0x11 (Windows 10 2004+)
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass

    def confirm_and_close(self):
        self.destroy()
        if self.on_confirm:
            self.on_confirm()

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📜 Historique des Factures")
        self.geometry("950x600")
        self._search_after_id = None  # debounce timer
        
        # Prevent screenshots for history too
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass

        # Filter Bar (Horizontal)
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=20, pady=20)
        
        # Identity Search
        ctk.CTkLabel(filter_frame, text="Recherche Nom/NIF:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="Mecheni...", width=200)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self._schedule_refresh)
        self.search_entry.bind("<Return>", lambda e: self.refresh_list())
        
        # Wilaya Filter
        ctk.CTkLabel(filter_frame, text="Wilaya:").pack(side="left", padx=5)
        self.wilaya_var = ctk.StringVar(value="Tous")
        self.wilaya_menu = ctk.CTkOptionMenu(filter_frame, values=["Tous", "Ouargla", "Tougourt", "Ilizi"], 
                                             variable=self.wilaya_var, command=lambda _: self.refresh_list(), width=120)
        self.wilaya_menu.pack(side="left", padx=5)
        
        # Product Filter
        ctk.CTkLabel(filter_frame, text="Produit:").pack(side="left", padx=5)
        product_list = ["Tous"] + list(self.master.products.keys())
        self.product_var = ctk.StringVar(value="Tous")
        self.product_menu = ctk.CTkOptionMenu(filter_frame, values=product_list, 
                                              variable=self.product_var, command=lambda _: self.refresh_list(), width=140)
        self.product_menu.pack(side="left", padx=5)
        
        btn_refresh = ctk.CTkButton(filter_frame, text="🔄 Actualiser", width=100, command=self.refresh_list, fg_color="#37474F")
        btn_refresh.pack(side="right", padx=5)

        self.results_count_lbl = ctk.CTkLabel(filter_frame, text="Recherche...", font=ctk.CTkFont(size=11, slant="italic"), text_color="#90caf9")
        self.results_count_lbl.pack(side="right", padx=15)

        
        # Header for the list - Using unified column configure
        header_frame = tk.Frame(self, bg="gray20")
        header_frame.pack(fill="x", padx=20, pady=0)
        for i, weight in enumerate([0, 0, 1, 0, 0]):
            header_frame.grid_columnconfigure(i, weight=weight)

        tk.Label(header_frame, text="Facture #",   width=15, bg="gray20", fg="white", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
        tk.Label(header_frame, text="Date",        width=15, bg="gray20", fg="white", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(header_frame, text="Agriculteur", width=40, bg="gray20", fg="white", font=("Segoe UI", 10, "bold"), anchor="w").grid(row=0, column=2, padx=5, pady=5)
        tk.Label(header_frame, text="Montant Net", width=15, bg="gray20", fg="white", font=("Segoe UI", 10, "bold")).grid(row=0, column=3, padx=5, pady=5)
        tk.Label(header_frame, text="Actions",     width=12, bg="gray20", fg="white", font=("Segoe UI", 10, "bold")).grid(row=0, column=4, padx=5, pady=5)
        
        # Scrollable list — canvas-based for smooth scrolling on Windows
        list_container = tk.Frame(self, bg="#2b2b2b")
        list_container.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self._list_canvas = tk.Canvas(list_container, bg="#2b2b2b",
                                      bd=0, highlightthickness=0)
        _scrollbar = ctk.CTkScrollbar(list_container, command=self._list_canvas.yview)
        self._list_canvas.configure(yscrollcommand=_scrollbar.set)

        _scrollbar.pack(side="right", fill="y")
        self._list_canvas.pack(side="left", fill="both", expand=True)

        # Inner frame that holds the rows
        self.list_frame = tk.Frame(self._list_canvas, bg="#2b2b2b")
        self._canvas_window = self._list_canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw")

        # Resize inner frame width when canvas resizes
        def _on_canvas_resize(e):
            self._list_canvas.itemconfig(self._canvas_window, width=e.width)
        self._list_canvas.bind("<Configure>", _on_canvas_resize)

        # Update scrollregion when inner frame changes size
        def _on_frame_configure(e):
            self._list_canvas.configure(
                scrollregion=self._list_canvas.bbox("all"))
        self.list_frame.bind("<Configure>", _on_frame_configure)

        # --- Mousewheel: Improved responsiveness ---
        def _on_mousewheel(event):
            # Scroll faster: 3 units per notch instead of 1
            delta = int(-3 * (event.delta / 120))
            self._list_canvas.yview_scroll(delta, "units")

        self.bind("<MouseWheel>", _on_mousewheel)
        
        # Accumulate area (Bottom)
        self.accum_frame = ctk.CTkFrame(self)
        self.accum_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_accum = ctk.CTkButton(self.accum_frame, text="📊 Accumulate Totals", 
                                       command=self.accumulate_totals, 
                                       fg_color="#FBC02D", text_color="black", font=ctk.CTkFont(weight="bold"))
        self.btn_accum.pack(side="left", padx=10, pady=10)
        
        self.totals_label = ctk.CTkLabel(self.accum_frame, text="Cliquer pour calculer les totaux de la liste.", 
                                         font=ctk.CTkFont(size=12), justify="left")
        self.totals_label.pack(side="left", padx=20)

        # Status Bar / Tooltip area
        self.status_bar = ctk.CTkLabel(self, text="Survoler un bouton pour voir son action...", 
                                       font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.status_bar.pack(pady=5)
        
        self.refresh_list()

    def _schedule_refresh(self, event=None):
        """Debounce search: wait 300ms after last keystroke before refreshing."""
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self.refresh_list)

    def _set_status(self, text):
        self.status_bar.configure(text=text, text_color="white")

    def _clear_status(self, _=None):
        self.status_bar.configure(text="Survoler un bouton pour voir son action...", text_color="gray")

    def accumulate_totals(self):
        """Fetches grouped aggregate data and displays it in a professional table popup."""
        query = self.search_entry.get().strip()
        wilaya = self.wilaya_var.get()
        product = self.product_var.get()
        
        # Get per-product rows
        data_grouped = database.get_grouped_accumulation(query if query else None, wilaya, product)
        # Get overall invoice-level totals (for Net and Retenues)
        grand_totals = database.get_filtered_totals(query if query else None, wilaya, product)
        
        if not data_grouped:
            messagebox.showinfo("Information", "Aucune donnée à accumuler pour ces filtres.", parent=self)
            return
            
        AccumulationWindow(self, data_grouped, grand_totals)


    def refresh_list(self):
        # Clear existing widgets and reset scroll position
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self._list_canvas.yview_moveto(0)

        query = self.search_entry.get().strip()
        wilaya = self.wilaya_var.get()
        product = self.product_var.get()

        invoices = database.get_all_invoices(query if query else None, wilaya, product)

        if not invoices:
            self.results_count_lbl.configure(text="0 résultat trouvé")
            lbl = tk.Label(self.list_frame, text="Aucune facture trouvée.",
                           font=("Segoe UI", 11, "italic"), bg="#2b2b2b", fg="gray")
            lbl.pack(pady=20)
            return

        self.results_count_lbl.configure(text=f"{len(invoices)} résultats trouvés")


        # Configure shared column layout on the list container
        for i, weight in enumerate([0, 0, 1, 0, 0]):
            self.list_frame.grid_columnconfigure(i, weight=weight)

        for i, inv in enumerate(invoices):
            inv_id = inv["id"]
            dec   = inv["decompte"]
            dt    = inv["date"]
            name  = inv["farmer_name"]
            net   = inv["total_net"]
            path  = inv["pdf_path"]

            # Alternating zebra background for readability without extra frames
            bg_color = "#2b2b2b" if i % 2 == 0 else "#333333"

            # Grid labels directly onto list_frame (Maximum performance)
            tk.Label(self.list_frame, text=dec,  width=15, bg=bg_color, fg="white", font=("Segoe UI", 10), height=2).grid(row=i, column=0, sticky="nsew", padx=1)
            tk.Label(self.list_frame, text=dt,   width=15, bg=bg_color, fg="white", font=("Segoe UI", 10), height=2).grid(row=i, column=1, sticky="nsew", padx=1)
            tk.Label(self.list_frame, text=name, width=40, bg=bg_color, fg="white", font=("Segoe UI", 10), height=2, anchor="w").grid(row=i, column=2, sticky="nsew", padx=1)
            tk.Label(self.list_frame, text=f"{net:,.2f} DA", width=15, bg=bg_color, fg="#A5D6A7", font=("Segoe UI", 10, "bold"), height=2).grid(row=i, column=3, sticky="nsew", padx=1)

            actions_frame = tk.Frame(self.list_frame, bg=bg_color, height=35)
            actions_frame.grid(row=i, column=4, sticky="nsew", padx=1)

            btn_view = ctk.CTkButton(actions_frame, text="👁️", width=40, height=25,
                                     font=ctk.CTkFont(size=14),
                                     command=lambda p=path: self.view_pdf(p))
            btn_view.pack(side="left", padx=2, pady=5)
            btn_view.bind("<Enter>", lambda e: self._set_status("👁️ Aperçu de la facture."))
            btn_view.bind("<Leave>", self._clear_status)

            btn_regen = ctk.CTkButton(actions_frame, text="🔄", width=40, height=25,
                                      fg_color="#2E7D32", font=ctk.CTkFont(size=14),
                                      command=lambda i_id=inv_id: self.regenerate_pdf(i_id))
            btn_regen.pack(side="left", padx=2, pady=5)
            btn_regen.bind("<Enter>", lambda e: self._set_status("🔄 Régénérer le PDF."))
            btn_regen.bind("<Leave>", self._clear_status)

            btn_edit = ctk.CTkButton(actions_frame, text="✏️+", width=40, height=25,
                                     fg_color="#FBC02D", text_color="black", font=ctk.CTkFont(size=14, weight="bold"),
                                     command=lambda i_id=inv_id: self.start_edit(i_id))
            btn_edit.pack(side="left", padx=2, pady=5)
            btn_edit.bind("<Enter>", lambda e: self._set_status("✏️+ Charger pour modification (Mise à jour)."))
            btn_edit.bind("<Leave>", self._clear_status)

    def start_edit(self, inv_id):
        """Loads an invoice for editing and closes the history window."""
        self.master.load_invoice_for_edit(inv_id)
        self.destroy()

    def view_pdf(self, path):
        if path and os.path.exists(path):
            InvoicePreviewWindow(self, path, mode="view")
        else:
            messagebox.showerror("Erreur", "Le fichier PDF original n'a pas été trouvé à l'emplacement sauvegardé.\nVeuillez utiliser le bouton Régénérer (🔄).", parent=self)

    def regenerate_pdf(self, inv_id):
        data = database.get_invoice_details(inv_id)
        if data:
            farmer_name = data['identity']['farmer']
            # Clean name for filename
            farmer_clean = "".join(x for x in farmer_name if x.isalnum() or x in " -_").strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"facture_{farmer_clean}_regen_{timestamp}.pdf"
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            
            try:
                generate_facture_pdf(data, output_path)
                # Open the internal previewer in view mode
                InvoicePreviewWindow(self, output_path, mode="view")
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de la reconstruction: {e}", parent=self)

class AccumulationWindow(ctk.CTkToplevel):
    def __init__(self, parent, data, grand_totals):
        super().__init__(parent)
        self.title("Rapport Financier d'Accumulation")
        self.geometry("1100x650")
        self.attributes("-topmost", True)
        
        # Screenshot protection
        try:
            from ctypes import windll
            windll.user32.SetWindowDisplayAffinity(self.winfo_id(), 0x00000011)
        except:
            pass
            
        header_font = ctk.CTkFont(size=14, weight="bold")
        main_font = ctk.CTkFont(size=12)
        summary_font = ctk.CTkFont(size=16, weight="bold")
        
        # Table Scrollable Frame
        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Headers
        headers = ["Nature du Produit", "Agriculteurs", "Qte Totale", "Avant Taxes", "Bonification", "Réfaction", "Montant Brut"]
        for col, h in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=h, font=header_font, width=140).grid(row=0, column=col, padx=5, pady=10)
            
        # Data Rows
        row_idx = 1
        for row in data:
            ctk.CTkLabel(self.table_frame, text=row['nature'], font=main_font, width=140).grid(row=row_idx, column=0, padx=5, pady=5)
            ctk.CTkLabel(self.table_frame, text=str(row['farmer_count']), font=main_font, width=140).grid(row=row_idx, column=1, padx=5, pady=5)
            ctk.CTkLabel(self.table_frame, text=f"{row['qte']:,.2f}", font=main_font, width=140).grid(row=row_idx, column=2, padx=5, pady=5)
            ctk.CTkLabel(self.table_frame, text=f"{row['avant']:,.2f}", font=main_font, width=140).grid(row=row_idx, column=3, padx=5, pady=5)
            ctk.CTkLabel(self.table_frame, text=f"{row['bon']:,.2f}", font=main_font, width=140).grid(row=row_idx, column=4, padx=5, pady=5)
            ctk.CTkLabel(self.table_frame, text=f"{row['refac']:,.2f}", font=main_font, width=140).grid(row=row_idx, column=5, padx=5, pady=5)
            ctk.CTkLabel(self.table_frame, text=f"{row['net_prod']:,.2f}", font=main_font, width=140).grid(row=row_idx, column=6, padx=5, pady=5)
            row_idx += 1
            
        # --- SUMMARY ROWS (Integrated into the same table) ---
        
        # 1. Spacer/Divider Line
        ctk.CTkFrame(self.table_frame, height=2, fg_color="gray").grid(row=row_idx, column=0, columnspan=7, sticky="ew", pady=10)
        row_idx += 1
        
        # 2. TOTAL GÉNÉRAL (Sum of columns)
        ctk.CTkLabel(self.table_frame, text="TOTAL GÉNÉRAL", font=header_font).grid(row=row_idx, column=0, padx=5, pady=5)
        # Count all unique farmers (We can sum them from the grouped data for simplicity in this view)
        total_farmers = sum(r['farmer_count'] for r in data)
        ctk.CTkLabel(self.table_frame, text=str(total_farmers), font=header_font).grid(row=row_idx, column=1, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_avant'] / 6000 if grand_totals['total_avant'] > 0 else 0:,.2f}?", font=header_font).grid_forget() # Placeholder logic removed
        
        # Summing the rest from grand_totals
        ctk.CTkLabel(self.table_frame, text=f"{sum(r['qte'] for r in data):,.2f}", font=header_font).grid(row=row_idx, column=2, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_avant']:,.2f}", font=header_font).grid(row=row_idx, column=3, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_bon']:,.2f}", font=header_font).grid(row=row_idx, column=4, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_refac']:,.2f}", font=header_font).grid(row=row_idx, column=5, padx=5, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_avant'] + grand_totals['total_bon'] - grand_totals['total_refac']:,.2f}", font=header_font).grid(row=row_idx, column=6, padx=5, pady=5)
        row_idx += 1
        
        # 3. TOTAL RETENUES
        ctk.CTkLabel(self.table_frame, text="TOTAL RETENUES (TAXES)", font=header_font, text_color="#FF8A65").grid(row=row_idx, column=0, columnspan=6, sticky="e", padx=20, pady=5)
        ctk.CTkLabel(self.table_frame, text=f"- {grand_totals['total_retenues']:,.2f}", font=header_font, text_color="#FF8A65").grid(row=row_idx, column=6, padx=5, pady=5)
        row_idx += 1
        
        ctk.CTkLabel(self.table_frame, text=f"{grand_totals['total_net']:,.2f} DA", font=summary_font, text_color="#A5D6A7").grid(row=row_idx, column=6, padx=5, pady=10)

class AdminPanelWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️ Panneau d'Administration")
        self.geometry("700x550")
        self.grab_set()
        
        # Tabs for Users and Products
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tab_users = self.tabs.add("Utilisateurs")
        self.tab_prods = self.tabs.add("Produits")
        
        self._setup_users_tab()
        self._setup_prods_tab()
        
    def _setup_users_tab(self):
        # Add User UI
        add_frame = ctk.CTkFrame(self.tab_users)
        add_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(add_frame, text="Nouveau Utilisateur:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=5)
        self.new_user_entry = ctk.CTkEntry(add_frame, placeholder_text="Login")
        self.new_user_entry.grid(row=1, column=0, padx=5, pady=5)
        self.new_pass_entry = ctk.CTkEntry(add_frame, placeholder_text="Pass", show="*")
        self.new_pass_entry.grid(row=1, column=1, padx=5, pady=5)
        self.new_role_var = ctk.StringVar(value="user")
        ctk.CTkOptionMenu(add_frame, values=["user", "admin"], variable=self.new_role_var, width=100).grid(row=1, column=2, padx=5, pady=5)
        
        ctk.CTkButton(add_frame, text="Ajouter", command=self._add_user_cmd, width=80).grid(row=1, column=3, padx=5, pady=5)
        
        # User List
        list_frame = ctk.CTkScrollableFrame(self.tab_users, height=300)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.users_list_frame = list_frame
        self._refresh_users()

    def _refresh_users(self):
        for w in self.users_list_frame.winfo_children(): w.destroy()
        users = database.get_all_users()
        for u, r in users:
            f = ctk.CTkFrame(self.users_list_frame)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=u, width=150, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(f, text=f"({r})", text_color="gray").pack(side="left", padx=10)
            if u != "admin": # Primary admin protection
                ctk.CTkButton(f, text="X", width=30, fg_color="#C62828", command=lambda un=u: self._del_user_cmd(un)).pack(side="right", padx=10)

    def _add_user_cmd(self):
        u = self.new_user_entry.get().strip()
        p = self.new_pass_entry.get().strip()
        r = self.new_role_var.get()
        if u and p:
            if database.add_user(u, p, r):
                self._refresh_users()
                self.new_user_entry.delete(0, 'end'); self.new_pass_entry.delete(0, 'end')
            else: messagebox.showerror("Error", "User exists or DB error")
        else: messagebox.showwarning("!", "Fill all fields")

    def _del_user_cmd(self, un):
        if messagebox.askyesno("Confirm", f"Delete user {un}?", parent=self):
            database.delete_user(un)
            self._refresh_users()

    def _setup_prods_tab(self):
        add_frame = ctk.CTkFrame(self.tab_prods)
        add_frame.pack(fill="x", padx=10, pady=10)
        
        self.new_prod_entry = ctk.CTkEntry(add_frame, placeholder_text="Nom du produit")
        self.new_prod_entry.grid(row=0, column=0, padx=5, pady=5)
        self.new_price_entry = ctk.CTkEntry(add_frame, placeholder_text="Prix (ex: 6000)")
        self.new_price_entry.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(add_frame, text="Ajouter Produit", command=self._add_prod_cmd).grid(row=0, column=2, padx=5, pady=5)
        
        list_frame = ctk.CTkScrollableFrame(self.tab_prods, height=300)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.prods_list_frame = list_frame
        self._refresh_prods()

    def _refresh_prods(self):
        for w in self.prods_list_frame.winfo_children(): w.destroy()
        prods = database.get_db_products()
        for name, price in prods.items():
            f = ctk.CTkFrame(self.prods_list_frame)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=name, width=200, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(f, text=f"{price:,.2f} DA", text_color="#90caf9").pack(side="left", padx=10)
            ctk.CTkButton(f, text="Suppr", width=50, fg_color="#C62828", command=lambda n=name: self._del_prod_cmd(n)).pack(side="right", padx=10)

    def _add_prod_cmd(self):
        n = self.new_prod_entry.get().strip()
        p_str = self.new_price_entry.get().strip()
        try:
            p = float(p_str)
            if n and database.add_db_product(n, p):
                self._refresh_prods()
                self.new_prod_entry.delete(0, 'end'); self.new_price_entry.delete(0, 'end')
                # Trigger main app to reload products
                if hasattr(self.master, 'reload_products'): self.master.reload_products()
            else: messagebox.showerror("!", "Error adding product")
        except: messagebox.showerror("!", "Price must be a number")

    def _del_prod_cmd(self, n):
        if messagebox.askyesno("Confirm", f"Delete {n}?", parent=self):
            database.delete_db_product(n)
            self._refresh_prods()
            if hasattr(self.master, 'reload_products'): self.master.reload_products()

class App(ctk.CTkToplevel):
    def __init__(self, master, username="admin", role="user", on_disconnect=None):
        super().__init__(master)
        
        self.username = username
        self.role = role
        self.on_disconnect = on_disconnect
        
        # Load products and setup UI
        self.reload_products()
        self._setup_ui()
        
    def reload_products(self):
        """Fetches products from the database and updates the UI."""
        self.products = database.get_db_products()
        self.current_product_list = list(self.products.keys())
        if hasattr(self, 'nature_menu'):
            self.nature_menu.configure(values=self.current_product_list)

    def open_history(self):
        HistoryWindow(self)

    def open_admin_panel(self):
        AdminPanelWindow(self)
    
    def _setup_ui(self):
        self.title("Facture PDF Generator")
        self.geometry("800x900")
        
        # Initialize Database
        database.init_db()
        
        # Make grid responsive
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # top bar
        self.grid_rowconfigure(1, weight=1)  # main content
        
        # --- TOP BAR (Account Info & Disconnect) ---
        top_bar = ctk.CTkFrame(self, fg_color="#1a1a2e", height=45, corner_radius=0)
        top_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        top_bar.grid_columnconfigure(1, weight=1)
        
        # Account type icon + label
        role_display = "Administrateur" if self.role == "admin" else "Utilisateur"
        account_info = ctk.CTkLabel(top_bar, 
                                    text=f"👤  {self.username.upper()}  |  {role_display}",
                                    font=ctk.CTkFont(size=13, weight="bold"),
                                    text_color="#90caf9")
        account_info.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        
        # Action Center (Management Buttons)
        actions_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions_frame.grid(row=0, column=1, padx=5, pady=0)
        
        # History is available to all per user request
        self.history_btn = ctk.CTkButton(actions_frame, text="📜 Historique", width=120, height=30,
                                         fg_color="#455A64", command=self.open_history)
        self.history_btn.pack(side="left", padx=5)
        
        # Admin Panel restricted
        if self.role == "admin":
            self.admin_btn = ctk.CTkButton(actions_frame, text="⚙️ Admin Panel", width=120, height=30,
                                            fg_color="#1565C0", command=self.open_admin_panel)
            self.admin_btn.pack(side="left", padx=5)
        
        # Disconnect button
        disconnect_btn = ctk.CTkButton(top_bar, text="🔒 Déconnexion", width=140, height=30,
                                        fg_color="#C62828", hover_color="#8E0000",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        command=self._disconnect)
        disconnect_btn.grid(row=0, column=2, padx=15, pady=8, sticky="e")
        
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)

        row_idx = 0
        
        # --- TITLE ---
        title = ctk.CTkLabel(self.scrollable_frame, text="Generate Invoice", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=row_idx, column=0, columnspan=2, pady=(10, 20))
        row_idx += 1
        
        # --- IDENTITY DETAILS ---
        id_frame = ctk.CTkFrame(self.scrollable_frame)
        id_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        id_frame.grid_columnconfigure(1, weight=1)
        id_frame.grid_columnconfigure(3, weight=1)
        row_idx += 1
        
        ctk.CTkLabel(id_frame, text="Identity Details", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, pady=10)
        
        # Row 1: Nom de l'agriculteur & Address
        ctk.CTkLabel(id_frame, text="Nom de l'agriculteur").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.farmer_entry = ctk.CTkEntry(id_frame)
        self.farmer_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        vcmd_farmer = (self.register(self._validate_farmer), '%P')
        self.farmer_entry.configure(validate='key', validatecommand=vcmd_farmer)
        self.farmer_entry.bind("<Return>", self._on_farmer_enter)

        ctk.CTkLabel(id_frame, text="L'adresse").grid(row=1, column=2, padx=10, pady=5, sticky="e")
        self.remis_entry = ctk.CTkEntry(id_frame, state="disabled")
        self.remis_entry.grid(row=1, column=3, padx=10, pady=5, sticky="ew")
        self.remis_entry.bind("<Return>", self._on_address_enter)
        
        # Row 2: Wilaya
        ctk.CTkLabel(id_frame, text="Wilaya").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.wilaya_var = ctk.StringVar(value="Ouargla")
        self.wilaya_menu = ctk.CTkOptionMenu(id_frame, values=["Ouargla", "Tougourt", "Ilizi"], 
                                             variable=self.wilaya_var, command=self._on_wilaya_choice, state="disabled")
        self.wilaya_menu.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Row 3: NIF & Piece ID
        ctk.CTkLabel(id_frame, text="NIF (Facultatif)").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.nif_entry = ctk.CTkEntry(id_frame, state="disabled")
        self.nif_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        vcmd_nif = (self.register(self._validate_nif), '%P')
        self.nif_entry.configure(validate='key', validatecommand=vcmd_nif)
        self.nif_entry.bind("<KeyRelease>", self._on_nif_key)
        self.nif_entry.bind("<Return>", self._on_nif_enter)

        ctk.CTkLabel(id_frame, text="Pièce d'identité (9 chiffres)").grid(row=3, column=2, padx=10, pady=5, sticky="e")
        self.piece_entry = ctk.CTkEntry(id_frame, state="disabled")
        self.piece_entry.grid(row=3, column=3, padx=10, pady=5, sticky="ew")
        vcmd = (self.register(self._validate_piece), '%P')
        self.piece_entry.configure(validate='key', validatecommand=vcmd)
        self.piece_entry.bind("<KeyRelease>", self._on_piece_key)
        self.piece_entry.bind("<Return>", self._on_piece_enter)
        
        # Row 4: Date & Decompte
        ctk.CTkLabel(id_frame, text="Derifier le (Date)").grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.date_entry = ctk.CTkEntry(id_frame)
        self.date_entry.insert(0, datetime.datetime.now().strftime("%d/%m/%Y"))
        self.date_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.date_entry.configure(state="disabled")
        
        ctk.CTkLabel(id_frame, text="Decompte N°").grid(row=4, column=2, padx=10, pady=5, sticky="e")
        self.decompte_entry = ctk.CTkEntry(id_frame)
        self.current_count = self.load_count()
        year = datetime.datetime.now().year
        self.decompte_entry.insert(0, f"{self.current_count}/{year}")
        self.decompte_entry.grid(row=4, column=3, padx=10, pady=5, sticky="ew")
        self.decompte_entry.configure(state="disabled")

        # Row 5: Edit Identity Button (Allows fixing typos) - Starts DISABLED
        self.edit_id_btn = ctk.CTkButton(id_frame, text="Modifier l'identité ✏️", 
                                         width=150, height=24, fg_color="#37474F",
                                         state="disabled",
                                         command=self.unlock_identity)
        self.edit_id_btn.grid(row=5, column=0, columnspan=4, pady=(5, 10))

        # Bind checks to all identity fields to enable button when full
        self.farmer_entry.bind("<KeyRelease>", self._check_id_ready, add="+")
        self.remis_entry.bind("<KeyRelease>", self._check_id_ready, add="+")
        self.nif_entry.bind("<KeyRelease>", self._check_id_ready, add="+")
        self.piece_entry.bind("<KeyRelease>", self._check_id_ready, add="+")


        # --- PRODUCT DATA ---
        prod_frame = ctk.CTkFrame(self.scrollable_frame)
        prod_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        prod_frame.grid_columnconfigure(1, weight=1)
        prod_frame.grid_columnconfigure(3, weight=1)
        row_idx += 1
        
        ctk.CTkLabel(prod_frame, text="Détails des Produits", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.multi_prod_var = ctk.BooleanVar(value=False)
        self.multi_prod_check = ctk.CTkCheckBox(prod_frame, text="Plusieurs produits ?", variable=self.multi_prod_var, font=ctk.CTkFont(weight="bold"))
        self.multi_prod_check.grid(row=0, column=2, columnspan=2, padx=10, sticky="e")

        ctk.CTkLabel(prod_frame, text="Nature de produit").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.nature_var = ctk.StringVar(value=" ")
        self.nature_menu = ctk.CTkOptionMenu(prod_frame, values=self.current_product_list, variable=self.nature_var, command=self._on_nature_choice, state="disabled")
        self.nature_menu.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.nature_menu.bind("<Return>", self._on_nature_enter)
        
        ctk.CTkLabel(prod_frame, text="Quantité").grid(row=1, column=2, padx=10, pady=5, sticky="e")
        self.quantite_entry = ctk.CTkEntry(prod_frame, state="disabled")
        self.quantite_entry.grid(row=1, column=3, padx=10, pady=5, sticky="w")
        self.quantite_entry.bind("<Return>", self._on_qty_enter)
        self.quantite_entry.bind("<Control-Return>", lambda e: self._on_qty_enter(e, jump_to_taxes=True))
        
        ctk.CTkLabel(prod_frame, text="Bonification").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.bon_entry = ctk.CTkEntry(prod_frame, state="disabled")
        self.bon_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.bon_entry.bind("<Return>", self._on_bon_enter)
        self.bon_entry.bind("<Control-Return>", lambda e: self._on_bon_enter(e, jump_to_taxes=True))
        
        ctk.CTkLabel(prod_frame, text="Réfaction").grid(row=2, column=2, padx=10, pady=5, sticky="e")
        self.refac_entry = ctk.CTkEntry(prod_frame, state="disabled")
        self.refac_entry.grid(row=2, column=3, padx=10, pady=5, sticky="w")
        self.refac_entry.bind("<Return>", self._on_refac_enter)
        self.refac_entry.bind("<Control-Return>", lambda e: self._on_refac_enter(e, jump_to_taxes=True))
        
        # Added products summary & buttons
        self.added_products = []
        
        self.add_prod_btn = ctk.CTkButton(prod_frame, text="Ajouter le produit", command=self.add_product, state="disabled")
        self.add_prod_btn.grid(row=3, column=0, pady=10, padx=10)
        
        self.clear_prod_btn = ctk.CTkButton(prod_frame, text="Vider la liste", command=self.clear_products, fg_color="#C62828", state="disabled")
        self.clear_prod_btn.grid(row=3, column=1, pady=10, padx=10)
        
        self.prod_count_lbl = ctk.CTkLabel(prod_frame, text="Produits: 0 / 5", font=ctk.CTkFont(size=12, weight="bold"))
        self.prod_count_lbl.grid(row=3, column=2, padx=10)
        
        self.to_taxes_btn = ctk.CTkButton(prod_frame, text="Terminer et passer aux taxes ➔", command=self._go_to_taxes, state="disabled", fg_color="#E65100")
        self.to_taxes_btn.grid(row=3, column=3, pady=10, padx=10)
        
        self.prod_listbox = ctk.CTkScrollableFrame(prod_frame, height=85, label_text="Produits ajoutés", label_font=ctk.CTkFont(size=11, weight="bold"))
        self.prod_listbox.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=5)
        
        # --- TAXES / RETENUES ---
        tax_frame = ctk.CTkFrame(self.scrollable_frame)
        tax_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        tax_frame.grid_columnconfigure(1, weight=1)
        tax_frame.grid_columnconfigure(2, weight=1)
        tax_frame.grid_columnconfigure(3, weight=1)
        row_idx += 1
        
        ctk.CTkLabel(tax_frame, text="Retenues Diverses", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, pady=10)
        
        ctk.CTkLabel(tax_frame, text="Tax Name").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(tax_frame, text="Quantité").grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkLabel(tax_frame, text="P.U").grid(row=1, column=2, padx=5, pady=5)
        ctk.CTkLabel(tax_frame, text="Amount / Total").grid(row=1, column=3, padx=5, pady=5)
        
        self.tax_inputs = []
        for i, tax_name in enumerate(TAXES_LIST):
            r = i + 2
            ctk.CTkLabel(tax_frame, text=tax_name).grid(row=r, column=0, padx=5, pady=5, sticky="w")
            
            if tax_name in ["taxe pour compte CNA", "taxe pour chambre agricole"]:
                # Show all three columns for these dynamic taxes
                nbre_en = ctk.CTkEntry(tax_frame, width=80)
                nbre_en.grid(row=r, column=1, padx=5, pady=5)
                nbre_en.configure(state="disabled")
                
                pu_en = ctk.CTkEntry(tax_frame, width=80)
                pu_en.grid(row=r, column=2, padx=5, pady=5)
                if tax_name == "taxe pour compte CNA":
                    pu_en.insert(0, "15")
                pu_en.configure(state="disabled")
                
                amount_en = ctk.CTkEntry(tax_frame, width=100)
                amount_en.grid(row=r, column=3, padx=5, pady=5)
                amount_en.configure(state="disabled")
            else:
                # For all other taxes: only show Amount column
                nbre_en = ctk.CTkEntry(tax_frame, width=80)
                nbre_en.grid_forget()  # hide
                
                pu_en = ctk.CTkEntry(tax_frame, width=80)
                pu_en.grid_forget()  # hide
                
                amount_en = ctk.CTkEntry(tax_frame, width=100)
                amount_en.grid(row=r, column=3, padx=5, pady=5)
            
            # Universal binds for tax amounts
            amount_en.bind("<KeyRelease>", lambda e: self.calculate())
            amount_en.bind("<Return>", lambda e, idx=i: self._on_tax_enter(idx))
            
            self.tax_inputs.append({
                "name": tax_name,
                "nbre": nbre_en,
                "pu": pu_en,
                "amount": amount_en
            })

        # "Done" button for taxes
        self.tax_done_btn = ctk.CTkButton(tax_frame, text="Confirm Taxes (Done)", command=self.confirm_taxes, fg_color="#3B8ED0")
        self.tax_done_btn.grid(row=len(TAXES_LIST) + 2, column=3, pady=10, padx=5)
            
        # --- RESULTS / CALC ---
        res_frame = ctk.CTkFrame(self.scrollable_frame)
        res_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        row_idx += 1
        
        self.res_lbl = ctk.CTkLabel(res_frame, text="Totals will be calculated automatically.", font=ctk.CTkFont(size=14))
        self.res_lbl.pack(pady=15)
        
        # BUTTONS
        btn_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=20)
        
        self.calc_btn = ctk.CTkButton(btn_frame, text="Clear All (Restart)", command=self.clear_all, fg_color="#C62828")
        self.calc_btn.grid(row=0, column=0, padx=10)
        
        self.hist_btn = ctk.CTkButton(btn_frame, text="📜 View History", command=self.show_history, fg_color="#455A64")
        self.hist_btn.grid(row=0, column=1, padx=10)
        
        self._compiled_data = None
        
        # Apply screenshot protection and set initial focus
        self.after(200, self._init_final_setup)

    def _disconnect(self):
        """Handles disconnect: closes App and returns to login."""
        if self.on_disconnect:
            self.on_disconnect()
        else:
            self.destroy()

    def _init_final_setup(self):
        """Handles focus and screenshot protection once UI is ready."""
        self.farmer_entry.focus()
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            # WDA_EXCLUDEFROMCAPTURE = 0x11
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass

    def load_count(self):
        try:
            if os.path.exists("counter.txt"):
                with open("counter.txt", "r") as f:
                    return int(f.read().strip())
            return 1
        except:
            return 1

    def _check_id_ready(self, event=None):
        """Disables/Enables the Modify button based on form completion."""
        # Only check if we are NOT in 'Done' state (green button state handled in unlock/lock)
        if self.edit_id_btn.cget("text") == "Terminer (Done) ✅":
            return

        name = self.farmer_entry.get().strip()
        addr = self.remis_entry.get().strip()
        nif = self.nif_entry.get().strip()
        piece = self.piece_entry.get().strip()
        wilaya = self.wilaya_var.get().strip()
        
        if name and addr and wilaya and (len(nif) == 0 or len(nif) == 20) and len(piece) == 9:
            self.edit_id_btn.configure(state="normal")
        else:
            self.edit_id_btn.configure(state="disabled")


    def unlock_identity(self):
        """Unlocks all identity fields for quick correction of typos and changes button to 'Done'."""
        self.last_focused_before_edit = self.focus_get()
        self.farmer_entry.configure(state="normal")
        self.remis_entry.configure(state="normal")
        self.wilaya_menu.configure(state="normal")
        self.nif_entry.configure(state="normal")
        self.piece_entry.configure(state="normal")
        
        # Change button to "Done" state
        self.edit_id_btn.configure(text="Terminer (Done) ✅", fg_color="#2E7D32", command=self.lock_identity)
        self.farmer_entry.focus()

    def lock_identity(self):
        """Re-locks identity fields and restores the 'Edit' button."""
        self.farmer_entry.configure(state="disabled")
        self.remis_entry.configure(state="disabled")
        self.wilaya_menu.configure(state="disabled")
        self.nif_entry.configure(state="disabled")
        self.piece_entry.configure(state="disabled")
        
        # Change button back to "Modify" state
        self.edit_id_btn.configure(text="Modifier l'identité ✏️", fg_color="#37474F", command=self.unlock_identity)
        
        # Restore focus to where it was
        if hasattr(self, 'last_focused_before_edit') and self.last_focused_before_edit:
            self.last_focused_before_edit.focus()
        else:
            self.quantite_entry.focus()


    def _on_tax_enter(self, index):
        """Moves focus to the next tax field when Enter is pressed."""
        if index < len(self.tax_inputs) - 1:
            self.tax_inputs[index + 1]["amount"].focus()
        else:
            self.calc_btn.focus()
            messagebox.showinfo("Navigation", "Saisie des taxes terminée. Vous pouvez cliquer sur 'Final Calculate & Generate' !")

    def show_history(self):
        HistoryWindow(self)

    def save_count(self, n):
        try:
            with open("counter.txt", "w") as f:
                f.write(str(n))
        except:
            pass

    def confirm_taxes(self):
        """Validates all inputs and enables the Final Calculate/Generate buttons."""
        if self.calculate():
            # Disable tax modification
            # Lock EVERYTHING
            self.quantite_entry.configure(state="disabled")
            self.bon_entry.configure(state="disabled")
            self.refac_entry.configure(state="disabled")
            self.nature_menu.configure(state="disabled")
            self.add_prod_btn.configure(state="disabled")
            self.clear_prod_btn.configure(state="disabled")
            
            # Lock taxes
            for tax in self.tax_inputs:
                tax["nbre"].configure(state="disabled")
                tax["pu"].configure(state="disabled")
                tax["amount"].configure(state="disabled")
            
            # Lock identity
            self.farmer_entry.configure(state="disabled")
            self.remis_entry.configure(state="disabled")
            self.wilaya_menu.configure(state="disabled")
            self.nif_entry.configure(state="disabled")
            self.piece_entry.configure(state="disabled")
            
            self.tax_done_btn.configure(state="disabled", text="Confirmed & Locked")

            messagebox.showinfo("Confirmed", "Les taxes et l'identité ont été verrouillées. Le PDF va être généré.", parent=self)
            self.generate()
        else:
            # calculate() already handles visual warning in res_lbl
            self.calc_btn.configure(state="disabled")

    def _validate_farmer(self, value):
        """Allow only letters and spaces."""
        if value == '':
            return True
        # Check if all chars are alpha or space
        return all(c.isalpha() or c.isspace() for c in value)

    def _validate_piece(self, value):
        """Allow only digits, max 9 characters."""
        return (value == '' or value.isdigit()) and len(value) <= 9

    def _validate_nif(self, value):
        """Allow only digits, max 20 characters."""
        return (value == '' or value.isdigit()) and len(value) <= 20

    def _on_nif_key(self, event=None):
        """Live feedback on NIF length."""
        val = self.nif_entry.get().strip()
        if len(val) == 20 or len(val) == 0:
            self.nif_entry.configure(border_color=["#979797", "#3d3d3d"]) # default
        else:
            self.nif_entry.configure(border_color="red")

    def _on_piece_key(self, event=None):
        """Live feedback on ID length."""
        val = self.piece_entry.get().strip()
        if len(val) == 9:
            self.piece_entry.configure(border_color=["#979797", "#3d3d3d"]) # default
        else:
            self.piece_entry.configure(border_color="red")

    def safe_float(self, val):
        try:
            val = val.replace(',', '.')
            if not val.strip(): return 0.0
            return float(val)
        except:
            return 0.0

    def _on_nature_choice(self, choice):
        """When product is selected, move focus to Quantity."""
        if choice and choice.strip():
            self.quantite_entry.focus()

    def _on_nature_enter(self, event=None):
        """Handler for Enter key on the product dropdown."""
        choice = self.nature_var.get()
        if choice and choice.strip():
            self.quantite_entry.focus()
        else:
            messagebox.showwarning("Précision", "Veuillez sélectionner une nature de produit dans la liste.", parent=self)
            self.nature_menu.focus()
            try:
                self.nature_menu._open_dropdown_menu()
            except:
                pass

    # --- GUIDED WORKFLOW HANDLERS ---
    def _on_farmer_enter(self, event=None):
        if self.farmer_entry.get().strip():
            self.remis_entry.configure(state="normal")
            self.remis_entry.focus()
        else:
            messagebox.showwarning("Précision", "Veuillez saisir le nom de l'agriculteur.", parent=self)
            self.farmer_entry.focus()

    def _on_address_enter(self, event=None):
        if self.remis_entry.get().strip():
            self.wilaya_menu.configure(state="normal")
            self.wilaya_menu.focus()
            try:
                self.wilaya_menu._open_dropdown_menu()
            except:
                pass
        else:
            messagebox.showwarning("Précision", "Veuillez saisir l'adresse.", parent=self)
            self.remis_entry.focus()

    def _on_wilaya_choice(self, choice):
        """When wilaya is selected, move focus to NIF."""
        if choice.strip():
            self.nif_entry.configure(state="normal")
            self.nif_entry.focus()


    def _on_nif_enter(self, event=None):
        val = self.nif_entry.get().strip()
        if len(val) == 20 or len(val) == 0:
            self.piece_entry.configure(state="normal")
            self.piece_entry.focus()
        else:
            messagebox.showwarning("Validation", "Le NIF doit contenir exactement 20 chiffres ou rester vide.", parent=self)
            self.nif_entry.focus()

    def _on_piece_enter(self, event=None):
        val = self.piece_entry.get().strip()
        if len(val) == 9:
            # Unlock the entire Product Details section
            self.nature_menu.configure(state="normal")
            self.quantite_entry.configure(state="normal")
            self.bon_entry.configure(state="normal")
            self.refac_entry.configure(state="normal")
            self.add_prod_btn.configure(state="normal")
            self.clear_prod_btn.configure(state="normal")
            
            # ASK: Multiple products?
            ans = messagebox.askyesno("Multi-Produits", "L'agriculteur a-t-il plus d'un produit ?", parent=self)
            if ans:
                self.multi_prod_var.set(True)
            else:
                self.multi_prod_var.set(False)

            # Move to nature de produit and drop the list
            self.nature_menu.focus()
            try:
                self.nature_menu._open_dropdown_menu()
            except:
                pass
        else:
            messagebox.showwarning("Validation", "La pièce d'identité doit contenir exactement 9 chiffres.", parent=self)
            self.piece_entry.focus()

    def _on_qty_enter(self, event=None, jump_to_taxes=False):
        if jump_to_taxes:
            self._on_refac_enter(jump_to_taxes=True)
            return
        if self.safe_float(self.quantite_entry.get()) > 0:
            self.bon_entry.focus()
        else:
            messagebox.showwarning("Validation", "La quantité doit être supérieure à 0.")

    def _on_bon_enter(self, event=None, jump_to_taxes=False):
        if jump_to_taxes:
            self._on_refac_enter(jump_to_taxes=True)
            return
        self.refac_entry.focus()

    def _on_refac_enter(self, event=None, jump_to_taxes=False):
        bon_val = self.bon_entry.get().strip()
        refac_val = self.refac_entry.get().strip()
        if not bon_val and not refac_val:
            messagebox.showwarning("Précision", "Veuillez saisir soit une bonification, soit une réfaction.")
            self.bon_entry.focus()
        else:
            self.add_product(jump_to_taxes=jump_to_taxes)

    def add_product(self, jump_to_taxes=False):
        if len(self.added_products) >= 5:
            messagebox.showwarning("Limite atteinte", "Vous ne pouvez pas ajouter plus de 5 produits.", parent=self)
            return
        # 1. Identity Validation
        farmer = self.farmer_entry.get().strip()
        adresse = self.remis_entry.get().strip()
        nif = self.nif_entry.get().strip()
        piece = self.piece_entry.get().strip()
        
        if not farmer:
            messagebox.showwarning("Validation", "Veuillez saisir le nom de l'agriculteur.", parent=self)
            self.farmer_entry.focus()
            return
        if not adresse:
            messagebox.showwarning("Validation", "Veuillez saisir l'adresse.", parent=self)
            self.remis_entry.focus()
            return
        if nif and len(nif) != 20:
            messagebox.showwarning("Validation", "Le NIF doit contenir exactement 20 chiffres (ou rester vide).", parent=self)
            self.nif_entry.focus()
            return
        if len(piece) != 9:
            messagebox.showwarning("Validation", "La pièce d'identité doit contenir exactement 9 chiffres.", parent=self)
            self.piece_entry.focus()
            return

        nature = self.nature_var.get()
        if not nature or nature.strip() == "":
            messagebox.showwarning("Validation", "Veuillez sélectionner la nature du produit.", parent=self)
            return

        prix_u = self.products.get(nature, 0)
        qte = self.safe_float(self.quantite_entry.get())
        if qte <= 0:
            messagebox.showwarning("Validation", "La quantité doit être supérieure à 0.")
            return
            
        bon = self.safe_float(self.bon_entry.get())
        refac = self.safe_float(self.refac_entry.get())
        
        if bon <= 0 and refac <= 0:
            messagebox.showwarning("Validation", "Chaque produit doit avoir soit une bonification, soit une réfaction.")
            return
        
        montant_avant = qte * prix_u
        montant_brut = montant_avant + (qte * bon) - (qte * refac)
        
        self.added_products.append({
            "nature": nature,
            "quantite": qte,
            "prix_u": prix_u,
            "montant_avant_tax": montant_avant,
            "bon": bon,
            "refac": refac,
            "montant_brut": montant_brut
        })
        
        row = ctk.CTkFrame(self.prod_listbox, fg_color="gray25", corner_radius=6)
        row.pack(fill="x", padx=2, pady=2)
        
        prod_info = f"📦 {nature} | Qte: {qte} | {montant_brut:,.2f} DA"
        lbl = ctk.CTkLabel(row, text=prod_info, anchor="w", font=ctk.CTkFont(size=11))
        lbl.pack(fill="x", padx=10, pady=3)
        
        self.quantite_entry.delete(0, 'end')
        self.bon_entry.configure(state="normal")
        self.bon_entry.delete(0, 'end')
        self.refac_entry.configure(state="normal")
        self.refac_entry.delete(0, 'end')
        
        # Lock Identity Fields after first product is added
        self.farmer_entry.configure(state="disabled")
        self.remis_entry.configure(state="disabled")
        self.nif_entry.configure(state="disabled")
        self.piece_entry.configure(state="disabled")
        
        self.prod_count_lbl.configure(text=f"Produits: {len(self.added_products)} / 5")
        self.to_taxes_btn.configure(state="normal")
        
        if len(self.added_products) >= 5:
            self.add_prod_btn.configure(state="disabled")
        
        self.calculate()
        
        can_continue_products = self.multi_prod_var.get() and len(self.added_products) < 5
        
        if jump_to_taxes or not can_continue_products:
            self._go_to_taxes()
        else:
            self.nature_menu.focus()
            try:
                self.nature_menu._open_dropdown_menu()
            except:
                pass

    def _go_to_taxes(self):
        self.add_prod_btn.configure(state="disabled")
        for tax in self.tax_inputs:
            if tax["name"] == "redevance CH AGP":
                tax["amount"].focus()
                break
        
    def clear_products(self, focus_nature=True):
        self.added_products = []
        for widget in self.prod_listbox.winfo_children():
            widget.destroy()
        
        self.prod_count_lbl.configure(text="Produits: 0 / 5")
        self.add_prod_btn.configure(state="normal")
        self.to_taxes_btn.configure(state="disabled")
        
        # Clear current inputs to prevent calculate() from picking up partial values
        self.quantite_entry.delete(0, 'end')
        self.bon_entry.configure(state="normal")
        self.bon_entry.delete(0, 'end')
        self.refac_entry.configure(state="normal")
        self.refac_entry.delete(0, 'end')
        self.nature_var.set(" ")
        
        # Focus back to nature_menu and open dropdown if requested
        if focus_nature:
            self.nature_menu.focus()
            try:
                self.nature_menu._open_dropdown_menu()
            except:
                pass

        
        # Reset Taxes
        for tax in self.tax_inputs:
            tax["nbre"].configure(state="normal")
            tax["nbre"].delete(0, 'end')
            if tax["name"] == "taxe pour compte CNA":
                tax["pu"].configure(state="normal")
                tax["pu"].delete(0, 'end')
                tax["pu"].insert(0, "15")
                tax["pu"].configure(state="disabled")
            elif tax["name"] == "taxe pour chambre agricole":
                tax["pu"].configure(state="normal")
                tax["pu"].delete(0, 'end')
                tax["pu"].configure(state="disabled")
            else:
                tax["pu"].delete(0, 'end')
            
            tax["amount"].configure(state="normal")
            tax["amount"].delete(0, 'end')
            
            # Re-read initial states
            if tax["name"] in ["taxe pour compte CNA", "taxe pour chambre agricole"]:
                tax["nbre"].configure(state="disabled")
                tax["amount"].configure(state="disabled")
        
        self.calculate()

    def clear_all(self):
        """Resets the entire application to the startup state."""
        # 1. Clear products
        self.added_products = []
        for widget in self.prod_listbox.winfo_children():
            widget.destroy()
        
        # 2. Reset Identity
        for entry in [self.farmer_entry, self.remis_entry, self.nif_entry, self.piece_entry]:
            entry.configure(state="normal")
            entry.delete(0, 'end')
        
        # Reset restricted states
        self.remis_entry.configure(state="disabled")
        self.wilaya_menu.configure(state="disabled")
        self.wilaya_var.set("Ouargla")
        self.nif_entry.configure(state="disabled")
        self.piece_entry.configure(state="disabled")

        
        # 3. Reset Product inputs
        for entry in [self.quantite_entry, self.bon_entry, self.refac_entry]:
            entry.configure(state="normal")
            entry.delete(0, 'end')
            entry.configure(state="disabled")
        self.nature_var.set(" ")
        self.nature_menu.configure(state="normal")
        
        # 4. Reset Taxes using existing clear_products logic
        self.multi_prod_var.set(False)
        self.clear_products(focus_nature=False) # This handles tax reset without opening menu
        
        # 5. Reset buttons
        self.add_prod_btn.configure(state="disabled")
        self.clear_prod_btn.configure(state="disabled")
        self.tax_done_btn.configure(state="normal", text="Confirm Taxes (Done)")
        # self.gen_btn.configure(state="disabled") (Removed redundant button)
        pass
        
        # 6. Reset visual feedback
        self.res_lbl.configure(text="Totals will be calculated automatically.")
        self.farmer_entry.configure(border_color=["#979797", "#3d3d3d"])
        self.remis_entry.configure(border_color=["#979797", "#3d3d3d"])
        self.nif_entry.configure(border_color=["#979797", "#3d3d3d"])
        self.piece_entry.configure(border_color=["#979797", "#3d3d3d"])
        
        self.farmer_entry.focus()

    def calculate(self):
        # 1. Identity Validation
        farmer = self.farmer_entry.get().strip()
        adresse = self.remis_entry.get().strip()
        nif = self.nif_entry.get().strip()
        piece = self.piece_entry.get().strip()
        
        is_valid = True
        
        # Highlight Farmer
        if not farmer:
            self.farmer_entry.configure(border_color="red")
            is_valid = False
        else:
            self.farmer_entry.configure(border_color=["#979797", "#3d3d3d"]) # default
            
        # Highlight Address
        if not adresse:
            self.remis_entry.configure(border_color="red")
            is_valid = False
        else:
            self.remis_entry.configure(border_color=["#979797", "#3d3d3d"]) # default
        
        # Highlight NIF
        if nif and len(nif) != 20:
            self.nif_entry.configure(border_color="red")
            is_valid = False
        else:
            self.nif_entry.configure(border_color=["#979797", "#3d3d3d"]) # default
            
        # Highlight ID
        if len(piece) != 9:
            self.piece_entry.configure(border_color="red")
            is_valid = False
        else:
            self.piece_entry.configure(border_color=["#979797", "#3d3d3d"]) # default
            
        if not is_valid:
            self.res_lbl.configure(text="Veuillez remplir les informations d'identité (Champs en ROUGE)")
            return False

        products = list(self.added_products)
        
        # Also include currently typed product if valid
        nature = self.nature_var.get()
        prix_u = self.products.get(nature, 0)
        qte = self.safe_float(self.quantite_entry.get())
        if qte > 0:
            bon = self.safe_float(self.bon_entry.get())
            refac = self.safe_float(self.refac_entry.get())
            montant_avant = qte * prix_u
            current_brut = montant_avant + (qte * bon) - (qte * refac)
            
            products.append({
                "nature": nature,
                "quantite": qte,
                "prix_u": prix_u,
                "montant_avant_tax": montant_avant,
                "bon": bon,
                "refac": refac,
                "montant_brut": current_brut
            })

        montant_brut = sum(p["montant_brut"] for p in products)
        total_weight = sum(p["quantite"] for p in products)
        
        # 2. Retenues calcs
        total_retenues = 0.0
        retenues_data = []
        
        for tax in self.tax_inputs:
            name = tax["name"]
            
            nbre_str = tax["nbre"].get()
            pu_str = tax["pu"].get()
            amount_str = tax["amount"].get()
            
            nbre = self.safe_float(nbre_str) if nbre_str else None
            pu = self.safe_float(pu_str) if pu_str else None
            amount = self.safe_float(amount_str)
            
            if name == "taxe pour compte CNA":
                # CNA is always 15 * total weight
                tax["nbre"].configure(state="normal")
                tax["nbre"].delete(0, ctk.END)
                tax["nbre"].insert(0, f"{total_weight:.2f}")
                tax["nbre"].configure(state="disabled")
                
                tax["pu"].configure(state="normal")
                tax["pu"].delete(0, ctk.END)
                tax["pu"].insert(0, "15")
                tax["pu"].configure(state="disabled")
                
                amount = total_weight * 15
                tax["amount"].configure(state="normal")
                tax["amount"].delete(0, ctk.END)
                tax["amount"].insert(0, f"{amount:.2f}")
                tax["amount"].configure(state="disabled")
                
                # Update nbre/pu for data recording
                nbre, pu = total_weight, 15.0
                
            elif name == "taxe pour chambre agricole":
                # Mixed rates: 5 for Orge, 3 for others
                has_orge = any("ORGE" in p["nature"].upper() for p in products)
                has_others = any("ORGE" not in p["nature"].upper() for p in products)
                
                # Weight update
                tax["nbre"].configure(state="normal")
                tax["nbre"].delete(0, ctk.END)
                tax["nbre"].insert(0, f"{total_weight:.2f}")
                tax["nbre"].configure(state="disabled")
                
                # P.U Display logic
                pu_display = "3/5" if (has_orge and has_others) else ("5" if has_orge else "3")
                tax["pu"].configure(state="normal")
                tax["pu"].delete(0, ctk.END)
                tax["pu"].insert(0, pu_display)
                tax["pu"].configure(state="disabled")
                
                # Amount calculation (Weighted Sum)
                amount = sum(p["quantite"] * (5 if "ORGE" in p["nature"].upper() else 3) for p in products)
                tax["amount"].configure(state="normal")
                tax["amount"].delete(0, ctk.END)
                tax["amount"].insert(0, f"{amount:.2f}")
                tax["amount"].configure(state="disabled")
                
                # Update nbre/pu for data recording
                nbre = total_weight
                pu = "3/5" if (has_orge and has_others) else (5.0 if has_orge else 3.0)
                
            elif not amount_str and nbre and pu:
                amount = nbre * pu
                tax["amount"].delete(0, ctk.END)
                tax["amount"].insert(0, str(amount))
                
            total_retenues += amount
            retenues_data.append({
                "name": name,
                "nbre": nbre,
                "pu": pu,
                "amount": amount
            })
                
        montant_net = montant_brut - total_retenues
        
        self.res_lbl.configure(text=f"Montant Brut: {montant_brut:.2f} | Total Retenues: {total_retenues:.2f} | Net: {montant_net:.2f}")
        
        self._compiled_data = {
            "products": products,
            "identity": {
                "adresse": self.remis_entry.get(),
                "wilaya": self.wilaya_var.get(),
                "nif": self.nif_entry.get(),
                "piece_identite": self.piece_entry.get(),
                "date": self.date_entry.get(),
                "decompte": self.decompte_entry.get(),
                "farmer": self.farmer_entry.get()
            },
            "retenues": retenues_data,
            "totals": {
                "total_retenues": total_retenues,
                "montant_net": montant_net
            }
        }
        return True
        
    def generate(self):
        if not self.calculate():
            return

        # 2. Product List Validation
        if not self.added_products:
            messagebox.showwarning("Validation", "La liste des produits est vide. Veuillez ajouter au moins un produit avant de générer la facture.", parent=self)
            return

        # 3. Financial Integrity Validation
        net = self._compiled_data["totals"]["montant_net"]
        if net <= 0:
            messagebox.showwarning("Validation", f"Le montant net ({net:.2f}) est invalide. Veuillez vérifier vos calculs.", parent=self)
            return

        # 4. Show "Perfect" Preview Window by generating it as a temp file first
        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_preview.pdf")
        try:
            generate_facture_pdf(self._compiled_data, temp_path)
            self._temp_pdf_path = temp_path
            InvoicePreviewWindow(self, temp_path, self.finalize_generation)
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate preview: {e}")

    def finalize_generation(self):
        if not self._compiled_data or not hasattr(self, '_temp_pdf_path'):
            return
            
        farmer_name = self._compiled_data['identity']['farmer']
        # Clean farmer name for filename
        farmer_clean = "".join(x for x in farmer_name if x.isalnum() or x in " -_").strip()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"facture_{farmer_clean}_{timestamp}.pdf"
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        
        try:
            # Re-save/Move from temp to final destination
            if os.path.exists(self._temp_pdf_path):
                import shutil
                shutil.move(self._temp_pdf_path, output_path)
            
            # 2. Save everything to the SQLite Database (The Silent Backup)
            database.save_invoice(self._compiled_data, output_path)
            
            messagebox.showinfo("Success", f"Facture generated successfully!\nSaved to: {output_path}", parent=self)
            
            # Increment counter
            self.current_count += 1
            self.save_count(self.current_count)
            self.decompte_entry.configure(state="normal")
            self.decompte_entry.delete(0, 'end')
            year = datetime.datetime.now().year
            self.decompte_entry.insert(0, f"{self.current_count}/{year}")
            self.decompte_entry.configure(state="disabled")
            
            # Optionally auto-open the PDF
            os.startfile(output_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate PDF.\n{e}", parent=self)

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("CCLS - Authentification")
        self.geometry("500x700")
        self.resizable(False, False)
        
        # Center the window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (500 // 2)
        y = (screen_height // 2) - (700 // 2)
        self.geometry(f"500x700+{x}+{y}")
        
        # Background protection (screenshots)
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass
            
        # Main Frame with slight shadow effect (simulated with border)
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, border_width=2, border_color="#1f538d")
        self.main_frame.pack(pady=40, padx=40, fill="both", expand=True)
        
        # Logo handling
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 140))
                self.logo_label = ctk.CTkLabel(self.main_frame, image=self.logo_img, text="")
                self.logo_label.pack(pady=(30, 10))
        except:
            pass
            
        self.title_label = ctk.CTkLabel(self.main_frame, text="Système de Facturation", 
                                        font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.pack(pady=(10, 30))
        
        # Input Container
        input_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        input_container.pack(pady=10, padx=30, fill="x")
        
        ctk.CTkLabel(input_container, text="Nom d'utilisateur", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10)
        self.username_entry = ctk.CTkEntry(input_container, placeholder_text="admin", 
                                           width=280, height=45, font=ctk.CTkFont(size=14))
        self.username_entry.pack(pady=(5, 15))
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        
        ctk.CTkLabel(input_container, text="Mot de passe", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10)
        self.password_entry = ctk.CTkEntry(input_container, placeholder_text="••••••••", 
                                           show="*", width=280, height=45, font=ctk.CTkFont(size=14))
        self.password_entry.pack(pady=(5, 15))
        self.password_entry.bind("<Return>", lambda e: self.login())
        
        # Login Button
        self.login_btn = ctk.CTkButton(self.main_frame, text="SE CONNECTER", command=self.login, 
                                        width=350, height=55, font=ctk.CTkFont(size=20, weight="bold"),
                                        fg_color="#1f538d", hover_color="#163e66", corner_radius=12)
        self.login_btn.pack(pady=(30, 20), padx=20, fill="x")
        
        # Footer
        self.footer = ctk.CTkLabel(self.main_frame, text="© 2026 CCLS Ouargla - Sécurisé", 
                                   font=ctk.CTkFont(size=10, slant="italic"), text_color="gray")
        self.footer.pack(side="bottom", pady=10)

        # Initial Focus
        self.after(200, lambda: self.username_entry.focus())

    def login(self):
        # 0. Check if App is already running
        if hasattr(self, 'app') and self.app and self.app.winfo_exists():
            self.app.lift()
            self.withdraw()
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Attention", "Veuillez remplir tous les champs.")
            return
            
        success, role = database.verify_login(username, password)
        if success:
            self.withdraw()
            self.app = App(self, username=username, role=role, on_disconnect=lambda: self._return_to_login())
            self.app.protocol("WM_DELETE_WINDOW", lambda: self.on_app_close())
        else:
            messagebox.showerror("Erreur", "Nom d'utilisateur ou mot de passe incorrect.")
            self.password_entry.delete(0, 'end')
    
    def _return_to_login(self):
        """Closes the main app and returns to the login screen."""
        if hasattr(self, 'app') and self.app:
            self.app.destroy()
            self.app = None
        self.password_entry.delete(0, 'end')
        self.deiconify()
            
    def on_app_close(self):
        if hasattr(self, 'app') and self.app:
            self.app.destroy()
        self.destroy()

if __name__ == "__main__":
    database.init_db()
    login_app = LoginWindow()
    login_app.mainloop()