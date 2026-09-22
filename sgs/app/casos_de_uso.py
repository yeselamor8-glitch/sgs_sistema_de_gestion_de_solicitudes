"""
Capa de aplicación — casos de uso. Es la ÚNICA capa que la futura UI
(PySide6, Fase 5) debe llamar. Nunca expone sesiones de SQLAlchemy ni
modelos ORM directamente a la UI: recibe/devuelve tipos simples.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import select

from sgs.config.db import get_session
from sgs.motores import motor_auth, motor_clasificacion, motor_importacion_sac, motor_semaforo, motor_tiempos
from sgs.motores.lector_archivo_sac import leer_archivo_sac
from sgs.repos.gestion_solicitud_repo import GestionSolicitudRepo
from sgs.repos.importacion_sac_repo import ImportacionSacRepo
from sgs.repos.reglas_repo import ReglaClasificacionRepo, ReglaTiemposRepo
from sgs.repos.solicitud_repo import SolicitudRepo
from sgs.repos.usuario_repo import UsuarioRepo
from sgs.repos.vista_columnas_repo import VistaColumnasRepo


@dataclass(frozen=True)
class ResultadoAutenticacion:
    ok: bool
    usuario_id: int | None = None
    username: str | None = None
    nombre: str | None = None
    rol: str | None = None
    mensaje_error: str | None = None


def autenticar(username: str, password: str) -> ResultadoAutenticacion:
    """
    Único punto de entrada de login para la UI. Nunca expone
    password_hash ni el objeto Usuario de SQLAlchemy hacia afuera.
    """
    username = (username or "").strip()
    if not username or not password:
        return ResultadoAutenticacion(ok=False, mensaje_error="Ingresa usuario y contraseña.")

    with get_session() as db:
        usuario = UsuarioRepo(db).obtener_por_username(username)
        if usuario is None:
            # mismo mensaje que "contraseña incorrecta" a propósito:
            # no revelar si el usuario existe o no
            return ResultadoAutenticacion(ok=False, mensaje_error="Usuario o contraseña incorrectos.")

        if not motor_auth.verificar_password(password, usuario.password_hash):
            return ResultadoAutenticacion(ok=False, mensaje_error="Usuario o contraseña incorrectos.")

        return ResultadoAutenticacion(
            ok=True, usuario_id=usuario.id, username=usuario.username, nombre=usuario.nombre, rol=usuario.rol
        )


def clasificar_solicitud(datos_sac: dict[str, str | None]) -> motor_clasificacion.ResultadoClasificacion:
    """
    Clasifica una solicitud SAC contra las reglas activas.
    `datos_sac` trae las claves crudas del exporte SAC (motivo,
    tipoasuntosol, solicitud, detalle, tipoidentificacion, ...).
    """
    with get_session() as db:
        reglas = ReglaClasificacionRepo(db).listar_reglas_activas()
    return motor_clasificacion.clasificar(datos_sac, reglas)


def _semaforo_por_indicador(indicador: str | None) -> str:
    """Indicador del paso de traslado (columna AD de la maestra) -> estado.
    Ya NO es la fuente del semáforo de la solicitud (ver
    `calcular_semaforo_solicitud`); se conserva como respaldo/mapeo."""
    return motor_semaforo.calcular_semaforo(indicador)


def _semaforo_solicitud(
    hoy: dt.date,
    solicitud,
    traslado,
    respuesta,
    ente_control,
    festivos: set[dt.date],
    parametros,
    dias_habiles_cerca: int = motor_semaforo.DIAS_HABILES_CERCA,
) -> str:
    """Semáforo EN VIVO de la solicitud (fases 1/2 + COMPLETADO), siempre
    contra la fecha actual — así cualquier vista que se recargue "lee el
    hoy" y refleja traslados/radicados/respuestas sin esperar a la BD.

    `dias_habiles_cerca` es el umbral configurable de "cerca de vencer"
    (amarillo) tomado de Configuración → Semaforización."""
    return motor_semaforo.calcular_semaforo_solicitud(
        hoy,
        fecha_ingreso=solicitud.sac_fecha_ingreso.date() if solicitud.sac_fecha_ingreso else None,
        fecha_traslado=traslado.fecha_traslado if traslado else None,
        fecha_limite_respuesta=traslado.fecha_limite_respuesta if traslado else None,
        prioridad_caso=solicitud.sac_prioridad_caso,
        eps=solicitud.doc_eps,
        solicitud=solicitud.sac_solicitud,
        motivo=solicitud.sac_motivo,
        parametros=parametros,
        hubo_respuesta=respuesta.hubo_respuesta if respuesta else None,
        radicado_ente_control=(ente_control.radicado if ente_control else "") or "",
        estado_gestion=solicitud.estado_gestion,
        dias_habiles_cerca=dias_habiles_cerca,
    )


def calcular_tiempos_y_semaforo(
    fecha_traslado: dt.date,
    prioridad_caso: str | None,
    eps: str | None,
    solicitud: str | None,
    festivos: set[dt.date],
    proceso_id: int,
    fecha_ingreso: dt.date | None = None,
    motivo: str | None = None,
) -> dict:
    """Devuelve fecha límite, la regla que se usó, y el semáforo (por la
    regla del INDICADOR de la maestra, no por umbrales configurables)."""
    with get_session() as db:
        parametros = ReglaTiemposRepo(db).cargar_parametros(festivos, proceso_id=proceso_id)

    fecha_limite, regla_aplicada = motor_tiempos.calcular_fecha_limite(
        fecha_traslado, prioridad_caso, eps, solicitud, parametros, motivo=motivo
    )
    indicador = None
    if fecha_ingreso is not None:
        oportunidad = motor_tiempos.calcular_oportunidad_traslado(fecha_ingreso, fecha_traslado, festivos)
        indicador = motor_tiempos.indicador_oportunidad_traslado(oportunidad)

    return {
        "fecha_limite": fecha_limite,
        "regla_aplicada": regla_aplicada,
        "semaforo": _semaforo_por_indicador(indicador),
    }


def obtener_mis_solicitudes(funcionario_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
    """Caso de uso detrás de la pantalla 'Mis solicitudes' del funcionario."""
    with get_session() as db:
        repo = SolicitudRepo(db)
        solicitudes = repo.listar_por_funcionario(funcionario_id, limit=limit, offset=offset)
        return [
            {
                "id": s.id,
                "numero_solicitud_sac": s.numero_solicitud_sac,
                "sac_solicitud": s.sac_solicitud,
                "estado_gestion": s.estado_gestion,
                "clasificacion_estado": s.clasificacion_estado,
            }
            for s in solicitudes
        ]


def _fecha_texto(valor) -> str:
    return valor.isoformat() if valor is not None else ""


def _fecha_obj(valor) -> dt.date | None:
    """Acepta str 'yyyy-mm-dd' o ya un date/datetime (los motores devuelven
    date y la UI envía str) y normaliza a date. None si vacío o inválido."""
    if not valor:
        return None
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    try:
        return dt.datetime.strptime(valor, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _edad_calculada(fecha_nacimiento, doc_edad, fecha_referencia: dt.date | None = None) -> str:
    """Edad en años cumplidos al momento del ingreso (como la maestra, que
    la calcula contra la FECHA DE INGRESO); si no hay fecha de nacimiento,
    respaldo con el valor venido del exporte (doc_edad)."""
    if fecha_nacimiento is not None:
        anios = motor_tiempos.calcular_edad(fecha_nacimiento, fecha_referencia)
        if anios is not None:
            return str(anios)
    return str(doc_edad or "").strip() or ""


def _poblacion_priorizada(sexo: str, fecha_nacimiento, fecha_referencia, doc_poblacion: str) -> str:
    """POB PRIORIZADA como la deriva la maestra cuando el exporte no la
    trae: gestantes, menores de 18 y adultos de 60 o más."""
    if (doc_poblacion or "").strip():
        return doc_poblacion
    if fecha_nacimiento is not None:
        edad = motor_tiempos.calcular_edad(fecha_nacimiento, fecha_referencia)
        if edad is not None and edad < 18:
            return "MENOR DE EDAD"
        if edad is not None and edad >= 60:
            return "ADULTO MAYOR"
    return ""


def _funcionarios_por_proceso(db, proceso_ids: list[int | None]) -> dict[int, str]:
    """Nombres del(los) usuario(s) asignados a cada proceso en la pestaña
    'Asignación de funcionarios' (Configuración). Sin asignación = 'Sin
    asignar'. Es AGNÓSTICO del funcionario individual de cada solicitud."""
    from sgs.repos.permisos_repo import FuncionarioProcesoRepo

    ids = {pid for pid in proceso_ids if pid is not None}
    mapa = FuncionarioProcesoRepo(db).usuarios_por_proceso(list(ids))
    return {
        pid: (", ".join(mapa.get(pid, [])) if mapa.get(pid) else "Sin asignar")
        for pid in ids
    }


