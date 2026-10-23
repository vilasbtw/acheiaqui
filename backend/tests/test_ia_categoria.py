def _categoria_do_item(client, descricao="Carteira com documentos", **extra):
    from datetime import timedelta
    from app.tempo import agora_local

    corpo = {
        "campus": "tsta",
        "descricao": descricao,
        "local_encontrado": "Biblioteca",
        "encontrado_em": (agora_local() - timedelta(hours=1)).isoformat(timespec="minutes"),
    }
    corpo.update(extra)
    resposta = client.post("/itens", json=corpo)
    assert resposta.status_code == 201
    return resposta.json()["categoria"]


def test_categoria_sugerida_pela_ia_e_aplicada(client, monkeypatch):
    monkeypatch.setattr("app.routers.itens.sugerir_categoria", lambda descricao, categorias: "documentos")
    assert _categoria_do_item(client) == "Documentos"


def test_ia_recebe_descricao_e_nomes_das_categorias(client, monkeypatch):
    recebido = {}

    def falsa_ia(descricao, categorias):
        recebido.update(descricao=descricao, categorias=categorias)
        return None

    monkeypatch.setattr("app.routers.itens.sugerir_categoria", falsa_ia)
    _categoria_do_item(client, descricao="Mochila preta")
    assert recebido["descricao"] == "Mochila preta"
    assert set(recebido["categorias"]) == {"Documentos", "Eletrônicos", "Bolsas e mochilas"}


def test_categoria_inventada_pela_ia_e_ignorada(client, monkeypatch):
    monkeypatch.setattr("app.routers.itens.sugerir_categoria", lambda descricao, categorias: "Instrumentos")
    assert _categoria_do_item(client) is None


def test_falha_da_ia_nao_impede_o_registro(client, monkeypatch):
    def ia_quebrada(descricao, categorias):
        raise TimeoutError("provedor fora do ar")

    monkeypatch.setattr("app.routers.itens.sugerir_categoria", ia_quebrada)
    assert _categoria_do_item(client) is None


def test_categoria_informada_pelo_usuario_dispensa_a_ia(client, monkeypatch, id_categoria):
    def nao_deveria_ser_chamada(descricao, categorias):
        raise AssertionError("a IA não deveria ser chamada")

    monkeypatch.setattr("app.routers.itens.sugerir_categoria", nao_deveria_ser_chamada)
    assert _categoria_do_item(client, categoria_id=id_categoria("Eletrônicos")) == "Eletrônicos"
