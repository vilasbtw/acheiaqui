"""
Limites contra uso abusivo do POST /itens (decisão 001).

O registro é público (sem login), chama a IA externa (cota gratuita) e pode gravar foto no banco (500 MB).
Três camadas, da mais barata para a mais robusta:

1. Por IP, na memória do processo: barra um script martelando a API. É generoso de propósito: no Wi-Fi do campus
   todo mundo sai pelo MESMO IP público, e um limite apertado bloquearia o campus inteiro.
   Zera quando o Render reinicia e não vale entre instâncias (hoje é uma só); as camadas 2 e 3 cobrem isso.
2. Total de itens nas últimas 24 h, contado no banco: segura a cota da IA (no máximo uma chamada por item).
3. Total de fotos nas últimas 24 h, contado no banco: é o que mais ocupa espaço.

Qual IP? Atrás do proxy do Render, `request.client.host` é o IP do proxy, igual para todo mundo, e o
X-Forwarded-For pode ser forjado pelo visitante (o Render só acrescenta a ele). Por isso o cabeçalho vem do .env:
IP_CABECALHO_CLIENTE=True-Client-IP no Render (colocado pelo Cloudflare). Sem a variável, usa a conexão (local/testes).
"""
import ipaddress
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.item_foto import ItemFoto

POR_IP_MAXIMO = 20  # registros por IP...
POR_IP_JANELA_S = 10 * 60  # ...a cada 10 minutos
ITENS_POR_DIA = 200  # todos os campi juntos; o uso real esperado é bem menor
FOTOS_POR_DIA = 60  # 60 x 600 KB = 36 MB por dia, no pior caso
_MAX_IPS_NA_MEMORIA = 10_000


def _recusar(mensagem: str, espera_s: int) -> HTTPException:
    return HTTPException(status_code=429, detail=mensagem, headers={"Retry-After": str(espera_s)})


class LimitePorIP:
    """Janela deslizante: guarda os horários das últimas tentativas de cada IP."""

    def __init__(self, maximo: int, janela_s: int):
        self.maximo = maximo
        self.janela_s = janela_s
        self._tentativas: dict[str, deque] = {}
        self._trava = threading.Lock()  # rotas síncronas rodam em várias threads

    def registrar(self, ip: str, agora: float | None = None) -> int:
        """Conta uma tentativa. Devolve 0 se pode seguir, ou quantos segundos esperar."""
        agora = time.monotonic() if agora is None else agora
        limite = agora - self.janela_s
        with self._trava:
            if len(self._tentativas) > _MAX_IPS_NA_MEMORIA:  # não deixa a memória crescer sem fim
                self._tentativas = {k: v for k, v in self._tentativas.items() if v and v[-1] > limite}
            fila = self._tentativas.setdefault(ip, deque())
            while fila and fila[0] <= limite:
                fila.popleft()
            if len(fila) >= self.maximo:
                return max(1, int(fila[0] - limite) + 1)
            fila.append(agora)
            return 0

    def limpar(self):
        with self._trava:
            self._tentativas.clear()


limite_por_ip = LimitePorIP(POR_IP_MAXIMO, POR_IP_JANELA_S)


def ip_do_cliente(request: Request) -> str:
    nome = os.getenv("IP_CABECALHO_CLIENTE", "").strip()
    if nome:
        valor = request.headers.get(nome, "").split(",")[0].strip()
        try:
            return str(ipaddress.ip_address(valor))
        except ValueError:
            pass  # cabeçalho ausente ou estranho: cai para o IP da conexão
    return request.client.host if request.client else "desconhecido"


def exigir_limite_por_ip(request: Request) -> None:
    """Dependency do POST /itens. Roda antes de tudo, então conta também as tentativas inválidas."""
    espera = limite_por_ip.registrar(ip_do_cliente(request))
    if espera:
        raise _recusar("Muitos registros seguidos a partir desta rede. Aguarde alguns minutos e tente de novo.", espera)


def _ultimas_24h() -> datetime:
    # criado_em é gravado pelo banco com now(), que no Supabase (e no CI) está em UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)


def exigir_limite_diario(sessao: Session, com_foto: bool) -> None:
    """Chamado no registro depois das validações e ANTES da IA: estourou, não gasta a cota."""
    desde = _ultimas_24h()
    if sessao.query(Item).filter(Item.criado_em >= desde).count() >= ITENS_POR_DIA:
        raise _recusar("O sistema atingiu o limite de registros do dia. Tente de novo mais tarde ou procure a CAE.", 3600)
    if com_foto and sessao.query(ItemFoto).filter(ItemFoto.criado_em >= desde).count() >= FOTOS_POR_DIA:
        raise _recusar("O limite de fotos do dia foi atingido. Remova a foto e registre o item sem ela.", 3600)


PERDIDOS_POR_DIA = 100  # registros de item perdido (Etapa 6), todos os campi juntos


def exigir_limite_diario_perdidos(sessao: Session) -> None:
    """Cada perdido pode chamar a IA (categoria): o limite segura a cota e a tabela."""
    from app.models.perdido import Perdido  # import aqui: evita ciclo models -> services

    if sessao.query(Perdido).filter(Perdido.criado_em >= _ultimas_24h()).count() >= PERDIDOS_POR_DIA:
        raise _recusar("O sistema atingiu o limite de registros de itens perdidos do dia. Tente amanhã ou procure a CAE.", 3600)