def _nombre_ciudadano(ciudadano, solicitud) -> str:
    """Fuente única del nombre visible del ciudadano: el registrado en la
    tabla de ciudadanos; si no se pudo resolver, el nombre tal como llegó
    en el exporte SAC (doc_nombre). Listado y detalle usan el mismo."""
    if ciudadano is not None and (ciudadano.nombre or "").strip():
        return ciudadano.nombre
    return solicitud.doc_nombre or ""


def _fila_solicitud(fila: dict) -> dict:
    solicitud = fila["solicitud"]
    ciudadano = fila["ciudadano"]
    proceso = fila["proceso"]
    funcionario = fila["funcionario"]
    traslado = fila["traslado"]
    respuesta = fila["respuesta"]
    ente_control = fila.get("ente_control")
    return {
        "id": solicitud.id,
        "numero_solicitud_sac": solicitud.numero_solicitud_sac,
        "semaforo": "SIN_FECHA",
        "estado_sac": solicitud.sac_estado or "",
        "nombre_ciudadano": _nombre_ciudadano(ciudadano, solicitud),
        "documento": ciudadano.numero_documento if ciudadano else solicitud.doc_numero_documento or "",
        "proceso": proceso.nombre if proceso else "Sin proceso",
        "funcionario": funcionario.nombre if funcionario else "Sin asignar",
        "funcionario_id": solicitud.funcionario_id,
        "proceso_id": solicitud.proceso_id,
        "motivo": solicitud.sac_motivo or "",
        "tipo_asunto": solicitud.sac_tipo_asunto or "",
        "solicitud": solicitud.sac_solicitud or "",
        "prioridad_caso": solicitud.sac_prioridad_caso or "",
        "eps": solicitud.doc_eps or "",
        "fecha_ingreso": _fecha_texto(solicitud.sac_fecha_ingreso),
        "fecha_limite": _fecha_texto(traslado.fecha_limite_respuesta if traslado else None),
        "estado_gestion": solicitud.estado_gestion or "",
        "clasificacion_estado": solicitud.clasificacion_estado or "",
        "fecha_traslado": _fecha_texto(traslado.fecha_traslado if traslado else None),
        "indicador_oportunidad_traslado": traslado.indicador_oportunidad if traslado else None,
        "institucion_competente": traslado.institucion_competente if traslado else "",
        "radicado_ente_control": (ente_control.radicado if ente_control else "") or "",
        # objetos ORM internos (no llegan a la UI) — los usa el semáforo en vivo
        "obj_solicitud": solicitud,
        "traslado": traslado,
        "respuesta": respuesta,
        "ente_control": ente_control,
    }


def obtener_solicitudes(
    filtros: dict | None,
    usuario_id: int | None,
    rol: str | None,
    hay_criterios: bool = False,
) -> list[dict]:
    """Lista de solicitudes para el módulo Solicitudes / Mis solicitudes,
    con el semáforo calculado en vivo y ya ordenada según el contexto.

    Orden automático (el orden manual por clic lo aplica la UI encima):
      * Vista por defecto (``hay_criterios=False``): por urgencia del
        semáforo (VENCIDO > CERCA_DE_VENCIMIENTO > A_TIEMPO > SIN_FECHA >
        COMPLETADO); a igual color, la fecha de ingreso MÁS ANTIGUA primero.
      * Con cualquier búsqueda o filtro activo (``hay_criterios=True``):
        por fecha de ingreso DESCENDENTE (más reciente primero).

    Nota de cambio de comportamiento: antes el orden por defecto era
    siempre por fecha de ingreso descendente. El orden por semáforo se
    resuelve aquí, en Python, porque el semáforo se calcula en vivo y no
    existe como columna en la base de datos.
    """
    filtros = dict(filtros or {})
    if rol != "ADMINISTRADOR":
        from sgs.repos.permisos_repo import FuncionarioProcesoRepo

        with get_session() as db:
            filtros["proceso_ids"] = (
                FuncionarioProcesoRepo(db).procesos_de(usuario_id)
                if usuario_id is not None
                else []
            )
    with get_session() as db:
        filas = [_fila_solicitud(fila) for fila in SolicitudRepo(db).listar_con_filtros(filtros)]
        funcionarios = _funcionarios_por_proceso(db, [f["proceso_id"] for f in filas])
        repo_tiempos = ReglaTiemposRepo(db)
        festivos = repo_tiempos.cargar_festivos()
        parametros_cache: dict[int, object] = {}

        def parametros_de(proceso_id: int | None):
            clave = proceso_id or 0
            if clave not in parametros_cache:
                parametros_cache[clave] = repo_tiempos.cargar_parametros(festivos, proceso_id=clave)
            return parametros_cache[clave]

        hoy = dt.date.today()
        dias_cerca = _umbral_cerca_semaforo(db)
        for fila in filas:
            fila["funcionario"] = funcionarios.get(fila["proceso_id"], "Sin asignar")
            fila["semaforo"] = _semaforo_solicitud(
                hoy,
                fila["obj_solicitud"],
                fila["traslado"],
                fila["respuesta"],
                fila["ente_control"],
                festivos,
                parametros_de(fila["proceso_id"]),
                dias_cerca,
            )
        return _ordenar_por_defecto(filas, hay_criterios)


def _clave_fecha_desc(fecha_iso: str | None) -> int:
    """Clave numérica para ordenar fechas ISO en DESCENDENTE sin usar
    reverse (así el flag de 'vacía al final' no se invierte). Devuelve el
    ordinal de la fecha negado; las vacías/ inválidas devuelven 0 y se
    empujan al final mediante el flag previo de la clave compuesta."""
    fecha = _fecha_obj(fecha_iso)
    return -fecha.toordinal() if fecha else 0


