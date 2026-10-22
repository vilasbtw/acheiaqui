"""
Backup simples: exporta cada tabela do schema public para um arquivo CSV.
O plano gratuito do Supabase NÃO faz backup automático, então rode isto ANTES de migrar produção.

Uso (venv ativo):
    python backend/scripts/exportar_dados.py --env backend/.env.prod

Saída: backend/backups/AAAA-MM-DD_HHMMSS/<tabela>.csv
ATENÇÃO: os arquivos têm dados pessoais (contato de quem achou, nome de quem retirou).
A pasta backups/ é ignorada pelo Git automaticamente; não envie esses arquivos a ninguém; apague quando não precisar mais.
O backup guarda os DADOS. A estrutura das tabelas está nas migrações em db/migrations/.
"""
import argparse
import datetime
import os
import pathlib
import sys

import psycopg2
from psycopg2 import sql

RAIZ_BACKEND = pathlib.Path(__file__).resolve().parents[1]


def ler_env(caminho):
    arquivo = pathlib.Path(caminho)
    if not arquivo.exists():
        sys.exit(f"ERRO: não achei o arquivo {arquivo}.")
    dados = {}
    for linha in arquivo.read_text(encoding="utf-8", errors="ignore").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            dados[chave.strip()] = valor.strip().strip('"').strip("'")
    return dados


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exporta as tabelas do banco para CSV.")
    origem = ap.add_mutually_exclusive_group(required=True)
    origem.add_argument("--env", help="arquivo .env com a DATABASE_URL")
    origem.add_argument("--usar-variavel-de-ambiente", action="store_true")
    ap.add_argument("--saida", default=str(RAIZ_BACKEND / "backups"), help="pasta de destino")
    args = ap.parse_args(argv)

    url = os.environ.get("DATABASE_URL", "") if args.usar_variavel_de_ambiente else ler_env(args.env).get("DATABASE_URL", "")
    url = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    if not url:
        sys.exit("ERRO: DATABASE_URL está vazia ou ausente.")

    raiz_backups = pathlib.Path(args.saida)
    raiz_backups.mkdir(parents=True, exist_ok=True)
    protecao = raiz_backups / ".gitignore"
    if not protecao.exists():
        protecao.write_text("*\n", encoding="utf-8")  # a pasta inteira fica fora do Git, mesmo sem regra na raiz

    pasta = raiz_backups / datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    pasta.mkdir()
    try:
        conn = psycopg2.connect(url, connect_timeout=15)
    except psycopg2.Error as erro:
        sys.exit(f"ERRO ao conectar: {str(erro).strip().splitlines()[0]}")

    resumo = []
    with conn, conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
        tabelas = [linha[0] for linha in cur.fetchall()]
        for tabela in tabelas:
            consulta = sql.SQL("COPY (SELECT * FROM {} ORDER BY 1) TO STDOUT WITH CSV HEADER").format(sql.Identifier(tabela))
            with open(pasta / f"{tabela}.csv", "w", encoding="utf-8", newline="") as arquivo:
                cur.copy_expert(consulta.as_string(conn), arquivo)
            cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabela)))
            resumo.append((tabela, cur.fetchone()[0]))
    conn.close()

    print(f"Backup em: {pasta}")
    for tabela, linhas in resumo:
        print(f"  {tabela:20} {linhas} linha(s)")
    print("\nLembrete: contém dados pessoais. Não envie, não commite, apague depois.")


if __name__ == "__main__":
    main()
