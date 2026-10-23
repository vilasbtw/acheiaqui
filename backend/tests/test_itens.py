from datetime import datetime, timedelta, timezone

from app.tempo import FUSO_CAMPUS, agora_local


# ---------- Registro (RF01 / RF02) ----------

def test_registra_item_minimo(client, payload):
    resposta = client.post("/itens", json=payload())
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["descricao"] == "Garrafa térmica azul"
    assert dados["local_encontrado"] == "Biblioteca"
    assert dados["categoria"] is None  # sem IA e sem categoria informada
    assert dados["id"] > 0


def test_resposta_publica_nunca_traz_contato(client, payload):
    resposta = client.post("/itens", json=payload(contato_achador="maria@exemplo.com"))
    assert resposta.status_code == 201
    assert "contato_achador" not in resposta.json()
    assert "status" not in resposta.json()


def test_contato_opcional_vazio_vira_nulo(client_cae, payload):
    client_cae.post("/itens", json=payload(contato_achador="   "))
    item = client_cae.get("/cae/itens").json()[0]
    assert item["contato_achador"] is None


def test_contato_informado_fica_visivel_so_para_a_cae(client_cae, payload):
    client_cae.post("/itens", json=payload(contato_achador="maria@exemplo.com"))
    assert client_cae.get("/cae/itens").json()[0]["contato_achador"] == "maria@exemplo.com"
    publico = client_cae.get("/itens", params={"campus": "tsta"}).json()
    assert "contato_achador" not in publico[0]


def test_registra_com_categoria_informada(client, payload, id_categoria):
    resposta = client.post("/itens", json=payload(categoria_id=id_categoria("Eletrônicos")))
    assert resposta.status_code == 201
    assert resposta.json()["categoria"] == "Eletrônicos"


def test_categoria_inexistente_da_400(client, payload):
    assert client.post("/itens", json=payload(categoria_id=999)).status_code == 400


def test_campos_obrigatorios(client, payload):
    for campo in ("descricao", "local_encontrado", "encontrado_em"):
        dados = payload()
        dados.pop(campo)
        assert client.post("/itens", json=dados).status_code == 422, campo


def test_textos_muito_curtos_ou_longos_sao_recusados(client, payload):
    assert client.post("/itens", json=payload(descricao="  ab  ")).status_code == 422
    assert client.post("/itens", json=payload(descricao="x" * 1001)).status_code == 422
    assert client.post("/itens", json=payload(local_encontrado="x" * 101)).status_code == 422
    assert client.post("/itens", json=payload(contato_achador="x" * 101)).status_code == 422


def test_horario_no_futuro_e_recusado(client, payload):
    futuro = (agora_local() + timedelta(days=1)).isoformat(timespec="minutes")
    assert client.post("/itens", json=payload(encontrado_em=futuro)).status_code == 422


def test_horario_com_fuso_e_convertido_para_o_campus(client_cae, payload):
    utc = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0)
    resposta = client_cae.post("/itens", json=payload(encontrado_em=utc.isoformat()))
    assert resposta.status_code == 201
    esperado = utc.astimezone(FUSO_CAMPUS).replace(tzinfo=None)
    assert datetime.fromisoformat(resposta.json()["encontrado_em"]) == esperado


# ---------- Busca pública (RF03 / RF04) ----------

def test_busca_por_palavra_da_descricao(client, payload):
    client.post("/itens", json=payload(descricao="Garrafa térmica azul"))
    client.post("/itens", json=payload(descricao="Carregador de celular"))
    resposta = client.get("/itens", params={"campus": "tsta", "q": "garrafa"})
    assert [i["descricao"] for i in resposta.json()] == ["Garrafa térmica azul"]


def test_busca_ignora_maiusculas(client, payload):
    client.post("/itens", json=payload(descricao="Garrafa térmica azul"))
    assert len(client.get("/itens", params={"campus": "tsta", "q": "GARRAFA"}).json()) == 1


