"""
Ejecuta operaciones pesadas (leer Excel, clasificar, guardar miles de
filas, armar DataFrames) en un hilo de fondo para que la ventana NO se
congele. Muestra un overlay de carga sobre el widget mientras corre y
entrega el resultado (o el error) al hilo principal por callbacks.

Uso típico:
    ejecutar_en_fondo(
        self,
        lambda: casos_de_uso.confirmar_importacion_sac(ruta, nombre, uid),
        on_ok=self._al_terminar,
        on_error=self._al_fallar,
        mensaje="Guardando importación…",
    )

En pruebas (variable de entorno SGS_TAREAS_SINCRONAS=1, o parámetro
`sincrono=True`) la función se ejecuta en el momento, sin hilo, para no
depender del bucle de eventos.
"""
from __future__ import annotations

import os
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal

from sgs.ui.widgets.overlay_carga import OverlayCarga

# Referencias vivas a controladores en curso (evita que el GC los elimine
# antes de terminar).
_EN_CURSO: list[_TareaFondo] = []


def _modo_sincrono(sincrono: bool | None) -> bool:
    if sincrono is not None:
        return sincrono
    return os.environ.get("SGS_TAREAS_SINCRONAS") == "1"


class _Worker(QObject):
    """Vive en el hilo de fondo: ejecuta la función y emite el resultado."""

    resultado = Signal(object)
    error = Signal(object)

    def __init__(self, funcion: Callable):
        super().__init__()
        self._funcion = funcion

    def ejecutar(self) -> None:
        try:
            valor = self._funcion()
        except Exception as exc:  # noqa: BLE001 — se reenvía al hilo principal
            self.error.emit(exc)
        else:
            self.resultado.emit(valor)


class _TareaFondo(QObject):
    """Controlador que vive en el HILO PRINCIPAL (mismo que `widget`). Sus
    slots reciben las señales del worker por conexión en cola, así que se
    ejecutan siempre en el hilo principal — nunca en el de fondo."""

    def __init__(self, widget, funcion, on_ok, on_error, mensaje):
        super().__init__(widget)  # padre = widget → afinidad al hilo principal
        self._on_ok = on_ok
        self._on_error = on_error

        self._overlay = OverlayCarga(widget)
        self._overlay.mostrar(mensaje)

        self._hilo = QThread()
        self._worker = _Worker(funcion)
        self._worker.moveToThread(self._hilo)

        self._worker.resultado.connect(self._al_ok)
        self._worker.error.connect(self._al_error)
        self._hilo.started.connect(self._worker.ejecutar)
        self._hilo.finished.connect(self._al_finalizar_hilo)

        _EN_CURSO.append(self)
        self._hilo.start()

    def _al_ok(self, valor) -> None:
        self._overlay.ocultar()
        self._hilo.quit()
        try:
            self._on_ok(valor)
        finally:
            pass

    def _al_error(self, exc) -> None:
        self._overlay.ocultar()
        self._hilo.quit()
        if self._on_error is not None:
            self._on_error(exc)

    def _al_finalizar_hilo(self) -> None:
        self._overlay.deleteLater()
        self._worker.deleteLater()
        self._hilo.deleteLater()
        if self in _EN_CURSO:
            _EN_CURSO.remove(self)


def ejecutar_en_fondo(
    widget,
    funcion: Callable,
    on_ok: Callable[[object], None],
    on_error: Callable[[Exception], None] | None = None,
    mensaje: str = "Procesando…",
    sincrono: bool | None = None,
) -> None:
    """Corre `funcion()` en segundo plano mostrando un overlay sobre
    `widget`. Al terminar oculta el overlay y llama `on_ok(resultado)` o
    `on_error(exc)` en el hilo principal."""

    # Modo síncrono (tests): ejecutar directo sin hilo ni overlay.
    if _modo_sincrono(sincrono):
        try:
            valor = funcion()
        except Exception as exc:  # noqa: BLE001
            if on_error is not None:
                on_error(exc)
            return
        on_ok(valor)
        return

    _TareaFondo(widget, funcion, on_ok, on_error, mensaje)
