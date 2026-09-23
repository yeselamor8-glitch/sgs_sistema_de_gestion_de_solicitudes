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
    "A_TIEMPO": ("#0284C7", "#E0F2FE"),
    "CERCA_DE_VENCIMIENTO": ("#D97706", "#FEF3C7"),
    "VENCIDO": ("#DC2626", "#FEE2E2"),
    "COMPLETADO": ("#16A34A", "#DCFCE7"),
    "SIN_FECHA": ("#64748B", "#F1F5F9"),
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
QLabel[role="title"] {{ font-size: 20px; font-weight: 700; color: #0F172A; letter-spacing: -0.2px; }}
QLabel[role="subtitle"] {{ font-size: 15px; font-weight: 600; color: #1E293B; }}
QLabel[role="secondary"] {{ color: #64748B; font-size: 12px; }}
QLabel[role="metric"] {{ font-size: 28px; font-weight: 700; color: {COLORES["primary"]}; }}

/* Botones — default NEUTRO (surface con borde). El azul es variant="primary". */
QPushButton {{
    background-color: {COLORES["surface"]};
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: {BORDES["md"]}px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #F8FAFC;
    border-color: #94A3B8;
    color: #0F172A;
}}
QPushButton:pressed {{
    background-color: #F1F5F9;
    border-color: #64748B;
}}
QPushButton:disabled {{
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}}

QPushButton[variant="primary"] {{
    background-color: {COLORES["primary"]};
    color: #FFFFFF;
    border: 1px solid #0087BD;
    font-weight: 700;
}}
QPushButton[variant="primary"]:hover {{
    background-color: {COLORES["primary_dark"]};
    border-color: #006094;
}}
QPushButton[variant="primary"]:pressed {{
    background-color: #005F94;
}}
QPushButton[variant="primary"]:disabled {{
    background-color: #BAE6FD;
    color: #FFFFFF;
    border: none;
}}

QPushButton[variant="secondary"] {{
    background-color: {COLORES["secondary"]};
    color: white;
    border: 1px solid #008A44;
    font-weight: 700;
}}
QPushButton[variant="secondary"]:hover {{ background-color: #008A44; }}
QPushButton[variant="secondary"]:pressed {{ background-color: #007538; }}

QPushButton[variant="ghost"] {{
    background-color: #FFFFFF;
    color: {COLORES["primary_dark"]};
    border: 1px solid #BAE6FD;
    font-weight: 600;
}}
QPushButton[variant="ghost"]:hover {{
    background-color: #F0F9FF;
    border-color: {COLORES["primary"]};
    color: {COLORES["primary_dark"]};
}}
QPushButton[variant="ghost"]:pressed {{
    background-color: #E0F2FE;
}}

QPushButton[variant="danger"] {{
    background-color: #EF4444;
    color: white;
    border: 1px solid #DC2626;
    font-weight: 600;
}}
QPushButton[variant="danger"]:hover {{ background-color: #DC2626; }}
QPushButton[variant="danger"]:pressed {{ background-color: #B91C1C; }}

/* Entradas */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1.5px solid #CBD5E1;
    border-radius: {BORDES["md"]}px;
    padding: 7px 10px;
    selection-background-color: #BAE6FD;
    selection-color: #0F172A;
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
    border-color: #94A3B8;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 1.5px solid {COLORES["primary"]};
    background-color: #FFFFFF;
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
QComboBox:disabled, QDateEdit:disabled {{
    background-color: #F8FAFC;
    color: #94A3B8;
    border-color: #E2E8F0;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
    padding-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: {BORDES["md"]}px;
    selection-background-color: #E0F2FE;
    selection-color: #0F172A;
    outline: none;
    padding: 4px;
}}

/* Tablas */
QTableWidget, QTableView {{
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    color: #1E293B;
    border: 1px solid #E2E8F0;
    border-radius: {BORDES["lg"]}px;
    gridline-color: #F1F5F9;
    selection-background-color: #E0F2FE;
    selection-color: #0F172A;
}}
QTableWidget::item, QTableView::item {{
    padding: 6px 8px;
    border-bottom: 1px solid #F1F5F9;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: #E0F2FE;
    color: #0369A1;
    font-weight: 500;
}}
QTableWidget::item:hover, QTableView::item:hover {{
    background-color: #F0F9FF;
}}
QHeaderView::section {{
    background-color: #F8FAFC;
    color: #475569;
    border: none;
    border-bottom: 1px solid #CBD5E1;
    padding: 10px 10px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.3px;
}}
QHeaderView::section:hover {{
    background-color: #F1F5F9;
    color: #0F172A;
}}
QTableCornerButton::section {{ background-color: #F8FAFC; border: none; border-bottom: 1px solid #CBD5E1; }}

/* Widgets embebidos en celdas de tabla */
QTableWidget QComboBox, QTableView QComboBox {{
    padding: 3px 8px;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    min-height: 24px;
    font-size: 12px;
    background-color: #FFFFFF;
}}
QTableWidget QPushButton, QTableView QPushButton {{
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    min-height: 24px;
}}

/* Pestañas */
QTabWidget::pane {{
    border: 1px solid #E2E8F0;
    border-radius: {BORDES["lg"]}px;
    background-color: #FFFFFF;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: #64748B;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: {BORDES["md"]}px;
    border-top-right-radius: {BORDES["md"]}px;
    font-weight: 500;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {COLORES["primary_dark"]};
    font-weight: 700;
    border-bottom: 3px solid {COLORES["primary"]};
    background: #FFFFFF;
}}
QTabBar::tab:hover:!selected {{
    color: #1E293B;
    background: #F1F5F9;
}}

/* Checkboxes */
QCheckBox {{ spacing: 8px; color: #1E293B; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 4px;
    border: 1.5px solid #CBD5E1; background: #FFFFFF;
}}
QCheckBox::indicator:hover {{
    border-color: {COLORES["primary"]};
}}
QCheckBox::indicator:checked {{
    background: {COLORES["primary"]};
    border-color: {COLORES["primary"]};
}}

/* RadioButtons */
QRadioButton {{ spacing: 8px; color: #1E293B; font-weight: 500; }}
QRadioButton::indicator {{
    width: 18px; height: 18px; border-radius: 9px;
    border: 1.5px solid #CBD5E1; background: #FFFFFF;
}}
QRadioButton::indicator:hover {{ border-color: {COLORES["primary"]}; }}
QRadioButton::indicator:checked {{
    background: {COLORES["primary"]};
    border-color: {COLORES["primary"]};
}}

/* GroupBox */
QGroupBox {{
    border: 1px solid #E2E8F0; border-radius: {BORDES["lg"]}px;
    margin-top: 14px; padding: 14px; font-weight: 600;
    background-color: #FFFFFF;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 14px; padding: 0 6px;
    color: #334155; font-size: 13px; font-weight: 700;
}}

/* Menús y tooltips */
QMenuBar {{ background-color: #FFFFFF; color: #1E293B; border-bottom: 1px solid #E2E8F0; }}
QMenuBar::item:selected {{ background-color: #F1F5F9; }}
QMenu {{
    background-color: #FFFFFF; color: #1E293B;
    border: 1px solid #CBD5E1; border-radius: {BORDES["md"]}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{ background-color: #E0F2FE; color: #0284C7; }}
QToolTip {{
    background-color: #0F172A; color: #FFFFFF;
    border: none; border-radius: 6px; padding: 6px 10px;
    font-size: 12px;
}}

/* Scrollbars delgadas, redondeadas y modernas */
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1; border-radius: 4px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar:horizontal {{
    background: transparent; height: 8px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD5E1; border-radius: 4px; min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: #94A3B8; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
