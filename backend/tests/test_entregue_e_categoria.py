"""
1. Devolução de um achado confirmado fecha o pedido de quem perdeu: status `entregue` (migração 0009).
2. A CAE corrige a categoria; a sugestão original da IA fica guardada para medir a acurácia (migração 0010).
"""
from datetime import timedelta

from app.models.item import Item
from app.models.perdido import Perdido
from app.routers.perdidos import hash_do_token
from app.tempo import agora_local


def _perdido(client, descricao="Garrafa azul"):
    corpo = {"campus": "tsta", "descricao": descricao, "contato": "Ana",
             "perdido_em": (agora_local().date() - timedelta(days=1)).isoformat()}
    return client.post("/perdidos", json=corpo).json()["token"]


def _id(sessao, token):
    return sessao.query(Perdido).filter(Perdido.token_hash == hash_do_token(token)).one().id


def _confirmado(client, payload, sessao):
    item_id = client.post("/itens", json=payload(descricao="Garrafa azul com adesivo")).json()["id"]
    token = _perdido(client)
    perdido_id = _id(sessao, token)
    client.post(f"/cae/perdidos/{perdido_id}/confirmar", json={"item_id": item_id})
    return item_id, perdido_id, token


# ---------- entregue ----------

def test_devolucao_marca_o_perdido_como_entregue(client_cae, payload, sessao_teste):
    item_id, perdido_id, token = _confirmado(client_cae, payload, sessao_teste)
    assert client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "Ana Souza"}).status_code == 201

    visto = client_cae.post("/perdidos/acompanhar", json={"token": token}).json()
    assert visto["status"] == "entregue" and visto["item_encontrado"] == "Garrafa azul com adesivo"
    na_cae = client_cae.get("/cae/perdidos", params={"status": "entregue"}).json()
    assert [p["id"] for p in na_cae] == [perdido_id]
    assert na_cae[0]["item"]["id"] == item_id


def test_devolucao_de_achado_sem_perdido_nao_mexe_em_outros_pedidos(client_cae, payload, sessao_teste):
    _, perdido_id, _ = _confirmado(client_cae, payload, sessao_teste)
    outro = client_cae.post("/itens", json=payload(descricao="Caderno")).json()["id"]
    procurando = _id(sessao_teste, _perdido(client_cae, "Mochila"))
    client_cae.post(f"/cae/itens/{outro}/devolucao", json={"nome_retirante": "João Silva"})
    sessao_teste.expire_all()
    assert sessao_teste.get(Perdido, perdido_id).status == "encontrado"
    assert sessao_teste.get(Perdido, procurando).status == "procurando"


def test_entregue_nao_reabre_e_quem_perdeu_nao_encerra(client_cae, payload, sessao_teste):
    item_id, perdido_id, token = _confirmado(client_cae, payload, sessao_teste)
    client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "Ana Souza"})
    resposta = client_cae.post(f"/cae/perdidos/{perdido_id}/reabrir")
    assert resposta.status_code == 409 and "entregue" in resposta.json()["detail"]
    assert client_cae.post("/perdidos/encerrar", json={"token": token}).status_code == 409


# ---------- correção de categoria ----------

def test_registro_guarda_a_sugestao_da_ia(client_cae, payload, monkeypatch):
    monkeypatch.setattr("app.routers.itens.sugerir_categoria", lambda d, c: "Documentos")
    client_cae.post("/itens", json=payload(descricao="Carteira com RG"))
    item = client_cae.get("/cae/itens").json()[0]
    assert item["categoria"] == "Documentos" and item["categoria_ia"] == "Documentos"
    assert item["categoria_corrigida_em"] is None


def test_categoria_escolhida_pela_pessoa_nao_conta_como_ia(client_cae, payload, id_categoria):
    client_cae.post("/itens", json=payload(categoria_id=id_categoria("Eletrônicos")))
    assert client_cae.get("/cae/itens").json()[0]["categoria_ia"] is None


def test_cae_corrige_e_a_sugestao_da_ia_continua_guardada(client_cae, payload, monkeypatch, id_categoria, sessao_teste):
    monkeypatch.setattr("app.routers.itens.sugerir_categoria", lambda d, c: "Documentos")
    item_id = client_cae.post("/itens", json=payload(descricao="Carregador")).json()["id"]
    resposta = client_cae.post(f"/cae/itens/{item_id}/categoria", json={"categoria_id": id_categoria("Eletrônicos")})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["categoria"] == "Eletrônicos" and corpo["categoria_ia"] == "Documentos"
    assert corpo["categoria_corrigida_em"] is not None
    assert client_cae.get("/itens", params={"campus": "tsta", "q": "eletronicos"}).json()[0]["id"] == item_id


def test_tirar_a_categoria_e_salvar_igual(client_cae, payload, id_categoria):
    item_id = client_cae.post("/itens", json=payload(categoria_id=id_categoria("Eletrônicos"))).json()["id"]
    igual = client_cae.post(f"/cae/itens/{item_id}/categoria", json={"categoria_id": id_categoria("Eletrônicos")}).json()
    assert igual["categoria_corrigida_em"] is None  # nada mudou, não conta como correção
    sem = client_cae.post(f"/cae/itens/{item_id}/categoria", json={"categoria_id": None}).json()
    assert sem["categoria"] is None and sem["categoria_corrigida_em"] is not None


def test_categoria_inexistente(client_cae, payload):
    item_id = client_cae.post("/itens", json=payload()).json()["id"]
    assert client_cae.post(f"/cae/itens/{item_id}/categoria", json={"categoria_id": 999999}).status_code == 400


def test_cae_de_outro_campus_nao_corrige(logar, payload, id_categoria, sessao_teste):
    item_id = logar("tsta").post("/itens", json=payload()).json()["id"]
    resposta = logar("tstb").post(f"/cae/itens/{item_id}/categoria", json={"categoria_id": id_categoria("Documentos")})
    assert resposta.status_code == 404
    sessao_teste.expire_all()
    assert sessao_teste.get(Item, item_id).categoria_id is None


def test_corrigir_exige_login(client, payload):
    item_id = client.post("/itens", json=payload()).json()["id"]
    assert client.post(f"/cae/itens/{item_id}/categoria", json={"categoria_id": None}).status_code == 401
