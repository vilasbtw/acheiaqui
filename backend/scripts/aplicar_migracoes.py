"""
Aplica no banco as migrações SQL da pasta db/migrations/ que ainda não foram aplicadas.

Uso (com o venv ativo, de qualquer pasta):
    python backend/scripts/aplicar_migracoes.py --env backend/.env --listar     # só mostra o estado
    python backend/scripts/aplicar_migracoes.py --env backend/.env              # aplica no banco de DESENVOLVIMENTO
    python backend/scripts/aplicar_migracoes.py --env backend/.env.prod         # aplica em PRODUÇÃO (faça backup antes)

Regras:
  - Cada migração roda numa transação: se der erro, nada daquela migração fica no banco.
  - Uma migração já aplicada nunca deve ser editada (o script detecta e recusa). Crie uma nova.
  - Se a migração deixar qualquer tabela do schema public SEM RLS, ela é desfeita (decisão D17).
  - Antes de aplicar, o script mostra em QUAL banco vai mexer e pede confirmação.
  - Não imprime a senha.
"""
import argparse
import hashlib
import os
import pathlib
import re
import sys
from urllib.parse import urlparse

import psycopg2

RAIZ = pathlib.Path(__file__).resolve().parents[2]
PASTA_PADRAO = RAIZ / "db" / "migrations"
PADRAO_NOME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")

SQL_TABELA_CONTROLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  versao      VARCHAR(4)  PRIMARY KEY,
  nome        TEXT        NOT NULL,
  checksum    CHAR(64)    NOT NULL,
  aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE schema_migrations ENABLE ROW LEVEL SECURITY;
