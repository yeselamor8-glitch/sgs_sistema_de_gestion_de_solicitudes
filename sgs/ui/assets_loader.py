"""
Carga centralizada de recursos visuales (logos, iconos, fuentes) desde
sgs/assets/. Es tolerante a que los archivos aún no existan: si falta un
recurso, devuelve un pixmap/icono vacío en vez de reventar, para que la
app funcione mientras se van agregando los assets institucionales.

Uso:
    from sgs.ui.assets_loader import assets
    assets.cargar_fuentes()               # una vez, al iniciar la app
    label.setPixmap(assets.logo_principal())
    boton.setIcon(assets.icono("campana", 20))
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QFontDatabase, QIcon, QPixmap

_BASE = Path(__file__).resolve().parent.parent / "assets"

# Fuentes esperadas (los 4 pesos de Inter). Si alguno falta, se ignora.
_FUENTES = [
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
]


class AssetsLoader:
    """Resuelve rutas y carga pixmaps/iconos/fuentes con caché."""

    def __init__(self, base: Path = _BASE):
        self._base = base

    # ------------------------------------------------------------------
    def ruta(self, *partes: str) -> Path:
        """Ruta absoluta a un recurso dentro de sgs/assets/."""
        return self._base.joinpath(*partes)

    def existe(self, *partes: str) -> bool:
        return self.ruta(*partes).is_file()

    # ------------------------------------------------------------------
    @lru_cache(maxsize=128)
    def pixmap(self, *partes: str) -> QPixmap:
        """QPixmap del recurso; vacío si no existe (no lanza)."""
        ruta = self.ruta(*partes)
        if not ruta.is_file():
            return QPixmap()
        return QPixmap(str(ruta))

    @lru_cache(maxsize=128)
    def icono(self, nombre: str, tamano: int = 24) -> QIcon:
        """QIcon desde images/iconos/<nombre>.svg (o .png). Vacío si falta.

        `tamano` se conserva en la clave de caché para futuros usos que
        rendericen a un tamaño concreto."""
        for carpeta in (("images", "iconos"), ("images",), ("iconos",)):
            for ext in (".svg", ".png"):
                ruta = self.ruta(*carpeta, f"{nombre}{ext}")
                if ruta.is_file():
                    return QIcon(str(ruta))
        return QIcon()

    # ------------------------------------------------------------------
    def _primer_pixmap(self, candidatos: list[tuple[str, ...]]) -> QPixmap:
        """Devuelve el primer recurso que exista entre varias rutas
        candidatas (tolera que los assets estén en images/ o images/logo/)."""
        for partes in candidatos:
            if self.existe(*partes):
                return self.pixmap(*partes)
        return QPixmap()

    def logo_principal(self) -> QPixmap:
        return self._primer_pixmap([
            ("images", "logo", "logo_principal.png"),
            ("images", "logo_principal.png"),
        ])

    def logo_icono(self) -> QPixmap:
        return self._primer_pixmap([
            ("images", "logo", "logo_icono.png"),
            ("images", "logo_icono.png"),
        ])

    # ------------------------------------------------------------------
    def cargar_fuentes(self) -> list[str]:
        """Registra las fuentes Inter en Qt. Devuelve las familias
        efectivamente cargadas (vacío si no hay archivos todavía).
        Seguro de llamar aunque no exista la carpeta."""
        familias: list[str] = []
        carpeta = self.ruta("fuentes")
        if not carpeta.is_dir():
            return familias
        for nombre in _FUENTES:
            archivo = carpeta / nombre
            if not archivo.is_file():
                continue
            font_id = QFontDatabase.addApplicationFont(str(archivo))
            if font_id != -1:
                familias.extend(QFontDatabase.applicationFontFamilies(font_id))
        vistas: list[str] = []
        for f in familias:
            if f not in vistas:
                vistas.append(f)
        return vistas


# Instancia compartida — importar `assets` desde aquí.
assets = AssetsLoader()
