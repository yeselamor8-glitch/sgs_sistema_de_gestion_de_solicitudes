-- =====================================================================
-- SISTEMA DE GESTIÓN DE SOLICITUDES — Esquema PostgreSQL (Fase 3)
-- =====================================================================
-- Convenciones:
--   * PK: id BIGSERIAL salvo donde se indique clave natural.
--   * Timestamps: created_at / updated_at en tablas mutables relevantes.
--   * Todo lo "bloque SAC" es de solo lectura desde la app (solo lo
--     escribe el importador); lo "bloque gestión" es editable según
--     nivel de permiso.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid(), crypt() para hash de password

-- ---------------------------------------------------------------------
-- 1. CATÁLOGOS
-- ---------------------------------------------------------------------

CREATE TABLE catalogo_eps (
    id              SMALLSERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE catalogo_regimen (
    id              SMALLSERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE
);

CREATE TABLE catalogo_municipio (
    id              SMALLSERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE
);

CREATE TABLE festivos (
    fecha           DATE PRIMARY KEY,
    descripcion     TEXT
);

-- ---------------------------------------------------------------------
-- 2. CIUDADANOS (maestro — valores más recientes conocidos)
-- ---------------------------------------------------------------------

CREATE TABLE ciudadanos (
    id                  BIGSERIAL PRIMARY KEY,
    tipo_documento      TEXT NOT NULL,
    numero_documento    TEXT NOT NULL,
    nombre              TEXT,
    sexo                TEXT,
    fecha_nacimiento    DATE,
    telefono            TEXT,
    correo              TEXT,
    municipio_origen_id     SMALLINT REFERENCES catalogo_municipio(id),
    municipio_residencia_id SMALLINT REFERENCES catalogo_municipio(id),
    poblacion_priorizada    TEXT,
    regimen_id          SMALLINT REFERENCES catalogo_regimen(id),
    eps_id              SMALLINT REFERENCES catalogo_eps(id),
    fecha_retiro        DATE,
    entidad_responsable TEXT,
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tipo_documento, numero_documento)
);

-- ---------------------------------------------------------------------
-- 3. PROCESOS Y MOTOR DE CLASIFICACIÓN
-- ---------------------------------------------------------------------

