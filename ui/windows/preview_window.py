import customtkinter as ctk
import os
import fitz  # PyMuPDF
import ctypes
from PIL import Image

class InvoicePreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, pdf_path, on_confirm=None, mode="creation", on_cancel=None):
        super().__init__(parent)
        self.title("Invoice Preview (Exact Layout)")
        
        # ... (geometry logic kept same)
        w = 850
        h = 700
        try:
            x = (self.winfo_screenwidth() // 2) - (w // 2)
            self.geometry(f"{w}x{h}+{max(0, x)}+30")
        except:
            self.geometry(f"{w}x{h}")
            
        self.resizable(True, True)
        self.lift()
        self.on_confirm = on_confirm
        self.on_cancel_callback = on_cancel
        self.pdf_path = pdf_path
        self.mode = mode
        
        # Hook the 'X' button to delete the preview file too
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
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
            self.btn_print = ctk.CTkButton(btn_frame, text="🖨️ Imprimer & Enregistrer", command=self.confirm_and_close,
                                           fg_color="#2E7D32", font=ctk.CTkFont(family="Poppins", size=15, weight="bold"), height=45)
            self.btn_print.pack(side="left", expand=True, padx=10)
            
            self.btn_cancel = ctk.CTkButton(btn_frame, text="❌ ANNULER", command=self.on_cancel,
                                             fg_color="#C62828", font=ctk.CTkFont(family="Poppins", size=15), height=45)
            self.btn_cancel.pack(side="right", expand=True, padx=10)
        else:
            # View-only / History mode - Now looks identical to creation mode
            self.btn_print = ctk.CTkButton(btn_frame, text="🖨️ IMPRIMER / OUVRIR", command=lambda: os.startfile(self.pdf_path) if os.path.exists(self.pdf_path) else None,
                                           fg_color="#2E7D32", font=ctk.CTkFont(family="Poppins", size=15, weight="bold"), height=45)
            self.btn_print.pack(side="left", expand=True, padx=10)
            
            self.btn_close = ctk.CTkButton(btn_frame, text="❌ FERMER", command=self.on_cancel,
                                           fg_color="#C62828", font=ctk.CTkFont(family="Poppins", size=15), height=45)
            self.btn_close.pack(side="right", expand=True, padx=10)

        # Scrollable area for the image (Takes remaining space)
        self.scroll_canvas = ctk.CTkScrollableFrame(main_frame, fg_color="#f0f0f0")
        self.scroll_canvas.pack(side="top", fill="both", expand=True, pady=(0, 10))
        
        # Zooming state - Start at 1.0 (Standard view)
        self.zoom_level = 1.0
        
        # Render the PDF to an image
        self._render_pdf()
        
        # Bind Mouse Wheel for Zoom
        self.bind("<Control-MouseWheel>", self._on_mouse_wheel) # Windows
        self.image_label.bind("<Control-MouseWheel>", self._on_mouse_wheel)
        
    def _on_mouse_wheel(self, event):
        """Handles Control + Scroll for zooming."""
        if event.delta > 0:
            self.zoom_level = min(5.0, self.zoom_level + 0.3)
        else:
            self.zoom_level = max(1.0, self.zoom_level - 0.3)
        self._render_pdf()

    def _render_pdf(self):
        """Renders the PDF at the current zoom level."""
        try:
            doc = fitz.open(self.pdf_path)
            page = doc.load_page(0)
            
            # Use high-quality rendering base (2.0) even for 1.0 zoom to keep text sharp
            render_scale = 2.0 * self.zoom_level
            mat = fitz.Matrix(render_scale, render_scale)
            pix = page.get_pixmap(matrix=mat)
            
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Calculate display size: Fit to window width or standard scale
            # We want the image to be readable at 1.0 without being massive
            display_w = pix.width // 2
            display_h = pix.height // 2
            
            self.preview_image = ctk.CTkImage(light_image=img, dark_image=img, size=(display_w, display_h))
            
            if hasattr(self, 'image_label'):
                self.image_label.configure(image=self.preview_image)
            else:
                self.image_label = ctk.CTkLabel(self.scroll_canvas, image=self.preview_image, text="")
                self.image_label.pack(expand=True, padx=20, pady=20)
            doc.close()
        except Exception as e:
            if hasattr(self, 'image_label'):
                self.image_label.configure(text=f"Error rendering: {e}", image=None)
            else:
                ctk.CTkLabel(self.scroll_canvas, text=f"Error rendering preview: {e}").pack(pady=50)

    def on_cancel(self):
        try:
            # Delete the temp file (always for view, and if cancelled for creation)
            if os.path.exists(self.pdf_path):
                os.remove(self.pdf_path)
        except:
            pass
        
        if self.on_cancel_callback:
            self.on_cancel_callback()
            
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