"""

SQL_TABELAS_SEM_RLS = """
SELECT c.relname
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity
ORDER BY 1
"""


class ErroMigracao(Exception):
    pass


# ---------- funções puras (testadas sem banco) ----------

def checksum(texto: str) -> str:
    """Impressão digital do arquivo. Ignora a diferença de fim de linha entre Windows e Linux."""
    return hashlib.sha256(texto.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def listar_arquivos(pasta: pathlib.Path):
    """Devolve [(versao, nome, checksum, caminho)] em ordem. Recusa nomes fora do padrão e números repetidos."""
    arquivos, vistos = [], {}
    for caminho in sorted(pathlib.Path(pasta).glob("*.sql")):
        achou = PADRAO_NOME.match(caminho.name)
        if not achou:
            raise ErroMigracao(
                f"Nome inválido: {caminho.name}. Use NNNN_descricao_em_minusculas.sql (ex.: 0002_campi.sql)."
            )
        versao = achou.group(1)
        if versao in vistos:
            raise ErroMigracao(f"Número repetido {versao}: {vistos[versao]} e {caminho.name}.")
        vistos[versao] = caminho.name
        arquivos.append((versao, caminho.name, checksum(caminho.read_text(encoding="utf-8")), caminho))
    return arquivos


def planejar(arquivos, aplicadas):
    """arquivos: saída de listar_arquivos. aplicadas: {versao: (nome, checksum)}.
    Devolve (pendentes, problemas)."""
    problemas, pendentes = [], []
    por_versao = {a[0]: a for a in arquivos}
    for versao, (nome, soma) in sorted(aplicadas.items()):
        if versao not in por_versao:
            problemas.append(f"A migração {versao} ({nome}) está no banco mas o arquivo sumiu da pasta.")
        elif por_versao[versao][2] != soma:
            problemas.append(
                f"A migração {versao} ({nome}) já foi aplicada e o arquivo foi ALTERADO depois. "
                "Desfaça a alteração e crie uma migração nova."
            )
    maior = max(aplicadas) if aplicadas else None
    for versao, nome, _, _ in arquivos:
        if versao in aplicadas:
            continue
        if maior is not None and versao < maior:
            problemas.append(
                f"A migração {versao} ({nome}) é mais antiga que a última aplicada ({maior}). Renumere para uma maior."
            )
        pendentes.append(versao)
    return [a for a in arquivos if a[0] in pendentes], problemas


# ---------- banco ----------

def ler_env(caminho):
    arquivo = pathlib.Path(caminho)
    if not arquivo.exists():
        raise ErroMigracao(f"Não achei o arquivo {arquivo}.")
    dados = {}
    for linha in arquivo.read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            dados[chave.strip()] = valor.strip().strip('"').strip("'")
    return dados


def url_do_banco(args):
    if args.usar_variavel_de_ambiente:
        url = os.environ.get("DATABASE_URL", "")
    else:
        url = ler_env(args.env).get("DATABASE_URL", "")
    if not url:
        raise ErroMigracao("DATABASE_URL está vazia ou ausente.")
    return url.replace("postgresql+psycopg2://", "postgresql://", 1)


def descrever_destino(url):
    p = urlparse(url)
    return f"servidor {p.hostname}:{p.port or 5432}, banco '{(p.path or '/')[1:]}', usuário '{p.username}'"


def migracoes_aplicadas(conn):
    """Lê o que já foi aplicado SEM criar nada (para --listar ser só leitura)."""
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.schema_migrations')")
        if cur.fetchone()[0] is None:
            return {}
        cur.execute("SELECT versao, nome, checksum FROM schema_migrations")
        return {v: (n, s.strip()) for v, n, s in cur.fetchall()}


def aplicar(conn, pendentes):
    with conn, conn.cursor() as cur:
        cur.execute(SQL_TABELA_CONTROLE)
    for versao, nome, soma, caminho in pendentes:
        print(f"  aplicando {nome} ...", end=" ", flush=True)
        try:
            with conn, conn.cursor() as cur:  # uma transação por migração: erro = rollback
                cur.execute(caminho.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations (versao, nome, checksum) VALUES (%s, %s, %s)",
                    (versao, nome, soma),
                )
                cur.execute(SQL_TABELAS_SEM_RLS)
                sem_rls = [r[0] for r in cur.fetchall()]
                if sem_rls:
                    raise ErroMigracao(
                        "tabela(s) sem RLS: " + ", ".join(sem_rls)
                        + ". Acrescente ALTER TABLE <tabela> ENABLE ROW LEVEL SECURITY; na migração."
                    )
        except ErroMigracao as erro:
            print("DESFEITA")
            raise ErroMigracao(f"{nome}: {erro}") from None
        except psycopg2.Error as erro:
            print("DESFEITA")
            raise ErroMigracao(f"{nome}: {str(erro).strip().splitlines()[0]}") from None
        print("ok")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Aplica as migrações SQL pendentes.")
    origem = ap.add_mutually_exclusive_group(required=True)
    origem.add_argument("--env", help="arquivo .env com a DATABASE_URL (ex.: backend/.env ou backend/.env.prod)")
    origem.add_argument("--usar-variavel-de-ambiente", action="store_true", help="usa a variável DATABASE_URL (para o CI)")
    ap.add_argument("--listar", action="store_true", help="só mostra o estado; não altera nada")
    ap.add_argument("--sim", action="store_true", help="não pergunta antes de aplicar (CI)")
    ap.add_argument("--pasta", default=str(PASTA_PADRAO), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    try:
        arquivos = listar_arquivos(pathlib.Path(args.pasta))
        url = url_do_banco(args)
        print(f"Destino: {descrever_destino(url)}")
        conn = psycopg2.connect(url, connect_timeout=15)
    except ErroMigracao as erro:
        print(f"ERRO: {erro}")
        return 1
    except psycopg2.Error as erro:
        print(f"ERRO ao conectar: {str(erro).strip().splitlines()[0]}")
        return 1

    try:
        aplicadas = migracoes_aplicadas(conn)
        conn.rollback()
        pendentes, problemas = planejar(arquivos, aplicadas)
        print("\nMigrações:")
        for versao, nome, _, _ in arquivos:
            estado = "aplicada" if versao in aplicadas else "PENDENTE"
            print(f"  {nome:45} {estado}")
        for versao in sorted(set(aplicadas) - {a[0] for a in arquivos}):
            print(f"  {versao}_? (arquivo sumiu)                       aplicada")
        if problemas:
            print("\nPROBLEMAS:")
            for p in problemas:
                print(f"  - {p}")
            return 1
        if args.listar:
            return 0
        if not pendentes:
            print("\nNada a aplicar: o banco já está em dia.")
            return 0
        if not args.sim:
            resposta = input(f"\nAplicar {len(pendentes)} migração(ões) NESSE banco? Digite 'sim' para continuar: ")
            if resposta.strip().lower() != "sim":
                print("Cancelado. Nada foi alterado.")
                return 1
        print()
        aplicar(conn, pendentes)
        print("\nPronto. O banco está em dia.")
        return 0
    except ErroMigracao as erro:
        print(f"\nERRO: {erro}\nNada daquela migração ficou no banco.")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
