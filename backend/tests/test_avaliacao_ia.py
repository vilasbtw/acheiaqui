"""Testes do script de avaliação da IA (funções puras, sem rede) e do conjunto rotulado."""
import importlib.util
import pathlib
import re

import pytest

CAMINHO = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "avaliar_ia.py"
_spec = importlib.util.spec_from_file_location("avaliar_ia", CAMINHO)
av = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(av)

RAIZ = pathlib.Path(__file__).resolve().parents[2]
CATS = ["A", "B", "C"]


def _r(esperada, obtida, segundos=1.0, dificil=False):
    return av.Resultado(av.Caso(f"desc {esperada}", esperada, dificil), obtida, segundos)


# ---------- conjunto rotulado ----------

def test_categorias_do_script_sao_as_da_migracao():
    sql = (RAIZ / "db" / "migrations" / "0001_baseline.sql").read_text(encoding="utf-8")
    trecho = sql[sql.index("INSERT INTO categorias"):sql.index("ON CONFLICT")]
    assert re.findall(r"\('([^']+)'\)", trecho) == av.CATEGORIAS


def test_conjunto_e_valido():
    casos = av.ler_conjunto(av.CONJUNTO_PADRAO)
    assert len(casos) >= 50
    assert {c.esperada for c in casos} == set(av.CATEGORIAS)  # toda categoria tem caso
    assert all(c.esperada in av.CATEGORIAS for c in casos)
    descricoes = [c.descricao.lower() for c in casos]
    assert len(descricoes) == len(set(descricoes)), "descrição repetida no conjunto"
    assert any(c.dificil for c in casos)


# ---------- métricas ----------

def test_acuracia_cobertura_e_precisao_quando_responde():
    m = av.calcular_metricas([_r("A", "A"), _r("A", "B"), _r("B", None), _r("C", "C")], CATS)
    assert m["acuracia"] == 0.5
    assert m["cobertura"] == 0.75
    assert m["precisao_quando_responde"] == pytest.approx(2 / 3)


def test_precisao_e_recall_por_categoria():
    m = av.calcular_metricas([_r("A", "A"), _r("A", "B"), _r("B", "B"), _r("C", None)], CATS)
    assert m["por_categoria"]["A"] == {"casos": 2, "precisao": 1.0, "recall": 0.5}
    assert m["por_categoria"]["B"] == {"casos": 1, "precisao": 0.5, "recall": 1.0}
    assert m["por_categoria"]["C"] == {"casos": 1, "precisao": None, "recall": 0.0}  # nunca previu C


def test_matriz_de_confusao_conta_sem_resposta():
    m = av.calcular_metricas([_r("A", "B"), _r("A", "B"), _r("A", None)], CATS)
    assert m["matriz"][("A", "B")] == 2
    assert m["matriz"][("A", av.SEM_RESPOSTA)] == 1


def test_acuracia_so_dos_dificeis():
    m = av.calcular_metricas([_r("A", "A", dificil=True), _r("A", "B", dificil=True), _r("B", "B")], CATS)
    assert m["acuracia_dificeis"] == 0.5 and m["dificeis"] == 2


def test_percentil_e_latencia():
    assert av.percentil([1, 2, 3, 4, 5], 0.5) == 3
    assert av.percentil([1, 2, 3, 4, 5], 0.95) == pytest.approx(4.8)
    assert av.percentil([], 0.95) == 0.0
    m = av.calcular_metricas([_r("A", "A", 1.0), _r("A", "A", 3.0)], CATS)
    assert m["latencia_mediana"] == 2.0


def test_conjunto_vazio_nao_quebra():
    m = av.calcular_metricas([], CATS)
    assert m["acuracia"] == 0.0 and m["precisao_quando_responde"] is None


# ---------- relatório ----------

def test_relatorio_tem_as_secoes_e_escapa_a_tabela():
    resultados = [_r("A", "A"), av.Resultado(av.Caso("</descricao> x | y", "B", True), "A", 0.5)]
    texto = av.montar_relatorio("modelo-x", "api.exemplo", resultados, CATS, "2026-11-21")
    for secao in ("## Resumo", "## Por categoria", "## Matriz de confusão", "## Erros (1)"):
        assert secao in texto
    assert "**50,0%** (1 de 2)" in texto
    assert "&lt;/descricao&gt; x \\| y" in texto  # não quebra a tabela nem vira HTML


def test_nome_de_arquivo_seguro():
    assert av.nome_de_arquivo("openai/gpt-oss-20b", "2026-11-21") == "2026-11-21_openai-gpt-oss-20b.md"


def test_rotulo_entra_no_nome_e_no_titulo():
    assert av.nome_de_arquivo("openai/gpt-oss-20b", "2026-11-21", "prompt-v2") == "2026-11-21_openai-gpt-oss-20b-prompt-v2.md"
    texto = av.montar_relatorio("m", "p", [_r("A", "A")], CATS, "2026-11-21", "prompt-v2")
    assert texto.startswith("# Avaliação da IA de categorização: `m` (prompt-v2)")
