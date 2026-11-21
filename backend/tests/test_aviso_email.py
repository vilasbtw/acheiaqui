"""Etapa 7 (D28): aviso por e-mail só com consentimento, só depois da confirmação da CAE, em segundo plano."""
from datetime import timedelta

import httpx
import pytest
from sqlalchemy.orm import sessionmaker

from app.models.perdido import Perdido
from app.routers.perdidos import hash_do_token
from app.services import aviso, email
from app.services.email import enviar_email
from app.tempo import agora_local


@pytest.fixture()
def caixa(monkeypatch):
    """Substitui o envio de verdade: guarda os e-mails e devolve `estado["erro"]` (None = enviado)."""
    estado = {"enviados": [], "erro": None}

    def falso(para, assunto, texto):
        estado["enviados"].append({"para": para, "assunto": assunto, "texto": texto})
        return estado["erro"]

    monkeypatch.setattr(aviso, "enviar_email", falso)
    return estado


def _dia(dias_atras=1):
    return (agora_local().date() - timedelta(days=dias_atras)).isoformat()


def _perdido(client, **extra):
    corpo = {"campus": "tsta", "descricao": "Garrafa térmica azul", "perdido_em": _dia(), "contato": "Ana"}
    corpo.update(extra)
    resposta = client.post("/perdidos", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["token"]


def _id(sessao, token):
    return sessao.query(Perdido).filter(Perdido.token_hash == hash_do_token(token)).one().id


def _confirmar(client, payload, sessao, **extra_perdido):
    item_id = client.post("/itens", json=payload(descricao="Garrafa azul com adesivo")).json()["id"]
    perdido_id = _id(sessao, _perdido(client, **extra_perdido))
    resposta = client.post(f"/cae/perdidos/{perdido_id}/confirmar", json={"item_id": item_id})
    assert resposta.status_code == 200
    return perdido_id, resposta.json()


COM_AVISO = {"aviso_consentido": True, "email_aviso": "Ana@Exemplo.com"}


# ---------- consentimento no registro ----------

def test_com_consentimento_o_email_e_gravado(client, sessao_teste):
    perdido_id = _id(sessao_teste, _perdido(client, **COM_AVISO))
    perdido = sessao_teste.get(Perdido, perdido_id)
    assert perdido.aviso_consentido is True and perdido.email_aviso == "ana@exemplo.com"


def test_sem_consentimento_o_email_nem_e_gravado(client, sessao_teste):
    perdido_id = _id(sessao_teste, _perdido(client, email_aviso="ana@exemplo.com"))
    perdido = sessao_teste.get(Perdido, perdido_id)
    assert perdido.aviso_consentido is False and perdido.email_aviso is None


@pytest.mark.parametrize("email_aviso, trecho", [(None, "informe o seu e-mail"), ("", "informe o seu e-mail"),
                                                 ("ana", "não parece válido"), ("ana@exemplo", "não parece válido"),
                                                 ("a b@exemplo.com", "não parece válido")])
def test_consentimento_exige_email_valido(client, email_aviso, trecho):
    corpo = {"campus": "tsta", "descricao": "Garrafa", "perdido_em": _dia(), "contato": "Ana",
             "aviso_consentido": True, "email_aviso": email_aviso}
    resposta = client.post("/perdidos", json=corpo)
    assert resposta.status_code == 422 and trecho in resposta.text


def test_link_publico_nao_mostra_o_email(client):
    token = _perdido(client, **COM_AVISO)
    resposta = client.post("/perdidos/acompanhar", json={"token": token})
    assert "exemplo.com" not in resposta.text


# ---------- envio depois da confirmação ----------

def test_confirmar_envia_o_aviso_em_segundo_plano(client_cae, payload, sessao_teste, caixa):
    perdido_id, _ = _confirmar(client_cae, payload, sessao_teste, **COM_AVISO)
    assert len(caixa["enviados"]) == 1
    enviado = caixa["enviados"][0]
    assert enviado["para"] == "ana@exemplo.com"
    assert "Garrafa térmica azul" in enviado["texto"] and "Garrafa azul com adesivo" in enviado["texto"]
    assert "Retirada na sala 101 do campus A." in enviado["texto"]
    sessao_teste.expire_all()
    perdido = sessao_teste.get(Perdido, perdido_id)
    assert perdido.aviso_enviado_em is not None and perdido.aviso_erro is None


def test_sem_consentimento_nao_envia(client_cae, payload, sessao_teste, caixa):
    _confirmar(client_cae, payload, sessao_teste)
    assert caixa["enviados"] == []


def test_registrar_nao_envia_nada(client, caixa):
    _perdido(client, **COM_AVISO)
    assert caixa["enviados"] == []


def test_falha_fica_registrada_e_a_cae_reenvia(client_cae, payload, sessao_teste, caixa):
    caixa["erro"] = "o provedor de e-mail respondeu 500"
    perdido_id, _ = _confirmar(client_cae, payload, sessao_teste, **COM_AVISO)
    lista = client_cae.get("/cae/perdidos").json()[0]
    assert lista["aviso_enviado_em"] is None and lista["aviso_erro"] == "o provedor de e-mail respondeu 500"

    caixa["erro"] = None
    assert client_cae.post(f"/cae/perdidos/{perdido_id}/reenviar-aviso").status_code == 200
    assert len(caixa["enviados"]) == 2
    lista = client_cae.get("/cae/perdidos").json()[0]
    assert lista["aviso_enviado_em"] is not None and lista["aviso_erro"] is None


def test_reenviar_so_quando_faz_sentido(client_cae, payload, sessao_teste, caixa):
    sem_aviso, _ = _confirmar(client_cae, payload, sessao_teste)
    assert client_cae.post(f"/cae/perdidos/{sem_aviso}/reenviar-aviso").status_code == 409
    procurando = _id(sessao_teste, _perdido(client_cae, **COM_AVISO))
    assert client_cae.post(f"/cae/perdidos/{procurando}/reenviar-aviso").status_code == 409
    assert caixa["enviados"] == []


def test_cae_de_outro_campus_nao_reenvia(logar, payload, sessao_teste, caixa):
    perdido_id, _ = _confirmar(logar("tsta"), payload, sessao_teste, **COM_AVISO)
    assert logar("tstb").post(f"/cae/perdidos/{perdido_id}/reenviar-aviso").status_code == 404
    assert len(caixa["enviados"]) == 1


def test_tarefa_nao_envia_se_a_confirmacao_foi_desfeita_antes(client_cae, payload, sessao_teste, caixa):
    perdido_id, _ = _confirmar(client_cae, payload, sessao_teste, **COM_AVISO)
    client_cae.post(f"/cae/perdidos/{perdido_id}/reabrir")
    aviso.enviar_aviso(sessionmaker(bind=sessao_teste.get_bind()), perdido_id)
    assert len(caixa["enviados"]) == 1  # só o da confirmação


# ---------- cliente do Brevo ----------

@pytest.fixture()
def brevo(monkeypatch):
    monkeypatch.setenv("EMAIL_API_KEY", "chave-secreta-teste")
    monkeypatch.setenv("EMAIL_REMETENTE", "grupo@exemplo.com")
    chamadas = []

    def falso_post(url, headers=None, json=None, timeout=None):
        chamadas.append({"url": url, "headers": headers, "json": json})
        return httpx.Response(estado["status"], text=estado["texto"])

    estado = {"status": 201, "texto": "{}"}
    monkeypatch.setattr(email.httpx, "post", falso_post)
    return chamadas, estado


def test_sem_configuracao_nao_chama_o_provedor(monkeypatch):
    monkeypatch.delenv("EMAIL_API_KEY", raising=False)
    monkeypatch.setattr(email.httpx, "post", lambda *a, **k: pytest.fail("não deveria chamar"))
    assert "não configurado" in enviar_email("ana@exemplo.com", "Assunto", "Texto")


def test_monta_a_requisicao_do_brevo(brevo):
    chamadas, _ = brevo
    assert enviar_email("ana@exemplo.com", "Assunto", "Texto puro") is None
    pedido = chamadas[0]
    assert pedido["url"] == "https://api.brevo.com/v3/smtp/email"
    assert pedido["headers"]["api-key"] == "chave-secreta-teste"
    assert pedido["json"]["to"] == [{"email": "ana@exemplo.com"}]
    assert pedido["json"]["sender"] == {"name": "Achei Aqui", "email": "grupo@exemplo.com"}
    assert pedido["json"]["textContent"] == "Texto puro" and "htmlContent" not in pedido["json"]


def test_erro_do_provedor_volta_como_motivo_sem_vazar_a_chave(brevo, caplog):
    _, estado = brevo
    estado.update(status=401, texto='{"message": "Key not found"}')
    with caplog.at_level("WARNING", logger="achei_aqui.email"):
        motivo = enviar_email("ana@exemplo.com", "Assunto", "Texto")
    assert motivo == "o provedor de e-mail respondeu 401"
    assert "Key not found" in caplog.text and "chave-secreta-teste" not in caplog.text


def test_falha_de_rede(brevo, monkeypatch):
    def quebra(*a, **k):
        raise httpx.ConnectTimeout("lento")

    monkeypatch.setattr(email.httpx, "post", quebra)
    assert enviar_email("ana@exemplo.com", "Assunto", "Texto") == "falha de rede (ConnectTimeout)"
