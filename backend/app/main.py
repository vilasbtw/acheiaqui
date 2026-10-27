import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import obter_sessao  # importar antes dos routers: carrega o .env
from app.routers import cae, campi, categorias, itens

app = FastAPI(title="Achei Aqui API", version="0.1.0")

# A API só devolve JSON: nada dela deve ser embutido em outra página, executado como script ou guardado em cache.
CABECALHOS_SEGURANCA = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cache-Control": "no-store",
}
CSP_API = "default-src 'none'; frame-ancestors 'none'"
# O Swagger (/docs) e o ReDoc carregam scripts de CDN; com a CSP acima eles ficariam em branco.
PAGINAS_DE_DOCUMENTACAO = ("/docs", "/redoc")


def _origens_permitidas() -> list[str]:
    """URLs do frontend autorizadas a chamar a API (CORS). Vem do .env: FRONTEND_URL."""
    bruto = os.getenv("FRONTEND_URL", "")
    origens = [o.strip().rstrip("/") for o in bruto.split(",") if o.strip()]
    return origens or ["http://localhost:5500", "http://127.0.0.1:5500"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_origens_permitidas(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# Declarado depois do CORS de propósito: fica por fora e também marca as respostas que o CORS devolve sozinho.
@app.middleware("http")
async def cabecalhos_de_seguranca(request: Request, call_next):
    resposta = await call_next(request)
    for nome, valor in CABECALHOS_SEGURANCA.items():
        resposta.headers.setdefault(nome, valor)
    if not request.url.path.startswith(PAGINAS_DE_DOCUMENTACAO):
        resposta.headers.setdefault("Content-Security-Policy", CSP_API)
    return resposta


app.include_router(campi.router)
app.include_router(categorias.router)
app.include_router(itens.router)
app.include_router(cae.router)


@app.get("/")
def raiz():
    return {"status": "ok", "mensagem": "API do Achei Aqui no ar"}


@app.get("/saude")
def saude(sessao: Session = Depends(obter_sessao)):
    """Verifica a API e o banco. Um monitor externo chama isto para manter tudo acordado (D11)."""
    try:
        sessao.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Banco de dados indisponível.") from None
    return {"status": "ok"}
