"""Multi-campus, lado público (D20 e D22): lista de campi, registro com campus e feed por campus."""


def _campi_de_teste(client):
    """No PostgreSQL a lista também traz o hto, semeado pela migração 0002."""
    return [c for c in client.get("/campi").json() if c["sigla"].startswith("tst")]


def test_lista_so_campi_ativos_em_ordem_de_nome(client):
    assert client.get("/campi").status_code == 200
    assert [c["sigla"] for c in _campi_de_teste(client)] == ["tsta", "tstb"]  # o tstx está inativo


def test_lista_de_campi_traz_o_texto_de_retirada(client):
    campus = _campi_de_teste(client)[0]
    assert campus == {
        "sigla": "tsta",
        "nome": "[TESTE] Campus A",
        "cidade": "Cidade de teste",
        "info_retirada": "Retirada na sala 101 do campus A.",
    }


def test_publico_nao_consegue_criar_campus(client):
    assert client.post("/campi", json={"sigla": "novo", "nome": "Novo"}).status_code == 405


# ---------- Registro ----------

def test_registro_exige_campus(client, payload):
    dados = payload()
    dados.pop("campus")
    assert client.post("/itens", json=dados).status_code == 422


def test_registro_em_campus_inexistente_ou_inativo_e_recusado(client, payload):
    for sigla in ("zzz", "tstx", "TSTA"):
        resposta = client.post("/itens", json=payload(campus=sigla))
        assert resposta.status_code == 400, sigla
        assert resposta.json()["detail"] == "Campus inexistente ou inativo."


def test_campus_invalido_nao_gasta_a_cota_da_ia(client, payload, monkeypatch):
    def nao_deveria_ser_chamada(descricao, categorias):
        raise AssertionError("a IA não deveria ser chamada")

    monkeypatch.setattr("app.routers.itens.sugerir_categoria", nao_deveria_ser_chamada)
    assert client.post("/itens", json=payload(campus="zzz")).status_code == 400


def test_registro_devolve_o_campus_com_o_texto_de_retirada(client, payload):
    campus = client.post("/itens", json=payload(campus="tstb")).json()["campus"]
    assert campus["sigla"] == "tstb"
    assert campus["info_retirada"] == "Retirada na sala 202 do campus B."


# ---------- Feed ----------

def test_feed_exige_campus(client):
    assert client.get("/itens").status_code == 422


def test_feed_de_campus_inexistente_ou_inativo_da_404(client):
    assert client.get("/itens", params={"campus": "zzz"}).status_code == 404
    assert client.get("/itens", params={"campus": "tstx"}).status_code == 404


def test_feed_de_um_campus_nao_mostra_itens_do_outro(client, payload):
    client.post("/itens", json=payload(campus="tsta", descricao="Garrafa do campus A"))
    client.post("/itens", json=payload(campus="tstb", descricao="Garrafa do campus B"))
    feed_a = client.get("/itens", params={"campus": "tsta"}).json()
    feed_b = client.get("/itens", params={"campus": "tstb"}).json()
    assert [i["descricao"] for i in feed_a] == ["Garrafa do campus A"]
    assert [i["descricao"] for i in feed_b] == ["Garrafa do campus B"]
    assert {i["campus"]["sigla"] for i in feed_a} == {"tsta"}


def test_busca_tambem_respeita_o_campus(client, payload):
    client.post("/itens", json=payload(campus="tsta", descricao="Garrafa azul"))
    client.post("/itens", json=payload(campus="tstb", descricao="Garrafa vermelha"))
    resultado = client.get("/itens", params={"campus": "tstb", "q": "garrafa"}).json()
    assert [i["descricao"] for i in resultado] == ["Garrafa vermelha"]


def test_detalhe_informa_o_campus(client, payload):
    item_id = client.post("/itens", json=payload(campus="tstb")).json()["id"]
    campus = client.get(f"/itens/{item_id}").json()["campus"]
    assert campus["sigla"] == "tstb"
    assert campus["nome"] == "[TESTE] Campus B"