def test_busca_por_nome_da_categoria(client, payload, id_categoria):
    client.post("/itens", json=payload(descricao="Carteira preta", categoria_id=id_categoria("Documentos")))
    client.post("/itens", json=payload(descricao="Caderno verde"))
    resposta = client.get("/itens", params={"campus": "tsta", "q": "documentos"})
    assert [i["descricao"] for i in resposta.json()] == ["Carteira preta"]


def test_busca_por_local(client, payload):
    client.post("/itens", json=payload(descricao="Guarda-chuva", local_encontrado="Cantina"))
    client.post("/itens", json=payload(descricao="Caderno", local_encontrado="Biblioteca"))
    assert [i["descricao"] for i in client.get("/itens", params={"campus": "tsta", "q": "cantina"}).json()] == ["Guarda-chuva"]


def test_mais_palavras_batendo_aparece_primeiro(client, payload):
    client.post("/itens", json=payload(descricao="Garrafa azul", local_encontrado="Cantina"))
    client.post("/itens", json=payload(descricao="Garrafa vermelha", local_encontrado="Biblioteca"))
    client.post("/itens", json=payload(descricao="Garrafa azul e branca", local_encontrado="Bloco A"))
    ordem = [i["descricao"] for i in client.get("/itens", params={"campus": "tsta", "q": "garrafa azul"}).json()]
    assert ordem[-1] == "Garrafa vermelha"
    assert set(ordem[:2]) == {"Garrafa azul", "Garrafa azul e branca"}


def test_busca_sem_resultado_devolve_lista_vazia(client, payload):
    client.post("/itens", json=payload())
    assert client.get("/itens", params={"campus": "tsta", "q": "violao"}).json() == []


def test_busca_so_com_palavras_curtas_nao_devolve_tudo(client, payload):
    client.post("/itens", json=payload())
    assert client.get("/itens", params={"campus": "tsta", "q": "de a"}).json() == []


def test_busca_nao_trata_curingas_como_curingas(client, payload):
    client.post("/itens", json=payload())
    assert client.get("/itens", params={"campus": "tsta", "q": "%%%"}).json() == []
    assert client.get("/itens", params={"campus": "tsta", "q": "___"}).json() == []


def test_sem_busca_lista_mais_recentes_primeiro(client, payload):
    for nome in ("Primeiro item", "Segundo item", "Terceiro item"):
        client.post("/itens", json=payload(descricao=nome))
    assert [i["descricao"] for i in client.get("/itens", params={"campus": "tsta"}).json()] == ["Terceiro item", "Segundo item", "Primeiro item"]


def test_paginacao(client, payload):
    for numero in range(5):
        client.post("/itens", json=payload(descricao=f"Item numero {numero}"))
    primeira = client.get("/itens", params={"campus": "tsta", "limit": 2, "offset": 0}).json()
    segunda = client.get("/itens", params={"campus": "tsta", "limit": 2, "offset": 2}).json()
    assert len(primeira) == 2 and len(segunda) == 2
    assert not {i["id"] for i in primeira} & {i["id"] for i in segunda}


def test_limites_de_paginacao_invalidos(client):
    assert client.get("/itens", params={"campus": "tsta", "limit": 0}).status_code == 422
    assert client.get("/itens", params={"campus": "tsta", "limit": 51}).status_code == 422
    assert client.get("/itens", params={"campus": "tsta", "offset": -1}).status_code == 422


def test_busca_longa_demais_e_recusada(client):
    assert client.get("/itens", params={"campus": "tsta", "q": "a" * 101}).status_code == 422


def test_item_devolvido_some_da_busca_publica(client_cae, payload):
    item = client_cae.post("/itens", json=payload()).json()
    assert len(client_cae.get("/itens", params={"campus": "tsta"}).json()) == 1
    client_cae.post(f"/cae/itens/{item['id']}/devolucao", json={"nome_retirante": "João Silva"})
    assert client_cae.get("/itens", params={"campus": "tsta"}).json() == []
    assert client_cae.get(f"/itens/{item['id']}").status_code == 404


def test_detalhe_do_item(client, payload):
    item = client.post("/itens", json=payload()).json()
    resposta = client.get(f"/itens/{item['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["descricao"] == "Garrafa térmica azul"


def test_detalhe_de_item_inexistente(client):
    assert client.get("/itens/999").status_code == 404
