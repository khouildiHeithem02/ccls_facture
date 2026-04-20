import customtkinter as ctk
from tkinter import messagebox
import database

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
