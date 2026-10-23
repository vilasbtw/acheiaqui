"""
Isolamento entre campi na área da CAE (D21). É o maior risco da Etapa 1: sem estes testes verdes, não há deploy.
`logar("tsta")` = pessoa da CAE do campus A; `logar("tstb")` = do campus B; `logar(None)` = logado sem vínculo.
"""
import pytest

from app.models.devolucao import Devolucao
from app.models.item import Item


def _registrar(client, payload, campus, descricao="Garrafa azul", **extra):
    return client.post("/itens", json=payload(campus=campus, descricao=descricao, **extra)).json()["id"]


def test_cae_ve_so_o_historico_do_proprio_campus(logar, payload):
    publico = logar("tsta")
    _registrar(publico, payload, "tsta", "Item do campus A", contato_achador="ana@exemplo.com")
    _registrar(publico, payload, "tstb", "Item do campus B", contato_achador="beto@exemplo.com")

    historico_a = logar("tsta").get("/cae/itens").json()
    assert [i["descricao"] for i in historico_a] == ["Item do campus A"]
    assert historico_a[0]["contato_achador"] == "ana@exemplo.com"

    historico_b = logar("tstb").get("/cae/itens").json()
    assert [i["descricao"] for i in historico_b] == ["Item do campus B"]


def test_filtros_do_historico_nao_furam_o_isolamento(logar, payload):
    publico = logar("tsta")
    _registrar(publico, payload, "tstb", "Item do campus B")
    cae_a = logar("tsta")
    for params in ({"status": "disponivel"}, {"data_inicio": "2000-01-01"}, {"limit": 50, "offset": 0}):
        assert cae_a.get("/cae/itens", params=params).json() == [], params


def test_cae_nao_devolve_item_de_outro_campus(logar, payload, sessao_teste):
    item_id = _registrar(logar("tstb"), payload, "tstb")
    resposta = logar("tsta").post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    assert resposta.status_code == 404  # 404, e não 403: não revela que o item existe em outro campus
    assert resposta.json()["detail"] == "Item não encontrado."
    sessao_teste.expire_all()
    assert sessao_teste.get(Item, item_id).status == "disponivel"
    assert sessao_teste.query(Devolucao).count() == 0


def test_a_cae_do_campus_do_item_consegue_devolver(logar, payload):
    item_id = _registrar(logar("tstb"), payload, "tstb")
    resposta = logar("tstb").post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    assert resposta.status_code == 201
    assert resposta.json()["campus"]["sigla"] == "tstb"


def test_item_devolvido_de_outro_campus_tambem_da_404_e_nao_409(logar, payload):
    item_id = _registrar(logar("tstb"), payload, "tstb")
    logar("tstb").post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    resposta = logar("tsta").post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "Outra Pessoa"})
    assert resposta.status_code == 404


def test_cae_ve_o_proprio_campus(logar):
    resposta = logar("tstb").get("/cae/campus")
    assert resposta.status_code == 200
    assert resposta.json()["sigla"] == "tstb"
    assert resposta.json()["nome"] == "[TESTE] Campus B"


def _rotas_da_cae():
    from app.main import app

    for caminho, metodos in app.openapi()["paths"].items():
        if not caminho.startswith("/cae"):
            continue
        for metodo in metodos:
            if metodo in ("get", "post", "put", "patch", "delete"):
                yield metodo.upper(), caminho


@pytest.mark.parametrize(("metodo", "caminho"), list(_rotas_da_cae()))
def test_logado_sem_vinculo_com_a_cae_recebe_403_em_toda_rota(logar, payload, metodo, caminho):
    """Se alguém criar uma rota nova em /cae que não confere o campus, este teste avisa."""
    item_id = _registrar(logar(None), payload, "tsta")
    resposta = logar(None).request(metodo, caminho.replace("{item_id}", str(item_id)), json={})
    assert resposta.status_code == 403, f"{metodo} {caminho} deixou passar quem não é da CAE"
