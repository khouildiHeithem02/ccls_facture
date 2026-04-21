import customtkinter as ctk
from tkinter import messagebox
import database
import datetime
try:
    from tkcalendar import DateEntry
except ImportError:
    # Fallback if installation hasn't fully propagated in this environment (unlikely given previous command)
    DateEntry = None

class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Mot de passe requis", on_success=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x170")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()
        
        self.on_success = on_success
        # Note: We rely on the parent having a 'username' attribute or being the master app
        self.parent_app = parent.master if hasattr(parent, 'master') else parent
        
        ctk.CTkLabel(self, text="Entrez votre mot de passe\npour confirmer l'action:", 
                     font=ctk.CTkFont(family="Poppins", size=14, weight="bold")).pack(pady=(20, 10))
        self.pw_entry = ctk.CTkEntry(self, show="*", width=220, height=35, font=ctk.CTkFont(family="Poppins", size=15))
        self.pw_entry.pack(pady=10)
        self.pw_entry.focus()
        self.pw_entry.bind("<Return>", lambda e: self.verify())
        
        ctk.CTkButton(self, text="Confirmer", command=self.verify, height=40, font=ctk.CTkFont(family="Poppins", size=14, weight="bold"),
                      fg_color="#FBC02D", text_color="black").pack(pady=10)
        
    def verify(self):
        pw = self.pw_entry.get()
        # Ensure we can get the username from the app context
        username = getattr(self.parent_app, 'username', None)
        if not username:
             # Fallback if accessed differently
             username = getattr(self.master, 'username', 'admin')

        success, _ = database.verify_login(username, pw)
        if success:
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Erreur", "Mot de passe incorrect.", parent=self)

class ReceiptsDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_receipts=None, on_save=None):
        super().__init__(parent)
        self.title("Gestion des Bons de Réception")
        self.geometry("750x600") # Slightly larger window for better layout
        self.on_save = on_save
        self.receipts = [dict(r) for r in initial_receipts] if initial_receipts else []
        
        self.attributes("-topmost", True)
        self.grab_set()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        ctk.CTkLabel(self, text="Bons de Réception (Shipments)", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, pady=20)
        
        # Scrollable area for list
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        # Entry Area: Reverting to CTK for better consistency
        entry_frame = ctk.CTkFrame(self)
        entry_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        entry_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        ctk.CTkLabel(entry_frame, text="N° Bon", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=5, pady=(5, 2))
        self.ref_en = ctk.CTkEntry(entry_frame, width=120, height=35)
        self.ref_en.grid(row=1, column=0, padx=5, pady=(0, 10))
        self.ref_en.bind("<Return>", lambda e: self.date_en.focus_set())
        
        ctk.CTkLabel(entry_frame, text="Date", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, padx=5, pady=(5, 2))
        # Date Entry with dynamic formatting
        self.date_en = ctk.CTkEntry(entry_frame, width=150, height=35, placeholder_text="JJ / MM / AAAA")
        self.date_en.grid(row=1, column=1, padx=5, pady=(0, 10))
        self.date_en.bind("<KeyRelease>", self._auto_format_date)
        self.date_en.bind("<Return>", lambda e: self.qte_en.focus())


        ctk.CTkLabel(entry_frame, text="Quantité", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=2, padx=5, pady=(5, 2))
        self.qte_en = ctk.CTkEntry(entry_frame, width=120, height=35)
        self.qte_en.grid(row=1, column=2, padx=5, pady=(0, 10))
        self.qte_en.bind("<Return>", lambda e: self._add_receipt())
        
        self.add_btn = ctk.CTkButton(entry_frame, text="Ajouter", width=100, height=35, command=self._add_receipt, 
                                      font=ctk.CTkFont(size=12, weight="bold"), fg_color="#2E7D32")
        self.add_btn.grid(row=1, column=3, padx=10, pady=(0, 10))

        
        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.total_lbl = ctk.CTkLabel(footer, text="Total: 0.00", font=ctk.CTkFont(size=16, weight="bold"))
        self.total_lbl.pack(side="left")
        
        ctk.CTkButton(footer, text="Terminer", command=self._finalize, width=120, fg_color="#1976D2").pack(side="right")
        
        self._refresh_list()
        self.after(100, self.ref_en.focus_set)

    def _auto_format_date(self, e=None):
        """Automatically insert slashes for DD / MM / YYYY formatting."""
        if e and e.keysym == "BackSpace": return
        
        # Extract only digits
        val = "".join([c for c in self.date_en.get() if c.isdigit()])
        if len(val) > 8: val = val[:8]
        
        parts = []
        if len(val) > 0: parts.append(val[:2])
        if len(val) > 2: parts.append(val[2:4])
        if len(val) > 4: parts.append(val[4:8])
        
        formatted = " / ".join(parts)
        
        if self.date_en.get() != formatted:
            self.date_en.delete(0, 'end')
            self.date_en.insert(0, formatted)
            
        # Update border color automatically when 8 digits are reached
        if len(val) == 8:
            is_valid, _ = self._validate_date_value(formatted)
            if not is_valid:
                self.date_en.configure(border_color="red")
            else:
                self.date_en.configure(border_color=["#979797", "#3d3d3d"])
        elif len(val) < 8:
             # Reset color while they are still typing to avoid premature red
             self.date_en.configure(border_color=["#979797", "#3d3d3d"])

    def _validate_date_value(self, date_str):
        """Helper to validate date and future-date constraints."""
        clean_date = date_str.replace(" ", "")
        try:
            input_date = datetime.datetime.strptime(clean_date, "%d/%m/%Y")
            if input_date > datetime.datetime.now():
                return False, "La date ne peut pas être dans le futur."
            return True, ""
        except ValueError:
            return False, "Format de date ou valeur invalide (JJ / MM / AAAA)."

    def _add_receipt(self):
        ref = self.ref_en.get().strip()
        date_str = self.date_en.get().strip()
        
        # 1. Validation Logic (Reusing the helper)
        is_valid, error_msg = self._validate_date_value(date_str)
        if not is_valid:
            self.date_en.configure(border_color="red")
            messagebox.showwarning("Erreur Date", error_msg, parent=self)
            self.date_en.focus_set()
            return
            
        # Reset color on success
        self.date_en.configure(border_color=["#979797", "#3d3d3d"])

        try:
            qte = float(self.qte_en.get())
            if qte <= 0: raise ValueError()
        except:
            messagebox.showwarning("Erreur", "Quantité invalide.", parent=self); self.qte_en.focus(); return

        if not ref or not date_str:
            messagebox.showwarning("Erreur", "Veuillez remplir tous les champs.", parent=self); return
            
        self.receipts.append({"ref": ref, "date": date_str, "qte": qte})
        
        # 3. Clear ALL fields as requested
        self.ref_en.delete(0, 'end')
        self.qte_en.delete(0, 'end')
        self.date_en.delete(0, 'end')
        
        self._refresh_list()
        self.ref_en.focus()

    def _refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
            
        total = 0
        for i, r in enumerate(self.receipts):
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=f"Bon N°: {r['ref']}", width=150, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=f"Date: {r['date']}", width=120).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=f"{r['qte']:.2f}", width=100, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
            
            ctk.CTkButton(row, text="🗑️", width=30, fg_color="#C62828", command=lambda idx=i: self._remove(idx)).pack(side="right", padx=10)
            total += r['qte']
            
        self.total_lbl.configure(text=f"Total: {total:.2f}")

    def _remove(self, idx):
        self.receipts.pop(idx)
        self._refresh_list()

    def _finalize(self):
        if not self.receipts:
            messagebox.showwarning("Attention", "Veuillez ajouter au moins un bon.", parent=self); return
        if self.on_save:
            self.on_save(self.receipts)
        self.destroy()

