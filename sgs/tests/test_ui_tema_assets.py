"""Verifica el sistema de diseño: alias de tema retrocompatibles y que el
AssetsLoader tolera la ausencia de archivos."""
from PySide6.QtGui import QIcon, QPixmap

from sgs.ui import theme
from sgs.ui.assets_loader import AssetsLoader, assets


def test_theme_mantiene_alias_de_compatibilidad():
    # Los nombres antiguos deben seguir existiendo (no romper pantallas).
    for nombre in (
        "BG_APP", "BG_CARD", "BORDER", "TEXT_PRIMARY", "TEXT_SECONDARY",
        "ACCENT", "ACCENT_LIGHT", "SEMAFORO_ROJO", "SEMAFORO_VERDE",
        "SEMAFORO_AMARILLO", "SEMAFORO_COLORES", "FONT_FAMILY", "RADIUS",
        "STYLESHEET_APP",
    ):
        assert hasattr(theme, nombre), f"Falta el alias {nombre}"


def test_theme_nuevos_tokens_presentes():
    assert theme.COLORES["primary"] == "#00A0DF"
    assert set(theme.COLORES_SEMAFORO) == {"VERDE", "AMARILLO", "ROJO", "GRIS"}
    assert "display_large" in theme.TIPOGRAFIA
    assert theme.ESPACIADO["md"] == 16
    assert theme.BORDES["full"] == 999


def test_alias_apuntan_a_los_nuevos_valores():
    assert theme.ACCENT == theme.COLORES["primary"]
    assert theme.BG_APP == theme.COLORES["background"]
    assert theme.SEMAFORO_ROJO == theme.COLORES_SEMAFORO["ROJO"]


def test_assets_loader_tolera_archivos_faltantes(tmp_path):
    # Base apuntando a una carpeta vacía: nada existe, pero no revienta.
    loader = AssetsLoader(base=tmp_path)
    assert loader.cargar_fuentes() == []
    assert isinstance(loader.logo_principal(), QPixmap)
    assert loader.logo_principal().isNull()
    assert isinstance(loader.icono("inexistente"), QIcon)


def test_assets_instancia_compartida_no_revienta():
    # La instancia real puede no tener assets todavía; debe seguir viva.
    assert isinstance(assets.logo_icono(), QPixmap)
    assert isinstance(assets.cargar_fuentes(), list)
