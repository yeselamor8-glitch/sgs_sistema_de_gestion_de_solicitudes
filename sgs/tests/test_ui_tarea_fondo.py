from PySide6.QtWidgets import QApplication, QWidget

from sgs.ui.widgets.overlay_carga import OverlayCarga
from sgs.ui.widgets.tarea_fondo import ejecutar_en_fondo


def _app():
    return QApplication.instance() or QApplication([])


def test_ejecutar_en_fondo_sincrono_entrega_resultado():
    app = _app()
    padre = QWidget()
    recibido = {}
    ejecutar_en_fondo(
        padre,
        lambda: 2 + 3,
        on_ok=lambda r: recibido.setdefault("ok", r),
        on_error=lambda e: recibido.setdefault("err", e),
        sincrono=True,
    )
    assert recibido == {"ok": 5}
    app.processEvents()


def test_ejecutar_en_fondo_sincrono_captura_error():
    app = _app()
    padre = QWidget()
    recibido = {}

    def _falla():
        raise ValueError("boom")

    ejecutar_en_fondo(
        padre,
        _falla,
        on_ok=lambda r: recibido.setdefault("ok", r),
        on_error=lambda e: recibido.setdefault("err", str(e)),
        sincrono=True,
    )
    assert recibido == {"err": "boom"}
    app.processEvents()


def test_ejecutar_en_fondo_real_no_se_cuelga():
    # Ejecuta en un QThread REAL (sincrono=False) y espera el resultado con
    # un event loop acotado. Si hubiera deadlock en la limpieza del hilo,
    # este test agotaría el timeout y fallaría.
    from PySide6.QtCore import QEventLoop, QTimer

    app = _app()
    padre = QWidget()
    recibido = {}
    loop = QEventLoop()

    def _ok(r):
        recibido["ok"] = r
        loop.quit()

    ejecutar_en_fondo(
        padre,
        lambda: sum(range(1000)),
        on_ok=_ok,
        on_error=lambda e: (recibido.setdefault("err", e), loop.quit()),
        mensaje="Trabajando…",
        sincrono=False,
    )

    QTimer.singleShot(5000, loop.quit)  # tope de seguridad
    loop.exec()
    assert recibido.get("ok") == sum(range(1000))
    app.processEvents()


def test_overlay_carga_muestra_y_oculta():
    app = _app()
    padre = QWidget()
    padre.resize(400, 300)
    overlay = OverlayCarga(padre)
    assert overlay.isHidden()

    overlay.mostrar("Procesando prueba…")
    assert not overlay.isHidden()

    overlay.ocultar()
    assert overlay.isHidden()
    app.processEvents()
