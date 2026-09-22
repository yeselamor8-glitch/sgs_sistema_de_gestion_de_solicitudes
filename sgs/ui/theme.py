"""
Sistema de diseño centralizado — Material Design 3 con identidad
institucional (Alcaldía de Medellín · Secretaría de Salud).

Color institucional principal: #00A0DF (azul claro).

Estructura:
  * COLORES / COLORES_SEMAFORO — tokens de color (fuente de verdad).
  * TIPOGRAFIA / ESPACIADO / BORDES — escalas de diseño.
  * STYLESHEET_APP — hoja de estilos global (MD3, tema claro).
  * Alias de compatibilidad — los nombres antiguos (BG_APP, ACCENT,
    SEMAFORO_ROJO, ...) siguen existiendo apuntando a los nuevos valores,
    para que las pantallas ya escritas no se rompan. Migrar a COLORES[...]
    de forma gradual.

Ningún widget debe escribir colores "a mano": todos importan de aquí.
"""
from __future__ import annotations

# ----------------------------------------------------------------------
# Tokens de color (Material Design 3 · identidad institucional)
# ----------------------------------------------------------------------
COLORES = {
    # Identidad institucional
    "primary":         "#00A0DF",
    "primary_dark":    "#0077B6",
    "primary_light":   "#4FC3F7",
    "on_primary":      "#FFFFFF",
    "secondary":       "#00A651",

    # Estados
    "success":         "#00A651",
    "warning":         "#FFC107",
    "alert":           "#FF7F27",
    "error":           "#E53935",
    "info":            "#009B9E",

    # Superficies
    "background":      "#F5F7FA",
    "surface":         "#FFFFFF",
    "surface_variant": "#EAF6FC",
    "surface_hover":   "#F0F9FE",
    "on_surface":      "#1A1A1A",
    "on_surface_var":  "#6B7280",

    # Bordes
    "outline":         "#DDE4EA",
    "outline_variant": "#EEF2F6",
}

COLORES_SEMAFORO = {
    "VERDE":    "#00A651",
    "AMARILLO": "#FFC107",
    "ROJO":     "#E53935",
    "GRIS":     "#9E9E9E",
}

# ----------------------------------------------------------------------
# Tipografía / espaciado / bordes
# ----------------------------------------------------------------------
FUENTE_PRINCIPAL = "Inter"

TIPOGRAFIA = {
    "display_large":   (FUENTE_PRINCIPAL, 32, "Bold"),
    "display_medium":  (FUENTE_PRINCIPAL, 28, "Bold"),
    "headline_large":  (FUENTE_PRINCIPAL, 22, "SemiBold"),
    "headline_medium": (FUENTE_PRINCIPAL, 20, "SemiBold"),
    "title_large":     (FUENTE_PRINCIPAL, 16, "Medium"),
    "title_medium":    (FUENTE_PRINCIPAL, 14, "Medium"),
    "body_large":      (FUENTE_PRINCIPAL, 14, "Normal"),
    "body_medium":     (FUENTE_PRINCIPAL, 13, "Normal"),
    "body_small":      (FUENTE_PRINCIPAL, 12, "Normal"),
    "label_large":     (FUENTE_PRINCIPAL, 12, "Medium"),
    "label_medium":    (FUENTE_PRINCIPAL, 11, "Medium"),
}

ESPACIADO = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32, "xxl": 48}
BORDES = {"sm": 4, "md": 8, "lg": 12, "xl": 16, "full": 999}

# Familia de fuente efectiva: Inter si se cargó; si no, alternativas del SO.
FONT_STACK = f"{FUENTE_PRINCIPAL}, Segoe UI, Arial, sans-serif"

# ----------------------------------------------------------------------
# Alias de compatibilidad (NO eliminar: los usan las pantallas actuales)
# ----------------------------------------------------------------------
BG_APP = COLORES["background"]
BG_SIDEBAR = COLORES["surface"]
BG_SIDEBAR_HOVER = COLORES["surface_hover"]
BG_SIDEBAR_ACTIVE = COLORES["surface_variant"]
BG_CARD = COLORES["surface"]
BORDER = COLORES["outline"]
BORDER_SIDEBAR = COLORES["outline_variant"]

TEXT_PRIMARY = COLORES["on_surface"]
TEXT_SECONDARY = COLORES["on_surface_var"]
TEXT_ON_SIDEBAR = "#3D4452"
TEXT_ON_SIDEBAR_ACTIVE = COLORES["primary"]
TEXT_ON_SIDEBAR_MUTED = "#9299A8"

