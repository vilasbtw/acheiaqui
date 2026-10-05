"""
Fixtures dos testes: banco SQLite em memória (sem tocar no Supabase) e API real.
- `client`     : visitante sem login (para testar o que é público e o bloqueio 401)
- `client_cae` : simula uma pessoa da CAE já autenticada
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra os models)
from app.auth import exigir_autenticacao_cae
from app.database import Base, obter_sessao
from app.main import app
from app.models.categoria import Categoria
from app.tempo import agora_local

CATEGORIAS = ("Documentos", "Eletrônicos", "Bolsas e mochilas")


@pytest.fixture()
def sessao_teste():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(motor)
    sessao = sessionmaker(bind=motor, autoflush=False)()
    sessao.add_all([Categoria(nome=nome) for nome in CATEGORIAS])
    sessao.commit()
    yield sessao
    sessao.close()
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
