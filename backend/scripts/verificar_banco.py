"""
Diagnóstico da conexão com o banco (Fase 2.5). Pode ser apagado depois.

Onde colocar: backend/scripts/verificar_banco.py
Como rodar (com o venv ativo, de qualquer pasta):
    python backend/scripts/verificar_banco.py

NÃO imprime a senha. Mostra o que o código está lendo e tenta conectar.
"""
import os
import pathlib
import sys

import psycopg2
from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def main():
    pasta_backend = pathlib.Path(__file__).resolve().parent.parent
    caminho_env = pasta_backend / ".env"

    print(f".env: {caminho_env} -> {'existe' if caminho_env.exists() else 'NAO EXISTE'}")
    config_env = dotenv_values(caminho_env) if caminho_env.exists() else {}
    valor_env = config_env.get("DATABASE_URL")
    valor_sistema = os.environ.get("DATABASE_URL")

    # load_dotenv() NÃO sobrescreve variáveis que já existem no sistema/terminal.
    if valor_sistema is not None and valor_env is not None and valor_sistema != valor_env:
        print(
            "\nATENCAO: existe uma variavel de ambiente DATABASE_URL no Windows/terminal "
            "com valor DIFERENTE do .env.\n"
            "O load_dotenv() nao sobrescreve variaveis ja existentes, entao o app esta "
            "usando a do sistema e ignorando o .env.\n"
            "No PowerShell: Remove-Item Env:DATABASE_URL  (e confira as variaveis de "
            "ambiente do Windows)\n"
        )

    origem = "variavel de ambiente do sistema" if valor_sistema else ".env"
    texto_url = valor_sistema or valor_env
    if not texto_url:
        sys.exit("DATABASE_URL nao encontrada nem no sistema nem no .env")
    print(f"Origem da DATABASE_URL usada pelo app: {origem}")

    try:
        url = make_url(texto_url)
    except Exception as erro:
        sys.exit(f"A DATABASE_URL tem formato invalido ({type(erro).__name__}). "
                 "Formato: postgresql://USUARIO:SENHA@HOST:5432/postgres")

    senha = url.password or ""
    print(f"  usuario : {url.username}")
    print(f"  host    : {url.host}")
    print(f"  porta   : {url.port}")
    print(f"  banco   : {url.database}")
    print(f"  senha   : {len(senha)} caracteres (nao exibida)")

    problemas = []
    if not senha:
        problemas.append("a senha esta vazia")
    if "[" in senha or "]" in senha:
        problemas.append("a senha tem colchetes [ ]: remova, eles sao so do modelo do painel")
    if senha.upper() in ("SENHA", "YOUR-PASSWORD", "[YOUR-PASSWORD]", "PASSWORD"):
        problemas.append("a senha ainda e o texto-modelo")
    if any(c in senha for c in " \"'"):
        problemas.append("a senha tem espaco ou aspas")
    simbolos = sorted({c for c in senha if not c.isalnum()})
    if simbolos:
        problemas.append("a senha tem simbolos (" + " ".join(simbolos) +
                         "): precisam de codificacao na URL; prefira so letras e numeros")
    if url.host and "pooler.supabase.com" in url.host and "." not in (url.username or ""):
        problemas.append("no pooler o usuario deve ser postgres.ID_DO_PROJETO")

    url_supabase = config_env.get("SUPABASE_URL", "")
    if url_supabase and url.username and "." in url.username:
        id_projeto = url_supabase.replace("https://", "").split(".")[0]
        if url.username.split(".", 1)[1] != id_projeto:
            problemas.append("o ID do projeto no usuario nao bate com o da SUPABASE_URL")

    if problemas:
        print("\nPossiveis problemas encontrados:")
        for problema in problemas:
            print(f"  - {problema}")
    else:
        print("\nFormato da URL parece correto.")

    print("\nTentando conectar...")
    try:
        conexao = psycopg2.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=senha,
            dbname=url.database,
            connect_timeout=15,
        )
        cursor = conexao.cursor()
        cursor.execute("SELECT count(*) FROM categorias")
        quantidade = cursor.fetchone()[0]
        conexao.close()
        print(f"[OK] Conectou. A tabela categorias tem {quantidade} linha(s).")
    except Exception as erro:
        mensagem = str(erro).strip().splitlines()[0]
        print(f"[FALHOU] {mensagem}")
        if "password authentication failed" in mensagem:
            print("  -> Senha recusada. Resete a senha em Project Settings -> Database "
                  "(use so letras e numeros), atualize o .env e rode este script de novo.")
        elif "Tenant or user not found" in mensagem:
            print("  -> Usuario ou regiao/host errados. Copie a Session pooler de novo "
                  "em Connect e confira o host.")
        elif "could not translate host name" in mensagem:
            print("  -> Host digitado errado. Copie do painel.")
        sys.exit(1)


if __name__ == "__main__":
    main()
