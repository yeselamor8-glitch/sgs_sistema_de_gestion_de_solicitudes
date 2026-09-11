"""
Tema visual centralizado. Ningún widget debe escribir colores o
tamaños "a mano" — todos importan de aquí, para que un cambio de
paleta se haga en un solo lugar.

Tema CLARO en su totalidad (institucional — Alcaldía de Medellín,
Secretaría de Salud). El sidebar también es claro, no oscuro.
"""
from __future__ import annotations

# Paleta — clara, moderna, profesional, institucional
BG_APP = "#F4F5F7"
BG_SIDEBAR = "#FFFFFF"
BG_SIDEBAR_HOVER = "#F1F4FA"
BG_SIDEBAR_ACTIVE = "#EAF0FE"
BG_CARD = "#FFFFFF"
BORDER = "#E3E5E9"
BORDER_SIDEBAR = "#EDEEF1"

TEXT_PRIMARY = "#1A1D23"
TEXT_SECONDARY = "#6B7280"
TEXT_ON_SIDEBAR = "#3D4452"
TEXT_ON_SIDEBAR_ACTIVE = "#3B5FE0"
TEXT_ON_SIDEBAR_MUTED = "#9299A8"

ACCENT = "#3B5FE0"
ACCENT_LIGHT = "#EAF0FE"

# Semaforización — única fuente de verdad para los 3 colores en toda la app
SEMAFORO_VERDE = "#1E9E5A"
SEMAFORO_VERDE_BG = "#E5F7EE"
SEMAFORO_AMARILLO = "#B8860B"
SEMAFORO_AMARILLO_BG = "#FDF3DA"
SEMAFORO_ROJO = "#D63B3B"
SEMAFORO_ROJO_BG = "#FCE8E8"

SEMAFORO_COLORES = {
    "VERDE": (SEMAFORO_VERDE, SEMAFORO_VERDE_BG),
    "AMARILLO": (SEMAFORO_AMARILLO, SEMAFORO_AMARILLO_BG),
    "ROJO": (SEMAFORO_ROJO, SEMAFORO_ROJO_BG),
}

FONT_FAMILY = "Segoe UI, Inter, Arial"
RADIUS = 10

STYLESHEET_APP = f"""
QMainWindow {{ background-color: {BG_APP}; }}
QWidget {{ background-color: {BG_APP}; color: {TEXT_PRIMARY}; font-family: {FONT_FAMILY}; font-size: 13px; }}
QStackedWidget {{ background-color: {BG_APP}; }}
QScrollArea {{ background-color: {BG_APP}; border: none; }}
QScrollArea > QWidget > QWidget {{ background-color: {BG_APP}; }}
QLabel {{ background-color: transparent; }}
QLabel[role="title"] {{ font-size: 18px; font-weight: 600; }}
QLabel[role="secondary"] {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
QPushButton {{
    background-color: {ACCENT}; color: white; border: none;
    border-radius: {RADIUS}px; padding: 8px 14px; font-weight: 500;
}}
QPushButton:hover {{ background-color: #2E4FC4; }}
QPushButton[variant="ghost"] {{
    background-color: transparent; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
}}
QPushButton[variant="ghost"]:hover {{ background-color: {ACCENT_LIGHT}; }}
QLineEdit {{
    border: 1px solid {BORDER}; border-radius: {RADIUS}px;
    padding: 8px 10px; background-color: white;
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QTableWidget {{
    background-color: {BG_CARD}; border: 1px solid {BORDER};
    border-radius: {RADIUS}px; gridline-color: {BORDER};
}}
QHeaderView::section {{
    background-color: {BG_CARD}; color: {TEXT_SECONDARY};
    border: none; border-bottom: 1px solid {BORDER};
    padding: 8px; font-weight: 600;
}}
"""