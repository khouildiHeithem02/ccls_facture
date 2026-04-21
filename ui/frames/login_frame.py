import customtkinter as ctk
import os
from PIL import Image
from tkinter import messagebox
import database

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success=None):
        super().__init__(master, fg_color="transparent")
        self.on_login_success = on_login_success
            
        # Main Frame with slight shadow effect (simulated with border)
        self.main_frame = ctk.CTkFrame(self, corner_radius=20, border_width=1, border_color="#d0d0d0", 
                                        width=500, fg_color="white")
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.main_frame.pack_propagate(False)
        self.main_frame.configure(height=750) 
        
        # Logo handling
        try:
            # Look for logo in the root project folder
            logo_path = os.path.join(os.getcwd(), "logo.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(120, 140))
                self.logo_label = ctk.CTkLabel(self.main_frame, image=self.logo_img, text="")
                self.logo_label.pack(pady=(30, 10))
        except:
            pass
            
        self.title_label = ctk.CTkLabel(self.main_frame, text="Système de Facturation", 
                                        font=ctk.CTkFont(family="Poppins", size=32, weight="bold"))
        self.title_label.pack(pady=(10, 40))
        
        # Input Container
        input_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        input_container.pack(pady=10, padx=30, fill="x")
        
        ctk.CTkLabel(input_container, text="Nom d'utilisateur", font=ctk.CTkFont(family="Poppins", size=16)).pack(anchor="w", padx=10)
        self.username_entry = ctk.CTkEntry(input_container, placeholder_text="admin", 
                                           width=400, height=55, font=ctk.CTkFont(family="Poppins", size=18))
        self.username_entry.pack(pady=(5, 25))
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        
        ctk.CTkLabel(input_container, text="Mot de passe", font=ctk.CTkFont(family="Poppins", size=16)).pack(anchor="w", padx=10)
        self.password_entry = ctk.CTkEntry(input_container, placeholder_text="••••••••", 
                                           show="*", width=400, height=55, font=ctk.CTkFont(family="Poppins", size=18))
        self.password_entry.pack(pady=(5, 25))
        self.password_entry.bind("<Return>", lambda e: self.login())
        
        # Login Button
        self.login_btn = ctk.CTkButton(self.main_frame, text="SE CONNECTER", command=self.login, 
                                        width=400, height=65, font=ctk.CTkFont(family="Poppins", size=22, weight="bold"),
                                        fg_color="#1f538d", hover_color="#163e66", corner_radius=15)
        self.login_btn.pack(pady=(40, 20), padx=20)
        
        # Footer
        self.footer = ctk.CTkLabel(self.main_frame, text="© 2026 CCLS Ouargla - Sécurisé", 
                                   font=ctk.CTkFont(family="Poppins", size=14, slant="italic"), text_color="gray")
        self.footer.pack(side="bottom", pady=20)

        # Initial Focus
        self.after(200, lambda: self.username_entry.focus())

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Attention", "Veuillez remplir tous les champs.")
            return
            
        success, role = database.verify_login(username, password)
        if success:
            if self.on_login_success:
                self.on_login_success(username, role)
        else:
            messagebox.showerror("Erreur", "Nom d'utilisateur ou mot de passe incorrect.")
            self.password_entry.delete(0, 'end')
