from datetime import timedelta

from app.tempo import agora_local


def _data(dias_atras, hora=10):
    dia = agora_local().date() - timedelta(days=dias_atras)
    return f"{dia.isoformat()}T{hora:02d}:00"


def test_historico_exige_login(client):
    assert client.get("/cae/itens").status_code == 401


def test_historico_com_token_mal_formado_da_401(client):
    assert client.get("/cae/itens", headers={"Authorization": "Basic abc"}).status_code == 401


def test_historico_mostra_status_e_contato(client_cae, payload):
    client_cae.post("/itens", json=payload(contato_achador="maria@exemplo.com"))
    itens = client_cae.get("/cae/itens").json()
    assert len(itens) == 1
    assert itens[0]["status"] == "disponivel"
    assert itens[0]["contato_achador"] == "maria@exemplo.com"
    assert itens[0]["devolucao"] is None


def test_historico_inclui_devolvidos_com_quem_retirou(client_cae, payload):
    item_id = client_cae.post("/itens", json=payload()).json()["id"]
    client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    item = client_cae.get("/cae/itens").json()[0]
    assert item["status"] == "devolvido"
    assert item["devolucao"]["nome_retirante"] == "João Silva"


def test_filtro_por_status(client_cae, payload):
    a = client_cae.post("/itens", json=payload(descricao="Item A")).json()["id"]
    client_cae.post("/itens", json=payload(descricao="Item B"))
    client_cae.post(f"/cae/itens/{a}/devolucao", json={"nome_retirante": "João Silva"})
    disponiveis = client_cae.get("/cae/itens", params={"status": "disponivel"}).json()
    devolvidos = client_cae.get("/cae/itens", params={"status": "devolvido"}).json()
    assert [i["descricao"] for i in disponiveis] == ["Item B"]
    assert [i["descricao"] for i in devolvidos] == ["Item A"]


def test_status_invalido_e_recusado(client_cae):
    assert client_cae.get("/cae/itens", params={"status": "expirado"}).status_code == 422


def test_filtro_por_periodo(client_cae, payload):
    client_cae.post("/itens", json=payload(descricao="Antigo", encontrado_em=_data(10)))
    client_cae.post("/itens", json=payload(descricao="Recente", encontrado_em=_data(3)))
    hoje = agora_local().date()

    desde = (hoje - timedelta(days=5)).isoformat()
    assert [i["descricao"] for i in client_cae.get("/cae/itens", params={"data_inicio": desde}).json()] == ["Recente"]

    ate = (hoje - timedelta(days=5)).isoformat()
    assert [i["descricao"] for i in client_cae.get("/cae/itens", params={"data_fim": ate}).json()] == ["Antigo"]


def test_periodo_inclui_o_dia_final_inteiro(client_cae, payload):
    client_cae.post("/itens", json=payload(descricao="Fim do dia", encontrado_em=_data(4, hora=23)))
    dia = (agora_local().date() - timedelta(days=4)).isoformat()
    itens = client_cae.get("/cae/itens", params={"data_inicio": dia, "data_fim": dia}).json()
    assert [i["descricao"] for i in itens] == ["Fim do dia"]


def test_periodo_invertido_da_422(client_cae):
    resposta = client_cae.get("/cae/itens", params={"data_inicio": "2026-09-20", "data_fim": "2026-09-10"})
    assert resposta.status_code == 422


def test_historico_pagina(client_cae, payload):
    for numero in range(4):
        client_cae.post("/itens", json=payload(descricao=f"Item numero {numero}"))
    assert len(client_cae.get("/cae/itens", params={"limit": 3}).json()) == 3
    assert len(client_cae.get("/cae/itens", params={"limit": 3, "offset": 3}).json()) == 1
