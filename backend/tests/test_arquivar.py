"""Etapa 3 (D23): a CAE arquiva um registro falso (spam) sem apagar, e pode desfazer."""


def _registrar(client, payload, **extra):
    return client.post("/itens", json=payload(**extra)).json()["id"]


def test_arquivar_tira_o_item_da_busca_publica(client_cae, payload):
    item_id = _registrar(client_cae, payload, descricao="Spam de teste")
    resposta = client_cae.post(f"/cae/itens/{item_id}/arquivar")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "arquivado"
    assert client_cae.get("/itens", params={"campus": "tsta"}).json() == []
    assert client_cae.get("/itens", params={"campus": "tsta", "q": "spam"}).json() == []
    assert client_cae.get(f"/itens/{item_id}").status_code == 404


def test_arquivado_continua_no_historico_da_cae(client_cae, payload):
    item_id = _registrar(client_cae, payload)
    client_cae.post(f"/cae/itens/{item_id}/arquivar")
    assert [i["status"] for i in client_cae.get("/cae/itens").json()] == ["arquivado"]
    assert len(client_cae.get("/cae/itens", params={"status": "arquivado"}).json()) == 1
    assert client_cae.get("/cae/itens", params={"status": "disponivel"}).json() == []


def test_desarquivar_devolve_o_item_para_a_busca(client_cae, payload):
    item_id = _registrar(client_cae, payload)
    client_cae.post(f"/cae/itens/{item_id}/arquivar")
    resposta = client_cae.post(f"/cae/itens/{item_id}/desarquivar")
    assert resposta.status_code == 200 and resposta.json()["status"] == "disponivel"
    assert len(client_cae.get("/itens", params={"campus": "tsta"}).json()) == 1


def test_nao_arquiva_item_devolvido_nem_arquiva_duas_vezes(client_cae, payload):
    devolvido = _registrar(client_cae, payload)
    client_cae.post(f"/cae/itens/{devolvido}/devolucao", json={"nome_retirante": "João Silva"})
    assert client_cae.post(f"/cae/itens/{devolvido}/arquivar").status_code == 409

    arquivado = _registrar(client_cae, payload)
    client_cae.post(f"/cae/itens/{arquivado}/arquivar")
    assert client_cae.post(f"/cae/itens/{arquivado}/arquivar").status_code == 409


def test_so_desarquiva_o_que_esta_arquivado(client_cae, payload):
    item_id = _registrar(client_cae, payload)
    resposta = client_cae.post(f"/cae/itens/{item_id}/desarquivar")
    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "Este item não está arquivado."


def test_nao_devolve_item_arquivado(client_cae, payload):
    item_id = _registrar(client_cae, payload)
    client_cae.post(f"/cae/itens/{item_id}/arquivar")
    resposta = client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    assert resposta.status_code == 409
    assert "arquivado" in resposta.json()["detail"]


def test_arquivar_exige_login(client, payload):
    item_id = _registrar(client, payload)
    assert client.post(f"/cae/itens/{item_id}/arquivar").status_code == 401
    assert client.post(f"/cae/itens/{item_id}/desarquivar").status_code == 401


def test_cae_de_outro_campus_nao_arquiva_nem_desarquiva(logar, payload, sessao_teste):
    from app.models.item import Item

    item_id = _registrar(logar("tsta"), payload)
    assert logar("tstb").post(f"/cae/itens/{item_id}/arquivar").status_code == 404
    logar("tsta").post(f"/cae/itens/{item_id}/arquivar")
    assert logar("tstb").post(f"/cae/itens/{item_id}/desarquivar").status_code == 404
    sessao_teste.expire_all()
    assert sessao_teste.get(Item, item_id).status == "arquivado"
