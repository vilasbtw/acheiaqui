"""
Foto do item enviada no registro (D4/D25).

O navegador comprime a imagem e manda como data URL ("data:image/jpeg;base64,...") dentro do JSON.
Aqui não se confia no tipo declarado: o tipo real vem dos primeiros bytes do arquivo (assinatura),
e só JPEG, PNG e WebP passam. Assim a API nunca guarda (nem devolve para a CAE) outro tipo de arquivo.
"""
import base64
import binascii
import re
from typing import NamedTuple

MAX_FOTO_BYTES = 600_000  # mesmo limite do CHECK da migração 0004
# Tamanho máximo do texto em base64 (+ o prefixo "data:...;base64,"), para recusar antes de decodificar.
MAX_FOTO_TEXTO = 4 * ((MAX_FOTO_BYTES + 2) // 3) + 40

_DATA_URL = re.compile(r"^data:image/[a-z0-9.+-]+;base64,(?P<dados>[A-Za-z0-9+/]+={0,2})$")


class FotoInvalida(ValueError):
    pass


class Foto(NamedTuple):
    tipo: str
    conteudo: bytes


def _tipo_pela_assinatura(conteudo: bytes) -> str | None:
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    return None


def decodificar_foto(data_url: str) -> Foto:
    """Converte o data URL em (tipo, bytes) ou levanta FotoInvalida com uma mensagem para quem registrou."""
    achou = _DATA_URL.match(data_url)
    if not achou:
        raise FotoInvalida("A foto não está num formato válido. Escolha outra imagem.")
    try:
        conteudo = base64.b64decode(achou.group("dados"), validate=True)
    except (binascii.Error, ValueError):
        raise FotoInvalida("A foto não está num formato válido. Escolha outra imagem.") from None
    if not conteudo:
        raise FotoInvalida("A foto está vazia. Escolha outra imagem.")
    if len(conteudo) > MAX_FOTO_BYTES:
        raise FotoInvalida("A foto é muito grande. Escolha uma imagem menor.")
    tipo = _tipo_pela_assinatura(conteudo)
    if tipo is None:
        raise FotoInvalida("Envie uma foto em JPEG, PNG ou WebP.")
    return Foto(tipo, conteudo)
