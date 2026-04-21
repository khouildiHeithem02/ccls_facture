import customtkinter as ctk

# --- TAXES LIST ---
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

# --- UI CONSTANTS ---
FONT_FAMILY = "Poppins"

def get_font(size=14, weight="normal", slant="roman"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight, slant=slant)

# Appearance
APPEARANCE_MODE = "light"
COLOR_THEME = "blue"