def _ordenar_por_defecto(filas: list[dict], hay_criterios: bool) -> list[dict]:
    """Orden automático del listado de solicitudes (ver
    ``obtener_solicitudes``). No aplica el orden manual por clic — eso lo
    resuelve la UI sobre el resultado de esta función."""
    if hay_criterios:
        # Con criterios activos: fecha de ingreso descendente (más
        # reciente primero). Las fechas vacías caen SIEMPRE al final
        # (primer elemento de la clave: 0 = tiene fecha, 1 = vacía; no se
        # invierte porque va fuera del reverse).
        return sorted(
            filas,
            key=lambda f: (
                0 if f.get("fecha_ingreso") else 1,
                _clave_fecha_desc(f.get("fecha_ingreso")),
            ),
        )
    # Vista por defecto: por urgencia del semáforo; a igual color, la
    # fecha de ingreso más antigua primero (las vacías al final).
    return sorted(
        filas,
        key=lambda f: (
            motor_semaforo.rango_urgencia(f.get("semaforo")),
            f.get("fecha_ingreso") == "",
            f.get("fecha_ingreso") or "",
        ),
    )


def contar_solicitudes(filtros: dict | None, usuario_id: int | None, rol: str | None) -> int:
    """Total de solicitudes que coinciden con los filtros actuales de la
    pantalla (misma lógica de `obtener_solicitudes`, pero COUNT en SQL)."""
    filtros = dict(filtros or {})
    if rol != "ADMINISTRADOR":
        from sgs.repos.permisos_repo import FuncionarioProcesoRepo

        with get_session() as db:
            filtros["proceso_ids"] = (
                FuncionarioProcesoRepo(db).procesos_de(usuario_id)
                if usuario_id is not None
                else []
            )
    with get_session() as db:
        return SolicitudRepo(db).contar(filtros)


def obtener_dashboard(usuario_id: int | None, rol: str | None) -> dict:
    filas = obtener_solicitudes({}, usuario_id, rol)
    conteos = {"total": len(filas), "en_tiempo": 0, "proximas_vencer": 0, "vencidas": 0, "completadas": 0}
    for fila in filas:
        if fila["semaforo"] == motor_semaforo.A_TIEMPO:
            conteos["en_tiempo"] += 1
        elif fila["semaforo"] == motor_semaforo.CERCA_DE_VENCIMIENTO:
            conteos["proximas_vencer"] += 1
        elif fila["semaforo"] == motor_semaforo.VENCIDO:
            conteos["vencidas"] += 1
        elif fila["semaforo"] == motor_semaforo.COMPLETADO:
            conteos["completadas"] += 1
    prioritarias = [
        (f["numero_solicitud_sac"], f["proceso"], f["semaforo"], f["estado_gestion"])
        for f in filas if f["semaforo"] in (motor_semaforo.VENCIDO, motor_semaforo.CERCA_DE_VENCIMIENTO)
    ][:10]
    por_proceso: dict[str, int] = {}
    for fila in filas:
        por_proceso[fila["proceso"]] = por_proceso.get(fila["proceso"], 0) + 1
    maximo = max(por_proceso.values(), default=1)
    conteos["atencion_prioritaria"] = prioritarias
    conteos["por_proceso"] = [
        (nombre, total, round(total * 100 / maximo)) for nombre, total in por_proceso.items()
    ]
    return conteos


def obtener_detalle_solicitud(numero_solicitud: str) -> dict:
    with get_session() as db:
        fila = SolicitudRepo(db).obtener_detalle(numero_solicitud)
        if fila is None:
            raise ValueError(f"No existe la solicitud {numero_solicitud}")
        solicitud = fila["solicitud"]
        ciudadano = fila["ciudadano"]
        proceso = fila["proceso"]
        traslado = fila["traslado"]
        respuesta = fila["respuesta"]
        ente = fila["ente_control"]
        festivos = ReglaTiemposRepo(db).cargar_festivos()
        parametros = ReglaTiemposRepo(db).cargar_parametros(festivos, proceso_id=solicitud.proceso_id or 0)
        hoy = dt.date.today()
        limite = traslado.fecha_limite_respuesta if traslado else None
        fecha_ingreso = solicitud.sac_fecha_ingreso.date() if solicitud.sac_fecha_ingreso else None
        fecha_nacimiento = ciudadano.fecha_nacimiento if ciudadano else solicitud.doc_fecha_nacimiento
        return {
            "numero_solicitud_sac": numero_solicitud,
            "semaforo": _semaforo_solicitud(
                hoy, solicitud, traslado, respuesta, ente, festivos, parametros,
                _umbral_cerca_semaforo(db),
            ),
            "proceso": proceso.nombre if proceso else "Sin proceso",
            "funcionario": _funcionarios_por_proceso(db, [solicitud.proceso_id]).get(
                solicitud.proceso_id, "Sin asignar"
            ),
            "funcionario_id": solicitud.funcionario_id,
            "proceso_id": solicitud.proceso_id,
            "tipo_documento": ciudadano.tipo_documento if ciudadano else solicitud.doc_tipo_documento or "",
            "documento": ciudadano.numero_documento if ciudadano else solicitud.doc_numero_documento or "",
            "nombre_ciudadano": _nombre_ciudadano(ciudadano, solicitud),
            "sexo": ciudadano.sexo if ciudadano else solicitud.doc_sexo or "",
            "fecha_nacimiento": _fecha_texto(fecha_nacimiento),
            "edad": _edad_calculada(fecha_nacimiento, solicitud.doc_edad, fecha_ingreso),
            "telefono": ciudadano.telefono if ciudadano else solicitud.doc_telefono or "",
            "correo": ciudadano.correo if ciudadano else solicitud.doc_correo or "",
            "municipio_origen": solicitud.doc_municipio_origen or "",
            "municipio_residencia": solicitud.doc_municipio_residencia or "",
            "poblacion_priorizada": _poblacion_priorizada(
                ciudadano.sexo if ciudadano else solicitud.doc_sexo or "",
                fecha_nacimiento,
                fecha_ingreso,
                solicitud.doc_poblacion_priorizada or "",
            ),
            "regimen": solicitud.doc_regimen or "",
            "eps": solicitud.doc_eps or "",
            "motivo": solicitud.sac_motivo or "",
            "tipo_asunto": solicitud.sac_tipo_asunto or "",
            "solicitud": solicitud.sac_solicitud or "",
            "subclasificacion": solicitud.sac_subclasificacion or "",
            "prioridad_caso": solicitud.sac_prioridad_caso or "",
            "barrera_acceso": solicitud.sac_barrera_acceso or "",
            "usuario_sac": solicitud.sac_usuario or "",
            "fecha_ingreso": _fecha_texto(solicitud.sac_fecha_ingreso),
            "estado_sac": solicitud.sac_estado or "",
            "detalle": solicitud.sac_detalle or "",
            "actuacion_funcionario": solicitud.sac_actuacion_funcionario or "",
            "fecha_traslado": _fecha_texto(traslado.fecha_traslado if traslado else None),
            "institucion_competente": traslado.institucion_competente if traslado else "",
            "oportunidad_traslado_dias": traslado.oportunidad_dias_habiles if traslado else "",
            "indicador_oportunidad_traslado": traslado.indicador_oportunidad if traslado else "",
            "fecha_limite": _fecha_texto(limite),
            "dias_restantes": motor_semaforo.dias_habiles_restantes(hoy, limite, festivos) if limite else "",
            "hubo_respuesta": respuesta.hubo_respuesta if respuesta else "NO",
            "decision": respuesta.decision if respuesta else "",
            "fecha_respuesta": _fecha_texto(respuesta.fecha_respuesta if respuesta else None),
            "oportunidad_respuesta": respuesta.oportunidad_respuesta if respuesta else "",
            "notificacion_usuario": respuesta.notificacion_usuario if respuesta else "Pendiente",
            "respuesta_entidad": respuesta.respuesta_entidad if respuesta else "",
            "radicado_ente_control": ente.radicado if ente else "",
            "entidad_control": ente.entidad if ente else "",
            "fecha_reporte_control": _fecha_texto(ente.fecha_reporte if ente else None),
            "estado_gestion": solicitud.estado_gestion or "pendiente",
            "observaciones": solicitud.observaciones or "",
        }


