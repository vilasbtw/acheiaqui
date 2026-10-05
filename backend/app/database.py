"""
Configuração da conexão com o banco de dados (Supabase / PostgreSQL) via SQLAlchemy.

Preencher DATABASE_URL no .env (ver .env.example) com a connection string
(Session pooler) fornecida pelo Supabase.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Lê o arquivo backend/.env (procura a partir da pasta deste arquivo, então
# funciona independente de onde o uvicorn for iniciado).
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:senha@host:5432/postgres")

# Força o driver psycopg2 (o que está no requirements.txt). Sem isso, versões novas
# do SQLAlchemy podem escolher outro driver e falhar com "No module named 'psycopg'".
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def obter_sessao():
    """Dependency do FastAPI para injetar uma sessão de banco por requisição."""
    sessao = SessionLocal()
    try:
        yield sessao
    finally:
        sessao.close()
