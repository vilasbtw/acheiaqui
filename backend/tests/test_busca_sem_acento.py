"""Etapa 4 (D24): a busca ignora acentos e maiúsculas, nos dois sentidos."""
import pathlib
import re

import pytest

from app.models.item import Item
from app.services.busca import extrair_palavras, normalizar, texto_de_busca

RAIZ = pathlib.Path(__file__).resolve().parents[2]


def _buscar(client, q):
    return [i["descricao"] for i in client.get("/itens", params={"campus": "tsta", "q": q}).json()]


@pytest.mark.parametrize("busca", ["eletronico", "ELETRÔNICO", "Eletrônico", "eletrônico"])
def test_qualquer_grafia_encontra(client, payload, busca):
    client.post("/itens", json=payload(descricao="Carregador eletrônico"))
    assert _buscar(client, busca) == ["Carregador eletrônico"]


def test_item_sem_acento_e_encontrado_por_busca_com_acento(client, payload):
    client.post("/itens", json=payload(descricao="Garrafa termica azul"))
    assert _buscar(client, "térmica") == ["Garrafa termica azul"]


def test_local_sem_acento(client, payload):
    client.post("/itens", json=payload(descricao="Caderno", local_encontrado="Pátio"))
    assert _buscar(client, "patio") == ["Caderno"]


def test_cedilha(client, payload):
    client.post("/itens", json=payload(descricao="Calça jeans"))
    assert _buscar(client, "calca") == ["Calça jeans"]


def test_nome_da_categoria_sem_acento(client, payload, id_categoria):
    client.post("/itens", json=payload(descricao="Carregador", categoria_id=id_categoria("Eletrônicos")))
    client.post("/itens", json=payload(descricao="Caderno"))
    assert _buscar(client, "eletronicos") == ["Carregador"]


def test_resultado_mostra_o_texto_original_com_acento(client, payload):
    client.post("/itens", json=payload(descricao="Garrafa térmica"))
    assert client.get("/itens", params={"campus": "tsta", "q": "termica"}).json()[0]["descricao"] == "Garrafa térmica"


def test_texto_busca_e_preenchido_no_registro(client, payload, sessao_teste):
    item_id = client.post("/itens", json=payload(descricao="Óculos ESCUROS", local_encontrado="Pátio")).json()["id"]
    assert sessao_teste.get(Item, item_id).texto_busca == "oculos escuros patio"


def test_item_antigo_sem_texto_busca_ainda_aparece(client, payload, sessao_teste):
    """Gravado pelo código antigo entre a migração 0006 e o deploy: a busca usa a descrição original."""
    item_id = client.post("/itens", json=payload(descricao="Mochila verde")).json()["id"]
    sessao_teste.query(Item).filter(Item.id == item_id).update({Item.texto_busca: None})
    sessao_teste.commit()
    assert _buscar(client, "mochila") == ["Mochila verde"]


def test_busca_ainda_ordena_por_relevancia(client, payload):
    client.post("/itens", json=payload(descricao="Garrafa azul"))
    client.post("/itens", json=payload(descricao="Garrafa térmica azul"))
    client.post("/itens", json=payload(descricao="Caderno azul"))
    assert _buscar(client, "garrafa termica")[0] == "Garrafa térmica azul"


def test_simbolos_da_busca_nao_viram_curinga(client, payload):
    client.post("/itens", json=payload(descricao="Garrafa azul"))
    assert _buscar(client, "%%%") == []
    assert _buscar(client, "___") == []


# ---------- funções puras ----------

def _mapa_da_migracao() -> tuple[str, str]:
    """As duas linhas do translate da 0006 que só têm uma string entre aspas: com acento e sem acento."""
    sql = (RAIZ / "db" / "migrations" / "0006_itens_texto_busca.sql").read_text(encoding="utf-8")
    com, sem = re.findall(r"^\s*'([^'\n]+)',?\s*$", sql, flags=re.MULTILINE)
    return com, sem


def test_normalizar():
    assert normalizar("ÁGUA Térmica Ç") == "agua termica c"
    assert texto_de_busca("Óculos", "Pátio") == "oculos patio"


def test_extrair_palavras_normaliza_e_nao_repete():
    assert extrair_palavras("Eletrônico eletronico ELETRÔNICO de") == ["eletronico"]


def test_mapa_de_acentos_da_migracao_bate_com_o_python():
    """Os itens antigos são normalizados em SQL (translate) e os novos em Python: as duas regras precisam bater."""
    com, sem = _mapa_da_migracao()
    assert len(com) == len(sem)
    for original, trocado in zip(com, sem, strict=True):
        assert normalizar(original) == trocado.lower(), original


@pytest.mark.postgres
def test_migracao_normalizou_como_o_python(sessao_teste):
    """No PostgreSQL de verdade: aplica a regra da migração a um texto e compara com o Python."""
    from sqlalchemy import text

    com, sem = _mapa_da_migracao()
    exemplo = "Óculos ESCUROS da Conceição, Pátio Ü"
    via_sql = sessao_teste.execute(text("SELECT lower(translate(:t, :c, :s))"), {"t": exemplo, "c": com, "s": sem}).scalar_one()
    assert via_sql == normalizar(exemplo)
