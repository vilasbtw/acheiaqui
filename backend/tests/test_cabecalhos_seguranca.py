"""Cabeçalhos de segurança da API (alertas do ZAP). Se alguém remover o middleware, estes testes avisam."""
import pytest

from app.main import CABECALHOS_SEGURANCA, CSP_API

ROTAS = [
    ("GET", "/saude"),
    ("GET", "/campi"),
    ("GET", "/itens?campus=tsta"),
    ("GET", "/itens"),  # 422: erros também levam os cabeçalhos
    ("GET", "/itens/999"),  # 404
    ("GET", "/cae/itens"),  # 401
]


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS)
def test_respostas_da_api_levam_os_cabecalhos(client, metodo, caminho):
    resposta = client.request(metodo, caminho)
    for nome, valor in CABECALHOS_SEGURANCA.items():
        assert resposta.headers.get(nome) == valor, f"{nome} faltando em {metodo} {caminho}"
    assert resposta.headers.get("Content-Security-Policy") == CSP_API


def test_area_da_cae_nunca_fica_em_cache(client_cae):
    resposta = client_cae.get("/cae/itens")
    assert resposta.status_code == 200
    assert resposta.headers["Cache-Control"] == "no-store"


def test_cors_continua_funcionando_com_os_cabecalhos(client):
    resposta = client.options(
        "/itens",
        headers={"Origin": "http://localhost:5500", "Access-Control-Request-Method": "POST"},
    )
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == "http://localhost:5500"
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"


def test_documentacao_da_api_abre_sem_a_csp_estrita(client):
    resposta = client.get("/docs")
    assert resposta.status_code == 200
    assert "Content-Security-Policy" not in resposta.headers
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