CREATE TABLE procesos (
    id              SMALLSERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE,
    descripcion     TEXT,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

-- 20 procesos semilla (ver informe de análisis de maestras)
INSERT INTO procesos (nombre, descripcion) VALUES
    ('ACCESO_SERVICIOS_SALUD',           'Acceso a los servicios de salud (Savia Salud, base)'),
    ('ACCESO_SERVICIOS_SALUD_ESPECIALISTAS', 'Acceso a servicios de salud — especialistas (Savia Salud)'),
    ('ACCESO_SERVICIOS_SALUD_OTRAS_EPS',  'Acceso a servicios de salud — otras EPS'),
    ('ACCESO_SERVICIOS_SALUD_SURA_EPS',   'Acceso a servicios de salud — Sura EPS (filtro pendiente de definir)'),
    ('ACREDITACION_PERMANENCIA',          'Acreditación de permanencia'),
    ('AFILIACIONES',                      'Afiliaciones — subclasificación Excepcional'),
    ('AFILIACIONES_INFO',                 'Afiliaciones — información/orientación'),
    ('AFILIACIONES_TRANSACCIONALES',      'Afiliaciones — subclasificación Transaccional'),
    ('DISMINUCION_NIVEL',                 'Disminución o cambio de nivel'),
    ('LISTADO_CENSAL',                    'Listado censal / población especial'),
    ('NOVEDAD_DOCUMENTOS',                'Inconsistencia en documento'),
    ('PORTABILIDADES',                    'Portabilidad'),
    ('SALUD_PUBLICA',                     'Salud pública (excluye Discapacidad)'),
    ('SOAT',                              'SOAT / tránsito / accidente'),
    ('DISCAPACIDAD',                      'Discapacidad'),
    ('MIGRANTES_IRREGULARES_PPNA',        'Migrantes irregulares / PPNA (tipoidentificacion=PO)'),
    ('MOVILIDAD',                         'Movilidad (cambio de régimen)'),
    ('RECLAMACIONES',                     'Reclamaciones y quejas'),
    ('TRASLADO',                          'Traslado (EPS/municipio)'),
    ('URGENTES_Y_PRIORITARIOS',           'Urgentes y prioritarios');

CREATE TABLE reglas_clasificacion (
    id                  BIGSERIAL PRIMARY KEY,
    proceso_id          SMALLINT NOT NULL REFERENCES procesos(id),
    orden_evaluacion    SMALLINT NOT NULL DEFAULT 100,
    tipo_regla          TEXT NOT NULL CHECK (tipo_regla IN ('excepcion', 'normal')),
    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    descripcion         TEXT
);

CREATE TABLE condiciones_regla (
    id              BIGSERIAL PRIMARY KEY,
    regla_id        BIGINT NOT NULL REFERENCES reglas_clasificacion(id) ON DELETE CASCADE,
    campo           TEXT NOT NULL,          -- ej. 'motivo', 'tipoasuntosol', 'detalle', 'tipoidentificacion'
    operador        TEXT NOT NULL CHECK (operador IN ('igual_a', 'distinto_de', 'contiene')),
    valores         TEXT[] NOT NULL          -- varios valores = OR dentro de la condición
);

-- ---------------------------------------------------------------------
-- 4. TIEMPOS DE RESPUESTA (parámetros administrables)
-- ---------------------------------------------------------------------

CREATE TABLE reglas_tiempos_solicitud (
    id              SMALLSERIAL PRIMARY KEY,
    solicitud       TEXT NOT NULL,          -- valor del campo 'solicitud' SAC
    motivo          TEXT,                    -- NULL = aplica sin importar motivo;
                                              -- 'Reclamación'/'Queja' = override específico
                                              -- (hallazgo maestra DISCAPACIDAD: el Excel actual
                                              -- tiene esta tabla pero el VLOOKUP nunca la alcanza,
                                              -- es un bug que este sistema corrige)
    dias_habiles    SMALLINT NOT NULL,
    UNIQUE (solicitud, motivo)
);

CREATE TABLE reglas_tiempos_prioridad (
    id              SMALLSERIAL PRIMARY KEY,
    prioridad_caso  TEXT NOT NULL UNIQUE,   -- 'Riesgo Vital', 'Priorizado'
    dias_habiles    SMALLINT NOT NULL,
    es_dia_calendario BOOLEAN NOT NULL DEFAULT FALSE  -- Riesgo Vital usa +1 día calendario, no hábil
);

CREATE TABLE reglas_tiempos_eps (
    id              SMALLSERIAL PRIMARY KEY,
    eps_id          SMALLINT NOT NULL REFERENCES catalogo_eps(id) UNIQUE,
    dias_habiles    SMALLINT NOT NULL
);

CREATE TABLE parametros_semaforizacion (
    id                          SMALLINT PRIMARY KEY DEFAULT 1,
    dias_habiles_verde_hasta    SMALLINT NOT NULL DEFAULT 1,
    dias_habiles_amarillo_hasta SMALLINT NOT NULL DEFAULT 2,
    CHECK (id = 1)
);
INSERT INTO parametros_semaforizacion DEFAULT VALUES;

-- ---------------------------------------------------------------------
-- 5. USUARIOS, ROLES, PERMISOS
-- ---------------------------------------------------------------------

CREATE TABLE usuarios (
    id              BIGSERIAL PRIMARY KEY,
    codigo_sac      TEXT UNIQUE,             -- código en hoja USUARIOS / columna Y de MAESTRA
    username        TEXT NOT NULL UNIQUE,
    nombre          TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL CHECK (rol IN ('ADMINISTRADOR', 'FUNCIONARIO')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE permisos (
    id              SMALLSERIAL PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE     -- ej. 'importar_sac', 'ver_reportes_globales'
);

CREATE TABLE usuario_permiso (
    usuario_id      BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    permiso_id      SMALLINT NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, permiso_id)
);

CREATE TABLE funcionario_proceso (
    usuario_id      BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    proceso_id      SMALLINT NOT NULL REFERENCES procesos(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, proceso_id)
);

CREATE TABLE niveles_edicion_campo (
    id              SMALLSERIAL PRIMARY KEY,
    campo           TEXT NOT NULL,
    proceso_id      SMALLINT REFERENCES procesos(id),  -- NULL = aplica a todos los procesos
    nivel           SMALLINT NOT NULL CHECK (nivel IN (1, 2, 3)),
    UNIQUE (campo, proceso_id)
);

-- ---------------------------------------------------------------------
-- 6. SOLICITUDES (núcleo)
-- ---------------------------------------------------------------------

CREATE TABLE solicitudes (
    id                      BIGSERIAL PRIMARY KEY,
    numero_solicitud_sac    TEXT NOT NULL UNIQUE,   -- identificador principal, NUNCA el radicado
    ciudadano_id            BIGINT REFERENCES ciudadanos(id),

    -- ---- Bloque SAC: snapshot al momento de la importación, solo lectura ----
    doc_tipo_documento      TEXT,
    doc_numero_documento    TEXT,
    doc_nombre              TEXT,
    doc_sexo                TEXT,
    doc_fecha_nacimiento    DATE,
    doc_edad                SMALLINT,
    doc_telefono            TEXT,
    doc_correo              TEXT,
    doc_municipio_origen        TEXT,
    doc_municipio_residencia    TEXT,
    doc_poblacion_priorizada    TEXT,
    doc_regimen              TEXT,
    doc_eps                  TEXT,
    doc_fecha_retiro         DATE,
    doc_entidad_responsable  TEXT,

    sac_motivo               TEXT,
    sac_tipo_asunto           TEXT,
    sac_solicitud             TEXT,
    sac_subclasificacion      TEXT,
    sac_detalle               TEXT,
    sac_barrera_acceso        TEXT,
    sac_prioridad_caso         TEXT,
    sac_actuacion_funcionario  TEXT,
    sac_usuario                TEXT,
    sac_fecha_ingreso           TIMESTAMPTZ,
    sac_estado                  TEXT,
    sac_grupopoblacional        TEXT,
    sac_tipoidentificacion      TEXT,

    -- ---- Clasificación (resultado del motor de reglas) ----
    proceso_id               SMALLINT REFERENCES procesos(id),
    clasificacion_estado      TEXT NOT NULL DEFAULT 'sin_clasificar'
        CHECK (clasificacion_estado IN ('clasificada', 'sin_clasificar', 'conflicto')),

    -- ---- Asignación vigente (denormalizada — fuente de verdad en `asignaciones`) ----
    funcionario_id            BIGINT REFERENCES usuarios(id),

    -- ---- Gestión interna ----
    estado_gestion            TEXT NOT NULL DEFAULT 'pendiente',  -- catálogo a definir con el usuario
    observaciones              TEXT,

    -- ---- Calidad de verificación (Opción B — columnas planas, 1:1) ----
    calidad_dato_cumple        TEXT,       -- 'SI' | 'NO' | NULL
    calidad_dato_detalle       TEXT,
    calidad_dato_subsanado     TEXT,
    calidad_docs_cumple        TEXT,
    calidad_docs_detalle       TEXT,
    calidad_docs_subsanado     TEXT,

    creado_en                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_solicitudes_proceso ON solicitudes(proceso_id);
CREATE INDEX idx_solicitudes_funcionario ON solicitudes(funcionario_id);
CREATE INDEX idx_solicitudes_ciudadano ON solicitudes(ciudadano_id);
CREATE INDEX idx_solicitudes_clasificacion ON solicitudes(clasificacion_estado);
CREATE INDEX idx_solicitudes_fecha_ingreso ON solicitudes(sac_fecha_ingreso);

-- ---------------------------------------------------------------------
-- 7. ASIGNACIONES (historial de funcionario/proceso por solicitud)
-- ---------------------------------------------------------------------

CREATE TABLE asignaciones (
    id                  BIGSERIAL PRIMARY KEY,
    solicitud_id        BIGINT NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
    funcionario_id       BIGINT REFERENCES usuarios(id),
    proceso_id           SMALLINT REFERENCES procesos(id),
    fecha_inicio          TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_fin              TIMESTAMPTZ,             -- NULL = vigente
    origen                TEXT NOT NULL CHECK (origen IN ('importacion', 'reasignacion_manual', 'cambio_aprobado')),
    motivo_cambio          TEXT,
    usuario_que_asigna     BIGINT REFERENCES usuarios(id)
);

CREATE INDEX idx_asignaciones_solicitud ON asignaciones(solicitud_id);
CREATE UNIQUE INDEX idx_asignaciones_vigente ON asignaciones(solicitud_id) WHERE fecha_fin IS NULL;

-- ---------------------------------------------------------------------
-- 8. TRASLADO (primer traslado — institución competente)
-- ---------------------------------------------------------------------

CREATE TABLE traslados (
    id                      BIGSERIAL PRIMARY KEY,
    solicitud_id             BIGINT NOT NULL UNIQUE REFERENCES solicitudes(id) ON DELETE CASCADE,
    fecha_traslado            DATE,                 -- manual
    institucion_competente     TEXT,
    oportunidad_dias_habiles    SMALLINT,             -- calculado: NETWORKDAYS(ingreso, traslado) - 1 - festivos
    indicador_oportunidad       TEXT CHECK (indicador_oportunidad IN ('A_TIEMPO', 'CERCA_DE_VENCIMIENTO', 'VENCIDO')),
    fecha_limite_respuesta       DATE                  -- calculado por el motor de tiempos (ver sección 4)
);

-- ---------------------------------------------------------------------
-- 9. RESPUESTA
-- ---------------------------------------------------------------------

CREATE TABLE respuestas (
    id                      BIGSERIAL PRIMARY KEY,
    solicitud_id             BIGINT NOT NULL UNIQUE REFERENCES solicitudes(id) ON DELETE CASCADE,
    hubo_respuesta            TEXT CHECK (hubo_respuesta IN ('SI', 'NO', 'N_A')),
    decision                  TEXT,                  -- calculado: CERRAR_SAC | REMITIR_ENTE_CONTROL | N_A
    respuesta_entidad          TEXT,
    notificacion_usuario        TEXT,
    fecha_respuesta            DATE,
    oportunidad_respuesta        TEXT CHECK (oportunidad_respuesta IN ('OPORTUNA', 'INOPORTUNA', 'NO_HUBO_RESPUESTA', 'INCONSISTENTE'))
);

-- ---------------------------------------------------------------------
-- 10. ENTE DE CONTROL (segundo traslado — aquí sí vive el radicado)
-- ---------------------------------------------------------------------

CREATE TABLE entes_control (
    id                  BIGSERIAL PRIMARY KEY,
    solicitud_id         BIGINT NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
    radicado              TEXT,
    entidad                TEXT,
    fecha_reporte           DATE,
    respuesta_posterior      TEXT
);

CREATE INDEX idx_entes_control_solicitud ON entes_control(solicitud_id);

-- ---------------------------------------------------------------------
-- 11. SOLICITUDES DE CAMBIO
-- ---------------------------------------------------------------------

CREATE TABLE solicitudes_cambio (
    id                      BIGSERIAL PRIMARY KEY,
    solicitud_id             BIGINT NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
    tipo                      TEXT NOT NULL CHECK (tipo IN ('reasignacion_proceso', 'edicion_campo')),

    -- reasignación de proceso
    proceso_actual_id          SMALLINT REFERENCES procesos(id),
    proceso_solicitado_id       SMALLINT REFERENCES procesos(id),

    -- edición de campo restringido
    campo                      TEXT,
    valor_actual                TEXT,
    valor_propuesto              TEXT,

    motivo                     TEXT NOT NULL,
    estado                     TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    observacion_admin            TEXT,

    solicitado_por               BIGINT NOT NULL REFERENCES usuarios(id),
    aprobado_por                 BIGINT REFERENCES usuarios(id),
    creado_en                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resuelto_en                  TIMESTAMPTZ
);

CREATE INDEX idx_solicitudes_cambio_estado ON solicitudes_cambio(estado);
CREATE INDEX idx_solicitudes_cambio_solicitud ON solicitudes_cambio(solicitud_id);

-- ---------------------------------------------------------------------
-- 12. NOTIFICACIONES
-- ---------------------------------------------------------------------

CREATE TABLE notificaciones (
    id              BIGSERIAL PRIMARY KEY,
    usuario_id       BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo             TEXT NOT NULL,
    mensaje           TEXT NOT NULL,
    leida             BOOLEAN NOT NULL DEFAULT FALSE,
    referencia_tipo    TEXT,          -- ej. 'solicitud_cambio'
    referencia_id       BIGINT,
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notificaciones_usuario_no_leidas ON notificaciones(usuario_id) WHERE leida = FALSE;

-- ---------------------------------------------------------------------
-- 13. IMPORTACIÓN SAC
-- ---------------------------------------------------------------------

CREATE TABLE importaciones_sac (
    id              BIGSERIAL PRIMARY KEY,
    archivo_nombre   TEXT NOT NULL,
    usuario_id        BIGINT NOT NULL REFERENCES usuarios(id),
    fecha             TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_registros    INTEGER,
    nuevos             INTEGER,
    existentes         INTEGER,
    errores            INTEGER,
    sin_clasificar      INTEGER
);

CREATE TABLE importaciones_sac_detalle (
    id                  BIGSERIAL PRIMARY KEY,
    importacion_id        BIGINT NOT NULL REFERENCES importaciones_sac(id) ON DELETE CASCADE,
    solicitud_id           BIGINT NOT NULL REFERENCES solicitudes(id),
    accion                 TEXT NOT NULL CHECK (accion IN ('nuevo', 'actualizado', 'sin_cambios', 'error'))
);

CREATE INDEX idx_importaciones_detalle_importacion ON importaciones_sac_detalle(importacion_id);

-- ---------------------------------------------------------------------
-- 14. AUDITORÍA (bitácora genérica — complementa el historial de negocio)
-- ---------------------------------------------------------------------

CREATE TABLE auditoria (
    id                  BIGSERIAL PRIMARY KEY,
    usuario_id            BIGINT REFERENCES usuarios(id),
    accion                 TEXT NOT NULL,
    entidad                 TEXT NOT NULL,        -- ej. 'solicitud', 'usuario', 'regla_clasificacion'
    entidad_id               BIGINT,
    valor_anterior             JSONB,
    valor_nuevo                JSONB,
    solicitud_relacionada_id     BIGINT REFERENCES solicitudes(id),
    fecha                       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_auditoria_solicitud ON auditoria(solicitud_relacionada_id);
CREATE INDEX idx_auditoria_fecha ON auditoria(fecha);

-- ---------------------------------------------------------------------
-- ---------------------------------------------------------------------
-- 15b. PARÁMETROS GENERALES (clave/valor simple)
-- ---------------------------------------------------------------------

CREATE TABLE parametros_generales (
    clave       TEXT PRIMARY KEY,
    valor       TEXT,
    descripcion TEXT
);

-- ---------------------------------------------------------------------
-- 15. VISTAS DE COLUMNAS Y HERRAMIENTAS
-- ---------------------------------------------------------------------

CREATE TABLE vistas_columnas_usuario (
    usuario_id       BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    pantalla          TEXT NOT NULL,           -- 'solicitudes', 'mis_solicitudes', etc.
    configuracion       JSONB NOT NULL,          -- columnas visibles, orden, ancho
    PRIMARY KEY (usuario_id, pantalla)
);

CREATE TABLE herramientas (
    id              SMALLSERIAL PRIMARY KEY,
    nombre           TEXT NOT NULL UNIQUE,
    tipo             TEXT NOT NULL,             -- punto de extensión, a definir en Fase 14
    configuracion      JSONB,
    activo            BOOLEAN NOT NULL DEFAULT TRUE
);

-- =====================================================================
-- Fin del esquema Fase 3
-- =====================================================================