def previsualizar_traslado(numero_solicitud_sac: str, fecha_traslado: dt.date) -> dict:
    """Cálculo en vivo del bloque de tiempos del traslado para el Detalle,
    sin guardar nada. Devuelve fecha límite, oportunidad días, indicador,
    días restantes y semáforo (por la regla del INDICADOR de la maestra)."""
    with get_session() as db:
        solicitud = GestionSolicitudRepo(db).obtener_por_numero_sac(numero_solicitud_sac)
        if solicitud is None:
            raise ValueError(f"No existe la solicitud {numero_solicitud_sac}")
        festivos = ReglaTiemposRepo(db).cargar_festivos()
        parametros = ReglaTiemposRepo(db).cargar_parametros(festivos, proceso_id=solicitud.proceso_id)

        fecha_ingreso = solicitud.sac_fecha_ingreso.date() if solicitud.sac_fecha_ingreso else None
        if fecha_ingreso:
            bloque = motor_tiempos.calcular_bloque_traslado(
                fecha_ingreso,
                fecha_traslado,
                solicitud.sac_prioridad_caso,
                solicitud.doc_eps,
                solicitud.sac_solicitud,
                solicitud.sac_motivo,
                parametros,
            )
        else:
            fecha_limite, _ = motor_tiempos.calcular_fecha_limite(
                fecha_traslado,
                solicitud.sac_prioridad_caso,
                solicitud.doc_eps,
                solicitud.sac_solicitud,
                parametros,
                motivo=solicitud.sac_motivo,
            )
            bloque = {"fecha_limite": fecha_limite, "oportunidad_dias": None, "indicador_oportunidad": None}

        hoy = dt.date.today()
        return {
            "fecha_limite": _fecha_texto(bloque["fecha_limite"]),
            "oportunidad_dias": bloque["oportunidad_dias"],
            "indicador_oportunidad": bloque["indicador_oportunidad"],
            "dias_restantes": (
                motor_semaforo.dias_habiles_restantes(hoy, bloque["fecha_limite"], festivos)
                if bloque["fecha_limite"]
                else ""
            ),
            # Semáforo en vivo: al elegir fecha de traslado entra a FASE 2
            # (hoy vs la fecha límite de respuesta recién calculada).
            "semaforo": motor_semaforo.calcular_semaforo_solicitud(
                hoy,
                fecha_ingreso=solicitud.sac_fecha_ingreso.date() if solicitud.sac_fecha_ingreso else None,
                fecha_traslado=fecha_traslado,
                fecha_limite_respuesta=bloque["fecha_limite"],
                prioridad_caso=solicitud.sac_prioridad_caso,
                parametros=parametros,
                estado_gestion=solicitud.estado_gestion,
                dias_habiles_cerca=_umbral_cerca_semaforo(db),
            ),
        }


def listar_funcionarios_por_proceso(proceso_id: int | None) -> list[dict]:
    if proceso_id is None:
        return []
    with get_session() as db:
        return [
            {"id": u.id, "nombre": u.nombre, "username": u.username}
            for u in UsuarioRepo(db).listar_funcionarios_por_proceso(proceso_id)
        ]


def asignar_funcionario_a_solicitud(numero_sac: str, funcionario_id: int | None) -> None:
    with get_session() as db:
        GestionSolicitudRepo(db).actualizar_gestion(
            numero_sac, {"funcionario_id": funcionario_id}
        )
        _registrar_auditoria(
            accion="Asignó funcionario a solicitud",
            entidad="solicitud",
            valor_nuevo={"funcionario_id": funcionario_id, "numero_sac": numero_sac},
            db=db,
        )


def obtener_configuracion_columnas(usuario_id: int, pantalla: str) -> list[dict] | None:
    """None significa que el usuario nunca ha guardado una vista propia
    para esta pantalla -> la UI debe usar la configuración por defecto."""
    with get_session() as db:
        return VistaColumnasRepo(db).obtener(usuario_id, pantalla)


def guardar_configuracion_columnas(usuario_id: int, pantalla: str, configuracion: list[dict]) -> None:
    with get_session() as db:
        VistaColumnasRepo(db).guardar(usuario_id, pantalla, configuracion)


def guardar_gestion_solicitud(numero_solicitud_sac: str, cambios: dict) -> None:
    """
    Único punto de entrada para que la UI guarde cambios de gestión
    (Traslado, Respuesta, Ente de control, Estado, Observaciones).

    Cuando se guarda una fecha de traslado real, recalcula y persiste todo
    el bloque de tiempos (fecha límite de respuesta, oportunidad e
    indicador del traslado) usando `motor_tiempos` + los parámetros y
    festivos configurados. Cuando se guarda información de la respuesta
    (¿hubo respuesta? y/o fecha), recalcula `decision` y
    `oportunidad_respuesta` comparando contra la fecha límite vigente.
    Nunca acepta ni escribe otros campos del bloque SAC (`sac_*`) — esos
    son de solo lectura desde aquí; la única excepción es `estado_sac`
    (estado operativo gestionado desde el detalle), que se pasa tal cual
    al repositorio.
    """
    with get_session() as db:
        gestion = GestionSolicitudRepo(db)
        solicitud = gestion.obtener_por_numero_sac(numero_solicitud_sac)
        if solicitud is None:
            raise ValueError(f"No existe la solicitud {numero_solicitud_sac}")

        if cambios.get("fecha_traslado"):
            festivos = ReglaTiemposRepo(db).cargar_festivos()
            parametros = ReglaTiemposRepo(db).cargar_parametros(festivos, proceso_id=solicitud.proceso_id)
            fecha_traslado = _fecha_obj(cambios["fecha_traslado"])
            fecha_ingreso = solicitud.sac_fecha_ingreso.date() if solicitud.sac_fecha_ingreso else None
            if fecha_ingreso:
                bloque = motor_tiempos.calcular_bloque_traslado(
                    fecha_ingreso,
                    fecha_traslado,
                    solicitud.sac_prioridad_caso,
                    solicitud.doc_eps,
                    solicitud.sac_solicitud,
                    solicitud.sac_motivo,
                    parametros,
                )
            else:
                fecha_limite, _ = motor_tiempos.calcular_fecha_limite(
                    fecha_traslado,
                    solicitud.sac_prioridad_caso,
                    solicitud.doc_eps,
                    solicitud.sac_solicitud,
                    parametros,
                    motivo=solicitud.sac_motivo,
                )
                bloque = {"fecha_limite": fecha_limite, "oportunidad_dias": None, "indicador_oportunidad": None}
            cambios["fecha_limite_respuesta"] = bloque["fecha_limite"]
            if bloque["oportunidad_dias"] is not None:
                cambios["oportunidad_dias_habiles"] = bloque["oportunidad_dias"]
                cambios["indicador_oportunidad"] = bloque["indicador_oportunidad"]

        if "hubo_respuesta" in cambios or "fecha_respuesta" in cambios:
            fecha_limite = cambios.get("fecha_limite_respuesta")
            if fecha_limite is None:
                fecha_limite = gestion.obtener_fecha_limite_respuesta(numero_solicitud_sac)
            hubo = cambios.get("hubo_respuesta")
            fecha_respuesta = _fecha_obj(cambios.get("fecha_respuesta"))
            fecha_traslado = None
            if cambios.get("fecha_traslado"):
                fecha_traslado = _fecha_obj(cambios.get("fecha_traslado"))
            else:
                from sgs.models.orm import Solicitud as ModeloSolicitud, Traslado

                fecha_traslado = db.execute(
                    select(Traslado.fecha_traslado)
                    .join(ModeloSolicitud, ModeloSolicitud.id == Traslado.solicitud_id)
                    .where(ModeloSolicitud.numero_solicitud_sac == numero_solicitud_sac)
                ).scalar()
            bloque = motor_tiempos.calcular_bloque_respuesta(hubo, fecha_respuesta, fecha_limite, fecha_traslado)
            cambios["decision"] = bloque["decision"]
            cambios["oportunidad_respuesta"] = bloque["oportunidad_respuesta"]

        gestion.actualizar_gestion(numero_solicitud_sac, cambios)
        _registrar_auditoria(
            accion="Actualizó gestión de solicitud",
            entidad="solicitud",
            entidad_id=solicitud.id,
            valor_nuevo={k: str(v) for k, v in cambios.items() if v not in (None, "")},
            solicitud_relacionada_id=solicitud.id,
            db=db,
        )


