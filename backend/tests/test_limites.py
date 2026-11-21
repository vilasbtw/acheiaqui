"""Limites contra uso abusivo do POST /itens (decisão 001)."""
import base64
from datetime import datetime, timedelta, timezone

import pytest

from app.models.item import Item
from app.services import limites
from app.services.limites import LimitePorIP
from app.tempo import agora_local

FOTO = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 50).decode()


@pytest.fixture()
def ia_proibida(monkeypatch):
    def nao_deveria_ser_chamada(descricao, categorias):
        raise AssertionError("a IA não deveria ser chamada")

    monkeypatch.setattr("app.routers.itens.sugerir_categoria", nao_deveria_ser_chamada)


# ---------- janela deslizante (sem API) ----------

def test_janela_deixa_passar_ate_o_maximo_e_depois_pede_espera():
    limite = LimitePorIP(maximo=3, janela_s=60)
    assert [limite.registrar("1.1.1.1", agora=t) for t in (0, 1, 2)] == [0, 0, 0]
    assert limite.registrar("1.1.1.1", agora=3) == 58  # a tentativa do segundo 0 só sai da janela no 60


def test_janela_libera_quando_as_tentativas_antigas_expiram():
    limite = LimitePorIP(maximo=2, janela_s=60)
    limite.registrar("1.1.1.1", agora=0)
    limite.registrar("1.1.1.1", agora=10)
    assert limite.registrar("1.1.1.1", agora=30) > 0
    assert limite.registrar("1.1.1.1", agora=61) == 0


def test_cada_ip_tem_a_sua_conta():
    limite = LimitePorIP(maximo=1, janela_s=60)
    assert limite.registrar("1.1.1.1", agora=0) == 0
    assert limite.registrar("2.2.2.2", agora=0) == 0
    assert limite.registrar("1.1.1.1", agora=1) > 0


def test_tentativa_recusada_nao_estica_o_bloqueio():
    limite = LimitePorIP(maximo=1, janela_s=60)
    limite.registrar("1.1.1.1", agora=0)
    for t in range(1, 60):
        limite.registrar("1.1.1.1", agora=t)
    assert limite.registrar("1.1.1.1", agora=60) == 0


# ---------- por IP, pela API ----------

def test_por_ip_responde_429_com_retry_after(client, payload, monkeypatch):
    monkeypatch.setattr(limites.limite_por_ip, "maximo", 2)
    assert client.post("/itens", json=payload()).status_code == 201
    assert client.post("/itens", json=payload()).status_code == 201
    resposta = client.post("/itens", json=payload())
    assert resposta.status_code == 429
    assert int(resposta.headers["retry-after"]) > 0
    assert "Aguarde" in resposta.json()["detail"]


def test_por_ip_conta_tambem_as_tentativas_invalidas(client, payload, monkeypatch):
    monkeypatch.setattr(limites.limite_por_ip, "maximo", 2)
    client.post("/itens", json=payload(campus="zzz"))
    client.post("/itens", json={"lixo": True})
    assert client.post("/itens", json=payload()).status_code == 429


def test_por_ip_nao_afeta_a_busca(client, payload, monkeypatch):
    monkeypatch.setattr(limites.limite_por_ip, "maximo", 1)
    client.post("/itens", json=payload())
    assert client.post("/itens", json=payload()).status_code == 429
    assert client.get("/itens", params={"campus": "tsta"}).status_code == 200


def test_usa_o_cabecalho_configurado_para_separar_os_visitantes(client, payload, monkeypatch):
    monkeypatch.setenv("IP_CABECALHO_CLIENTE", "True-Client-IP")
    monkeypatch.setattr(limites.limite_por_ip, "maximo", 1)
    assert client.post("/itens", json=payload(), headers={"True-Client-IP": "200.1.1.1"}).status_code == 201
    assert client.post("/itens", json=payload(), headers={"True-Client-IP": "200.1.1.1"}).status_code == 429
    assert client.post("/itens", json=payload(), headers={"True-Client-IP": "200.2.2.2"}).status_code == 201


def test_sem_configuracao_o_cabecalho_e_ignorado(client, payload, monkeypatch):
    """Sem IP_CABECALHO_CLIENTE, trocar o cabeçalho não fura o limite."""
    monkeypatch.delenv("IP_CABECALHO_CLIENTE", raising=False)
    monkeypatch.setattr(limites.limite_por_ip, "maximo", 1)
    client.post("/itens", json=payload(), headers={"True-Client-IP": "200.1.1.1"})
    assert client.post("/itens", json=payload(), headers={"True-Client-IP": "200.9.9.9"}).status_code == 429


def test_cabecalho_com_valor_que_nao_e_ip_cai_para_a_conexao(client, payload, monkeypatch):
    monkeypatch.setenv("IP_CABECALHO_CLIENTE", "True-Client-IP")
    monkeypatch.setattr(limites.limite_por_ip, "maximo", 1)
    client.post("/itens", json=payload(), headers={"True-Client-IP": "abc"})
    assert client.post("/itens", json=payload(), headers={"True-Client-IP": "xyz"}).status_code == 429


# ---------- por dia, contado no banco ----------

def test_limite_diario_de_itens(client, payload, monkeypatch):
    monkeypatch.setattr(limites, "ITENS_POR_DIA", 2)
    client.post("/itens", json=payload())
    client.post("/itens", json=payload())
    resposta = client.post("/itens", json=payload())
    assert resposta.status_code == 429
    assert "limite de registros do dia" in resposta.json()["detail"]


def test_limite_diario_vale_para_todos_os_campi_juntos(client, payload, monkeypatch):
    monkeypatch.setattr(limites, "ITENS_POR_DIA", 1)
    client.post("/itens", json=payload(campus="tsta"))
    assert client.post("/itens", json=payload(campus="tstb")).status_code == 429


def test_limite_diario_nao_gasta_a_cota_da_ia(client, payload, monkeypatch, ia_proibida):
    monkeypatch.setattr(limites, "ITENS_POR_DIA", 0)
    assert client.post("/itens", json=payload()).status_code == 429


def test_itens_de_mais_de_24h_nao_contam(client, payload, monkeypatch, sessao_teste):
    monkeypatch.setattr(limites, "ITENS_POR_DIA", 1)
    client.post("/itens", json=payload())
    antigo = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25)
    sessao_teste.query(Item).update({Item.criado_em: antigo})
    sessao_teste.commit()
    assert client.post("/itens", json=payload()).status_code == 201


def test_limite_diario_de_fotos_so_barra_quem_manda_foto(client, payload, monkeypatch):
    monkeypatch.setattr(limites, "FOTOS_POR_DIA", 1)
    assert client.post("/itens", json=payload(foto=FOTO)).status_code == 201
    resposta = client.post("/itens", json=payload(foto=FOTO))
    assert resposta.status_code == 429
    assert "sem ela" in resposta.json()["detail"]
    assert client.post("/itens", json=payload()).status_code == 201  # sem foto, passa


def test_registro_invalido_responde_o_erro_dele_e_nao_o_do_limite(client, payload, monkeypatch):
    monkeypatch.setattr(limites, "ITENS_POR_DIA", 0)
    assert client.post("/itens", json=payload(campus="zzz")).status_code == 400
    encontrado = (agora_local() + timedelta(days=2)).isoformat(timespec="minutes")
    assert client.post("/itens", json=payload(encontrado_em=encontrado)).status_code == 422
