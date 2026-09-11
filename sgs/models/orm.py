"""
Modelos SQLAlchemy — mapeo 1:1 de schema.sql.

No contienen lógica de negocio: eso vive en sgs/motores/. Aquí solo
estructura y relaciones.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CatalogoEps(Base):
    __tablename__ = "catalogo_eps"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class CatalogoRegimen(Base):
    __tablename__ = "catalogo_regimen"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class CatalogoMunicipio(Base):
    __tablename__ = "catalogo_municipio"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Festivo(Base):
    __tablename__ = "festivos"

    fecha: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)


class ParametroGeneral(Base):
    __tablename__ = "parametros_generales"

    clave: Mapped[str] = mapped_column(String, primary_key=True)
    valor: Mapped[Optional[str]] = mapped_column(Text)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)


class Proceso(Base):
    __tablename__ = "procesos"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class ReglaClasificacion(Base):
    __tablename__ = "reglas_clasificacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proceso_id: Mapped[int] = mapped_column(ForeignKey("procesos.id"), nullable=False)
    orden_evaluacion: Mapped[int] = mapped_column(SmallInteger, default=100)
    tipo_regla: Mapped[str] = mapped_column(String, nullable=False)  # 'excepcion' | 'normal'
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)

    condiciones: Mapped[list["CondicionRegla"]] = relationship(
        back_populates="regla", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("tipo_regla IN ('excepcion','normal')", name="ck_tipo_regla"),
    )


class CondicionRegla(Base):
    __tablename__ = "condiciones_regla"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    regla_id: Mapped[int] = mapped_column(ForeignKey("reglas_clasificacion.id"), nullable=False)
    campo: Mapped[str] = mapped_column(String, nullable=False)
    operador: Mapped[str] = mapped_column(String, nullable=False)  # igual_a | distinto_de | contiene
    valores: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    regla: Mapped["ReglaClasificacion"] = relationship(back_populates="condiciones")


class ReglaTiemposSolicitud(Base):
    __tablename__ = "reglas_tiempos_solicitud"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    solicitud: Mapped[str] = mapped_column(String, nullable=False)
    motivo: Mapped[Optional[str]] = mapped_column(String)  # NULL = regla general
    dias_habiles: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (UniqueConstraint("solicitud", "motivo", name="uq_solicitud_motivo"),)


class ReglaTiemposPrioridad(Base):
    __tablename__ = "reglas_tiempos_prioridad"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    prioridad_caso: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    dias_habiles: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    es_dia_calendario: Mapped[bool] = mapped_column(Boolean, default=False)


class ReglaTiemposEps(Base):
    __tablename__ = "reglas_tiempos_eps"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    eps_id: Mapped[int] = mapped_column(ForeignKey("catalogo_eps.id"), unique=True, nullable=False)
    dias_habiles: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class Permiso(Base):
    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class UsuarioPermiso(Base):
    __tablename__ = "usuario_permiso"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    permiso_id: Mapped[int] = mapped_column(ForeignKey("permisos.id"), primary_key=True)


class FuncionarioProceso(Base):
    __tablename__ = "funcionario_proceso"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    proceso_id: Mapped[int] = mapped_column(ForeignKey("procesos.id"), primary_key=True)


class ParametrosSemaforizacion(Base):
    __tablename__ = "parametros_semaforizacion"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    dias_habiles_verde_hasta: Mapped[int] = mapped_column(SmallInteger, default=1)
    dias_habiles_amarillo_hasta: Mapped[int] = mapped_column(SmallInteger, default=2)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_sac: Mapped[Optional[str]] = mapped_column(String, unique=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    rol: Mapped[str] = mapped_column(String, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Solicitud(Base):
    __tablename__ = "solicitudes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_solicitud_sac: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    ciudadano_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ciudadanos.id"))

    # Bloque SAC (solo lectura desde la app, lo escribe el importador)
    doc_tipo_documento: Mapped[Optional[str]] = mapped_column(Text)
    doc_numero_documento: Mapped[Optional[str]] = mapped_column(Text)
    doc_nombre: Mapped[Optional[str]] = mapped_column(Text)
    doc_sexo: Mapped[Optional[str]] = mapped_column(Text)
    doc_fecha_nacimiento: Mapped[Optional[dt.date]] = mapped_column(Date)
    doc_edad: Mapped[Optional[int]] = mapped_column(SmallInteger)
    doc_telefono: Mapped[Optional[str]] = mapped_column(Text)
    doc_correo: Mapped[Optional[str]] = mapped_column(Text)
    doc_municipio_origen: Mapped[Optional[str]] = mapped_column(Text)
    doc_municipio_residencia: Mapped[Optional[str]] = mapped_column(Text)
    doc_poblacion_priorizada: Mapped[Optional[str]] = mapped_column(Text)
    doc_regimen: Mapped[Optional[str]] = mapped_column(Text)
    doc_eps: Mapped[Optional[str]] = mapped_column(Text)
    doc_fecha_retiro: Mapped[Optional[dt.date]] = mapped_column(Date)
    doc_entidad_responsable: Mapped[Optional[str]] = mapped_column(Text)
    sac_motivo: Mapped[Optional[str]] = mapped_column(Text)
    sac_tipo_asunto: Mapped[Optional[str]] = mapped_column(Text)
    sac_solicitud: Mapped[Optional[str]] = mapped_column(Text)
    sac_subclasificacion: Mapped[Optional[str]] = mapped_column(Text)
    sac_detalle: Mapped[Optional[str]] = mapped_column(Text)
    sac_prioridad_caso: Mapped[Optional[str]] = mapped_column(Text)
    sac_barrera_acceso: Mapped[Optional[str]] = mapped_column(Text)
    sac_actuacion_funcionario: Mapped[Optional[str]] = mapped_column(Text)
    sac_usuario: Mapped[Optional[str]] = mapped_column(Text)
    sac_estado: Mapped[Optional[str]] = mapped_column(Text)
    sac_tipoidentificacion: Mapped[Optional[str]] = mapped_column(Text)
    sac_grupopoblacional: Mapped[Optional[str]] = mapped_column(Text)
    sac_fecha_ingreso: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)

    proceso_id: Mapped[Optional[int]] = mapped_column(ForeignKey("procesos.id"))
    clasificacion_estado: Mapped[str] = mapped_column(String, default="sin_clasificar")

    funcionario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    estado_gestion: Mapped[str] = mapped_column(String, default="pendiente")
    observaciones: Mapped[Optional[str]] = mapped_column(Text)

    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    actualizado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Ciudadano(Base):
    __tablename__ = "ciudadanos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_documento: Mapped[str] = mapped_column(String, nullable=False)
    numero_documento: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[Optional[str]] = mapped_column(String)
    sexo: Mapped[Optional[str]] = mapped_column(String)
    fecha_nacimiento: Mapped[Optional[dt.date]] = mapped_column(Date)
    telefono: Mapped[Optional[str]] = mapped_column(String)
    correo: Mapped[Optional[str]] = mapped_column(String)
    municipio_origen_id: Mapped[Optional[int]] = mapped_column(SmallInteger)
    municipio_residencia_id: Mapped[Optional[int]] = mapped_column(SmallInteger)
    poblacion_priorizada: Mapped[Optional[str]] = mapped_column(String)
    regimen_id: Mapped[Optional[int]] = mapped_column(SmallInteger)
    eps_id: Mapped[Optional[int]] = mapped_column(SmallInteger)
    fecha_retiro: Mapped[Optional[dt.date]] = mapped_column(Date)
    entidad_responsable: Mapped[Optional[str]] = mapped_column(String)
    actualizado_en: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tipo_documento", "numero_documento", name="uq_ciudadano_doc"),
    )


class VistaColumnasUsuario(Base):
    __tablename__ = "vistas_columnas_usuario"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    pantalla: Mapped[str] = mapped_column(String, primary_key=True)
    configuracion: Mapped[dict] = mapped_column(JSON, nullable=False)


class Traslado(Base):
    __tablename__ = "traslados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), unique=True, nullable=False)
    fecha_traslado: Mapped[Optional[dt.date]] = mapped_column(Date)
    institucion_competente: Mapped[Optional[str]] = mapped_column(Text)
    oportunidad_dias_habiles: Mapped[Optional[int]] = mapped_column(SmallInteger)
    indicador_oportunidad: Mapped[Optional[str]] = mapped_column(String)
    fecha_limite_respuesta: Mapped[Optional[dt.date]] = mapped_column(Date)


class Respuesta(Base):
    __tablename__ = "respuestas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), unique=True, nullable=False)
    hubo_respuesta: Mapped[Optional[str]] = mapped_column(String)
    decision: Mapped[Optional[str]] = mapped_column(String)
    respuesta_entidad: Mapped[Optional[str]] = mapped_column(Text)
    notificacion_usuario: Mapped[Optional[str]] = mapped_column(Text)
    fecha_respuesta: Mapped[Optional[dt.date]] = mapped_column(Date)
    oportunidad_respuesta: Mapped[Optional[str]] = mapped_column(String)


class EnteControl(Base):
    __tablename__ = "entes_control"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), nullable=False)
    radicado: Mapped[Optional[str]] = mapped_column(Text)
    entidad: Mapped[Optional[str]] = mapped_column(Text)
    fecha_reporte: Mapped[Optional[dt.date]] = mapped_column(Date)
    respuesta_posterior: Mapped[Optional[str]] = mapped_column(Text)


class ImportacionSac(Base):
    __tablename__ = "importaciones_sac"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    archivo_nombre: Mapped[str] = mapped_column(String, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    total_registros: Mapped[Optional[int]] = mapped_column(Integer)
    nuevos: Mapped[Optional[int]] = mapped_column(Integer)
    existentes: Mapped[Optional[int]] = mapped_column(Integer)
    errores: Mapped[Optional[int]] = mapped_column(Integer)
    sin_clasificar: Mapped[Optional[int]] = mapped_column(Integer)


class ImportacionSacDetalle(Base):
    __tablename__ = "importaciones_sac_detalle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    importacion_id: Mapped[int] = mapped_column(ForeignKey("importaciones_sac.id"), nullable=False)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), nullable=False)
    accion: Mapped[str] = mapped_column(String, nullable=False)


class Asignacion(Base):
    __tablename__ = "asignaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), nullable=False)
    funcionario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    proceso_id: Mapped[Optional[int]] = mapped_column(ForeignKey("procesos.id"))
    fecha_inicio: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    fecha_fin: Mapped[Optional[dt.datetime]] = mapped_column(DateTime)
    origen: Mapped[str] = mapped_column(String, nullable=False)
    motivo_cambio: Mapped[Optional[str]] = mapped_column(Text)
    usuario_que_asigna: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))