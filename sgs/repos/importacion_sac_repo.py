from __future__ import annotations

import datetime as dt
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import Ciudadano, ImportacionSac, ImportacionSacDetalle, Solicitud

# Mapeo columna del exporte SAC -> columna sac_* de `solicitudes`.
# Centralizado aquí porque es el único lugar que escribe el bloque SAC.
MAPEO_CAMPOS_SAC = {
    "motivo": "sac_motivo",
    "tipoasuntosol": "sac_tipo_asunto",
    "solicitud": "sac_solicitud",
    "subclasificacion": "sac_subclasificacion",
    "detalle": "sac_detalle",
    "prioridad_caso": "sac_prioridad_caso",
    "tipoidentificacion": "sac_tipoidentificacion",
    "grupopoblacional": "sac_grupopoblacional",
    "barrera_acceso": "sac_barrera_acceso",
    "actuacionfuncionario": "sac_actuacion_funcionario",
    "usuariosac": "sac_usuario",
    "estado": "sac_estado",
}

# Ajustar únicamente este bloque si el exporte SAC usa otros encabezados.
MAPEO_CAMPOS_CIUDADANO = {
    "tipodocumento": "tipo_documento",
    "numerodocumento": "numero_documento",
    "nombreciudadano": "nombre",
    "nombre": "nombre",
    "sexo": "sexo",
    "fechanacimiento": "fecha_nacimiento",
    "telefono": "telefono",
    "correo": "correo",
    "municipioorigen": "municipio_origen_id",
    "municipioresidencia": "municipio_residencia_id",
    "poblacionpriorizada": "poblacion_priorizada",
    "regimen": "regimen_id",
    "eps": "eps_id",
    "fecharetiro": "fecha_retiro",
    "entidadresponsable": "entidad_responsable",
}

MAPEO_CAMPOS_DOCUMENTO = {
    "tipodocumento": "doc_tipo_documento",
    "numerodocumento": "doc_numero_documento",
    "nombreciudadano": "doc_nombre",
    "sexo": "doc_sexo",
    "fechanacimiento": "doc_fecha_nacimiento",
    "telefono": "doc_telefono",
    "correo": "doc_correo",
    "municipioorigen": "doc_municipio_origen",
    "municipioresidencia": "doc_municipio_residencia",
    "poblacionpriorizada": "doc_poblacion_priorizada",
    "regimen": "doc_regimen",
    "eps": "doc_eps",
    "fecharetiro": "doc_fecha_retiro",
    "entidadresponsable": "doc_entidad_responsable",
}

ALIASES_CAMPOS_CIUDADANO = {
    "tipodocumento": ("tipodocumento", "tipoidentificacion"),
    "numerodocumento": ("numerodocumento", "numeroidentificacion", "documento", "numerodoc"),
    "nombreciudadano": ("nombreciudadano", "nombre"),
    "fechanacimiento": ("fechanacimiento", "nacimiento"),
    "municipioorigen": ("municipioorigen", "municipio_origen"),
    "municipioresidencia": ("municipioresidencia", "municipio_residencia"),
    "poblacionpriorizada": ("poblacionpriorizada", "grupopoblacional"),
    "entidadresponsable": ("entidadresponsable", "entidad"),
}


def _valor_ciudadano(fila: dict, clave: str):
    if clave == "nombreciudadano":
        partes = [
            str(fila.get(nombre, "") or "").strip()
            for nombre in ("primernombre", "segundonombre", "primerapellido", "segundoapellido")
        ]
        nombre_completo = " ".join(parte for parte in partes if parte)
        if nombre_completo:
            return nombre_completo
    for alias in ALIASES_CAMPOS_CIUDADANO.get(clave, (clave,)):
        if alias in fila and fila[alias] not in (None, ""):
            return fila[alias]
    return None


def _valor_fecha(valor):
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if math.isfinite(float(valor)):
            # Excel serializa fechas contando días desde 1899-12-30.
            return dt.date(1899, 12, 30) + dt.timedelta(days=float(valor))
    if isinstance(valor, str) and valor.strip():
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return dt.datetime.strptime(valor.strip(), formato).date()
            except ValueError:
                continue
    return None