ACCENT = COLORES["primary"]
ACCENT_LIGHT = COLORES["surface_variant"]

# Semaforización — alias (mismos colores que COLORES_SEMAFORO, con sus BG).
SEMAFORO_BLANCO = "#FFFFFF"
SEMAFORO_BLANCO_BG = "#EFF1F4"
SEMAFORO_AMARILLO = COLORES_SEMAFORO["AMARILLO"]
SEMAFORO_AMARILLO_BG = "#FFF6DB"
SEMAFORO_ROJO = COLORES_SEMAFORO["ROJO"]
SEMAFORO_ROJO_BG = "#FCE5E5"
SEMAFORO_VERDE = COLORES_SEMAFORO["VERDE"]
SEMAFORO_VERDE_BG = "#E3F6EC"

SEMAFORO_COLORES = {
    "A_TIEMPO": (SEMAFORO_BLANCO, SEMAFORO_BLANCO_BG),
    "CERCA_DE_VENCIMIENTO": (SEMAFORO_AMARILLO, SEMAFORO_AMARILLO_BG),
    "VENCIDO": (SEMAFORO_ROJO, SEMAFORO_ROJO_BG),
    "COMPLETADO": (SEMAFORO_VERDE, SEMAFORO_VERDE_BG),
    "SIN_FECHA": (COLORES_SEMAFORO["GRIS"], "#EEF0F3"),
}

FONT_FAMILY = FONT_STACK
RADIUS = BORDES["lg"]  # 12

