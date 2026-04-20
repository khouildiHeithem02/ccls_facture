import customtkinter as ctk
from tkinter import messagebox
import database

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
        
        ctk.CTkLabel(add_frame, text="Nouveau Utilisateur:", font=ctk.CTkFont(family="Poppins", size=16, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        self.new_user_entry = ctk.CTkEntry(add_frame, placeholder_text="Login", font=ctk.CTkFont(family="Poppins", size=14), height=35)
        self.new_user_entry.grid(row=1, column=0, padx=5, pady=5)
        self.new_user_entry.bind("<Return>", lambda e: self.new_pass_entry.focus())
        self.new_pass_entry = ctk.CTkEntry(add_frame, placeholder_text="Pass", show="*", font=ctk.CTkFont(family="Poppins", size=14), height=35)
        self.new_pass_entry.grid(row=1, column=1, padx=5, pady=5)
        self.new_pass_entry.bind("<Return>", lambda e: self._add_user_cmd())
        self.new_role_var = ctk.StringVar(value="user")
        ctk.CTkOptionMenu(add_frame, values=["user"], variable=self.new_role_var, width=100, state="disabled", font=ctk.CTkFont(family="Poppins", size=13), height=35).grid(row=1, column=2, padx=5, pady=5)
        
        ctk.CTkButton(add_frame, text="Ajouter", command=self._add_user_cmd, width=100, height=35, font=ctk.CTkFont(family="Poppins", size=14, weight="bold")).grid(row=1, column=3, padx=5, pady=5)
        
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
        
        self.new_prod_entry = ctk.CTkEntry(add_frame, placeholder_text="Nom du produit", font=ctk.CTkFont(family="Poppins", size=14), height=35)
        self.new_prod_entry.grid(row=0, column=0, padx=5, pady=5)
        self.new_prod_entry.bind("<Return>", lambda e: self.new_price_entry.focus())
        self.new_price_entry = ctk.CTkEntry(add_frame, placeholder_text="Prix (ex: 6000)", font=ctk.CTkFont(family="Poppins", size=14), height=35)
        self.new_price_entry.grid(row=0, column=1, padx=5, pady=5)
        self.new_price_entry.bind("<Return>", lambda e: self._add_prod_cmd())
        ctk.CTkButton(add_frame, text="Ajouter Produit", command=self._add_prod_cmd, height=35, font=ctk.CTkFont(family="Poppins", size=14, weight="bold")).grid(row=0, column=2, padx=5, pady=5)
        
        list_frame = ctk.CTkScrollableFrame(self.tab_prods, height=300)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.prods_list_frame = list_frame
        self._refresh_prods()

    def _refresh_prods(self):
        for w in self.prods_list_frame.winfo_children(): w.destroy()
        prods = database.get_db_products()
        for name, price in prods.items():
            f = ctk.CTkFrame(self.prods_list_frame)
            f.pack(fill="x", pady=4)
            p_font = ctk.CTkFont(family="Poppins", size=14)
            ctk.CTkLabel(f, text=name, width=220, anchor="w", font=p_font).pack(side="left", padx=10)
            ctk.CTkLabel(f, text=f"{price:,.2f} DA", text_color="#1f538d", font=ctk.CTkFont(family="Poppins", size=14, weight="bold")).pack(side="left", padx=10)
            ctk.CTkButton(f, text="Suppr", width=60, height=30, fg_color="#C62828", font=p_font, command=lambda n=name: self._del_prod_cmd(n)).pack(side="right", padx=10)
            ctk.CTkButton(f, text="Modifier", width=80, height=30, fg_color="#1976D2", font=p_font, command=lambda n=name, p=price: self._modify_prod_cmd(n, p)).pack(side="right", padx=5)

    def _modify_prod_cmd(self, name, price):
        self.new_prod_entry.delete(0, 'end')
        self.new_prod_entry.insert(0, name)
        self.new_price_entry.delete(0, 'end')
        self.new_price_entry.insert(0, str(price))
        self.new_price_entry.focus()

    def _add_prod_cmd(self):
        n = self.new_prod_entry.get().strip()
        p_str = self.new_price_entry.get().strip()
        try:
            p = float(p_str)
            if n and database.add_db_product(n, p):
                self._refresh_prods()
                self.new_prod_entry.delete(0, 'end'); self.new_price_entry.delete(0, 'end')
                # Trigger main app to reload products if master exists
                master_app = self.master if hasattr(self.master, 'reload_products') else None
                if master_app: master_app.reload_products()
            else: messagebox.showerror("!", "Error adding product")
        except: messagebox.showerror("!", "Price must be a number")

    def _del_prod_cmd(self, n):
        if messagebox.askyesno("Confirm", f"Delete {n}?", parent=self):
            database.delete_db_product(n)
            self._refresh_prods()
            master_app = self.master if hasattr(self.master, 'reload_products') else None
            if master_app: master_app.reload_products()
