import customtkinter as ctk
import tkinter as tk
import os
import datetime
import ctypes
from tkinter import messagebox
from PIL import Image
import database
from pdf_generator import generate_facture_pdf
from ui.windows.admin_panel import AdminPanelWindow
from ui.windows.preview_window import InvoicePreviewWindow
from ui.windows.dialogs import ReceiptsDialog, PasswordDialog
from config import TAXES_LIST

class AppFrame(ctk.CTkFrame):
    def __init__(self, master, username="admin", role="user", on_disconnect=None, on_show_history=None):
        super().__init__(master)
        
        self.username = username
        self.role = role
        self.on_disconnect = on_disconnect
        self.on_show_history = on_show_history
        self.last_focused_input = None
        self.current_receipts = [] # Track receipts for current product being entered
        
        # Load products and setup UI
        self.reload_products()
        self._setup_ui()
        
        
    def reload_products(self):
        """Fetches products from the database and updates max limit automatically."""
        self.products = database.get_db_products()
        self.current_product_list = list(self.products.keys())
        
        self.max_products = len(self.current_product_list)
        if self.max_products == 0: self.max_products = 5 # Safety fallback
        
        if hasattr(self, 'nature_menu'):
            self.nature_menu.configure(values=self.current_product_list)
        
        if hasattr(self, 'prod_count_lbl'):
            self.prod_count_lbl.configure(text=f"Produits: {len(self.added_products)} / {self.max_products}")

    def open_history(self):
        if self.on_show_history:
            self.on_show_history(self.username, self.role)
        elif hasattr(self.master, 'show_history'):
            self.master.show_history(self.username, self.role)

    def open_admin_panel(self):
        AdminPanelWindow(self)
    
    def _setup_ui(self):
        # Configure Frame grid
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # top bar
        self.grid_rowconfigure(1, weight=1)  # main content
        
        # --- TOP BAR ---
        top_bar = ctk.CTkFrame(self, fg_color="#f8f9fa", height=60, corner_radius=0, border_width=1, border_color="#e0e0e0")
        top_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        top_bar.grid_columnconfigure(1, weight=1)
        
        info_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=15, pady=2, sticky="w")

        role_display = "Administrateur" if self.role == "admin" else "Utilisateur"
        account_info = ctk.CTkLabel(info_frame, 
                                    text=f"👤  {self.username.upper()}  |  {role_display}",
                                    font=ctk.CTkFont(family="Poppins", size=16, weight="bold"),
                                    text_color="#1f538d")
        account_info.pack(side="left")
        
        if self.role == "admin":
            self.admin_btn = ctk.CTkButton(info_frame, text="⚙️ Admin Panel", width=140, height=35,
                                            fg_color="#1565C0", font=ctk.CTkFont(family="Poppins", size=13),
                                            command=self.open_admin_panel)
            self.admin_btn.pack(side="left", padx=(20, 5))
            
        self.hist_btn = ctk.CTkButton(info_frame, text="📜 Historique", width=140, height=35,
                                       fg_color="#455A64", font=ctk.CTkFont(family="Poppins", size=13),
                                       command=self.open_history)
        self.hist_btn.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(info_frame, text="🧹 Effacer Tout", width=140, height=35,
                                        fg_color="#C62828", font=ctk.CTkFont(family="Poppins", size=13),
                                        command=self.clear_all)
        self.clear_btn.pack(side="left", padx=5)
        
        disconnect_btn = ctk.CTkButton(top_bar, text="🔒 Déconnexion", width=160, height=35,
                                        fg_color="#C62828", hover_color="#8E0000",
                                        font=ctk.CTkFont(family="Poppins", size=14, weight="bold"),
                                        command=self._disconnect)
        disconnect_btn.grid(row=0, column=2, padx=15, pady=5, sticky="e")
        
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)

        row_idx = 0
        tk.Label(self.scrollable_frame, text="Generate Invoice", 
                 font=("Poppins", 28, "bold"), bg="#ebebeb", fg="black").grid(row=row_idx, column=0, columnspan=2, pady=(20, 30))
        row_idx += 1
        
        # --- IDENTITY DETAILS ---
        # Switch to native tk.Frame for the massive container to eliminate scrolling lag
        id_frame = tk.Frame(self.scrollable_frame, bg="#dbdbdb", highlightthickness=1, highlightbackground="#cccccc")
        id_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        id_frame.grid_columnconfigure(1, weight=1)
        id_frame.grid_columnconfigure(3, weight=1)
        row_idx += 1
        
        tk.Label(id_frame, text="Identity Details", font=("Poppins", 15, "bold"), bg="#dbdbdb", fg="black").grid(row=0, column=0, columnspan=4, pady=15)
        
        tk.Label(id_frame, text="Nom de l'agriculteur", font=("Poppins", 11), bg="#dbdbdb", fg="black").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.farmer_entry = ctk.CTkEntry(id_frame, font=ctk.CTkFont(family="Poppins", size=16), height=40)
        self.farmer_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        vcmd_farmer = (self.register(self._validate_farmer), '%P')
        self.farmer_entry.configure(validate='key', validatecommand=vcmd_farmer)
        self.farmer_entry.bind("<Return>", self._on_farmer_enter)

        ctk.CTkLabel(id_frame, text="L'adresse", font=ctk.CTkFont(family="Poppins", size=15)).grid(row=1, column=2, padx=10, pady=10, sticky="e")
        self.remis_entry = ctk.CTkEntry(id_frame, state="disabled", font=ctk.CTkFont(family="Poppins", size=16), height=40)
        self.remis_entry.grid(row=1, column=3, padx=10, pady=10, sticky="ew")
        self.remis_entry.bind("<Return>", self._on_address_enter)
        
        ctk.CTkLabel(id_frame, text="Wilaya", font=ctk.CTkFont(family="Poppins", size=15)).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.wilaya_var = ctk.StringVar(value=" ")
        self.wilaya_menu = ctk.CTkOptionMenu(id_frame, values=["Ouargla", "Tougourt", "Ilizi"], 
                                             variable=self.wilaya_var, command=self._on_wilaya_choice, state="disabled",
                                             font=ctk.CTkFont(family="Poppins", size=15), height=35)
        self.wilaya_menu.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(id_frame, text="NIF (Facultatif)", font=ctk.CTkFont(family="Poppins", size=15)).grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.nif_entry = ctk.CTkEntry(id_frame, state="disabled", font=ctk.CTkFont(family="Poppins", size=16), height=40)
        self.nif_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        vcmd_nif = (self.register(self._validate_nif), '%P')
        self.nif_entry.configure(validate='key', validatecommand=vcmd_nif)
        self.nif_entry.bind("<KeyRelease>", self._on_nif_key)
        self.nif_entry.bind("<Return>", self._on_nif_enter)

        ctk.CTkLabel(id_frame, text="Pièce d'identité (9 chiffres)", font=ctk.CTkFont(family="Poppins", size=15)).grid(row=3, column=2, padx=10, pady=10, sticky="e")
        self.piece_entry = ctk.CTkEntry(id_frame, state="disabled", font=ctk.CTkFont(family="Poppins", size=16), height=40)
        self.piece_entry.grid(row=3, column=3, padx=10, pady=10, sticky="ew")
        vcmd = (self.register(self._validate_piece), '%P')
        self.piece_entry.configure(validate='key', validatecommand=vcmd)
        self.piece_entry.bind("<KeyRelease>", self._on_piece_key)
        self.piece_entry.bind("<Return>", self._on_piece_enter)
        
        ctk.CTkLabel(id_frame, text="Vérifier le (Date)", font=ctk.CTkFont(family="Poppins", size=15)).grid(row=4, column=0, padx=10, pady=10, sticky="e")
        self.date_var = ctk.StringVar(value=datetime.datetime.now().strftime("%d/%m/%Y"))
        self.date_var.trace_add("write", self._auto_format_invoice_date)
        self.date_entry = ctk.CTkEntry(id_frame, font=ctk.CTkFont(family="Poppins", size=15), height=35, textvariable=self.date_var)
        self.date_entry.grid(row=4, column=1, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(id_frame, text="Decompte N°", font=ctk.CTkFont(family="Poppins", size=15)).grid(row=4, column=2, padx=10, pady=10, sticky="e")
        self.decompte_entry = ctk.CTkEntry(id_frame, font=ctk.CTkFont(family="Poppins", size=15), height=35)
        self.current_count = self.load_count()
        year = datetime.datetime.now().year
        self.decompte_entry.insert(0, f"{self.current_count}/{year}")
        self.decompte_entry.grid(row=4, column=3, padx=10, pady=10, sticky="ew")
        self.decompte_entry.configure(state="disabled")

        self.edit_id_btn = ctk.CTkButton(id_frame, text="Modifier l'identité ✏️", 
                                         width=200, height=35, fg_color="#37474F",
                                         state="disabled", font=ctk.CTkFont(family="Poppins", size=13),
                                         command=self.unlock_identity)
        self.edit_id_btn.grid(row=5, column=0, columnspan=4, pady=(10, 15))

        self.farmer_entry.bind("<KeyRelease>", self._check_id_ready, add="+")
        self.remis_entry.bind("<KeyRelease>", self._check_id_ready, add="+")
        self.nif_entry.bind("<KeyRelease>", self._check_id_ready, add="+")
        self.piece_entry.bind("<KeyRelease>", self._check_id_ready, add="+")

        # --- PRODUCT DATA ---
        prod_frame = tk.Frame(self.scrollable_frame, bg="#dbdbdb", highlightthickness=1, highlightbackground="#cccccc")
        prod_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        prod_frame.grid_columnconfigure(1, weight=1)
        prod_frame.grid_columnconfigure(3, weight=1)
        row_idx += 1
        
        tk.Label(prod_frame, text="Détails des Produits", font=("Poppins", 15, "bold"), bg="#dbdbdb", fg="black").grid(row=0, column=0, columnspan=2, pady=15)
        
        self.multi_prod_var = ctk.BooleanVar(value=False)
        self.multi_prod_check = ctk.CTkCheckBox(prod_frame, text="Plusieurs produits ?", variable=self.multi_prod_var, 
                                                font=ctk.CTkFont(family="Poppins", size=15, weight="bold"))
        self.multi_prod_check.grid(row=0, column=2, columnspan=2, padx=20, sticky="e")

        tk.Label(prod_frame, text="Nature de produit", font=("Poppins", 11), bg="#dbdbdb", fg="black").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.nature_var = ctk.StringVar(value=" ")
        self.nature_menu = ctk.CTkOptionMenu(prod_frame, values=self.current_product_list, variable=self.nature_var, 
                                             command=self._on_nature_choice, state="disabled", font=ctk.CTkFont(family="Poppins", size=15), height=35)
        self.nature_menu.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        self.nature_menu.bind("<Return>", self._on_nature_enter)
        
        tk.Label(prod_frame, text="Quantité", font=("Poppins", 11), bg="#dbdbdb", fg="black").grid(row=1, column=2, padx=10, pady=10, sticky="e")
        qty_subframe = tk.Frame(prod_frame, bg="#dbdbdb")
        qty_subframe.grid(row=1, column=3, padx=10, pady=10, sticky="w")
        
        self.quantite_entry = ctk.CTkEntry(qty_subframe, state="readonly", font=ctk.CTkFont(family="Poppins", size=16), height=35, width=100)
        self.quantite_entry.pack(side="left")
        
        self.manage_receipts_btn = ctk.CTkButton(qty_subframe, text="📦 Bons", width=60, height=35, state="disabled", 
                                                 command=self.open_receipts_dialog, fg_color="#FBC02D", text_color="black")
        self.manage_receipts_btn.pack(side="left", padx=5)
        
        tk.Label(prod_frame, text="Bonification", font=("Poppins", 11), bg="#dbdbdb", fg="black").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.bon_entry = ctk.CTkEntry(prod_frame, state="disabled", font=ctk.CTkFont(family="Poppins", size=16), height=35)
        self.bon_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        self.bon_entry.bind("<Return>", self._on_bon_enter)
        self.bon_entry.bind("<Control-Return>", lambda e: self._on_bon_enter(e, jump_to_taxes=True))
        
        tk.Label(prod_frame, text="Réfaction", font=("Poppins", 11), bg="#dbdbdb", fg="black").grid(row=2, column=2, padx=10, pady=10, sticky="e")
        self.refac_entry = ctk.CTkEntry(prod_frame, state="disabled", font=ctk.CTkFont(family="Poppins", size=16), height=35)
        self.refac_entry.grid(row=2, column=3, padx=10, pady=10, sticky="w")
        self.refac_entry.bind("<Return>", self._on_refac_enter)
        self.refac_entry.bind("<Control-Return>", lambda e: self._on_refac_enter(e, jump_to_taxes=True))
        
        # Track last focused field for UX after identity edit
        for e in [self.quantite_entry, self.bon_entry, self.refac_entry]:
            e.bind("<FocusIn>", lambda event, entry=e: self._set_last_focused(entry))
        
        self.added_products = []
        # Buttons removed: Finalization is now automated by keyboard (Enter on Réfaction)
        
        self.prod_count_lbl = ctk.CTkLabel(prod_frame, text=f"Produits: 0 / {self.max_products}", 
                                           font=ctk.CTkFont(family="Poppins", size=15, weight="bold"))
        self.prod_count_lbl.grid(row=3, column=2, padx=10)
        
        self.to_taxes_btn = ctk.CTkButton(prod_frame, text="Terminer et passer aux taxes ➔", command=self._go_to_taxes, 
                                          state="disabled", fg_color="#E65100", font=ctk.CTkFont(family="Poppins", size=14, weight="bold"), height=40)
        self.to_taxes_btn.grid(row=3, column=3, pady=15, padx=10)
        
        self.prod_listbox = ctk.CTkScrollableFrame(prod_frame, height=120, label_text="Produits ajoutés", 
                                                    label_font=ctk.CTkFont(family="Poppins", size=14, weight="bold"))
        self.prod_listbox.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
        
        # --- TAXES ---
        tax_frame = tk.Frame(self.scrollable_frame, bg="#dbdbdb", highlightthickness=1, highlightbackground="#cccccc")
        tax_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        tax_frame.grid_columnconfigure(1, weight=1)
        tax_frame.grid_columnconfigure(2, weight=1)
        tax_frame.grid_columnconfigure(3, weight=1)
        row_idx += 1
        
        tk.Label(tax_frame, text="Retenues Diverses", font=("Poppins", 16, "bold"), bg="#dbdbdb", fg="black").grid(row=0, column=0, columnspan=4, pady=15)
        
        tk.Label(tax_frame, text="Tax Name", font=("Poppins", 11, "bold"), bg="#dbdbdb", fg="black").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Label(tax_frame, text="Quantité", font=("Poppins", 11, "bold"), bg="#dbdbdb", fg="black").grid(row=1, column=1, padx=5, pady=5)
        tk.Label(tax_frame, text="P.U", font=("Poppins", 11, "bold"), bg="#dbdbdb", fg="black").grid(row=1, column=2, padx=5, pady=5)
        tk.Label(tax_frame, text="Amount / Total", font=("Poppins", 11, "bold"), bg="#dbdbdb", fg="black").grid(row=1, column=3, padx=5, pady=5)
        
        self.tax_inputs = []
        for i, tax_name in enumerate(TAXES_LIST):
            r = i + 2
            tk.Label(tax_frame, text=tax_name, font=("Poppins", 10), bg="#dbdbdb", fg="black").grid(row=r, column=0, padx=5, pady=8, sticky="w")
            
            if tax_name in ["taxe pour compte CNA", "taxe pour chambre agricole"]:
                nbre_en = ctk.CTkEntry(tax_frame, width=80)
                nbre_en.grid(row=r, column=1, padx=5, pady=5)
                nbre_en.configure(state="disabled")
                
                pu_en = ctk.CTkEntry(tax_frame, width=80)
                pu_en.grid(row=r, column=2, padx=5, pady=5)
                if tax_name == "taxe pour compte CNA": pu_en.insert(0, "15")
                pu_en.configure(state="disabled")
                
                amount_en = ctk.CTkEntry(tax_frame, width=120, height=35, font=ctk.CTkFont(family="Poppins", size=15))
                amount_en.grid(row=r, column=3, padx=5, pady=5)
                amount_en.configure(state="disabled")
            else:
                nbre_en = ctk.CTkEntry(tax_frame, width=120)
                nbre_en.grid_forget()
                pu_en = ctk.CTkEntry(tax_frame, width=120)
                pu_en.grid_forget()
                amount_en = ctk.CTkEntry(tax_frame, width=120, height=35, font=ctk.CTkFont(family="Poppins", size=15))
                amount_en.grid(row=r, column=3, padx=5, pady=5)
            
            amount_en.bind("<KeyRelease>", lambda e: self.calculate())
            amount_en.bind("<Return>", lambda e, idx=i: self._on_tax_enter(idx))
            amount_en.bind("<FocusIn>", lambda event, entry=amount_en: self._set_last_focused(entry))
            
            self.tax_inputs.append({"name": tax_name, "nbre": nbre_en, "pu": pu_en, "amount": amount_en})

        self.tax_done_btn = ctk.CTkButton(tax_frame, text="Confirm Taxes (Done)", command=self.confirm_taxes, 
                                          fg_color="#3B8ED0", font=ctk.CTkFont(family="Poppins", size=16, weight="bold"), height=45)
        self.tax_done_btn.grid(row=len(TAXES_LIST) + 2, column=3, pady=15, padx=5)
            
        res_frame = tk.Frame(self.scrollable_frame, bg="#dbdbdb", highlightthickness=1, highlightbackground="#cccccc")
        res_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", pady=10)
        self.res_lbl = ctk.CTkLabel(res_frame, text="Totals will be calculated automatically.", font=ctk.CTkFont(family="Poppins", size=24, weight="bold"))
        self.res_lbl.pack(pady=25)
        
        self.after(200, lambda: self.farmer_entry.focus())

    def _disconnect(self):
        if self.on_disconnect: self.on_disconnect()

    def load_count(self):
        try:
            if os.path.exists("counter.txt"):
                with open("counter.txt", "r") as f: return int(f.read().strip())
            return 1
        except: return 1

    def save_count(self, n):
        try:
            with open("counter.txt", "w") as f: f.write(str(n))
        except: pass

    def _check_id_ready(self, event=None):
        if self.edit_id_btn.cget("text") == "Terminer (Done) ✅": return
        name, addr, nif, piece = self.farmer_entry.get().strip(), self.remis_entry.get().strip(), self.nif_entry.get().strip(), self.piece_entry.get().strip()
        if name and addr and (len(nif) == 0 or len(nif) == 20) and len(piece) == 9:
            self.edit_id_btn.configure(state="normal")
        else: self.edit_id_btn.configure(state="disabled")

    def unlock_identity(self):
        self.last_focused_before_edit = self.focus_get()
        for e in [self.farmer_entry, self.remis_entry, self.nif_entry, self.piece_entry]: e.configure(state="normal")
        self.wilaya_menu.configure(state="normal")
        self.edit_id_btn.configure(text="Terminer (Done) ✅", fg_color="#2E7D32", command=self.lock_identity)
        self.farmer_entry.focus()

    def lock_identity(self):
        for e in [self.farmer_entry, self.remis_entry, self.nif_entry, self.piece_entry]: e.configure(state="disabled")
        self.wilaya_menu.configure(state="disabled")
        self.edit_id_btn.configure(text="Modifier l'identité ✏️", fg_color="#37474F", command=self.unlock_identity)
        
        target = self.last_focused_input if self.last_focused_input else self.quantite_entry
        target.focus()
        self._scroll_to_widget(target)

    def _set_last_focused(self, entry):
        self.last_focused_input = entry

    def _scroll_to_widget(self, widget):
        """Intelligently scrolls the scrollable frame to put the target widget in view."""
        try:
            self.update_idletasks()
            # Get position relative to the scrollable container
            y = widget.winfo_y()
            total_h = self.scrollable_frame._parent_canvas.bbox("all")[3]
            if total_h > 0:
                # Calculate fraction (0 to 1) for yview_moveto
                # We subtract a small offset to give some breathing room at the top
                pos = max(0, (y - 50) / total_h)
                self.scrollable_frame._parent_canvas.yview_moveto(pos)
        except: pass # Failsafe if widget not yet rendered or frame structure changed

    def _on_tax_enter(self, index):
        if index < len(self.tax_inputs) - 1: self.tax_inputs[index + 1]["amount"].focus()
        else: messagebox.showinfo("Navigation", "Saisie des taxes terminée.")

    def confirm_taxes(self):
        if self.calculate():
            for e in [self.quantite_entry, self.bon_entry, self.refac_entry]: e.configure(state="disabled")
            self.nature_menu.configure(state="disabled")
            for tax in self.tax_inputs: 
                tax["nbre"].configure(state="disabled"); tax["pu"].configure(state="disabled"); tax["amount"].configure(state="disabled")
            self.tax_done_btn.configure(state="disabled", text="Confirmed & Locked")
            messagebox.showinfo("Confirmed", "Prêt pour la génération du PDF.", parent=self)
            self.generate()

    def _validate_farmer(self, v): return (v == '' or all(c.isalpha() or c.isspace() for c in v))
    def _validate_piece(self, v): return (v == '' or v.isdigit()) and len(v) <= 9
    def _validate_nif(self, v): return (v == '' or v.isdigit()) and len(v) <= 20
    def _on_nif_key(self, e=None): self.nif_entry.configure(border_color="red" if self.nif_entry.get().strip() and len(self.nif_entry.get().strip()) != 20 else ["#979797", "#3d3d3d"])
    def _on_piece_key(self, e=None): self.piece_entry.configure(border_color="red" if len(self.piece_entry.get().strip()) != 9 else ["#979797", "#3d3d3d"])

    def _auto_format_invoice_date(self, *args):
        val = self.date_var.get().replace("/", "")
        if len(val) > 8: val = val[:8]
        formatted = ""
        if len(val) >= 1: formatted += val[:2]
        if len(val) >= 3: formatted += "/" + val[2:4]
        if len(val) >= 5: formatted += "/" + val[4:8]
        if self.date_var.get() != formatted: self.date_var.set(formatted)

    def safe_float(self, v):
        try:
            v = v.replace(',', '.')
            return float(v) if v.strip() else 0.0
        except: return 0.0

    def _on_nature_choice(self, c): 
        if c and c.strip(): self.open_receipts_dialog()
    def _on_nature_enter(self, e=None): 
        c = self.nature_var.get()
        if c and c.strip(): self.open_receipts_dialog()
        else: messagebox.showwarning("Précision", "Veuillez sélectionner un produit."); self.nature_menu.focus()

    def _on_farmer_enter(self, e=None):
        if self.farmer_entry.get().strip(): self.remis_entry.configure(state="normal"); self.remis_entry.focus()
        else: messagebox.showwarning("Précision", "Veuillez saisir le nom."); self.farmer_entry.focus()
    def _on_address_enter(self, e=None):
        if self.remis_entry.get().strip(): 
            self.wilaya_menu.configure(state="normal")
            self.wilaya_menu.focus()
            self.wilaya_menu._clicked() # Auto-dropdown
        else: messagebox.showwarning("Précision", "Veuillez saisir l'adresse."); self.remis_entry.focus()
    def _on_wilaya_choice(self, c): self.nif_entry.configure(state="normal"); self.nif_entry.focus()
    def _on_nif_enter(self, e=None):
        val = self.nif_entry.get().strip()
        if len(val) == 20 or len(val) == 0: self.piece_entry.configure(state="normal"); self.piece_entry.focus()
        else: messagebox.showwarning("Validation", "NIF incorrect (20 chiffres)."); self.nif_entry.focus()
    def _on_piece_enter(self, e=None):
        if len(self.piece_entry.get().strip()) == 9:
            # Removed popup: automatically entering product entry mode
            self.multi_prod_var.set(True)
            for entry in [self.nature_menu, self.manage_receipts_btn, self.bon_entry, self.refac_entry]: entry.configure(state="normal")
            self.quantite_entry.configure(state="readonly")
            self.nature_menu.focus()
            self.nature_menu._clicked() # Auto-dropdown
        else: messagebox.showwarning("Validation", "Pièce identité incorrecte (9 chiffres)."); self.piece_entry.focus()

    def _on_nature_enter(self, e=None):
        """Keyboard Enter on Nature select -> Open Receipts Dialog"""
        if self.nature_var.get().strip():
             self.open_receipts_dialog()

    def _on_qty_enter(self, e=None, jump_to_taxes=False):
        if jump_to_taxes: self._on_refac_enter(jump_to_taxes=True); return
        if self.safe_float(self.quantite_entry.get()) > 0: self.bon_entry.focus()
        else: messagebox.showwarning("Validation", "Quantité > 0 svp.")
    def _on_bon_enter(self, e=None, jump_to_taxes=False):
        if jump_to_taxes: self._on_refac_enter(jump_to_taxes=True); return
        self.refac_entry.focus()
    def _on_refac_enter(self, e=None, jump_to_taxes=False):
        # Auto-add product when hitting Enter on the last entry field (Refac)
        self.add_product(jump_to_taxes=jump_to_taxes)

    def add_product(self, jump_to_taxes=False):
        if len(self.added_products) >= 5: messagebox.showwarning("Limite", "Max 5 produits."); return
        nature = self.nature_var.get()
        if not nature or nature.strip() == "": messagebox.showwarning("Validation", "Select Nature."); return
        prix_u = self.products.get(nature, 0)
        
        # Pull Qty from entry (which is now filled by the dialog)
        qte = self.safe_float(self.quantite_entry.get())
        if qte <= 0: messagebox.showwarning("Validation", "Veuillez ajouter des Bons de Réception."); self.open_receipts_dialog(); return
        
        bon, refac = self.safe_float(self.bon_entry.get()), self.safe_float(self.refac_entry.get())
        if bon <= 0 and refac <= 0: messagebox.showwarning("Validation", "Bon ou Refac requis."); return
        
        product_item = {
            "nature": nature, 
            "quantite": qte, 
            "prix_u": prix_u, 
            "bon": bon, 
            "refac": refac, 
            "montant_brut": (qte * prix_u) + (qte * bon) - (qte * refac),
            "receipts": list(self.current_receipts)
        }
        self.added_products.append(product_item)
        self._refresh_product_list_ui()
        
        # Reset current shipment state
        self.current_receipts = []
        
        # Lock Identity after first product
        for e in [self.farmer_entry, self.remis_entry, self.nif_entry, self.piece_entry]: e.configure(state="disabled")
        
        self.quantite_entry.configure(state="normal")
        self.quantite_entry.delete(0, 'end')
        self.quantite_entry.configure(state="readonly")
        self.bon_entry.delete(0, 'end'); self.refac_entry.delete(0, 'end')
        self.prod_count_lbl.configure(text=f"Produits: {len(self.added_products)} / {self.max_products}")
        self.to_taxes_btn.configure(state="normal")
        self.calculate()
        
        if len(self.added_products) >= 5:
            self._go_to_taxes()
        elif jump_to_taxes or not self.multi_prod_var.get(): 
            self._go_to_taxes()
        else: 
            self.nature_menu.focus()
            self.nature_menu._clicked() # Auto-dropdown

    def _go_to_taxes(self):
        for tax in self.tax_inputs:
            if tax["name"] == "redevance CH AGP": tax["amount"].focus(); break

    def clear_products(self, focus_nature=True):
        self.added_products = []
        self.current_receipts = []
        self._refresh_product_list_ui()
        self.prod_count_lbl.configure(text=f"Produits: 0 / {self.max_products}")
        self.to_taxes_btn.configure(state="disabled")
        if focus_nature: self.nature_menu.focus()
        self.calculate()

    def remove_product(self, index):
        """Removes a specific product from the list and refreshes UI."""
        if 0 <= index < len(self.added_products):
            self.added_products.pop(index)
            self._refresh_product_list_ui()
            self.prod_count_lbl.configure(text=f"Produits: {len(self.added_products)} / {self.max_products}")
            if not self.added_products:
                self.to_taxes_btn.configure(state="disabled")
            self.calculate()

    def clear_all(self):
        for e in [self.farmer_entry, self.remis_entry, self.nif_entry, self.piece_entry]: 
            e.configure(state="normal"); e.delete(0, 'end')
        self.wilaya_var.set(" ")
        self.clear_products()
        self.current_receipts = []
        self.res_lbl.configure(text="Totals will be calculated automatically.")
        self.farmer_entry.focus()

    def calculate(self):
        farmer, addr = self.farmer_entry.get().strip(), self.remis_entry.get().strip()
        nif, piece = self.nif_entry.get().strip(), self.piece_entry.get().strip()
        
        is_valid = True
        if not farmer: self.farmer_entry.configure(border_color="red"); is_valid = False
        else: self.farmer_entry.configure(border_color=["#979797", "#3d3d3d"])
        if not addr: self.remis_entry.configure(border_color="red"); is_valid = False
        else: self.remis_entry.configure(border_color=["#979797", "#3d3d3d"])
        if nif and len(nif) != 20: self.nif_entry.configure(border_color="red"); is_valid = False
        else: self.nif_entry.configure(border_color=["#979797", "#3d3d3d"])
        if len(piece) != 9: self.piece_entry.configure(border_color="red"); is_valid = False
        else: self.piece_entry.configure(border_color=["#979797", "#3d3d3d"])
        
        if not is_valid: self.res_lbl.configure(text="Identité incomplète (Rouge)"); return False

        products = list(self.added_products)
        total_weight = sum(p["quantite"] for p in products)
        m_brut = sum(p["montant_brut"] for p in products)
        
        total_retenues = 0.0
        retenues_data = []
        for tax in self.tax_inputs:
            name = tax["name"]
            amount = 0.0
            if name == "taxe pour compte CNA":
                amount = total_weight * 15
                for e in [tax["nbre"], tax["pu"], tax["amount"]]: e.configure(state="normal"); e.delete(0, 'end')
                tax["nbre"].insert(0, f"{total_weight:.2f}"); tax["pu"].insert(0, "15"); tax["amount"].insert(0, f"{amount:.2f}")
                for e in [tax["nbre"], tax["pu"], tax["amount"]]: e.configure(state="disabled")
            elif name == "taxe pour chambre agricole":
                amount = sum(p["quantite"] * (5 if "ORGE" in p["nature"].upper() else 3) for p in products)
                for e in [tax["nbre"], tax["pu"], tax["amount"]]: e.configure(state="normal"); e.delete(0, 'end')
                tax["nbre"].insert(0, f"{total_weight:.2f}"); tax["pu"].insert(0, "3/5"); tax["amount"].insert(0, f"{amount:.2f}")
                for e in [tax["nbre"], tax["pu"], tax["amount"]]: e.configure(state="disabled")
            else:
                amount = self.safe_float(tax["amount"].get())
            total_retenues += amount
            nbre = self.safe_float(tax["nbre"].get()) if tax["nbre"].winfo_viewable() or tax["nbre"].get() else None
            pu = tax["pu"].get() if tax["pu"].winfo_viewable() or tax["pu"].get() else None
            
            retenues_data.append({
                "name": name, 
                "nbre": nbre, 
                "pu": pu, 
                "amount": amount
            })
            
        m_net = m_brut - total_retenues
        self.res_lbl.configure(text=f"Brut: {m_brut:.2f} | Taxes: {total_retenues:.2f} | Net: {m_net:.2f} DA")
        self._compiled_data = {"products": products, "identity": {"farmer": self.farmer_entry.get(), "adresse": self.remis_entry.get(), "wilaya": self.wilaya_var.get(), "nif": self.nif_entry.get(), "piece_identite": self.piece_entry.get(), "date": self.date_entry.get(), "decompte": self.decompte_entry.get(), "user_account_name": self.username}, "retenues": retenues_data, "totals": {"total_retenues": total_retenues, "montant_net": m_net}}
        return True

    def generate(self):
        if not self.calculate(): return
        if not self.added_products: messagebox.showwarning("Validation", "Liste produits vide."); return
        if self._compiled_data["totals"]["montant_net"] <= 0: messagebox.showwarning("Validation", "Net <= 0."); return
        
        temp_path = os.path.join(os.getcwd(), "temp_preview.pdf")
        generate_facture_pdf(self._compiled_data, temp_path)
        InvoicePreviewWindow(self, temp_path, self.finalize_generation)

    def finalize_generation(self):
        database.save_invoice(self._compiled_data, "")
        messagebox.showinfo("Success", "Facture enregistrée !")
        self.current_count += 1; self.save_count(self.current_count)
        self.clear_all()

    def open_receipts_dialog(self, product_idx=None):
        """Opens the receipts manager. If index provided, edits existing product's receipts."""
        initial = []
        if product_idx is not None:
            initial = self.added_products[product_idx].get('receipts', [])
        else:
            initial = self.current_receipts

        def on_save(new_receipts):
            total_qty = sum(r['qte'] for r in new_receipts)
            if product_idx is not None:
                # Update existing product
                prod = self.added_products[product_idx]
                prod['receipts'] = [dict(r) for r in new_receipts]
                prod['quantite'] = total_qty
                # Recalculate brut
                prod['montant_brut'] = (total_qty * prod['prix_u']) + (total_qty * prod['bon']) - (total_qty * prod['refac'])
                self._refresh_product_list_ui()
                self.calculate()
            else:
                # Update current entry
                self.current_receipts = [dict(r) for r in new_receipts]
                self.quantite_entry.configure(state="normal")
                self.quantite_entry.delete(0, 'end')
                self.quantite_entry.insert(0, f"{total_qty:.2f}")
                self.quantite_entry.configure(state="readonly")
                # Automated flow: move focus to Bonification for next step
                self.bon_entry.focus()

        ReceiptsDialog(self, initial_receipts=initial, on_save=on_save)

    def _refresh_product_list_ui(self):
        """Re-renders the scrollable list of added products with Edit buttons."""
        for widget in self.prod_listbox.winfo_children():
            widget.destroy()

        for i, p in enumerate(self.added_products):
            # High-contrast design for better readability
            row = ctk.CTkFrame(self.prod_listbox, fg_color="#ffffff", border_width=1, border_color="#dddddd", corner_radius=8)
            row.pack(fill="x", padx=5, pady=4)
            
            # Product info - Show Bon numbers for clarity
            bons_list = [r['ref'] for r in p.get('receipts', [])]
            bons_str = ", ".join(bons_list)
            info_text = f"📦 {p['nature']} | Qté: {p['quantite']:.2f} | {p['montant_brut']:,.2f} DA"
            if bons_str:
                info_text += f"\n📄 Bons: {bons_str}"

            ctk.CTkLabel(row, text=info_text, 
                          anchor="w", font=ctk.CTkFont(family="Poppins", size=12, weight="bold"), 
                          text_color="#212121", justify="left").pack(side="left", fill="x", expand=True, padx=15, pady=8)
            
            # Action Buttons Area
            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="right", padx=10)
            
            # Edit Button for receipts
            ctk.CTkButton(actions, text="📝 BONS", width=70, height=30, font=ctk.CTkFont(family="Poppins", size=11, weight="bold"),
                          fg_color="#1565C0", hover_color="#0D47A1",
                          command=lambda idx=i: self.open_receipts_dialog(idx)).pack(side="left", padx=5)
            
            # Delete Button (Red X)
            ctk.CTkButton(actions, text="✕", width=30, height=30, font=ctk.CTkFont(size=14, weight="bold"),
                          fg_color="#C62828", hover_color="#B71C1C", text_color="white",
                          command=lambda idx=i: self.remove_product(idx)).pack(side="left", padx=5)