class ImportacionSacRepo:
    def __init__(self, db: Session):
        self.db = db

    def obtener_existentes(self, numeros: list[str]) -> dict[str, dict]:
        """Devuelve {numero_solicitud_sac: {campo_sac_generico: valor}} para
        las solicitudes que ya están en el sistema, en el mismo formato de
        claves genéricas que usa el motor (no sac_*), para poder comparar
        directamente contra las filas del archivo."""
        if not numeros:
            return {}
        stmt = select(Solicitud).where(Solicitud.numero_solicitud_sac.in_(numeros))
        existentes = {}
        for s in self.db.execute(stmt).scalars():
            existentes[s.numero_solicitud_sac] = {
                generico: getattr(s, columna) for generico, columna in MAPEO_CAMPOS_SAC.items()
            }
        return existentes

    def crear_o_actualizar_solicitud(self, fila: dict, numero_solicitud_sac: str, proceso_id: int | None,
                                      clasificacion_estado: str) -> tuple[Solicitud, bool]:
        """Devuelve (solicitud, es_nueva)."""
        stmt = select(Solicitud).where(Solicitud.numero_solicitud_sac == numero_solicitud_sac)
        solicitud = self.db.execute(stmt).scalar_one_or_none()
        es_nueva = solicitud is None
        if es_nueva:
            solicitud = Solicitud(numero_solicitud_sac=numero_solicitud_sac)
            self.db.add(solicitud)

        tipo_documento = _valor_ciudadano(fila, "tipodocumento")
        numero_documento = _valor_ciudadano(fila, "numerodocumento")
        if tipo_documento and numero_documento:
            ciudadano = self.db.execute(
                select(Ciudadano).where(
                    Ciudadano.tipo_documento == str(tipo_documento).strip(),
                    Ciudadano.numero_documento == str(numero_documento).strip(),
                )
            ).scalar_one_or_none()
            if ciudadano is None:
                ciudadano = Ciudadano(
                    tipo_documento=str(tipo_documento).strip(),
                    numero_documento=str(numero_documento).strip(),
                )
                self.db.add(ciudadano)
            for clave, columna in MAPEO_CAMPOS_CIUDADANO.items():
                valor = _valor_ciudadano(fila, clave)
                if valor not in (None, "") and hasattr(ciudadano, columna):
                    if columna in {"fecha_nacimiento", "fecha_retiro"}:
                        valor = _valor_fecha(valor)
                        if valor is None:
                            continue
                    if columna.endswith("_id"):
                        try:
                            valor = int(valor)
                        except (TypeError, ValueError):
                            continue
                    setattr(ciudadano, columna, valor)
            solicitud.ciudadano_id = ciudadano.id
            self.db.flush()

        for clave, columna in MAPEO_CAMPOS_DOCUMENTO.items():
            valor = _valor_ciudadano(fila, clave)
            if valor not in (None, ""):
                if columna.endswith("fecha_nacimiento") or columna.endswith("fecha_retiro"):
                    valor = _valor_fecha(valor)
                setattr(solicitud, columna, valor)
        edad = _valor_ciudadano(fila, "edad")
        if edad not in (None, ""):
            try:
                solicitud.doc_edad = int(edad)
            except (TypeError, ValueError):
                pass

        for generico, columna in MAPEO_CAMPOS_SAC.items():
            if generico in fila and fila.get(generico) not in (None, ""):
                setattr(solicitud, columna, fila.get(generico))
        if not solicitud.sac_tipo_asunto and fila.get("tipo_pqr"):
            solicitud.sac_tipo_asunto = fila["tipo_pqr"]
        if not solicitud.sac_detalle and fila.get("detallesolicitud"):
            solicitud.sac_detalle = fila["detallesolicitud"]
        if not solicitud.sac_usuario and fila.get("usuario"):
            solicitud.sac_usuario = fila["usuario"]
        if not solicitud.sac_estado and fila.get("estadosolicitud"):
            solicitud.sac_estado = fila["estadosolicitud"]
        actuaciones = [
            str(fila.get(clave, "") or "").strip()
            for clave in (
                "actuacionfuncionario1",
                "actuacionfuncionario2",
                "actuacionfuncionario3",
                "actuacionfuncionario4",
            )
            if str(fila.get(clave, "") or "").strip()
        ]
        if actuaciones:
            solicitud.sac_actuacion_funcionario = "\n".join(actuaciones)
        if fila.get("fechasolicitud") not in (None, ""):
            valor_fecha = fila["fechasolicitud"]
            solicitud.sac_fecha_ingreso = (
                valor_fecha if isinstance(valor_fecha, dt.datetime)
                else _valor_fecha(valor_fecha)
            )

        solicitud.proceso_id = proceso_id
        solicitud.clasificacion_estado = clasificacion_estado
        solicitud.actualizado_en = dt.datetime.utcnow()
        self.db.flush()
        return solicitud, es_nueva

    def registrar_importacion(
        self, archivo_nombre: str, usuario_id: int, conteos: dict, detalle: list[tuple[int, str]]
    ) -> ImportacionSac:
        """`detalle` es [(solicitud_id, accion), ...]."""
        importacion = ImportacionSac(
            archivo_nombre=archivo_nombre,
            usuario_id=usuario_id,
            total_registros=conteos.get("total"),
            nuevos=conteos.get("nuevos"),
            existentes=conteos.get("actualizados", 0) + conteos.get("sin_cambios", 0),
            errores=conteos.get("errores"),
            sin_clasificar=conteos.get("sin_clasificar"),
        )
        self.db.add(importacion)
        self.db.flush()

        for solicitud_id, accion in detalle:
            self.db.add(
                ImportacionSacDetalle(importacion_id=importacion.id, solicitud_id=solicitud_id, accion=accion)
            )
        self.db.flush()
        return importacion