# ----------------------------------------------------------------------
# Importar SAC
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class VistaPreviaImportacion:
    encabezados: list[str]
    total_filas: int
    filas_muestra: list[dict]  # primeras N filas, para mostrar en pantalla
    columnas_faltantes: list[str]  # no vacío = estructura inválida, no continuar


def validar_y_previsualizar_archivo_sac(ruta_archivo: str, filas_muestra: int = 20) -> VistaPreviaImportacion:
    """Pasos 'Seleccionar archivo' -> 'Validar estructura' -> 'Vista previa'."""
    archivo = leer_archivo_sac(ruta_archivo)
    faltantes = motor_importacion_sac.validar_estructura(archivo.encabezados)
    return VistaPreviaImportacion(
        encabezados=archivo.encabezados,
        total_filas=len(archivo.filas),
        filas_muestra=archivo.filas[:filas_muestra],
        columnas_faltantes=faltantes,
    )


def clasificar_y_detectar_duplicados(ruta_archivo: str) -> motor_importacion_sac.ResumenImportacion:
    """Pasos 'Clasificar' -> 'Detectar duplicados' -> 'Mostrar resumen'.
    Vuelve a leer el archivo (se asume mismo `ruta_archivo` de la vista
    previa) para no tener que mantener el contenido completo en memoria
    de la UI entre pasos."""
    archivo = leer_archivo_sac(ruta_archivo)
    numeros = [str(f.get("numerosolicitud", "")).strip() for f in archivo.filas if f.get("numerosolicitud")]

    with get_session() as db:
        reglas = ReglaClasificacionRepo(db).listar_reglas_activas()
        existentes = ImportacionSacRepo(db).obtener_existentes(numeros)

    return motor_importacion_sac.procesar_archivo(archivo.filas, existentes, reglas)


# Nombre del proceso destino por defecto para las solicitudes que ninguna
# regla de clasificación logra asignar (así no quedan sin proceso).
NOMBRE_PROCESO_SIN_CLASIFICACION = "SIN_CLASIFICACION"


def _id_proceso_sin_clasificacion(db) -> int:
    """Devuelve el id del proceso 'Sin clasificación', creándolo si aún no
    existe (por si el seed no se ejecutó). Así las solicitudes que ninguna
    regla clasifica siempre tienen un proceso destino."""
    from sgs.models.orm import Proceso

    proceso = db.execute(
        select(Proceso).where(Proceso.nombre == NOMBRE_PROCESO_SIN_CLASIFICACION)
    ).scalar_one_or_none()
    if proceso is None:
        proceso = Proceso(
            nombre=NOMBRE_PROCESO_SIN_CLASIFICACION,
            descripcion="Sin clasificación — destino por defecto de las solicitudes que ninguna regla clasifica",
            activo=True,
        )
        db.add(proceso)
        db.flush()
    return proceso.id


def confirmar_importacion_sac(ruta_archivo: str, archivo_nombre: str, usuario_id: int) -> dict:
    """Paso 'Confirmar importación' -> 'Guardar en PostgreSQL'.
    Repite la clasificación (para trabajar con datos frescos) y esta
    vez sí escribe: crea/actualiza cada solicitud y registra la
    importación con su detalle fila a fila.

    Las filas que ninguna regla clasifica se asignan al proceso
    'Sin clasificación' (proceso_id), pero conservan
    clasificacion_estado='sin_clasificar' para las métricas y filtros."""
    archivo = leer_archivo_sac(ruta_archivo)

    with get_session() as db:
        reglas = ReglaClasificacionRepo(db).listar_reglas_activas()
        repo_importacion = ImportacionSacRepo(db)
        numeros = [str(f.get("numerosolicitud", "")).strip() for f in archivo.filas if f.get("numerosolicitud")]
        existentes = repo_importacion.obtener_existentes(numeros)

        resumen = motor_importacion_sac.procesar_archivo(archivo.filas, existentes, reglas)
        proceso_sin_clasificar_id = _id_proceso_sin_clasificacion(db)

        detalle_para_registrar: list[tuple[int, str]] = []
        por_numero = {
            str(f.get("numerosolicitud", "")).strip(): f for f in archivo.filas if f.get("numerosolicitud")
        }

        for resultado in resumen.resultados:
            if resultado.accion == "error":
                continue  # las filas con error no se guardan
            fila = por_numero[resultado.numero_solicitud_sac]
            # Sin clasificar -> proceso 'Sin clasificación' (nunca queda en NULL).
            proceso_id = resultado.proceso_id if resultado.proceso_id is not None else proceso_sin_clasificar_id
            solicitud, _ = repo_importacion.crear_o_actualizar_solicitud(
                fila, resultado.numero_solicitud_sac, proceso_id, resultado.clasificacion_estado
            )
            detalle_para_registrar.append((solicitud.id, resultado.accion))

        importacion = repo_importacion.registrar_importacion(
            archivo_nombre=archivo_nombre,
            usuario_id=usuario_id,
            conteos={
                "total": resumen.total,
                "nuevos": resumen.nuevos,
                "actualizados": resumen.actualizados,
                "sin_cambios": resumen.sin_cambios,
                "errores": resumen.errores,
                "sin_clasificar": resumen.sin_clasificar,
            },
            detalle=detalle_para_registrar,
        )
        _registrar_auditoria(
            accion="Importó archivo SAC", entidad="importacion_sac", entidad_id=importacion.id,
            valor_nuevo={
                "archivo": archivo_nombre, "total": resumen.total, "nuevos": resumen.nuevos,
                "actualizados": resumen.actualizados, "errores": resumen.errores,
                "sin_clasificar": resumen.sin_clasificar,
            },
            db=db,
        )

    por_proceso: dict[str, int] = {}
    with get_session() as db:
        from sgs.models.orm import Proceso

        for resultado in resumen.resultados:
            if resultado.accion == "error" or resultado.proceso_id is None:
                continue
            proceso = db.get(Proceso, resultado.proceso_id)
            nombre = proceso.nombre if proceso else "Sin proceso"
            por_proceso[nombre] = por_proceso.get(nombre, 0) + 1

    return {
        "importacion_id": importacion.id,
        "total": resumen.total,
        "nuevos": resumen.nuevos,
        "actualizados": resumen.actualizados,
        "sin_cambios": resumen.sin_cambios,
        "errores": resumen.errores,
        "sin_clasificar": resumen.sin_clasificar,
        "conflictos": resumen.conflictos,
        "por_proceso": por_proceso,
    }


