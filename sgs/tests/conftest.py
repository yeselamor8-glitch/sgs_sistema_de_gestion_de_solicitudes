"""Configuración compartida de pruebas.

Activa el modo SÍNCRONO de las tareas en segundo plano (ejecutar_en_fondo):
en pruebas las operaciones se ejecutan en el momento, sin QThread ni
overlay, para que los tests que llaman a los métodos de la UI reciban el
resultado de inmediato (igual que antes de introducir los hilos)."""
import os

os.environ.setdefault("SGS_TAREAS_SINCRONAS", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])
