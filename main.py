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
        
        # Start maximized for full-screen experience
        self.after(0, lambda: self.state('zoomed'))
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
        
        # Apply screenshot protection once to the root window (HWND)
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            # WDA_EXCLUDEFROMCAPTURE = 0x11
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass
            
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
        """Callback from LoginFrame: Sets user and prepares dashboard/history."""
        self.username = username
        self.role = role
        
        # Destroy login frame as it's no longer needed
        if "login" in self.frames:
            self.frames["login"].destroy()
            del self.frames["login"]
            
        # Create App and History frames ONCE (Caching)
        self.title(f"CCLS Facture - Connecté: {username.upper()}")
        
        # Dashboard
        self.frames["dashboard"] = AppFrame(self.container, username=username, role=role, 
                                           on_disconnect=self.show_login, 
                                           on_show_history=self.show_history)
        self.frames["dashboard"].grid(row=0, column=0, sticky="nsew")
        
        # History
        self.frames["history"] = HistoryFrame(self.container, username=username, 
                                             on_back=self.show_dashboard)
        self.frames["history"].grid(row=0, column=0, sticky="nsew")
        
        # Show dashboard initially
        self.show_dashboard()

    def show_dashboard(self):
        """Instantly switch to dashboard."""
        self.title(f"CCLS Facture - Connecté: {self.username.upper()}")
        if "dashboard" in self.frames:
            self.frames["dashboard"].tkraise()
            # Reload products in case they changed in admin panel
            self.frames["dashboard"].reload_products()

    def show_history(self, *args):
        """Instantly switch to history."""
        self.title("CCLS Facture - 📜 Historique")
        if "history" in self.frames:
            # Refresh list before showing to ensure latest data
            self.frames["history"].refresh_list()
            self.frames["history"].tkraise()

if __name__ == "__main__":
    database.init_db()
    app = MainApplication()
    app.mainloop()
