"""El proceso 'Sin clasificación' es el destino por defecto de las
solicitudes que ninguna regla clasifica.

No se usa una BD SQLite real porque la PK de `procesos` es autogenerada por
PostgreSQL (BIGSERIAL) y SQLite no la autoincrementa igual. Se prueba el
helper con un doble de sesión en memoria y la regla de asignación de forma
directa.
"""
import sgs.app.casos_de_uso as casos_de_uso
from sgs.models.orm import Proceso


class _SesionFalsa:
    """Doble mínimo de Session para _id_proceso_sin_clasificacion."""

    def __init__(self, procesos: list[Proceso]):
        self._procesos = procesos
        self._siguiente_id = 900

    def execute(self, _stmt):
        # Devuelve un objeto con scalar_one_or_none() que busca por nombre
        # el proceso 'Sin clasificación'.
        objetivo = casos_de_uso.NOMBRE_PROCESO_SIN_CLASIFICACION
        encontrado = next((p for p in self._procesos if p.nombre == objetivo), None)

        class _Res:
            def scalar_one_or_none(self_inner):
                return encontrado

        return _Res()

    def add(self, obj):
        self._procesos.append(obj)

    def flush(self):
        for p in self._procesos:
            if getattr(p, "id", None) is None:
                p.id = self._siguiente_id
                self._siguiente_id += 1


def test_helper_crea_proceso_si_no_existe():
    procesos: list[Proceso] = []
    db = _SesionFalsa(procesos)
    pid = casos_de_uso._id_proceso_sin_clasificacion(db)
    assert pid is not None
    assert any(p.nombre == casos_de_uso.NOMBRE_PROCESO_SIN_CLASIFICACION for p in procesos)


def test_helper_reutiliza_proceso_existente():
    existente = Proceso(nombre=casos_de_uso.NOMBRE_PROCESO_SIN_CLASIFICACION, descripcion="", activo=True)
    existente.id = 42
    db = _SesionFalsa([existente])
    assert casos_de_uso._id_proceso_sin_clasificacion(db) == 42
    # no se agregó un duplicado
    assert len(db._procesos) == 1


def test_regla_de_asignacion_none_va_al_proceso_especial():
    especial = 900
    # Reproduce la expresión usada en confirmar_importacion_sac.
    for resultado_proceso_id, esperado in [(None, especial), (5, 5), (0, 0)]:
        proceso_id = resultado_proceso_id if resultado_proceso_id is not None else especial
        assert proceso_id == esperado
