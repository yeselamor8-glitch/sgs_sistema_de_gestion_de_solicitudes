# Sistema de Gestión de Solicitudes — scaffold Fase 4

## Estructura

```
sgs/
  config/
    settings.py     # SGS_DB_URL, entorno local/servidor, umbrales semáforo
    db.py           # engine + get_session()
  models/
    orm.py          # modelos SQLAlchemy (mapean schema.sql)
  motores/           # lógica de dominio pura, sin SQLAlchemy
    motor_tiempos.py       # fecha límite de respuesta (jerarquía Riesgo Vital > Priorizado > EPS > Solicitud > fallback)
    motor_semaforo.py      # semáforo general (verde/amarillo/rojo) sobre fecha límite
    motor_clasificacion.py # motor de reglas OR-en-columna / AND-entre-columnas / excepciones con prioridad
  repos/              # acceso a datos, un repo por agregado
  app/
    casos_de_uso.py   # ÚNICA capa que la UI (PySide6) debe llamar
  tests/
    test_motores.py   # pytest de los 3 motores contra casos reales de las maestras
schema.sql             # DDL de PostgreSQL (Fase 3)
```

## Cómo correr las pruebas

```bash
pip install -r requirements.txt
PYTHONPATH=. pytest sgs/tests/ -v
```

## Variable de entorno para local ↔ servidor

```bash
export SGS_DB_URL="postgresql+psycopg2://usuario:clave@localhost:5432/sgs_local"
# más adelante, sin tocar código:
export SGS_DB_URL="postgresql+psycopg2://usuario:clave@servidor-institucional:5432/sgs"
```

## Regla de oro respetada en todo el scaffold

`UI → capa de aplicación → motores de dominio → repositorios → SQLAlchemy → PostgreSQL`

La UI (Fase 5, PySide6) solo debe importar de `sgs.app.casos_de_uso`. Nunca de `sgs.models`, `sgs.repos` ni `sgs.motores` directamente — así la interfaz nunca depende de detalles de base de datos, y los motores se pueden seguir probando sin levantar PostgreSQL.

## Pendiente para cerrar la Fase 4 completamente

- Repos/casos de uso para: importación SAC, solicitudes de cambio, notificaciones, auditoría (mismo patrón que `solicitud_repo.py` / `reglas_repo.py`).
- Migraciones (Alembic) sobre `schema.sql` para poder versionar cambios de esquema.