# ----------------------------------------------------------------------
# Reportes / Análisis
# ----------------------------------------------------------------------

# Claves internas de `obtener_solicitudes` que NO deben llegar al análisis
# (son objetos ORM que usa el semáforo en vivo, no datos tabulares).
_CLAVES_INTERNAS_ANALISIS = {"obj_solicitud", "traslado", "respuesta", "ente_control"}


def obtener_solicitudes_para_analisis(usuario_id: int | None, rol: str | None) -> list[dict]:
    """Solicitudes del sistema en formato tabular para el módulo Reportes.

    Reutiliza `obtener_solicitudes` (respeta rol/proceso: el ADMINISTRADOR
    ve todo, el FUNCIONARIO solo sus procesos) y devuelve únicamente los
    campos planos, quitando los objetos ORM internos que el análisis no
    puede tabular ni exportar."""
    filas = obtener_solicitudes({}, usuario_id, rol)
    return [
        {k: v for k, v in fila.items() if k not in _CLAVES_INTERNAS_ANALISIS}
        for fila in filas
    ]


# ----------------------------------------------------------------------
# Configuración · Usuarios
# ----------------------------------------------------------------------

def listar_usuarios() -> list[dict]:
    with get_session() as db:
        return [
            {
                "id": u.id,
                "codigo_sac": u.codigo_sac,
                "username": u.username,
                "nombre": u.nombre,
                "rol": u.rol,
                "activo": u.activo,
            }
            for u in UsuarioRepo(db).listar()
        ]


def crear_usuario(codigo_sac: str, username: str, nombre: str, rol: str, password: str) -> int:
    from sgs.models.orm import Usuario as UsuarioModel

    with get_session() as db:
        usuario = UsuarioModel(
            codigo_sac=codigo_sac or None,
            username=username,
            nombre=nombre,
            rol=rol,
            password_hash=motor_auth.hashear_password(password),
            activo=True,
        )
        UsuarioRepo(db).guardar(usuario)
        _registrar_auditoria(
            accion="Creó usuario", entidad="usuario", entidad_id=usuario.id,
            valor_nuevo={"username": username, "rol": rol}, db=db,
        )
        return usuario.id


def cambiar_estado_usuario(usuario_id: int, activo: bool) -> None:
    with get_session() as db:
        repo = UsuarioRepo(db)
        usuario = repo.obtener_por_id(usuario_id)
        if usuario is None:
            raise ValueError(f"No existe el usuario {usuario_id}")
        anterior = usuario.activo
        usuario.activo = activo
        _registrar_auditoria(
            accion="Activó usuario" if activo else "Desactivó usuario",
            entidad="usuario", entidad_id=usuario_id,
            valor_anterior={"activo": anterior}, valor_nuevo={"activo": activo}, db=db,
        )


def restablecer_password(usuario_id: int, password_nueva: str) -> None:
    with get_session() as db:
        repo = UsuarioRepo(db)
        usuario = repo.obtener_por_id(usuario_id)
        if usuario is None:
            raise ValueError(f"No existe el usuario {usuario_id}")
        usuario.password_hash = motor_auth.hashear_password(password_nueva)
        _registrar_auditoria(
            accion="Restableció contraseña", entidad="usuario", entidad_id=usuario_id, db=db,
        )


def actualizar_usuario(
    usuario_id: int, nombre: str, rol: str, codigo_sac: str | None, password_nueva: str | None = None
) -> None:
    with get_session() as db:
        usuario = UsuarioRepo(db).obtener_por_id(usuario_id)
        if usuario is None:
            raise ValueError(f"No existe el usuario {usuario_id}")
        anterior = {"nombre": usuario.nombre, "rol": usuario.rol}
        usuario.nombre = nombre.strip()
        usuario.rol = rol
        usuario.codigo_sac = codigo_sac.strip() if codigo_sac else None
        if password_nueva:
            usuario.password_hash = motor_auth.hashear_password(password_nueva)
        _registrar_auditoria(
            accion="Editó usuario", entidad="usuario", entidad_id=usuario_id,
            valor_anterior=anterior, valor_nuevo={"nombre": nombre.strip(), "rol": rol}, db=db,
        )


# ----------------------------------------------------------------------
# Configuración · Procesos
# ----------------------------------------------------------------------

