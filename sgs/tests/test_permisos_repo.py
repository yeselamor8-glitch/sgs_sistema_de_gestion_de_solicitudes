import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sgs.models.orm import Base, FuncionarioProceso, Permiso, Proceso, Solicitud, Usuario, UsuarioPermiso
from sgs.repos.permisos_repo import FuncionarioProcesoRepo

TABLAS = [
    Usuario.__table__,
    Proceso.__table__,
    FuncionarioProceso.__table__,
    Permiso.__table__,
    UsuarioPermiso.__table__,
    Solicitud.__table__,
]


@pytest.fixture()
def sesion():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=TABLAS)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Proceso(id=1, nombre="RECLAMACIONES"))
    db.add(Proceso(id=2, nombre="TRASLADOS"))
    db.add(Usuario(id=10, username="a", nombre="Ana", password_hash="x", rol="FUNCIONARIO"))
    db.add(Usuario(id=11, username="l", nombre="Luis", password_hash="x", rol="FUNCIONARIO"))
    db.add(Usuario(id=12, username="e", nombre="Eva", password_hash="x", rol="FUNCIONARIO"))
    db.add(FuncionarioProceso(usuario_id=10, proceso_id=1))
    db.add(FuncionarioProceso(usuario_id=11, proceso_id=1))
    db.add(FuncionarioProceso(usuario_id=12, proceso_id=2))
    db.commit()
    yield db
    db.close()


def test_usuarios_por_proceso_devuelve_nombres_ordenados(sesion):
    repo = FuncionarioProcesoRepo(sesion)
    assert repo.usuarios_por_proceso([1, 2]) == {1: ["Ana", "Luis"], 2: ["Eva"]}
    assert repo.usuarios_por_proceso([2]) == {2: ["Eva"]}


def test_usuarios_por_proceso_sin_ids_devuelve_vacio(sesion):
    repo = FuncionarioProcesoRepo(sesion)
    assert repo.usuarios_por_proceso([]) == {}