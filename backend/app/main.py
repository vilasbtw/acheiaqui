import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import obter_sessao  # importar antes dos routers: carrega o .env
from app.routers import categorias, cae, itens

app = FastAPI(title="Achei Aqui API", version="0.1.0")


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
        raise HTTPException(status_code=503, detail="Banco de dados indisponível.")
    return {"status": "ok"}
