from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from sgs.models.orm import FuncionarioProceso, Permiso, Usuario, UsuarioPermiso


class PermisoRepo:
    def __init__(self, db: Session):
        self.db = db

    def obtener_o_crear(self, nombre: str) -> Permiso:
        permiso = self.db.execute(select(Permiso).where(Permiso.nombre == nombre)).scalar_one_or_none()
        if permiso is None:
            permiso = Permiso(nombre=nombre)
            self.db.add(permiso)
            self.db.flush()
        return permiso

    def usuario_tiene_permiso(self, usuario_id: int, nombre_permiso: str) -> bool:
        permiso = self.obtener_o_crear(nombre_permiso)
        stmt = select(UsuarioPermiso).where(
            UsuarioPermiso.usuario_id == usuario_id, UsuarioPermiso.permiso_id == permiso.id
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def establecer_permiso(self, usuario_id: int, nombre_permiso: str, activo: bool) -> None:
        permiso = self.obtener_o_crear(nombre_permiso)
        existente = self.db.execute(
            select(UsuarioPermiso).where(
                UsuarioPermiso.usuario_id == usuario_id, UsuarioPermiso.permiso_id == permiso.id
            )
        ).scalar_one_or_none()
        if activo and existente is None:
            self.db.add(UsuarioPermiso(usuario_id=usuario_id, permiso_id=permiso.id))
        elif not activo and existente is not None:
            self.db.delete(existente)
        self.db.flush()


class FuncionarioProcesoRepo:
    def __init__(self, db: Session):
        self.db = db

    def procesos_de(self, usuario_id: int) -> list[int]:
        stmt = select(FuncionarioProceso.proceso_id).where(FuncionarioProceso.usuario_id == usuario_id)
        return [pid for pid in self.db.execute(stmt).scalars()]

    def usuarios_por_proceso(self, proceso_ids: list[int]) -> dict[int, list[str]]:
        """Nombres de los funcionarios asignados a cada proceso
        (sección columnas: 'Funcionario' = usuario(s) que tienen ese
        proceso). Devuelve {proceso_id: [nombres]} ordenados por nombre."""
        if not proceso_ids:
            return {}
        stmt = (
            select(FuncionarioProceso.proceso_id, Usuario.nombre)
            .join(Usuario, Usuario.id == FuncionarioProceso.usuario_id)
            .where(FuncionarioProceso.proceso_id.in_(proceso_ids))
        )
        resultado: dict[int, list[str]] = {}
        for proceso_id, nombre in self.db.execute(stmt):
            resultado.setdefault(proceso_id, []).append(nombre)
        for nombres in resultado.values():
            nombres.sort()
        return resultado

    def establecer_procesos(self, usuario_id: int, proceso_ids: list[int]) -> None:
        actuales = set(self.procesos_de(usuario_id))
        deseados = set(proceso_ids)

        for proceso_id in actuales - deseados:
            fila = self.db.execute(
                select(FuncionarioProceso).where(
                    FuncionarioProceso.usuario_id == usuario_id, FuncionarioProceso.proceso_id == proceso_id
                )
            ).scalar_one_or_none()
            if fila:
                self.db.delete(fila)

        for proceso_id in deseados - actuales:
            self.db.add(FuncionarioProceso(usuario_id=usuario_id, proceso_id=proceso_id))

        self.db.flush()