from app.models.devolucao import Devolucao
from app.models.item import Item
from app.tempo import agora_local


def _registrar(client, payload, **extra):
    return client.post("/itens", json=payload(**extra)).json()["id"]


def test_devolucao_marca_item_como_devolvido(client_cae, payload, sessao_teste):
    item_id = _registrar(client_cae, payload)
    resposta = client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "  João Silva  "})
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["status"] == "devolvido"
    assert dados["devolucao"]["nome_retirante"] == "João Silva"
    assert dados["devolucao"]["data_devolucao"] == agora_local().date().isoformat()
    assert sessao_teste.get(Item, item_id).status == "devolvido"
    assert sessao_teste.query(Devolucao).count() == 1


def test_devolver_duas_vezes_da_409(client_cae, payload, sessao_teste):
    item_id = _registrar(client_cae, payload)
    client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    segunda = client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "Outra Pessoa"})
    assert segunda.status_code == 409
    assert sessao_teste.query(Devolucao).count() == 1


def test_item_inexistente_da_404(client_cae):
    assert client_cae.post("/cae/itens/999/devolucao", json={"nome_retirante": "João Silva"}).status_code == 404


def test_nome_do_retirante_e_obrigatorio(client_cae, payload):
    item_id = _registrar(client_cae, payload)
    for corpo in ({}, {"nome_retirante": ""}, {"nome_retirante": " "}, {"nome_retirante": "x" * 101}):
        assert client_cae.post(f"/cae/itens/{item_id}/devolucao", json=corpo).status_code == 422


def test_devolucao_exige_login(client, payload):
    item_id = _registrar(client, payload)
    resposta = client.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    assert resposta.status_code == 401


def test_rota_antiga_publica_de_devolucao_nao_existe(client, payload):
    item_id = _registrar(client, payload)
    resposta = client.post(f"/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    assert resposta.status_code in (404, 405)


def test_conflito_simultaneo_no_banco_vira_409(client_cae, payload, sessao_teste, monkeypatch):
    """Duas pessoas da CAE devolvendo o mesmo item ao mesmo tempo: a restrição UNIQUE do banco barra a segunda."""
    from sqlalchemy.exc import IntegrityError

    item_id = _registrar(client_cae, payload)

    def commit_com_conflito():
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    monkeypatch.setattr(sessao_teste, "commit", commit_com_conflito)
    resposta = client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    assert resposta.status_code == 409