def listar_procesos() -> list[dict]:
    from sgs.repos.proceso_repo import ProcesoRepo

    with get_session() as db:
        return [
            {"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion or "", "activo": p.activo}
            for p in ProcesoRepo(db).listar()
        ]


def crear_proceso(nombre: str, descripcion: str) -> int:
    from sgs.repos.proceso_repo import ProcesoRepo

    with get_session() as db:
        proceso = ProcesoRepo(db).crear(nombre, descripcion)
        _registrar_auditoria(
            accion="Creó proceso", entidad="proceso", entidad_id=proceso.id,
            valor_nuevo={"nombre": nombre}, db=db,
        )
        return proceso.id


def cambiar_estado_proceso(proceso_id: int, activo: bool) -> None:
    from sgs.repos.proceso_repo import ProcesoRepo

    with get_session() as db:
        ProcesoRepo(db).cambiar_estado(proceso_id, activo)
        _registrar_auditoria(
            accion="Activó proceso" if activo else "Desactivó proceso",
            entidad="proceso", entidad_id=proceso_id, valor_nuevo={"activo": activo}, db=db,
        )


# ----------------------------------------------------------------------
# Configuración · Roles y permisos
# ----------------------------------------------------------------------

def usuario_tiene_permiso(usuario_id: int, nombre_permiso: str) -> bool:
    from sgs.repos.permisos_repo import PermisoRepo

    with get_session() as db:
        return PermisoRepo(db).usuario_tiene_permiso(usuario_id, nombre_permiso)


def establecer_permiso(usuario_id: int, nombre_permiso: str, activo: bool) -> None:
    from sgs.repos.permisos_repo import PermisoRepo

    with get_session() as db:
        PermisoRepo(db).establecer_permiso(usuario_id, nombre_permiso, activo)


# ----------------------------------------------------------------------
# Configuración · Asignación de funcionarios a procesos
# ----------------------------------------------------------------------

def listar_procesos_de_funcionario(usuario_id: int) -> list[int]:
    from sgs.repos.permisos_repo import FuncionarioProcesoRepo

    with get_session() as db:
        return FuncionarioProcesoRepo(db).procesos_de(usuario_id)


def asignar_procesos_a_funcionario(usuario_id: int, proceso_ids: list[int]) -> None:
    from sgs.repos.permisos_repo import FuncionarioProcesoRepo

    with get_session() as db:
        FuncionarioProcesoRepo(db).establecer_procesos(usuario_id, proceso_ids)


# ----------------------------------------------------------------------
# Configuración · Semaforización
# ----------------------------------------------------------------------

def obtener_parametros_semaforizacion() -> dict:
    """Umbrales de semaforización, en términos de días hábiles restantes.

    - ``dias_amarillo_cerca``: una solicitud está "cerca de vencer"
      (amarillo) si le quedan ese número de días hábiles o menos. Es el
      valor que realmente gobierna el color en `motor_semaforo`.
    - ``dias_verde_hasta``: referencia del límite "a tiempo" (verde); se
      conserva por compatibilidad."""
    from sgs.repos.parametros_semaforizacion_repo import ParametrosSemaforizacionRepo

    with get_session() as db:
        fila = ParametrosSemaforizacionRepo(db).obtener()
        return {
            "dias_verde_hasta": fila.dias_habiles_verde_hasta,
            "dias_amarillo_cerca": fila.dias_habiles_amarillo_hasta,
        }


def guardar_parametros_semaforizacion(dias_verde_hasta: int, dias_amarillo_cerca: int) -> None:
    from sgs.repos.parametros_semaforizacion_repo import ParametrosSemaforizacionRepo

    with get_session() as db:
        ParametrosSemaforizacionRepo(db).guardar(dias_verde_hasta, dias_amarillo_cerca)
        _registrar_auditoria(
            accion="Guardó parámetros de semaforización", entidad="semaforizacion",
            valor_nuevo={"dias_amarillo_cerca": dias_amarillo_cerca, "dias_verde_hasta": dias_verde_hasta},
            db=db,
        )


def _umbral_cerca_semaforo(db) -> int:
    """Días hábiles del umbral 'cerca de vencer' (amarillo) configurado.
    Se lee una vez por consulta y se pasa al motor de semáforo. Si no se
    puede leer (parámetros aún no creados), usa el valor por defecto del
    motor — así una lectura auxiliar nunca rompe el cálculo principal."""
    from sgs.repos.parametros_semaforizacion_repo import ParametrosSemaforizacionRepo

    try:
        return ParametrosSemaforizacionRepo(db).obtener().dias_habiles_amarillo_hasta
    except Exception:
        return motor_semaforo.DIAS_HABILES_CERCA


# ----------------------------------------------------------------------
# Configuración · Reglas de clasificación (solo consulta por ahora)
# ----------------------------------------------------------------------

def listar_reglas_clasificacion_para_mostrar() -> list[dict]:
    with get_session() as db:
        return ReglaClasificacionRepo(db).listar_para_mostrar()


# Campos SAC que el motor de clasificación entiende, para el combo del
# editor de reglas (evita errores de tipeo del administrador).
CAMPOS_CLASIFICACION = [
    "motivo",
    "tipoasuntosol",
    "solicitud",
    "subclasificacion",
    "detalle",
    "tipoidentificacion",
    "numeroidentificacion",
    "detallesolicitud",
    "tipo_pqr",
    "estadosolicitud",
    "barrera_acceso",
    "grupopoblacional",
    "epsvigentesg",
    "epsvigente",
    "regimenafvigentesg",
    "prioridad_caso",
]

OPERADORES_CLASIFICACION = ["igual_a", "distinto_de", "contiene"]
TIPOS_REGLA = ["normal", "excepcion"]


def obtener_regla_clasificacion(regla_id: int) -> dict | None:
    with get_session() as db:
        return ReglaClasificacionRepo(db).obtener_para_editar(regla_id)


def crear_regla_clasificacion(
    proceso_id: int,
    tipo_regla: str,
    orden_evaluacion: int,
    condiciones: list[tuple[str, str, list[str]]],
    descripcion: str | None = None,
) -> int:
    _validar_regla(proceso_id, tipo_regla, condiciones)
    with get_session() as db:
        regla = ReglaClasificacionRepo(db).crear_regla(
            proceso_id, tipo_regla, orden_evaluacion, condiciones, descripcion
        )
        _registrar_auditoria(
            accion="Creó regla de clasificación", entidad="regla_clasificacion",
            entidad_id=regla.id, valor_nuevo={"proceso_id": proceso_id, "tipo": tipo_regla}, db=db,
        )
        return regla.id


def actualizar_regla_clasificacion(
    regla_id: int,
    proceso_id: int,
    tipo_regla: str,
    orden_evaluacion: int,
    condiciones: list[tuple[str, str, list[str]]],
    descripcion: str | None = None,
) -> None:
    _validar_regla(proceso_id, tipo_regla, condiciones)
    with get_session() as db:
        ReglaClasificacionRepo(db).actualizar_regla(
            regla_id, proceso_id, tipo_regla, orden_evaluacion, condiciones, descripcion
        )
        _registrar_auditoria(
            accion="Editó regla de clasificación", entidad="regla_clasificacion",
            entidad_id=regla_id, valor_nuevo={"proceso_id": proceso_id, "tipo": tipo_regla}, db=db,
        )


def eliminar_regla_clasificacion(regla_id: int) -> None:
    with get_session() as db:
        ReglaClasificacionRepo(db).eliminar_regla(regla_id)
        _registrar_auditoria(
            accion="Eliminó regla de clasificación", entidad="regla_clasificacion",
            entidad_id=regla_id, db=db,
        )


def cambiar_estado_regla_clasificacion(regla_id: int, activo: bool) -> None:
    with get_session() as db:
        ReglaClasificacionRepo(db).cambiar_estado(regla_id, activo)
        _registrar_auditoria(
            accion="Activó regla de clasificación" if activo else "Desactivó regla de clasificación",
            entidad="regla_clasificacion", entidad_id=regla_id,
            valor_nuevo={"activo": activo}, db=db,
        )


def _validar_regla(proceso_id, tipo_regla, condiciones) -> None:
    """Validaciones básicas antes de guardar una regla de clasificación."""
    if proceso_id is None:
        raise ValueError("Selecciona el proceso al que enruta la regla.")
    if tipo_regla not in TIPOS_REGLA:
        raise ValueError("El tipo de regla debe ser 'normal' o 'excepcion'.")
    if not condiciones:
        raise ValueError("La regla debe tener al menos una condición.")
    for campo, operador, valores in condiciones:
        if not campo:
            raise ValueError("Cada condición debe tener un campo.")
        if operador not in OPERADORES_CLASIFICACION:
            raise ValueError(f"Operador no válido: {operador}.")
        if not [v for v in valores if str(v).strip()]:
            raise ValueError(f"La condición sobre '{campo}' debe tener al menos un valor.")


# ----------------------------------------------------------------------
# Configuración · Tiempos de respuesta
# ----------------------------------------------------------------------

def listar_reglas_tiempos_solicitud(proceso_id: int) -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_reglas_solicitud(proceso_id)


def listar_reglas_tiempos_prioridad() -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_reglas_prioridad()


def listar_reglas_tiempos_eps(proceso_id: int) -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_reglas_eps(proceso_id)


def listar_festivos() -> list[dict]:
    with get_session() as db:
        return ReglaTiemposRepo(db).listar_festivos()


def guardar_reglas_tiempos_solicitud(proceso_id: int, filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_reglas_solicitud(proceso_id, filas)
        _registrar_auditoria(
            accion="Guardó tiempos por solicitud", entidad="tiempos_respuesta",
            entidad_id=proceso_id, valor_nuevo={"filas": len(filas)}, db=db,
        )


def guardar_reglas_tiempos_prioridad(filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_reglas_prioridad(filas)
        _registrar_auditoria(
            accion="Guardó tiempos por prioridad", entidad="tiempos_respuesta",
            valor_nuevo={"filas": len(filas)}, db=db,
        )


def guardar_reglas_tiempos_eps(proceso_id: int, filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_reglas_eps(proceso_id, filas)
        _registrar_auditoria(
            accion="Guardó tiempos por EPS", entidad="tiempos_respuesta",
            entidad_id=proceso_id, valor_nuevo={"filas": len(filas)}, db=db,
        )


def guardar_festivos(filas: list[dict]) -> None:
    with get_session() as db:
        ReglaTiemposRepo(db).reemplazar_festivos(filas)
        _registrar_auditoria(
            accion="Guardó festivos", entidad="tiempos_respuesta",
            valor_nuevo={"filas": len(filas)}, db=db,
        )


# ----------------------------------------------------------------------
# Configuración · Parámetros generales
# ----------------------------------------------------------------------

def obtener_parametros_generales() -> dict[str, str]:
    from sgs.repos.parametro_general_repo import ParametroGeneralRepo

    with get_session() as db:
        return ParametroGeneralRepo(db).listar()


def guardar_parametro_general(clave: str, valor: str) -> None:
    from sgs.repos.parametro_general_repo import ParametroGeneralRepo

    with get_session() as db:
        ParametroGeneralRepo(db).guardar(clave, valor)


# ----------------------------------------------------------------------
# Reasignación de solicitudes (solicitudes de cambio) y notificaciones
# ----------------------------------------------------------------------

def solicitar_reasignacion_proceso(
    numero_solicitud_sac: str, proceso_solicitado_id: int, motivo: str, usuario_id: int
) -> int:
    """El funcionario pide reasignar una solicitud a otro proceso. Crea la
    solicitud de cambio (pendiente) y notifica a los administradores.
    Devuelve el id de la solicitud de cambio creada."""
    from sgs.repos.cambios_repo import NotificacionRepo, SolicitudCambioRepo, ids_administradores

    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("El motivo de la reasignación es obligatorio.")

    with get_session() as db:
        solicitud = GestionSolicitudRepo(db).obtener_por_numero_sac(numero_solicitud_sac)
        if solicitud is None:
            raise ValueError(f"No existe la solicitud {numero_solicitud_sac}")
        if solicitud.proceso_id == proceso_solicitado_id:
            raise ValueError("La solicitud ya pertenece a ese proceso.")

        cambios = SolicitudCambioRepo(db)
        cambio = cambios.crear_reasignacion_proceso(
            solicitud_id=solicitud.id,
            proceso_actual_id=solicitud.proceso_id,
            proceso_solicitado_id=proceso_solicitado_id,
            motivo=motivo,
            solicitado_por=usuario_id,
        )

        proceso_destino = cambios._nombre_proceso(proceso_solicitado_id)
        mensaje = (
            f"Solicitud de reasignación de {numero_solicitud_sac} "
            f"hacia «{proceso_destino}»."
        )
        NotificacionRepo(db).crear_para_muchos(
            ids_administradores(db),
            tipo="solicitud_cambio",
            mensaje=mensaje,
            referencia_tipo="solicitud_cambio",
            referencia_id=cambio.id,
        )
        return cambio.id


def resolver_solicitud_cambio(
    cambio_id: int, aprobada: bool, admin_id: int, observacion: str | None = None
) -> None:
    """El administrador aprueba o rechaza una solicitud de cambio. Si la
    aprueba y es una reasignación de proceso, mueve la solicitud al proceso
    solicitado. En ambos casos notifica al funcionario que la pidió."""
    from sgs.repos.cambios_repo import NotificacionRepo, SolicitudCambioRepo

    with get_session() as db:
        repo = SolicitudCambioRepo(db)
        cambio = repo.obtener(cambio_id)
        if cambio is None:
            raise ValueError(f"No existe la solicitud de cambio {cambio_id}")

        numero = repo._numero_solicitud(cambio.solicitud_id)
        destino = repo._nombre_proceso(cambio.proceso_solicitado_id)
        repo.resolver(cambio_id, aprobada, admin_id, observacion)

        if aprobada:
            mensaje = f"Tu reasignación de {numero} hacia «{destino}» fue APROBADA."
        else:
            mensaje = f"Tu reasignación de {numero} hacia «{destino}» fue RECHAZADA."
        obs = (observacion or "").strip()
        if obs:
            mensaje += f" Observación: {obs}"

        NotificacionRepo(db).crear(
            usuario_id=cambio.solicitado_por,
            tipo="solicitud_cambio",
            mensaje=mensaje,
            referencia_tipo="solicitud_cambio",
            referencia_id=cambio.id,
        )
        _registrar_auditoria(
            accion="Aprobó reasignación" if aprobada else "Rechazó reasignación",
            entidad="solicitud_cambio",
            entidad_id=cambio.id,
            valor_anterior={"estado": "pendiente"},
            valor_nuevo={"estado": "aprobada" if aprobada else "rechazada",
                         "observacion": (observacion or "")},
            solicitud_relacionada_id=cambio.solicitud_id,
            db=db,
        )


def listar_solicitudes_cambio_pendientes() -> list[dict]:
    """Para el administrador: solicitudes de cambio por resolver."""
    from sgs.repos.cambios_repo import SolicitudCambioRepo

    with get_session() as db:
        repo = SolicitudCambioRepo(db)
        return [repo.a_dict(c) for c in repo.listar_pendientes()]


def listar_mis_solicitudes_cambio(usuario_id: int) -> list[dict]:
    """Para el funcionario: las solicitudes de cambio que él envió, con su
    estado y la observación del administrador."""
    from sgs.repos.cambios_repo import SolicitudCambioRepo

    with get_session() as db:
        repo = SolicitudCambioRepo(db)
        return [repo.a_dict(c) for c in repo.listar_por_solicitante(usuario_id)]


def contar_notificaciones_no_leidas(usuario_id: int) -> int:
    from sgs.repos.cambios_repo import NotificacionRepo

    if usuario_id is None:
        return 0
    with get_session() as db:
        return NotificacionRepo(db).contar_no_leidas(usuario_id)


def listar_notificaciones(usuario_id: int) -> list[dict]:
    from sgs.repos.cambios_repo import NotificacionRepo

    with get_session() as db:
        repo = NotificacionRepo(db)
        return [repo.a_dict(n) for n in repo.listar_de(usuario_id)]


def marcar_notificaciones_leidas(usuario_id: int) -> None:
    from sgs.repos.cambios_repo import NotificacionRepo

    with get_session() as db:
        NotificacionRepo(db).marcar_todas_leidas(usuario_id)


# ----------------------------------------------------------------------
# Auditoría
# ----------------------------------------------------------------------

def _registrar_auditoria(
    accion: str,
    entidad: str,
    entidad_id: int | None = None,
    valor_anterior: dict | None = None,
    valor_nuevo: dict | None = None,
    solicitud_relacionada_id: int | None = None,
    db=None,  # se acepta por compatibilidad, pero NO se usa la sesión de la acción
) -> None:
    """Escribe un registro de auditoría con el actor de la sesión actual.

    SIEMPRE usa su propia sesión (independiente de la acción de negocio):
    así, si auditar falla, su transacción se descarta sola y NUNCA
    contamina ni tumba la transacción de la acción principal. Tolerante a
    fallos: cualquier error se registra en consola y no se propaga.

    El parámetro `db` se conserva por compatibilidad con las llamadas
    existentes, pero se ignora a propósito (ver arriba)."""
    from sgs.app.contexto_sesion import usuario_id_actual
    from sgs.repos.auditoria_repo import AuditoriaRepo

    try:
        usuario_id = usuario_id_actual()
        with get_session() as db_auditoria:
            AuditoriaRepo(db_auditoria).registrar(
                usuario_id, accion, entidad, entidad_id,
                valor_anterior, valor_nuevo, solicitud_relacionada_id,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[auditoria] no se pudo registrar '{accion}' sobre '{entidad}': {exc}")


def listar_auditoria(filtros: dict | None = None) -> list[dict]:
    """Bitácora de acciones para la pantalla de Auditoría (solo lectura)."""
    from sgs.repos.auditoria_repo import AuditoriaRepo

    with get_session() as db:
        return AuditoriaRepo(db).listar(filtros)


def listar_entidades_auditoria() -> list[str]:
    from sgs.repos.auditoria_repo import AuditoriaRepo

    with get_session() as db:
        return AuditoriaRepo(db).entidades_distintas()
