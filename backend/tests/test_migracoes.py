"""Testes das funções puras do runner de migrações (não precisam de banco)."""
import importlib.util
import pathlib
import re

import pytest

CAMINHO = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "aplicar_migracoes.py"
_spec = importlib.util.spec_from_file_location("aplicar_migracoes", CAMINHO)
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

RAIZ = pathlib.Path(__file__).resolve().parents[2]


def test_checksum_ignora_fim_de_linha_do_windows():
    assert mig.checksum("a\nb\n") == mig.checksum("a\r\nb\r\n")
    assert mig.checksum("a\n") != mig.checksum("b\n")


def test_listar_arquivos_em_ordem(tmp_path):
    (tmp_path / "0002_segunda.sql").write_text("SELECT 2;")
    (tmp_path / "0001_primeira.sql").write_text("SELECT 1;")
    assert [a[0] for a in mig.listar_arquivos(tmp_path)] == ["0001", "0002"]


@pytest.mark.parametrize("nome", ["migracao.sql", "1_curta.sql", "0001_Maiuscula.sql", "0001 espaco.sql", "0001_acentuação.sql"])
def test_nome_fora_do_padrao_e_recusado(tmp_path, nome):
    (tmp_path / nome).write_text("SELECT 1;")
    with pytest.raises(mig.ErroMigracao, match="Nome inválido"):
        mig.listar_arquivos(tmp_path)


def test_numero_repetido_e_recusado(tmp_path):
    (tmp_path / "0001_a.sql").write_text("SELECT 1;")
    (tmp_path / "0001_b.sql").write_text("SELECT 2;")
    with pytest.raises(mig.ErroMigracao, match="repetido"):
        mig.listar_arquivos(tmp_path)


def _arquivos(tmp_path, conteudos):
    for nome, texto in conteudos.items():
        (tmp_path / nome).write_text(texto)
    return mig.listar_arquivos(tmp_path)


def test_planejar_tudo_pendente_no_banco_novo(tmp_path):
    arquivos = _arquivos(tmp_path, {"0001_a.sql": "x", "0002_b.sql": "y"})
    pendentes, problemas = mig.planejar(arquivos, {})
    assert [p[0] for p in pendentes] == ["0001", "0002"] and problemas == []


def test_planejar_so_o_que_falta(tmp_path):
    arquivos = _arquivos(tmp_path, {"0001_a.sql": "x", "0002_b.sql": "y"})
    aplicadas = {"0001": ("0001_a.sql", arquivos[0][2])}
    pendentes, problemas = mig.planejar(arquivos, aplicadas)
    assert [p[0] for p in pendentes] == ["0002"] and problemas == []


def test_planejar_detecta_arquivo_alterado(tmp_path):
    arquivos = _arquivos(tmp_path, {"0001_a.sql": "x"})
    _, problemas = mig.planejar(arquivos, {"0001": ("0001_a.sql", "0" * 64)})
    assert len(problemas) == 1 and "ALTERADO" in problemas[0]


def test_planejar_detecta_arquivo_que_sumiu(tmp_path):
    arquivos = _arquivos(tmp_path, {"0001_a.sql": "x"})
    _, problemas = mig.planejar(arquivos, {"0001": ("0001_a.sql", arquivos[0][2]), "0002": ("0002_b.sql", "1" * 64)})
    assert any("sumiu" in p for p in problemas)


def test_planejar_detecta_migracao_fora_de_ordem(tmp_path):
    arquivos = _arquivos(tmp_path, {"0001_a.sql": "x", "0002_b.sql": "y", "0003_c.sql": "z"})
    aplicadas = {"0001": ("0001_a.sql", arquivos[0][2]), "0003": ("0003_c.sql", arquivos[2][2])}
    _, problemas = mig.planejar(arquivos, aplicadas)
    assert any("mais antiga" in p for p in problemas)


def test_migracoes_reais_do_projeto_sao_validas_e_tem_rls():
    """Guarda do repositório: nomes corretos e toda CREATE TABLE do projeto tem RLS na mesma migração."""
    arquivos = mig.listar_arquivos(RAIZ / "db" / "migrations")
    assert arquivos and arquivos[0][0] == "0001"
    for _, nome, _, caminho in arquivos:
        texto = caminho.read_text(encoding="utf-8").lower()
        for tabela in re.findall(r"create table (?:if not exists )?(\w+)", texto):
            assert re.search(rf"alter table {tabela}\s+enable row level security", texto), f"{nome}: {tabela} sem RLS"
