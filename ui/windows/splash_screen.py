import customtkinter as ctk
from PIL import Image
import os
import ctypes

class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window Setup
        self.title("Chargement...")
        self.attributes("-fullscreen", True)
        self.configure(fg_color="#ffffff") # Clean white background
        
        # Screenshot protection
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except:
            pass

        # Content Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Logo
        logo_path = os.path.join(os.getcwd(), "logo.png")
        if os.path.exists(logo_path):
            logo_img = ctk.CTkImage(light_image=Image.open(logo_path), 
                                    dark_image=Image.open(logo_path), 
                                    size=(300, 350))
            self.logo_lbl = ctk.CTkLabel(self.container, image=logo_img, text="")
            self.logo_lbl.pack(pady=(0, 40))
            
        # Title
        self.title_lbl = ctk.CTkLabel(self.container, 
                                      text="SYSTÈME DE FACTURATION CCLS",
                                      font=ctk.CTkFont(family="Poppins", size=32, weight="bold"),
                                      text_color="#1f538d")
        self.title_lbl.pack(pady=10)
        
        self.subtitle_lbl = ctk.CTkLabel(self.container, 
                                         text="CCLS OUARGLA - Direction de la Production",
                                         font=ctk.CTkFont(family="Poppins", size=18),
                                         text_color="gray")
        self.subtitle_lbl.pack(pady=(0, 50))
        
        # Progress Bar
        self.progress = ctk.CTkProgressBar(self.container, width=500, height=12, 
                                            determinate_speed=0.5, fg_color="#e0e0e0", progress_color="#1f538d")
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        self.loading_lbl = ctk.CTkLabel(self.container, text="Chargement des ressources...", 
                                        font=ctk.CTkFont(family="Poppins", size=14, slant="italic"),
                                        text_color="#1f538d")
        self.loading_lbl.pack()
        
        # Start progress animation
        self.anim_id = None
        self.animate_progress(0)
        
        # Auto-close after 3.5 seconds
        self.after(3500, self.finish)
        
    def animate_progress(self, val):
        if val <= 1.0:
            self.progress.set(val)
            self.anim_id = self.after(30, lambda: self.animate_progress(val + 0.01))
            
    def finish(self):
        if self.anim_id:
            self.after_cancel(self.anim_id)
        self.quit()
        self.destroy()

if __name__ == "__main__":
    app = SplashScreen()
    app.mainloop()
