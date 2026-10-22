"""
Fixtures dos testes: API real + banco.
- Padrão (local, rápido): SQLite em memória, sem tocar em nenhum servidor.
- Com TEST_DATABASE_URL definida (CI): PostgreSQL de verdade, com as migrações já aplicadas.
  ATENÇÃO: nesse modo os testes APAGAM os dados das tabelas; por isso só aceitam banco LOCAL.
- `client`     : visitante sem login (para testar o que é público e o bloqueio 401)
- `client_cae` : simula uma pessoa da CAE já autenticada
"""
import os
from datetime import timedelta
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra os models)
from app.auth import exigir_autenticacao_cae
from app.database import Base, obter_sessao
from app.main import app
from app.models.categoria import Categoria
from app.tempo import agora_local

CATEGORIAS = ("Documentos", "Eletrônicos", "Bolsas e mochilas")

URL_POSTGRES = os.getenv("TEST_DATABASE_URL", "").strip()
USA_POSTGRES = bool(URL_POSTGRES)
HOSTS_PERMITIDOS = {"localhost", "127.0.0.1", "::1", "postgres"}
_motor_postgres = None


def pytest_collection_modifyitems(config, items):
    """Testes marcados com @pytest.mark.postgres só rodam quando há um PostgreSQL de teste."""
    if USA_POSTGRES:
        return
    pular = pytest.mark.skip(reason="precisa de PostgreSQL: defina TEST_DATABASE_URL (banco LOCAL de teste)")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(pular)


def _obter_motor_postgres():
    global _motor_postgres
    if _motor_postgres is None:
        host = urlparse(URL_POSTGRES).hostname
        if host not in HOSTS_PERMITIDOS:
            raise RuntimeError(
                f"TEST_DATABASE_URL aponta para '{host}'. Os testes APAGAM os dados, então só aceitam "
                "um banco local (localhost). Nunca use o banco do Supabase."
            )
        _motor_postgres = create_engine(URL_POSTGRES.replace("postgresql://", "postgresql+psycopg2://", 1))
    return _motor_postgres


@pytest.fixture()
def sessao_teste():
    if USA_POSTGRES:
        motor = _obter_motor_postgres()
        with motor.begin() as conexao:
            conexao.execute(text("TRUNCATE devolucoes, itens, categorias RESTART IDENTITY CASCADE"))
    else:
        motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(motor)
    sessao = sessionmaker(bind=motor, autoflush=False)()
    sessao.add_all([Categoria(nome=nome) for nome in CATEGORIAS])
    sessao.commit()
    yield sessao
    sessao.close()
    if not USA_POSTGRES:
        Base.metadata.drop_all(motor)
        motor.dispose()


@pytest.fixture()
def client(sessao_teste):
    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides.pop(exigir_autenticacao_cae, None)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_cae(sessao_teste):
    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides[exigir_autenticacao_cae] = lambda: {"id": "cae-teste"}
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def payload():
    """Monta o corpo de um registro válido; `extra` sobrescreve campos."""

    def _montar(**extra):
        dados = {
            "descricao": "Garrafa térmica azul",
            "local_encontrado": "Biblioteca",
            "encontrado_em": (agora_local() - timedelta(hours=2)).isoformat(timespec="minutes"),
        }
        dados.update(extra)
        return dados

    return _montar


@pytest.fixture()
def id_categoria(sessao_teste):
    """Devolve o id de uma categoria pelo nome."""

    def _buscar(nome):
        return sessao_teste.query(Categoria).filter_by(nome=nome).one().id

    return _buscar
