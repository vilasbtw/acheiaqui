class FalhaNoBanco:
    def execute(self, *args, **kwargs):
        raise RuntimeError("banco fora do ar")


def test_lista_categorias_em_ordem_alfabetica(client):
    resposta = client.get("/categorias")
    assert resposta.status_code == 200
    nomes = [c["nome"] for c in resposta.json()]
    assert nomes == ["Bolsas e mochilas", "Documentos", "Eletrônicos"]


def test_publico_nao_consegue_criar_categoria(client):
    assert client.post("/categorias", json={"nome": "Nova"}).status_code == 405


def test_raiz_responde(client):
    assert client.get("/").json()["status"] == "ok"


def test_saude_ok(client):
    resposta = client.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_saude_devolve_503_se_banco_cair(client):
    from app.database import obter_sessao
    from app.main import app

    app.dependency_overrides[obter_sessao] = lambda: FalhaNoBanco()
    resposta = client.get("/saude")
    assert resposta.status_code == 503
    assert "indisponível" in resposta.json()["detail"]
