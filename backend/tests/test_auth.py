import httpx
import pytest


@pytest.fixture()
def supabase_configurado(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://projeto.supabase.co/")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_teste")


def _simular_supabase(monkeypatch, status=None, erro=None):
    chamadas = []

    def falso_get(url, headers=None, timeout=None):
        chamadas.append({"url": url, "headers": headers})
        if erro:
            raise erro
        return httpx.Response(status, json={"id": "usuario-1"})

    monkeypatch.setattr("app.auth.httpx.get", falso_get)
    return chamadas


def test_token_valido_passa_e_e_enviado_ao_supabase(client, supabase_configurado, monkeypatch):
    chamadas = _simular_supabase(monkeypatch, status=200)
    resposta = client.get("/cae/itens", headers={"Authorization": "Bearer meu-token"})
    assert resposta.status_code == 200
    assert chamadas[0]["url"] == "https://projeto.supabase.co/auth/v1/user"
    assert chamadas[0]["headers"]["Authorization"] == "Bearer meu-token"
    assert chamadas[0]["headers"]["apikey"] == "sb_publishable_teste"


def test_token_invalido_da_401(client, supabase_configurado, monkeypatch):
    _simular_supabase(monkeypatch, status=401)
    resposta = client.get("/cae/itens", headers={"Authorization": "Bearer qualquer-coisa"})
    assert resposta.status_code == 401


def test_sem_token_da_401_sem_consultar_o_supabase(client, supabase_configurado, monkeypatch):
    chamadas = _simular_supabase(monkeypatch, status=200)
    assert client.get("/cae/itens").status_code == 401
    assert chamadas == []


def test_supabase_fora_do_ar_da_503(client, supabase_configurado, monkeypatch):
    _simular_supabase(monkeypatch, erro=httpx.ConnectError("sem rede"))
    resposta = client.get("/cae/itens", headers={"Authorization": "Bearer x"})
    assert resposta.status_code == 503


def test_servidor_sem_configuracao_do_supabase_da_500(client, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    resposta = client.get("/cae/itens", headers={"Authorization": "Bearer x"})
    assert resposta.status_code == 500


def test_todas_as_rotas_da_cae_estao_protegidas(client):
    """Se alguém criar uma rota nova em /cae sem proteção, este teste avisa."""
    from app.main import app

    caminhos = {c: m for c, m in app.openapi()["paths"].items() if c.startswith("/cae")}
    assert caminhos, "nenhuma rota /cae encontrada"
    for caminho, metodos in caminhos.items():
        for metodo in metodos:
            if metodo not in ("get", "post", "put", "patch", "delete"):
                continue
            url = caminho.replace("{item_id}", "1")
            resposta = client.request(metodo.upper(), url, json={})
            assert resposta.status_code == 401, f"{metodo.upper()} {caminho} está aberta!"
