"""
Sobe a API com um banco SQLite descartável para o teste dinâmico (DAST) na esteira.

Só deve ser usado no CI: o banco é criado do zero e apagado a cada execução, então o
scanner nunca encosta no Supabase real. Rodar de dentro de backend/ com PYTHONPATH=.
"""
import os
from datetime import datetime
from pathlib import Path

# Precisa vir antes de importar app.database, que lê a variável ao ser carregado.
CAMINHO_BANCO = Path("dast.db")
CAMINHO_BANCO.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///./{CAMINHO_BANCO}"
os.environ.setdefault("FRONTEND_URL", "http://localhost:5500")

import uvicorn  # noqa: E402

import app.models  # noqa: E402,F401  (registra os models)
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.campus import Campus  # noqa: E402
from app.models.categoria import Categoria  # noqa: E402
from app.models.item import Item  # noqa: E402


def preparar_banco() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as sessao:
        sessao.add_all([Categoria(nome=n) for n in ("Documentos", "Eletrônicos", "Chaves")])
        sessao.add(Campus(sigla="hto", nome="Hortolândia", cidade="Hortolândia", info_retirada="Procure a CAE."))
        sessao.commit()
        sessao.add(
            Item(
                descricao="Garrafa térmica azul",
                local_encontrado="Biblioteca",
                encontrado_em=datetime(2026, 10, 1, 10, 0),
                contato_achador="teste@exemplo.com",
                categoria_id=1,
                campus_id=1,
            )
        )
        sessao.commit()


def afrouxar_limites() -> None:
    """O ZAP manda milhares de requisições do mesmo IP. Com os limites da decisão 001 ligados, quase todas
    voltariam 429 e o POST /itens deixaria de ser testado de verdade. Só nesta cópia descartável."""
    from app.services import limites

    limites.limite_por_ip.maximo = 1_000_000
    limites.ITENS_POR_DIA = 1_000_000
    limites.FOTOS_POR_DIA = 1_000_000
    limites.PERDIDOS_POR_DIA = 1_000_000


if __name__ == "__main__":
    preparar_banco()
    afrouxar_limites()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
