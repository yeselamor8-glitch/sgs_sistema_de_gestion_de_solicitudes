from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgs.ui import theme
from sgs.ui.widgets.dialogo_usuario import DialogoUsuario

class ConfiguracionPage(QWidget):
    """Centro de configuración del sistema (sección 26 del documento
    funcional). Exclusivo del administrador."""

    permisos_cambiados = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        titulo = QLabel("Configuración")
        titulo.setProperty("role", "title")
        layout.addWidget(titulo)

        tabs = QTabWidget()
        tabs.addTab(self._tab_usuarios(), "Usuarios")
        tabs.addTab(self._tab_roles_permisos(), "Roles y permisos")
        tabs.addTab(self._tab_procesos(), "Procesos")
        tabs.addTab(self._tab_asignacion(), "Asignación de funcionarios")
        tabs.addTab(self._tab_tiempos(), "Tiempos de respuesta")
        tabs.addTab(self._tab_semaforizacion(), "Semaforización")
        tabs.addTab(self._tab_reglas_clasificacion(), "Reglas de clasificación")
        tabs.addTab(self._tab_parametros_generales(), "Parámetros generales")
        self.tabs = tabs
        tabs.currentChanged.connect(self._cambio_tab)
        layout.addWidget(tabs)

    def _cambio_tab(self, indice: int) -> None:
        texto = self.tabs.tabText(indice)
        if texto == "Roles y permisos":
            self._cargar_usuarios()
            self._cargar_permisos()
        elif texto == "Asignación de funcionarios":
            self._cargar_usuarios()
            self._cargar_procesos()
            self._cargar_asignaciones()

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------
    def _tab_usuarios(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        fila_botones = QHBoxLayout()
        boton_crear = QPushButton("+ Crear usuario")
        boton_crear.setProperty("variant", "primary")
        boton_crear.clicked.connect(self._crear_usuario)
        boton_estado = QPushButton("Activar/Desactivar seleccionado")
        boton_estado.setProperty("variant", "ghost")
        boton_estado.clicked.connect(self._alternar_estado_usuario)
        boton_reset = QPushButton("Restablecer contraseña")
        boton_reset.setProperty("variant", "ghost")
        boton_reset.clicked.connect(self._restablecer_password)
        boton_editar = QPushButton("Editar usuario")
        boton_editar.setProperty("variant", "ghost")
        boton_editar.clicked.connect(self._editar_usuario)
        fila_botones.addWidget(boton_crear)
        fila_botones.addWidget(boton_estado)
        fila_botones.addWidget(boton_reset)
        fila_botones.addWidget(boton_editar)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.tabla_usuarios = QTableWidget()
        self.tabla_usuarios.setColumnCount(5)
        self.tabla_usuarios.setHorizontalHeaderLabels(["Código SAC", "Usuario", "Nombre", "Rol", "Activo"])
        self.tabla_usuarios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_usuarios.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_usuarios.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla_usuarios)

        self.lbl_usuarios_estado = QLabel("")
        self.lbl_usuarios_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_usuarios_estado)

        self._usuarios_actuales: list[dict] = []
        self._cargar_usuarios()
        return pagina

    def _cargar_usuarios(self) -> None:
        try:
            from sgs.app.casos_de_uso import listar_usuarios

            self._usuarios_actuales = listar_usuarios()
            self.lbl_usuarios_estado.setText("")
        except Exception:
            self._usuarios_actuales = []
            self.lbl_usuarios_estado.setText(
                "No se pudo conectar con la base de datos — la lista de usuarios estará vacía hasta conectar."
            )
        self._refrescar_tabla_usuarios()

    def _refrescar_tabla_usuarios(self) -> None:
        self.tabla_usuarios.setRowCount(len(self._usuarios_actuales))
        for i, u in enumerate(self._usuarios_actuales):
            self.tabla_usuarios.setItem(i, 0, QTableWidgetItem(u.get("codigo_sac") or ""))
            self.tabla_usuarios.setItem(i, 1, QTableWidgetItem(u["username"]))
            self.tabla_usuarios.setItem(i, 2, QTableWidgetItem(u["nombre"]))
            self.tabla_usuarios.setItem(i, 3, QTableWidgetItem(u["rol"]))
            self.tabla_usuarios.setItem(i, 4, QTableWidgetItem("Sí" if u["activo"] else "No"))

    def _crear_usuario(self) -> None:
        dialogo = DialogoUsuario(parent=self)
        if not dialogo.exec():
            return
        datos = dialogo.datos()
        if not datos["username"] or not datos["password"]:
            QMessageBox.warning(self, "Datos incompletos", "Usuario y contraseña son obligatorios.")
            return
        try:
            from sgs.app.casos_de_uso import crear_usuario

            crear_usuario(datos["codigo_sac"], datos["username"], datos["nombre"], datos["rol"], datos["password"])
            self._cargar_usuarios()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo crear el usuario", str(exc))

    def _usuario_seleccionado(self) -> dict | None:
        fila = self.tabla_usuarios.currentRow()
        if fila < 0 or fila >= len(self._usuarios_actuales):
            return None
        return self._usuarios_actuales[fila]

    def _alternar_estado_usuario(self) -> None:
        usuario = self._usuario_seleccionado()
        if not usuario:
            return
        try:
            from sgs.app.casos_de_uso import cambiar_estado_usuario

            cambiar_estado_usuario(usuario["id"], not usuario["activo"])
            self._cargar_usuarios()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo actualizar", str(exc))

    def _restablecer_password(self) -> None:
        usuario = self._usuario_seleccionado()
        if not usuario:
            return
        dialogo = DialogoUsuario(usuario, parent=self)
        dialogo.setWindowTitle(f"Restablecer contraseña — {usuario['username']}")
        dialogo.campo_username.setEnabled(False)
        dialogo.campo_codigo_sac.setEnabled(False)
        dialogo.campo_nombre.setEnabled(False)
        dialogo.combo_rol.setEnabled(False)
        if not dialogo.exec():
            return
        nueva = dialogo.datos()["password"]
        if not nueva:
            return
        try:
            from sgs.app.casos_de_uso import restablecer_password

            restablecer_password(usuario["id"], nueva)
            QMessageBox.information(self, "Listo", "Contraseña actualizada.")
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo restablecer", str(exc))

    def _editar_usuario(self) -> None:
        usuario = self._usuario_seleccionado()
        if not usuario:
            return
        dialogo = DialogoUsuario(usuario, parent=self)
        dialogo.setWindowTitle(f"Editar usuario — {usuario['username']}")
        dialogo.campo_username.setEnabled(False)
        if not dialogo.exec():
            return
        datos = dialogo.datos()
        try:
            from sgs.app.casos_de_uso import actualizar_usuario

            actualizar_usuario(usuario["id"], datos["nombre"], datos["rol"], datos["codigo_sac"])
            self._cargar_usuarios()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo actualizar", str(exc))

    # ------------------------------------------------------------------
    # Roles y permisos
    # ------------------------------------------------------------------
    def _tab_roles_permisos(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        info = QLabel(
            "Los permisos son independientes del rol. Un funcionario puede tener un permiso especial "
            "(por ejemplo, Importar SAC) sin convertirse en administrador."
        )
        info.setWordWrap(True)
        info.setProperty("role", "secondary")
        layout.addWidget(info)

        self.tabla_permisos = QTableWidget()
        self.tabla_permisos.setColumnCount(2)
        self.tabla_permisos.setHorizontalHeaderLabels(["Usuario", "Permiso: Importar SAC"])
        self.tabla_permisos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla_permisos)
        self.lbl_permisos_estado = QLabel("")
        self.lbl_permisos_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_permisos_estado)

        boton_actualizar = QPushButton("Actualizar lista")
        boton_actualizar.setProperty("variant", "ghost")
        boton_actualizar.clicked.connect(self._cargar_permisos)
        layout.addWidget(boton_actualizar)

        self._cargar_usuarios()
        self._cargar_permisos()
        return pagina

    def _cargar_permisos(self) -> None:
        usuarios = [u for u in (self._usuarios_actuales or []) if u["rol"] == "FUNCIONARIO"]
        self.tabla_permisos.setRowCount(len(usuarios))
        self.lbl_permisos_estado.setText("" if usuarios else "No hay funcionarios para configurar permisos.")
        for i, u in enumerate(usuarios):
            self.tabla_permisos.setItem(i, 0, QTableWidgetItem(u["nombre"]))
            check = QCheckBox()
            try:
                from sgs.app.casos_de_uso import usuario_tiene_permiso

                check.setChecked(usuario_tiene_permiso(u["id"], "importar_sac"))
            except Exception:
                check.setChecked(False)
            check.stateChanged.connect(
                lambda estado, usuario_id=u["id"]: self._guardar_permiso_importar_sac(usuario_id, estado)
            )
            self.tabla_permisos.setCellWidget(i, 1, check)

    def _guardar_permiso_importar_sac(self, usuario_id: int, estado: int) -> None:
        try:
            from sgs.app.casos_de_uso import establecer_permiso

            establecer_permiso(usuario_id, "importar_sac", bool(estado))
            self.permisos_cambiados.emit()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo guardar el permiso", str(exc))

    # ------------------------------------------------------------------
    # Procesos
    # ------------------------------------------------------------------
    def _tab_procesos(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        fila_botones = QHBoxLayout()
        boton_agregar = QPushButton("+ Agregar proceso")
        boton_agregar.setProperty("variant", "primary")
        boton_agregar.clicked.connect(self._crear_proceso)
        boton_quitar = QPushButton("Activar/Desactivar seleccionado")
        boton_quitar.setProperty("variant", "ghost")
        boton_quitar.clicked.connect(self._alternar_estado_proceso)
        boton_actualizar = QPushButton("Actualizar lista")
        boton_actualizar.setProperty("variant", "ghost")
        boton_actualizar.clicked.connect(self._cargar_procesos)
        fila_botones.addWidget(boton_agregar)
        fila_botones.addWidget(boton_quitar)
        fila_botones.addWidget(boton_actualizar)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.tabla_procesos = QTableWidget()
        self.tabla_procesos.setColumnCount(3)
        self.tabla_procesos.setHorizontalHeaderLabels(["Nombre", "Descripción", "Activo"])
        self.tabla_procesos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_procesos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_procesos.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(self.tabla_procesos)

        self.lbl_procesos_estado = QLabel("")
        self.lbl_procesos_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_procesos_estado)

        self._procesos_actuales: list[dict] = []
        self._cargar_procesos()
        return pagina

    def _cargar_procesos(self) -> None:
        try:
            from sgs.app.casos_de_uso import listar_procesos

            self._procesos_actuales = listar_procesos()
            self.lbl_procesos_estado.setText(f"{len(self._procesos_actuales)} procesos.")
        except Exception:
            self._procesos_actuales = []
            self.lbl_procesos_estado.setText("No se pudo conectar con la base de datos.")
        self.tabla_procesos.setRowCount(len(self._procesos_actuales))
        for i, p in enumerate(self._procesos_actuales):
            self.tabla_procesos.setItem(i, 0, QTableWidgetItem(p["nombre"]))
            self.tabla_procesos.setItem(i, 1, QTableWidgetItem(p["descripcion"]))
            self.tabla_procesos.setItem(i, 2, QTableWidgetItem("Sí" if p["activo"] else "No"))

    def _crear_proceso(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        nombre, ok = QInputDialog.getText(self, "Nuevo proceso", "Nombre del proceso (identificador):")
        if not ok or not nombre.strip():
            return
        descripcion, _ = QInputDialog.getText(self, "Nuevo proceso", "Descripción:")
        try:
            from sgs.app.casos_de_uso import crear_proceso

            crear_proceso(nombre.strip(), descripcion.strip())
            self._cargar_procesos()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo crear el proceso", str(exc))

    def _alternar_estado_proceso(self) -> None:
        fila = self.tabla_procesos.currentRow()
        if fila < 0 or fila >= len(self._procesos_actuales):
            return
        proceso = self._procesos_actuales[fila]
        try:
            from sgs.app.casos_de_uso import cambiar_estado_proceso

            cambiar_estado_proceso(proceso["id"], not proceso["activo"])
            self._cargar_procesos()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo actualizar", str(exc))

    # ------------------------------------------------------------------
    # Asignación de funcionarios a procesos
    # ------------------------------------------------------------------
    def _tab_asignacion(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        info = QLabel("Qué proceso(s) puede gestionar cada funcionario. Selecciona una fila y pulsa editar, o haz doble clic.")
        info.setProperty("role", "secondary")
        layout.addWidget(info)

        self.tabla_asignacion = QTableWidget()
        self.tabla_asignacion.setColumnCount(2)
        self.tabla_asignacion.setHorizontalHeaderLabels(["Funcionario", "Procesos asignados"])
        self.tabla_asignacion.horizontalHeader().setStretchLastSection(True)
        self.tabla_asignacion.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_asignacion.cellDoubleClicked.connect(self._editar_asignacion)
        layout.addWidget(self.tabla_asignacion)
        self.lbl_asignacion_estado = QLabel("")
        self.lbl_asignacion_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_asignacion_estado)

        boton_actualizar = QPushButton("Actualizar lista")
        boton_actualizar.setProperty("variant", "ghost")
        boton_actualizar.clicked.connect(self._cargar_asignaciones)
        layout.addWidget(boton_actualizar)
        boton_editar = QPushButton("Editar asignación")
        boton_editar.clicked.connect(self._editar_asignacion_seleccionada)
        layout.addWidget(boton_editar)

        self._cargar_asignaciones()
        return pagina

    def _cargar_asignaciones(self) -> None:
        usuarios = [u for u in (self._usuarios_actuales or []) if u["rol"] == "FUNCIONARIO"]
        self.tabla_asignacion.setRowCount(len(usuarios))
        self.lbl_asignacion_estado.setText("" if usuarios else "No hay funcionarios para asignar procesos.")
        for i, u in enumerate(usuarios):
            self.tabla_asignacion.setItem(i, 0, QTableWidgetItem(u["nombre"]))
            self.tabla_asignacion.item(i, 0).setData(256, u["id"])  # Qt.UserRole == 256
            texto = self._texto_procesos_de(u["id"])
            self.tabla_asignacion.setItem(i, 1, QTableWidgetItem(texto))

    def _texto_procesos_de(self, usuario_id: int) -> str:
        try:
            from sgs.app.casos_de_uso import listar_procesos_de_funcionario

            ids_asignados = set(listar_procesos_de_funcionario(usuario_id))
            nombres = [p["nombre"] for p in self._procesos_actuales if p["id"] in ids_asignados]
            return ", ".join(nombres) if nombres else "(sin asignar)"
        except Exception:
            return "(no se pudo consultar)"

    def _editar_asignacion(self, fila: int, _columna: int) -> None:
        item = self.tabla_asignacion.item(fila, 0)
        usuario_id = item.data(256)
        try:
            from sgs.app.casos_de_uso import listar_procesos_de_funcionario

            asignados_actuales = set(listar_procesos_de_funcionario(usuario_id))
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo consultar", str(exc))
            return

        dialogo = QDialog(self)
        dialogo.setWindowTitle(f"Procesos de {item.text()}")
        dialogo.resize(340, 420)
        layout = QVBoxLayout(dialogo)
        lista = QListWidget()
        for p in self._procesos_actuales:
            elemento = QListWidgetItem(p["nombre"])
            elemento.setFlags(elemento.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            elemento.setCheckState(Qt.CheckState.Checked if p["id"] in asignados_actuales else Qt.CheckState.Unchecked)
            elemento.setData(256, p["id"])
            lista.addItem(elemento)
        layout.addWidget(lista)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)

        if not dialogo.exec():
            return

        nuevos_ids = [
            lista.item(i).data(256)
            for i in range(lista.count())
            if lista.item(i).checkState() == Qt.CheckState.Checked
        ]
        try:
            from sgs.app.casos_de_uso import asignar_procesos_a_funcionario

            asignar_procesos_a_funcionario(usuario_id, nuevos_ids)
            self._cargar_asignaciones()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo guardar", str(exc))

    def _editar_asignacion_seleccionada(self) -> None:
        fila = self.tabla_asignacion.currentRow()
        if fila >= 0:
            self._editar_asignacion(fila, 0)

    # ------------------------------------------------------------------
    # Tiempos de respuesta
    # ------------------------------------------------------------------
    def _tab_tiempos(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        fila_proceso = QHBoxLayout()
        etiqueta_proceso = QLabel("Proceso:")
        self.combo_proceso_tiempos = QComboBox()
        self.combo_proceso_tiempos.setMinimumWidth(320)
        self.combo_proceso_tiempos.currentIndexChanged.connect(self._cargar_tiempos)
        fila_proceso.addWidget(etiqueta_proceso)
        fila_proceso.addWidget(self.combo_proceso_tiempos, stretch=1)
        layout.addLayout(fila_proceso)

        subtabs = QTabWidget()

        self.tabla_tiempos_solicitud = self._tabla_editable(
            ["Solicitud", "Motivo (vacío = general)", "Días hábiles"], []
        )
        subtabs.addTab(self._envolver_con_boton_agregar(self.tabla_tiempos_solicitud), "Por solicitud")

        self.tabla_tiempos_prioridad = self._tabla_editable(
            ["Prioridad del caso", "Días", "¿Día calendario?"], []
        )
        subtabs.addTab(self._envolver_con_boton_agregar(self.tabla_tiempos_prioridad), "Por prioridad")

        self.tabla_tiempos_eps = self._tabla_editable(["EPS", "Días hábiles"], [])
        subtabs.addTab(self._envolver_con_boton_agregar(self.tabla_tiempos_eps), "Por EPS")

        self.tabla_festivos = self._tabla_editable(["Fecha (yyyy-mm-dd)", "Descripción"], [])
        subtabs.addTab(self._envolver_con_boton_agregar(self.tabla_festivos), "Festivos")

        layout.addWidget(subtabs)

        fila_botones = QHBoxLayout()
        boton_actualizar = QPushButton("Actualizar desde la base de datos")
        boton_actualizar.setProperty("variant", "ghost")
        boton_actualizar.clicked.connect(self._cargar_tiempos)
        boton_guardar = QPushButton("Guardar tiempos de respuesta")
        boton_guardar.setProperty("variant", "primary")
        boton_guardar.clicked.connect(self._guardar_tiempos)
        fila_botones.addWidget(boton_actualizar)
        fila_botones.addWidget(boton_guardar)
        layout.addLayout(fila_botones)

        self.lbl_tiempos_estado = QLabel("")
        self.lbl_tiempos_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_tiempos_estado)

        self._cargar_procesos_en_combo()
        self._cargar_tiempos()
        return pagina

    def _cargar_procesos_en_combo(self) -> None:
        try:
            from sgs.app.casos_de_uso import listar_procesos

            procesos = [p for p in listar_procesos() if p["activo"] and p["id"] is not None]
            self._procesos_combo = {p["id"]: p["nombre"] for p in procesos}
            self.combo_proceso_tiempos.blockSignals(True)
            self.combo_proceso_tiempos.clear()
            for pid, nombre in self._procesos_combo.items():
                self.combo_proceso_tiempos.addItem(nombre, pid)
            self.combo_proceso_tiempos.blockSignals(False)
        except Exception:
            self._procesos_combo = {}
            self.combo_proceso_tiempos.blockSignals(True)
            self.combo_proceso_tiempos.clear()
            self.combo_proceso_tiempos.blockSignals(False)

    def _proceso_tiempos_id(self) -> int | None:
        return self.combo_proceso_tiempos.currentData()

    def _cargar_tiempos(self) -> None:
        try:
            from sgs.app.casos_de_uso import (
                listar_festivos,
                listar_reglas_tiempos_eps,
                listar_reglas_tiempos_prioridad,
                listar_reglas_tiempos_solicitud,
            )

            proceso_id = self._proceso_tiempos_id()
            if proceso_id is None:
                self._llenar_tabla(self.tabla_tiempos_solicitud, [])
                self._llenar_tabla(self.tabla_tiempos_eps, [])
            else:
                self._llenar_tabla(
                    self.tabla_tiempos_solicitud,
                    [
                        [r["solicitud"], r["motivo"], str(r["dias_habiles"])]
                        for r in listar_reglas_tiempos_solicitud(proceso_id)
                    ],
                )
                self._llenar_tabla(
                    self.tabla_tiempos_eps,
                    [[r["eps"], str(r["dias_habiles"])] for r in listar_reglas_tiempos_eps(proceso_id)],
                )
            self._llenar_tabla(
                self.tabla_tiempos_prioridad,
                [
                    [r["prioridad_caso"], str(r["dias_habiles"]), "Sí" if r["es_dia_calendario"] else "No"]
                    for r in listar_reglas_tiempos_prioridad()
                ],
            )
            self._llenar_tabla(
                self.tabla_festivos, [[f["fecha"], f["descripcion"]] for f in listar_festivos()]
            )
            self.lbl_tiempos_estado.setText("")
        except Exception:
            self.lbl_tiempos_estado.setText("No se pudo conectar con la base de datos — las tablas quedarán vacías.")
            self.lbl_tiempos_estado.setStyleSheet(f"color: {theme.SEMAFORO_AMARILLO};")

    @staticmethod
    def _llenar_tabla(tabla: QTableWidget, filas: list[list[str]]) -> None:
        tabla.setRowCount(len(filas))
        for i, fila in enumerate(filas):
            for j, valor in enumerate(fila):
                tabla.setItem(i, j, QTableWidgetItem(str(valor)))

    def _guardar_tiempos(self) -> None:
        try:
            from sgs.app.casos_de_uso import (
                guardar_festivos,
                guardar_reglas_tiempos_eps,
                guardar_reglas_tiempos_prioridad,
                guardar_reglas_tiempos_solicitud,
            )

            proceso_id = self._proceso_tiempos_id()
            if proceso_id is None:
                self.lbl_tiempos_estado.setStyleSheet(f"color: {theme.SEMAFORO_AMARILLO};")
                self.lbl_tiempos_estado.setText("Selecciona un proceso para guardar las reglas por solicitud y por EPS.")
                return
            guardar_reglas_tiempos_solicitud(proceso_id, self._leer_tabla_solicitud())
            guardar_reglas_tiempos_prioridad(self._leer_tabla_prioridad())
            guardar_reglas_tiempos_eps(proceso_id, self._leer_tabla_eps())
            guardar_festivos(self._leer_tabla_festivos())

            self.lbl_tiempos_estado.setStyleSheet(f"color: {theme.SEMAFORO_VERDE};")
            self.lbl_tiempos_estado.setText("✅ Guardado.")
        except Exception as exc:
            self.lbl_tiempos_estado.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            self.lbl_tiempos_estado.setText(f"No se pudo guardar: {exc}")

    def _leer_tabla_solicitud(self) -> list[dict]:
        filas = []
        for i in range(self.tabla_tiempos_solicitud.rowCount()):
            solicitud = self._texto_celda(self.tabla_tiempos_solicitud, i, 0)
            motivo = self._texto_celda(self.tabla_tiempos_solicitud, i, 1)
            dias = self._texto_celda(self.tabla_tiempos_solicitud, i, 2) or "0"
            filas.append({"solicitud": solicitud, "motivo": motivo, "dias_habiles": dias})
        return filas

    def _leer_tabla_prioridad(self) -> list[dict]:
        filas = []
        for i in range(self.tabla_tiempos_prioridad.rowCount()):
            prioridad = self._texto_celda(self.tabla_tiempos_prioridad, i, 0)
            dias = self._texto_celda(self.tabla_tiempos_prioridad, i, 1) or "0"
            calendario = self._texto_celda(self.tabla_tiempos_prioridad, i, 2).strip().lower() in ("sí", "si", "true")
            filas.append({"prioridad_caso": prioridad, "dias_habiles": dias, "es_dia_calendario": calendario})
        return filas

    def _leer_tabla_eps(self) -> list[dict]:
        filas = []
        for i in range(self.tabla_tiempos_eps.rowCount()):
            eps = self._texto_celda(self.tabla_tiempos_eps, i, 0)
            dias = self._texto_celda(self.tabla_tiempos_eps, i, 1) or "0"
            filas.append({"eps": eps, "dias_habiles": dias})
        return filas

    def _leer_tabla_festivos(self) -> list[dict]:
        filas = []
        for i in range(self.tabla_festivos.rowCount()):
            fecha = self._texto_celda(self.tabla_festivos, i, 0)
            descripcion = self._texto_celda(self.tabla_festivos, i, 1)
            filas.append({"fecha": fecha, "descripcion": descripcion})
        return filas

    @staticmethod
    def _texto_celda(tabla: QTableWidget, fila: int, columna: int) -> str:
        item = tabla.item(fila, columna)
        return item.text().strip() if item else ""

    # ------------------------------------------------------------------
    # Semaforización
    # ------------------------------------------------------------------
    def _tab_semaforizacion(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        info = QLabel(
            "Define cuándo una solicitud se marca en AMARILLO (cerca de vencer). "
            "Una solicitud pasa a amarillo cuando le quedan ese número de días hábiles o menos "
            "antes de su fecha límite. Con más días queda en blanco (a tiempo); si ya venció, en rojo."
        )
        info.setWordWrap(True)
        info.setProperty("role", "secondary")
        layout.addWidget(info)

        formulario = QFormLayout()
        self.spin_dias_amarillo = QSpinBox()
        self.spin_dias_amarillo.setRange(0, 60)
        formulario.addRow(
            "Cerca de vencer (amarillo) si faltan N días hábiles o menos:", self.spin_dias_amarillo
        )
        layout.addLayout(formulario)

        boton_guardar = QPushButton("Guardar semaforización")
        boton_guardar.setProperty("variant", "primary")
        boton_guardar.clicked.connect(self._guardar_semaforizacion)
        layout.addWidget(boton_guardar)

        self.lbl_semaforizacion_estado = QLabel("")
        self.lbl_semaforizacion_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_semaforizacion_estado)
        layout.addStretch()

        self._cargar_semaforizacion()
        return pagina

    def _cargar_semaforizacion(self) -> None:
        try:
            from sgs.app.casos_de_uso import obtener_parametros_semaforizacion

            parametros = obtener_parametros_semaforizacion()
            self.spin_dias_amarillo.setValue(int(parametros.get("dias_amarillo_cerca", 1) or 1))
            self.lbl_semaforizacion_estado.setText("")
        except Exception:
            self.spin_dias_amarillo.setValue(1)
            self.lbl_semaforizacion_estado.setStyleSheet(f"color: {theme.SEMAFORO_AMARILLO};")
            self.lbl_semaforizacion_estado.setText(
                "No se pudo conectar con la base de datos — mostrando el valor por defecto."
            )

    def _guardar_semaforizacion(self) -> None:
        try:
            from sgs.app.casos_de_uso import (
                guardar_parametros_semaforizacion,
                obtener_parametros_semaforizacion,
            )

            # Se conserva el valor 'verde_hasta' existente; solo se edita el
            # umbral de amarillo, que es el que gobierna el color.
            verde_hasta = obtener_parametros_semaforizacion().get("dias_verde_hasta", 1)
            guardar_parametros_semaforizacion(verde_hasta, self.spin_dias_amarillo.value())
            self.lbl_semaforizacion_estado.setStyleSheet(f"color: {theme.SEMAFORO_VERDE};")
            self.lbl_semaforizacion_estado.setText("✅ Guardado.")
        except Exception as exc:
            self.lbl_semaforizacion_estado.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            self.lbl_semaforizacion_estado.setText(f"No se pudo guardar: {exc}")

    # ------------------------------------------------------------------
    # Reglas de clasificación
    # ------------------------------------------------------------------
    def _tab_reglas_clasificacion(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)

        info = QLabel(
            "Cada proceso puede tener varias reglas. Dentro de una regla, varios valores en el mismo "
            "campo son OR; entre campos distintos de la misma regla es AND. Las reglas tipo «excepción» "
            "se evalúan primero. Solo las reglas activas se usan al clasificar."
        )
        info.setWordWrap(True)
        info.setProperty("role", "secondary")
        layout.addWidget(info)

        fila_botones = QHBoxLayout()
        boton_crear = QPushButton("+ Crear regla")
        boton_crear.setProperty("variant", "primary")
        boton_crear.clicked.connect(self._crear_regla_clasificacion)
        boton_editar = QPushButton("Editar")
        boton_editar.setProperty("variant", "ghost")
        boton_editar.clicked.connect(self._editar_regla_seleccionada)
        boton_estado = QPushButton("Activar/Desactivar")
        boton_estado.setProperty("variant", "ghost")
        boton_estado.clicked.connect(self._alternar_estado_regla)
        boton_eliminar = QPushButton("Eliminar")
        boton_eliminar.setProperty("variant", "danger")
        boton_eliminar.clicked.connect(self._eliminar_regla_seleccionada)
        boton_actualizar = QPushButton("Actualizar lista")
        boton_actualizar.setProperty("variant", "ghost")
        boton_actualizar.clicked.connect(self._cargar_reglas_clasificacion)
        for b in (boton_crear, boton_editar, boton_estado, boton_eliminar, boton_actualizar):
            fila_botones.addWidget(b)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.tabla_reglas = QTableWidget()
        self.tabla_reglas.setColumnCount(5)
        self.tabla_reglas.setHorizontalHeaderLabels(
            ["Proceso", "Tipo", "Orden", "Activa", "Condiciones (resumen)"]
        )
        self.tabla_reglas.horizontalHeader().setStretchLastSection(True)
        self.tabla_reglas.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_reglas.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_reglas.verticalHeader().setVisible(False)
        self.tabla_reglas.cellDoubleClicked.connect(lambda *_: self._editar_regla_seleccionada())
        layout.addWidget(self.tabla_reglas)

        self.lbl_reglas_estado = QLabel("")
        self.lbl_reglas_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_reglas_estado)

        self._reglas_actuales: list[dict] = []
        self._cargar_reglas_clasificacion()
        return pagina

    def _cargar_reglas_clasificacion(self) -> None:
        try:
            from sgs.app.casos_de_uso import listar_reglas_clasificacion_para_mostrar

            self._reglas_actuales = listar_reglas_clasificacion_para_mostrar()
            self.lbl_reglas_estado.setText("")
        except Exception:
            self._reglas_actuales = []
            self.lbl_reglas_estado.setText("No se pudo conectar con la base de datos.")
        self.tabla_reglas.setRowCount(len(self._reglas_actuales))
        for i, r in enumerate(self._reglas_actuales):
            self.tabla_reglas.setItem(i, 0, QTableWidgetItem(r["proceso"]))
            self.tabla_reglas.setItem(i, 1, QTableWidgetItem(r["tipo"]))
            self.tabla_reglas.setItem(i, 2, QTableWidgetItem(str(r["orden"])))
            self.tabla_reglas.setItem(i, 3, QTableWidgetItem("Sí" if r.get("activo") else "No"))
            self.tabla_reglas.setItem(i, 4, QTableWidgetItem(r["resumen"]))

    def _regla_seleccionada(self) -> dict | None:
        fila = self.tabla_reglas.currentRow()
        if fila < 0 or fila >= len(self._reglas_actuales):
            return None
        return self._reglas_actuales[fila]

    def _abrir_dialogo_regla(self, regla: dict | None) -> None:
        from sgs.app.casos_de_uso import (
            CAMPOS_CLASIFICACION,
            OPERADORES_CLASIFICACION,
            TIPOS_REGLA,
            actualizar_regla_clasificacion,
            crear_regla_clasificacion,
            listar_procesos,
            obtener_regla_clasificacion,
        )
        from sgs.ui.widgets.dialogo_regla_clasificacion import DialogoReglaClasificacion

        try:
            procesos = [p for p in listar_procesos() if p["id"] is not None]
        except Exception as exc:
            QMessageBox.critical(self, "No se pudieron cargar los procesos", str(exc))
            return
        if not procesos:
            QMessageBox.information(self, "Sin procesos", "Primero crea un proceso en la pestaña «Procesos».")
            return

        datos = None
        if regla is not None:
            datos = obtener_regla_clasificacion(regla["id"])

        dialogo = DialogoReglaClasificacion(
            procesos, CAMPOS_CLASIFICACION, OPERADORES_CLASIFICACION, TIPOS_REGLA, datos, parent=self
        )
        if not dialogo.exec():
            return
        try:
            if regla is None:
                crear_regla_clasificacion(
                    dialogo.proceso_id(), dialogo.tipo_regla(), dialogo.orden(),
                    dialogo.condiciones(), dialogo.descripcion(),
                )
            else:
                actualizar_regla_clasificacion(
                    regla["id"], dialogo.proceso_id(), dialogo.tipo_regla(), dialogo.orden(),
                    dialogo.condiciones(), dialogo.descripcion(),
                )
            self._cargar_reglas_clasificacion()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo guardar la regla", str(exc))

    def _crear_regla_clasificacion(self) -> None:
        self._abrir_dialogo_regla(None)

    def _editar_regla_seleccionada(self) -> None:
        regla = self._regla_seleccionada()
        if regla is None:
            QMessageBox.information(self, "Selecciona una regla", "Elige una regla de la tabla para editarla.")
            return
        self._abrir_dialogo_regla(regla)

    def _alternar_estado_regla(self) -> None:
        regla = self._regla_seleccionada()
        if regla is None:
            QMessageBox.information(self, "Selecciona una regla", "Elige una regla para activar o desactivar.")
            return
        try:
            from sgs.app.casos_de_uso import cambiar_estado_regla_clasificacion

            cambiar_estado_regla_clasificacion(regla["id"], not regla.get("activo"))
            self._cargar_reglas_clasificacion()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo actualizar", str(exc))

    def _eliminar_regla_seleccionada(self) -> None:
        regla = self._regla_seleccionada()
        if regla is None:
            QMessageBox.information(self, "Selecciona una regla", "Elige una regla para eliminar.")
            return
        confirmar = QMessageBox.question(
            self, "Eliminar regla",
            f"¿Eliminar la regla de «{regla['proceso']}»? Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return
        try:
            from sgs.app.casos_de_uso import eliminar_regla_clasificacion

            eliminar_regla_clasificacion(regla["id"])
            self._cargar_reglas_clasificacion()
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo eliminar", str(exc))

    # ------------------------------------------------------------------
    # Parámetros generales
    # ------------------------------------------------------------------
    def _tab_parametros_generales(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        formulario = QFormLayout()

        self.campo_nombre_entidad = QLineEdit()
        self.campo_dias_fallback = QSpinBox()
        self.campo_dias_fallback.setRange(1, 60)

        formulario.addRow("Nombre de la entidad:", self.campo_nombre_entidad)
        formulario.addRow("Días hábiles por defecto (fallback):", self.campo_dias_fallback)
        layout.addLayout(formulario)

        boton_guardar = QPushButton("Guardar parámetros generales")
        boton_guardar.setProperty("variant", "primary")
        boton_guardar.clicked.connect(self._guardar_parametros_generales)
        layout.addWidget(boton_guardar)

        self.lbl_parametros_estado = QLabel("")
        self.lbl_parametros_estado.setProperty("role", "secondary")
        layout.addWidget(self.lbl_parametros_estado)
        layout.addStretch()

        self._cargar_parametros_generales()
        return pagina

    def _cargar_parametros_generales(self) -> None:
        try:
            from sgs.app.casos_de_uso import obtener_parametros_generales

            parametros = obtener_parametros_generales()
            self.campo_nombre_entidad.setText(
                parametros.get("nombre_entidad", "Alcaldía de Medellín — Secretaría de Salud")
            )
            self.campo_dias_fallback.setValue(int(parametros.get("dias_fallback_tiempo_respuesta", "10") or 10))
        except Exception:
            self.campo_nombre_entidad.setText("Alcaldía de Medellín — Secretaría de Salud")
            self.campo_dias_fallback.setValue(10)
            self.lbl_parametros_estado.setText("No se pudo conectar con la base de datos — mostrando valores por defecto.")
            self.lbl_parametros_estado.setStyleSheet(f"color: {theme.SEMAFORO_AMARILLO};")

    def _guardar_parametros_generales(self) -> None:
        try:
            from sgs.app.casos_de_uso import guardar_parametro_general

            guardar_parametro_general("nombre_entidad", self.campo_nombre_entidad.text().strip())
            guardar_parametro_general("dias_fallback_tiempo_respuesta", str(self.campo_dias_fallback.value()))
            self.lbl_parametros_estado.setStyleSheet(f"color: {theme.SEMAFORO_VERDE};")
            self.lbl_parametros_estado.setText("✅ Guardado.")
        except Exception as exc:
            self.lbl_parametros_estado.setStyleSheet(f"color: {theme.SEMAFORO_ROJO};")
            self.lbl_parametros_estado.setText(f"No se pudo guardar: {exc}")

    # ------------------------------------------------------------------
    # Helpers genéricos de tablas editables
    # ------------------------------------------------------------------
    @staticmethod
    def _tabla_editable(encabezados: list[str], filas: list[list[str]]) -> QTableWidget:
        tabla = QTableWidget()
        tabla.setColumnCount(len(encabezados))
        tabla.setHorizontalHeaderLabels(encabezados)
        tabla.setRowCount(len(filas))
        for i, fila in enumerate(filas):
            for j, valor in enumerate(fila):
                tabla.setItem(i, j, QTableWidgetItem(valor))
        return tabla

    def _envolver_con_boton_agregar(self, tabla: QTableWidget) -> QWidget:
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(0, 8, 0, 0)
        fila_botones = QHBoxLayout()
        boton_agregar = QPushButton("+ Agregar fila")
        boton_agregar.setProperty("variant", "ghost")
        boton_agregar.clicked.connect(lambda: self._agregar_fila(tabla))
        boton_quitar = QPushButton("Quitar fila seleccionada")
        boton_quitar.setProperty("variant", "ghost")
        boton_quitar.clicked.connect(lambda: tabla.removeRow(tabla.currentRow()))
        fila_botones.addWidget(boton_agregar)
        fila_botones.addWidget(boton_quitar)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)
        layout.addWidget(tabla)
        return contenedor

    @staticmethod
    def _agregar_fila(tabla: QTableWidget) -> None:
        fila = tabla.rowCount()
        tabla.insertRow(fila)
        for col in range(tabla.columnCount()):
            tabla.setItem(fila, col, QTableWidgetItem(""))

    @staticmethod
    def _marcar_inactivo(tabla: QTableWidget, columna_activo: int) -> None:
        fila = tabla.currentRow()
        if fila < 0:
            return
        tabla.setItem(fila, columna_activo, QTableWidgetItem("No"))