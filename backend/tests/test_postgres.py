"""
Regras do banco REAL (PostgreSQL). Só rodam no CI, ou local com TEST_DATABASE_URL.
Os testes em SQLite não enxergam estas regras (CHECK, UNIQUE, chave estrangeira, RLS).
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.item import Item
from app.tempo import agora_local

pytestmark = pytest.mark.postgres


def _novo_item(sessao):
    item = Item(descricao="Garrafa azul", local_encontrado="Cantina", encontrado_em=agora_local(), campus_id=_hto(sessao))
    sessao.add(item)
    sessao.commit()
    return item.id


def _hto(sessao):
    return sessao.execute(text("SELECT id FROM campi WHERE sigla = 'hto'")).scalar_one()


HTO = "(SELECT id FROM campi WHERE sigla = 'hto')"


def test_rls_ligado_em_todas_as_tabelas_do_public(sessao_teste):
    sem_rls = sessao_teste.execute(text(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity"
    )).scalars().all()
    assert sem_rls == []


def test_migracoes_foram_registradas(sessao_teste):
    versoes = sessao_teste.execute(text("SELECT versao FROM schema_migrations")).scalars().all()
    assert "0001" in versoes


def test_banco_recusa_status_invalido(sessao_teste):
    with pytest.raises(IntegrityError):
        sessao_teste.execute(text(
            "INSERT INTO itens (descricao, local_encontrado, encontrado_em, status, campus_id) "
            f"VALUES ('x', 'y', now(), 'expirado', {HTO})"
        ))
    sessao_teste.rollback()


def test_banco_recusa_duas_devolucoes_do_mesmo_item(sessao_teste):
    item_id = _novo_item(sessao_teste)
    sessao_teste.execute(text("INSERT INTO devolucoes (item_id, nome_retirante) VALUES (:i, 'Ana')"), {"i": item_id})
    sessao_teste.commit()
    with pytest.raises(IntegrityError):
        sessao_teste.execute(text("INSERT INTO devolucoes (item_id, nome_retirante) VALUES (:i, 'Beto')"), {"i": item_id})
    sessao_teste.rollback()


def test_banco_recusa_categoria_inexistente(sessao_teste):
    with pytest.raises(IntegrityError):
        sessao_teste.execute(text(
            "INSERT INTO itens (descricao, local_encontrado, encontrado_em, categoria_id, campus_id) "
            f"VALUES ('x', 'y', now(), 999999, {HTO})"
        ))
    sessao_teste.rollback()


def test_banco_recusa_campo_obrigatorio_nulo(sessao_teste):
    with pytest.raises(IntegrityError):
        sessao_teste.execute(text(f"INSERT INTO itens (local_encontrado, encontrado_em, campus_id) VALUES ('y', now(), {HTO})"))
    sessao_teste.rollback()


def test_nome_de_categoria_e_unico(sessao_teste):
    with pytest.raises(IntegrityError):
        sessao_teste.execute(text("INSERT INTO categorias (nome) VALUES ('Documentos')"))
    sessao_teste.rollback()
