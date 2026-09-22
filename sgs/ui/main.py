from __future__ import annotations

import sys
import traceback

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QMessageBox

from sgs.ui import theme
from sgs.ui.login_window import LoginWindow
from sgs.ui.main_window import MainWindow


def _paleta_clara() -> QPalette:
    """Fija explícitamente los colores base de Qt en modo claro — evita que
    la app herede un tema oscuro del sistema operativo (causa del fondo
    negro visto en la primera captura)."""
    paleta = QPalette()
    paleta.setColor(QPalette.ColorRole.Window, QColor(theme.BG_APP))
    paleta.setColor(QPalette.ColorRole.WindowText, QColor(theme.TEXT_PRIMARY))
    paleta.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    paleta.setColor(QPalette.ColorRole.Text, QColor(theme.TEXT_PRIMARY))
    paleta.setColor(QPalette.ColorRole.Button, QColor(theme.BG_CARD))
    paleta.setColor(QPalette.ColorRole.ButtonText, QColor(theme.TEXT_PRIMARY))
    return paleta


def main() -> int:
    from sgs.ui.assets_loader import assets

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Registrar las fuentes Inter (si están en sgs/assets/fuentes/); es
    # tolerante a que aún no existan — en ese caso el stylesheet cae a las
    # alternativas del sistema declaradas en FONT_STACK.
    assets.cargar_fuentes()
    app.setPalette(_paleta_clara())
    app.setStyleSheet(theme.STYLESHEET_APP)

    ventanas: dict[str, object] = {}

    def abrir_principal(usuario_id: int, usuario: str, rol: str) -> None:
        from sgs.app import contexto_sesion

        contexto_sesion.set_actor(usuario_id, usuario, rol)
        try:
            principal = MainWindow(rol=rol, nombre_usuario=usuario, usuario_id=usuario_id)
        except Exception as exc:
            traceback.print_exc()
            login = ventanas.get("login")
            if login is not None:
                QMessageBox.critical(
                    login,
                    "No se pudo abrir el sistema",
                    f"La sesión fue válida, pero no se pudo cargar la ventana principal:\n{exc}",
                )
            return
        ventanas["principal"] = principal
        principal.logout_solicitado.connect(mostrar_login)
        principal.show()
        login = ventanas.pop("login", None)
        if login:
            login.close()

    def mostrar_login() -> None:
        from sgs.app import contexto_sesion

        contexto_sesion.limpiar()
        principal = ventanas.pop("principal", None)
        if principal:
            principal.close()
        login = LoginWindow()
        ventanas["login"] = login
        login.login_exitoso.connect(abrir_principal)
        login.show()

    mostrar_login()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())