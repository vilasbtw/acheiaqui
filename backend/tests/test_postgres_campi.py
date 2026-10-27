"""
Regras do banco REAL para o multi-campus (migração 0002). Só rodam no CI, ou local com TEST_DATABASE_URL.
Os testes que gravam algo terminam com rollback: o campus de Hortolândia (semeado pela migração) é o único que fica.
"""
import importlib.util
import os
import pathlib
import uuid

import psycopg2
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DataError, IntegrityError

pytestmark = pytest.mark.postgres

CAMINHO = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "aplicar_migracoes.py"
_spec = importlib.util.spec_from_file_location("aplicar_migracoes", CAMINHO)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)


def _id_campus(sessao, sigla="hto"):
    return sessao.execute(text("SELECT id FROM campi WHERE sigla = :s"), {"s": sigla}).scalar_one()


def _criar_campus_de_teste(sessao):
    sessao.execute(text("INSERT INTO campi (sigla, nome, cidade) VALUES ('tst', 'Teste', 'Cidade de teste')"))
    return _id_campus(sessao, "tst")


def test_migracao_0002_foi_registrada(sessao_teste):
    versoes = sessao_teste.execute(text("SELECT versao FROM schema_migrations")).scalars().all()
    assert "0002" in versoes


def test_campus_de_hortolandia_foi_semeado(sessao_teste):
    campus = sessao_teste.execute(
        text("SELECT nome, cidade, ativo, info_retirada FROM campi WHERE sigla = 'hto'")
    ).one()
    assert campus.nome == "Hortolândia"
    assert campus.cidade == "Hortolândia"
    assert campus.ativo is True
    assert campus.info_retirada.strip() != ""


def test_sigla_do_campus_e_unica(sessao_teste):
    with pytest.raises(IntegrityError):
        sessao_teste.execute(text("INSERT INTO campi (sigla, nome, cidade) VALUES ('hto', 'Outro', 'Outra')"))
    sessao_teste.rollback()


@pytest.mark.parametrize("sigla", ["HTO", "h", "hto1", "tst-a", "tst_a", "abcdefghijk", ""])
def test_sigla_do_campus_so_aceita_letras_minusculas(sessao_teste, sigla):
    with pytest.raises((IntegrityError, DataError)):  # CHECK da sigla; acima de 10 letras, o VARCHAR(10)
        sessao_teste.execute(
            text("INSERT INTO campi (sigla, nome, cidade) VALUES (:s, 'Teste', 'Cidade')"), {"s": sigla}
        )
    sessao_teste.rollback()


def test_uma_pessoa_da_cae_pertence_a_um_campus_so(sessao_teste):
    hto = _id_campus(sessao_teste)
    tst = _criar_campus_de_teste(sessao_teste)
    usuario = str(uuid.uuid4())
    sql = text("INSERT INTO cae_membros (user_id, campus_id) VALUES (:u, :c)")
    sessao_teste.execute(sql, {"u": usuario, "c": hto})
    with pytest.raises(IntegrityError):
        sessao_teste.execute(sql, {"u": usuario, "c": tst})
    sessao_teste.rollback()


def test_membro_da_cae_exige_campus_existente(sessao_teste):
    with pytest.raises(IntegrityError):
        sessao_teste.execute(
            text("INSERT INTO cae_membros (user_id, campus_id) VALUES (:u, 999999)"), {"u": str(uuid.uuid4())}
        )
    sessao_teste.rollback()


def test_item_aceita_campus_valido_e_recusa_inexistente(sessao_teste):
    hto = _id_campus(sessao_teste)
    sql = text(
        "INSERT INTO itens (descricao, local_encontrado, encontrado_em, campus_id) VALUES ('x', 'y', now(), :c)"
    )
    sessao_teste.execute(sql, {"c": hto})
    with pytest.raises(IntegrityError):
        sessao_teste.execute(sql, {"c": 999999})
    sessao_teste.rollback()


def test_item_sem_campus_e_recusado_desde_a_0003(sessao_teste):
    versoes = sessao_teste.execute(text("SELECT versao FROM schema_migrations")).scalars().all()
    assert "0003" in versoes
    with pytest.raises(IntegrityError):
        sessao_teste.execute(
            text("INSERT INTO itens (descricao, local_encontrado, encontrado_em) VALUES ('x', 'y', now())")
        )
    sessao_teste.rollback()


def test_indice_do_feed_por_campus_existe(sessao_teste):
    indices = sessao_teste.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'itens'")).scalars().all()
    assert "idx_itens_campus_status_criado" in indices


@pytest.mark.parametrize("ultima_antiga", ["0001", "0002"])
def test_migracoes_preenchem_o_campus_dos_itens_antigos(sessao_teste, ultima_antiga):
    """Banco parado numa migração antiga, com itens sem campus; depois as demais migrações: todos viram do hto.

    "0001": banco do MVP (a 0002 preenche). "0002": itens gravados sem campus antes do deploy do backend novo
    (a 0003 preenche antes de travar o NOT NULL).
    Usa um banco temporário criado e apagado no mesmo servidor de teste (o `sessao_teste` acima já garante que
    ele é local). Se o usuário do banco não puder criar bancos, o teste é pulado.
    """
    url = os.environ["TEST_DATABASE_URL"].strip()
    nome = "teste_mig_" + uuid.uuid4().hex[:8]
    url_temporario = make_url(url).set(database=nome).render_as_string(hide_password=False)

    admin = psycopg2.connect(url)
    admin.autocommit = True  # CREATE DATABASE não roda dentro de transação
    try:
        try:
            with admin.cursor() as cur:
                cur.execute(f'CREATE DATABASE "{nome}"')
        except psycopg2.Error:
            pytest.skip("o usuário do banco de teste não pode criar bancos")

        conn = psycopg2.connect(url_temporario)
        try:
            arquivos = mig.listar_arquivos(mig.PASTA_PADRAO)
            antigas = [a for a in arquivos if a[0] <= ultima_antiga]
            novas = [a for a in arquivos if a[0] > ultima_antiga]

            mig.aplicar(conn, antigas)
            with conn, conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO itens (descricao, local_encontrado, encontrado_em) VALUES "
                    "('Garrafa antiga', 'Cantina', now()), ('Chave antiga', 'Biblioteca', now())"
                )

            mig.aplicar(conn, novas)
            with conn, conn.cursor() as cur:
                cur.execute("SELECT count(*), count(campus_id) FROM itens")
                total, com_campus = cur.fetchone()
                cur.execute("SELECT count(*) FROM itens i JOIN campi c ON c.id = i.campus_id WHERE c.sigla = 'hto'")
                de_hortolandia = cur.fetchone()[0]
                cur.execute("SELECT is_nullable FROM information_schema.columns "
                            "WHERE table_name = 'itens' AND column_name = 'campus_id'")
                aceita_nulo = cur.fetchone()[0]
        finally:
            conn.close()
        assert (total, com_campus, de_hortolandia) == (2, 2, 2)
        assert aceita_nulo == "NO"
    finally:
        with admin.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{nome}"')
        admin.close()
