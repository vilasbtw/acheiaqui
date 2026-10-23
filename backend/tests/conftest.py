"""
Fixtures dos testes: API real + banco.
- Padrão (local, rápido): SQLite em memória, sem tocar em nenhum servidor.
- Com TEST_DATABASE_URL definida (CI): PostgreSQL de verdade, com as migrações já aplicadas.
  ATENÇÃO: nesse modo os testes APAGAM os dados das tabelas; por isso só aceitam banco LOCAL.
- `client`     : visitante sem login (para testar o que é público e o bloqueio 401)
- `client_cae` : pessoa da CAE do campus de teste A, já autenticada (o vínculo em `cae_membros` é conferido de verdade)
- `logar`      : troca quem está logado no meio do teste: logar("tstb") = CAE do campus B; logar(None) = logado sem campus
Todo teste começa com três campi: tsta e tstb (ativos, cada um com uma pessoa da CAE) e tstx (inativo).
"""
import os
import uuid
from datetime import timedelta
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra os models)
from app.auth import exigir_autenticacao
from app.database import Base, obter_sessao
from app.main import app
from app.models.cae_membro import CaeMembro
from app.models.campus import Campus
from app.models.categoria import Categoria
from app.tempo import agora_local

CATEGORIAS = ("Documentos", "Eletrônicos", "Bolsas e mochilas")
CAMPI = (  # sigla, nome, ativo, info_retirada
    ("tsta", "[TESTE] Campus A", True, "Retirada na sala 101 do campus A."),
    ("tstb", "[TESTE] Campus B", True, "Retirada na sala 202 do campus B."),
    ("tstx", "[TESTE] Campus inativo", False, "Campus desativado."),
)
# Usuários do Supabase Auth simulados. A chave é o campus da pessoa; None = logado sem vínculo com a CAE.
USUARIOS = {
    "tsta": uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001"),
    "tstb": uuid.UUID("bbbbbbbb-0000-4000-8000-000000000002"),
    None: uuid.UUID("cccccccc-0000-4000-8000-000000000003"),
}

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
            conexao.execute(text("TRUNCATE devolucoes, itens, cae_membros, categorias RESTART IDENTITY CASCADE"))
            conexao.execute(text("DELETE FROM campi WHERE sigla <> 'hto'"))  # o hto vem da migração 0002 e fica
    else:
        motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(motor)
    sessao = sessionmaker(bind=motor, autoflush=False)()
    sessao.add_all([Categoria(nome=nome) for nome in CATEGORIAS])
    campi = [Campus(sigla=s, nome=n, cidade="Cidade de teste", ativo=a, info_retirada=i) for s, n, a, i in CAMPI]
    sessao.add_all(campi)
    sessao.flush()
    sessao.add_all([CaeMembro(user_id=USUARIOS[c.sigla], campus_id=c.id) for c in campi if c.sigla in USUARIOS])
    sessao.commit()
    yield sessao
    sessao.close()
    if not USA_POSTGRES:
        Base.metadata.drop_all(motor)
        motor.dispose()


@pytest.fixture()
def client(sessao_teste):
    app.dependency_overrides[obter_sessao] = lambda: sessao_teste
    app.dependency_overrides.pop(exigir_autenticacao, None)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def logar(client):
    """Simula só o Supabase (token válido); a consulta a `cae_membros` roda de verdade."""

    def _logar(sigla):
        usuario = USUARIOS[sigla]
        app.dependency_overrides[exigir_autenticacao] = lambda: usuario
        return client

    return _logar


@pytest.fixture()
def client_cae(logar):
    return logar("tsta")


@pytest.fixture()
def payload():
    """Monta o corpo de um registro válido (no campus A); `extra` sobrescreve campos."""

    def _montar(**extra):
        dados = {
            "campus": "tsta",
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
