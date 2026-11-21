"""
Envio de e-mail pela API HTTP do Brevo (Etapa 7, D28). O Render gratuito bloqueia as portas de SMTP.

Configuração no .env (sem ela, nada é enviado e o motivo vai para o log e para o painel da CAE):
  EMAIL_API_KEY        chave de API do Brevo (SMTP & API -> API Keys)
  EMAIL_REMETENTE      e-mail verificado no Brevo como remetente (Senders)
  EMAIL_REMETENTE_NOME nome que aparece no "De:" (padrão: Achei Aqui)

Só texto puro: o conteúdo inclui descrições digitadas por qualquer pessoa, e texto puro não executa nada.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("achei_aqui.email")

URL_BREVO = "https://api.brevo.com/v3/smtp/email"
TIMEOUT = httpx.Timeout(10.0)


def email_configurado() -> bool:
    return bool(os.getenv("EMAIL_API_KEY", "").strip() and os.getenv("EMAIL_REMETENTE", "").strip())


def enviar_email(para: str, assunto: str, texto: str) -> Optional[str]:
    """Envia um e-mail. Devolve None se deu certo, ou o motivo da falha (curto, sem a chave)."""
    chave = os.getenv("EMAIL_API_KEY", "").strip()
    remetente = os.getenv("EMAIL_REMETENTE", "").strip()
    if not chave or not remetente:
        logger.warning("E-mail desativado: faltam EMAIL_API_KEY e/ou EMAIL_REMETENTE no .env.")
        return "envio de e-mail não configurado no servidor"
    corpo = {
        "sender": {"name": os.getenv("EMAIL_REMETENTE_NOME", "").strip() or "Achei Aqui", "email": remetente},
        "to": [{"email": para}],
        "subject": assunto,
        "textContent": texto,
    }
    try:
        resposta = httpx.post(URL_BREVO, headers={"api-key": chave, "accept": "application/json"}, json=corpo, timeout=TIMEOUT)
    except httpx.HTTPError as erro:
        logger.warning("E-mail: falha de rede ou tempo esgotado (%s)", type(erro).__name__)
        return f"falha de rede ({type(erro).__name__})"
    if resposta.status_code not in (200, 201, 202):
        logger.warning("E-mail: o Brevo respondeu %s: %s", resposta.status_code, resposta.text[:300])
        return f"o provedor de e-mail respondeu {resposta.status_code}"
    return None
