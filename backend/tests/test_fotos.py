"""Foto do item (D4/D25): enviada no registro, guardada no banco, vista só pela CAE do campus do item."""
import base64

import pytest

from app.services.foto import MAX_FOTO_BYTES, FotoInvalida, decodificar_foto

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 200


def _data_url(conteudo, tipo="image/jpeg"):
    return f"data:{tipo};base64," + base64.b64encode(conteudo).decode()


# ---------- validação da foto ----------

@pytest.mark.parametrize("conteudo, tipo", [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")])
def test_aceita_jpeg_png_e_webp(conteudo, tipo):
    assert decodificar_foto(_data_url(conteudo)) == (tipo, conteudo)


def test_tipo_vem_dos_bytes_e_nao_do_que_foi_declarado():
    assert decodificar_foto(_data_url(PNG, tipo="image/jpeg")).tipo == "image/png"


@pytest.mark.parametrize("texto", [
    "nao e um data url",
    "data:image/jpeg;base64,",
    "data:image/jpeg;base64,@@@@",
    "data:text/html;base64," + base64.b64encode(JPEG).decode(),
    "data:image/jpeg," + base64.b64encode(JPEG).decode(),  # sem ;base64
])
def test_recusa_formato_invalido(texto):
    with pytest.raises(FotoInvalida):
        decodificar_foto(texto)


@pytest.mark.parametrize("conteudo", [b"<script>alert(1)</script>", b"%PDF-1.7", b"GIF89a" + b"\x00" * 10])
def test_recusa_arquivo_que_nao_e_imagem_permitida(conteudo):
    with pytest.raises(FotoInvalida, match="JPEG, PNG ou WebP"):
        decodificar_foto(_data_url(conteudo))


def test_recusa_foto_grande_demais():
    with pytest.raises(FotoInvalida, match="muito grande"):
        decodificar_foto(_data_url(JPEG + b"\x00" * MAX_FOTO_BYTES))


# ---------- registro ----------

def test_registro_com_foto(client, payload, sessao_teste):
    from app.models.item_foto import ItemFoto

    resposta = client.post("/itens", json=payload(foto=_data_url(JPEG)))
    assert resposta.status_code == 201
    foto = sessao_teste.get(ItemFoto, resposta.json()["id"])
    assert foto.tipo == "image/jpeg" and foto.conteudo == JPEG


def test_registro_sem_foto_continua_funcionando(client, payload):
    assert client.post("/itens", json=payload()).status_code == 201
    assert client.post("/itens", json=payload(foto="")).status_code == 201


def test_foto_invalida_recusa_o_registro_com_mensagem_clara(client, payload):
    resposta = client.post("/itens", json=payload(foto=_data_url(b"%PDF-1.7")))
    assert resposta.status_code == 422
    assert "JPEG, PNG ou WebP" in resposta.json()["detail"]


def test_texto_gigante_e_recusado_antes_de_decodificar(client, payload):
    assert client.post("/itens", json=payload(foto="data:image/jpeg;base64," + "A" * 2_000_000)).status_code == 422


def test_foto_invalida_nao_gasta_a_cota_da_ia(client, payload, monkeypatch):
    def nao_deveria_ser_chamada(descricao, categorias):
        raise AssertionError("a IA não deveria ser chamada")

    monkeypatch.setattr("app.routers.itens.sugerir_categoria", nao_deveria_ser_chamada)
    assert client.post("/itens", json=payload(foto=_data_url(b"nada"))).status_code == 422


# ---------- quem vê ----------

def test_publico_nao_ve_nada_da_foto(client, payload):
    item_id = client.post("/itens", json=payload(foto=_data_url(JPEG))).json()["id"]
    respostas = [
        client.post("/itens", json=payload(foto=_data_url(JPEG))).json(),
        client.get("/itens", params={"campus": "tsta"}).json()[0],
        client.get(f"/itens/{item_id}").json(),
    ]
    for corpo in respostas:
        assert not {"foto", "tem_foto", "foto_url"} & set(corpo)


def test_foto_exige_login(client, payload):
    item_id = client.post("/itens", json=payload(foto=_data_url(JPEG))).json()["id"]
    assert client.get(f"/cae/itens/{item_id}/foto").status_code == 401


def test_cae_ve_que_tem_foto_e_baixa_a_imagem(client_cae, payload):
    com = client_cae.post("/itens", json=payload(descricao="Com foto", foto=_data_url(PNG))).json()["id"]
    client_cae.post("/itens", json=payload(descricao="Sem foto"))
    itens = {i["descricao"]: i for i in client_cae.get("/cae/itens").json()}
    assert itens["Com foto"]["tem_foto"] is True
    assert itens["Sem foto"]["tem_foto"] is False

    resposta = client_cae.get(f"/cae/itens/{com}/foto")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"] == "image/png"
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert resposta.content == PNG


def test_item_sem_foto_da_404(client_cae, payload):
    item_id = client_cae.post("/itens", json=payload()).json()["id"]
    assert client_cae.get(f"/cae/itens/{item_id}/foto").status_code == 404
    assert client_cae.get("/cae/itens/999999/foto").status_code == 404


def test_cae_de_outro_campus_nao_ve_a_foto(logar, payload):
    cliente = logar("tsta")
    item_id = cliente.post("/itens", json=payload(foto=_data_url(JPEG))).json()["id"]
    assert logar("tstb").get(f"/cae/itens/{item_id}/foto").status_code == 404


def test_logado_sem_campus_nao_ve_a_foto(logar, payload):
    item_id = logar("tsta").post("/itens", json=payload(foto=_data_url(JPEG))).json()["id"]
    assert logar(None).get(f"/cae/itens/{item_id}/foto").status_code == 403


def test_devolucao_de_item_com_foto_continua_mostrando_tem_foto(client_cae, payload):
    item_id = client_cae.post("/itens", json=payload(foto=_data_url(JPEG))).json()["id"]
    resposta = client_cae.post(f"/cae/itens/{item_id}/devolucao", json={"nome_retirante": "João Silva"})
    assert resposta.status_code == 201 and resposta.json()["tem_foto"] is True