# ----------------------------------------------------------------------
# Hoja de estilos global (Material Design 3, tema claro)
# ----------------------------------------------------------------------
STYLESHEET_APP = f"""
/* Base */
QWidget {{
    background-color: {COLORES["background"]};
    color: {COLORES["on_surface"]};
    font-family: {FONT_STACK};
    font-size: 13px;
}}
QMainWindow, QDialog {{ background-color: {COLORES["background"]}; }}
QStackedWidget {{ background-color: {COLORES["background"]}; }}
QScrollArea {{ background-color: {COLORES["background"]}; border: none; }}
QScrollArea > QWidget > QWidget {{ background-color: {COLORES["background"]}; }}

/* Etiquetas por rol */
QLabel {{ background-color: transparent; color: {COLORES["on_surface"]}; }}
QLabel[role="title"] {{ font-size: 20px; font-weight: 700; color: {COLORES["on_surface"]}; }}
QLabel[role="subtitle"] {{ font-size: 15px; font-weight: 600; color: {COLORES["on_surface"]}; }}
QLabel[role="secondary"] {{ color: {COLORES["on_surface_var"]}; font-size: 12px; }}
QLabel[role="metric"] {{ font-size: 26px; font-weight: 700; color: {COLORES["primary"]}; }}

/* Botones — default NEUTRO (surface con borde). El azul es variant="primary". */
QPushButton {{
    background-color: {COLORES["surface"]};
    color: {COLORES["on_surface"]};
    border: 1px solid {COLORES["outline"]};
    border-radius: {BORDES["md"]}px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {COLORES["surface_variant"]}; border-color: {COLORES["primary_light"]}; }}
QPushButton:pressed {{ background-color: {COLORES["surface_hover"]}; }}
QPushButton:disabled {{ background-color: {COLORES["outline_variant"]}; color: #AEB6BF; border-color: {COLORES["outline"]}; }}

QPushButton[variant="primary"] {{
    background-color: {COLORES["primary"]}; color: {COLORES["on_primary"]}; border: none;
}}
QPushButton[variant="primary"]:hover {{ background-color: {COLORES["primary_dark"]}; }}
QPushButton[variant="primary"]:pressed {{ background-color: #005F94; }}

QPushButton[variant="secondary"] {{
    background-color: {COLORES["secondary"]}; color: white; border: none;
}}
QPushButton[variant="secondary"]:hover {{ background-color: #008A44; }}
QPushButton[variant="secondary"]:pressed {{ background-color: #007538; }}

QPushButton[variant="ghost"] {{
    background-color: transparent; color: {COLORES["primary"]};
    border: 1px solid {COLORES["outline"]};
}}
QPushButton[variant="ghost"]:hover {{
    background-color: {COLORES["surface_variant"]};
    border-color: {COLORES["primary_light"]};
}}
QPushButton[variant="ghost"]:pressed {{ background-color: {COLORES["surface_hover"]}; }}

QPushButton[variant="danger"] {{
    background-color: {COLORES["error"]}; color: white; border: none;
}}
QPushButton[variant="danger"]:hover {{ background-color: #C62828; }}
QPushButton[variant="danger"]:pressed {{ background-color: #B71C1C; }}

/* Entradas */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: {COLORES["surface"]};
    color: {COLORES["on_surface"]};
    border: 1px solid {COLORES["outline"]};
    border-radius: {BORDES["md"]}px;
    padding: 7px 10px;
    selection-background-color: {COLORES["primary_light"]};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {COLORES["primary"]};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: {COLORES["surface"]};
    color: {COLORES["on_surface"]};
    border: 1px solid {COLORES["outline"]};
    selection-background-color: {COLORES["surface_variant"]};
    selection-color: {COLORES["on_surface"]};
    outline: none;
}}

/* Tablas */
QTableWidget, QTableView {{
    background-color: {COLORES["surface"]};
    alternate-background-color: {COLORES["background"]};
    color: {COLORES["on_surface"]};
    border: 1px solid {COLORES["outline"]};
    border-radius: {BORDES["lg"]}px;
    gridline-color: {COLORES["outline_variant"]};
}}
QTableWidget::item, QTableView::item {{ padding: 4px 6px; }}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {COLORES["surface_variant"]};
    color: {COLORES["on_surface"]};
}}
QTableWidget::item:hover, QTableView::item:hover {{
    background-color: {COLORES["surface_hover"]};
}}
QHeaderView::section {{
    background-color: {COLORES["surface_variant"]};
    color: {COLORES["on_surface_var"]};
    border: none;
    border-bottom: 1px solid {COLORES["outline"]};
    padding: 9px 8px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
QTableCornerButton::section {{ background-color: {COLORES["surface_variant"]}; border: none; }}

/* Widgets embebidos en celdas de tabla (semáforo, combo de estado, botones):
   compactos para que no desborden la fila ni tapen las celdas vecinas. */
QTableWidget QComboBox, QTableView QComboBox {{
    padding: 2px 6px; border-radius: {BORDES["sm"]}px; min-height: 0;
}}
QTableWidget QPushButton, QTableView QPushButton {{
    padding: 4px 10px;
}}

/* Pestañas */
QTabWidget::pane {{ border: 1px solid {COLORES["outline"]}; border-radius: {BORDES["lg"]}px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {COLORES["on_surface_var"]};
    padding: 8px 16px; margin-right: 2px;
    border-top-left-radius: {BORDES["md"]}px; border-top-right-radius: {BORDES["md"]}px;
}}
QTabBar::tab:selected {{
    color: {COLORES["primary"]}; font-weight: 600;
    border-bottom: 2px solid {COLORES["primary"]};
}}
QTabBar::tab:hover {{ color: {COLORES["primary_dark"]}; }}

/* Checkboxes */
QCheckBox {{ spacing: 8px; color: {COLORES["on_surface"]}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: {BORDES["sm"]}px;
    border: 1px solid {COLORES["outline"]}; background: {COLORES["surface"]};
}}
QCheckBox::indicator:checked {{
    background: {COLORES["primary"]}; border-color: {COLORES["primary"]};
}}

/* GroupBox */
QGroupBox {{
    border: 1px solid {COLORES["outline"]}; border-radius: {BORDES["lg"]}px;
    margin-top: 12px; padding: 10px; font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {COLORES["on_surface_var"]}; }}

/* Menús y tooltips */
QMenuBar {{ background-color: {COLORES["surface"]}; color: {COLORES["on_surface"]}; }}
QMenuBar::item:selected {{ background-color: {COLORES["surface_variant"]}; }}
QMenu {{
    background-color: {COLORES["surface"]}; color: {COLORES["on_surface"]};
    border: 1px solid {COLORES["outline"]}; border-radius: {BORDES["md"]}px;
}}
QMenu::item:selected {{ background-color: {COLORES["surface_variant"]}; }}
QToolTip {{
    background-color: {COLORES["on_surface"]}; color: white;
    border: none; border-radius: {BORDES["sm"]}px; padding: 6px 8px;
}}

/* Scrollbars delgadas, sin flechas */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: #C6D0DA; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {COLORES["primary_light"]}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: #C6D0DA; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {COLORES["primary_light"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
