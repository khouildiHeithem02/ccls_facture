import customtkinter as ctk
import ctypes
import database
from ui.frames.login_frame import LoginFrame
from ui.frames.app_frame import AppFrame
from ui.frames.history_frame import HistoryFrame

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class MainApplication(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Système de Facturation CCLS")
        
        # Set a large initial size and start maximized
        self.geometry("1400x900")
        self.state('zoomed')
        self.resizable(True, True)
        
        # HWID Container for shared state
        self.username = None
        self.role = None
        
        # Main container for frames
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        # Frame Cache
        self.frames = {}
        
        self.show_login()

    def show_login(self):
        """Initial state: Only shows Login Frame."""
        self.title("CCLS - Authentification")
        
        # Clear existing cached frames on logout
        for f in self.frames.values():
            f.destroy()
        self.frames = {}
        
        login_frame = LoginFrame(self.container, on_login_success=self.on_login_complete)
        login_frame.grid(row=0, column=0, sticky="nsew")
        self.frames["login"] = login_frame
        login_frame.tkraise()

    def on_login_complete(self, username, role):
        """Callback from LoginFrame: Sets user and prepares dashboard only (Lazy Loading)."""
        self.username = username
        self.role = role
        
        # Destroy login frame as it's no longer needed
        if "login" in self.frames:
            self.frames["login"].destroy()
            del self.frames["login"]
            
        # Create ONLY the dashboard initially for maximum speed
        self.title(f"CCLS Facture - Connecté: {username.upper()}")
        
        self.frames["dashboard"] = AppFrame(self.container, username=username, role=role, 
                                           on_disconnect=self.show_login, 
                                           on_show_history=self.show_history)
        self.frames["dashboard"].grid(row=0, column=0, sticky="nsew")
        
        # Show dashboard immediately
        self.show_dashboard()

    def show_dashboard(self):
        """Instantly switch to dashboard."""
        self.title(f"CCLS Facture - Connecté: {self.username.upper()}")
        if "dashboard" in self.frames:
            self.frames["dashboard"].tkraise()

    def show_history(self, *args):
        """Lazy load and switch to history."""
        self.title("CCLS Facture - 📜 Historique")
        
        # Initialize history frame only on first request
        if "history" not in self.frames:
            self.frames["history"] = HistoryFrame(self.container, username=self.username, 
                                                 on_back=self.show_dashboard)
            self.frames["history"].grid(row=0, column=0, sticky="nsew")
        
        # Refresh list and show
        self.frames["history"].refresh_list()
        self.frames["history"].tkraise()

    def load_invoice_for_edit(self, invoice_id):
        """Fetches invoice details and populates the dashboard frame for editing."""
        data = database.get_invoice_details(invoice_id)
        if data:
            if "dashboard" in self.frames:
                self.frames["dashboard"].load_data_for_edit(data, invoice_id)
            else:
                messagebox.showerror("Erreur", "Le tableau de bord n'est pas chargé.")
if __name__ == "__main__":
    # Ensure database is initialized once at the very start
    database.init_db()
    
    # Show premium splash screen
    from ui.windows.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.mainloop()
    
    # Start the main application
    app = MainApplication()
    app.mainloop()
