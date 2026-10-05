"""
Verificação rápida da Fase 2 (Supabase). Pode ser apagado depois.

Onde colocar: backend/scripts/verificar_supabase.py
Como rodar (de qualquer pasta):  python backend/scripts/verificar_supabase.py

Lê SUPABASE_URL e SUPABASE_ANON_KEY de backend/.env. Usa só a biblioteca padrão.
Testes:
  1. A API REST pública NÃO devolve dados das tabelas (D17).
  2. O login da conta da CAE funciona.
  3. Criar conta nova (sign-up) é recusado (D6).
"""
import getpass
import json
import pathlib
import secrets
import sys
import urllib.error
import urllib.request


def carregar_env():
    caminho = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if not caminho.exists():
        sys.exit(f"Não achei {caminho}. Copie .env.example para .env e preencha.")
    dados = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        dados[chave.strip()] = valor.strip().strip('"').strip("'")
    return dados


def requisitar(metodo, url, chave, corpo=None):
    """Retorna (status, texto). status é None se não houve resposta (rede)."""
    cabecalhos = {"apikey": chave, "Content-Type": "application/json"}
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, headers=cabecalhos, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=20) as resposta:
            return resposta.status, resposta.read().decode()
    except urllib.error.HTTPError as erro:
        return erro.code, erro.read().decode()
    except urllib.error.URLError as erro:
        return None, str(erro.reason)


def resumo(texto, limite=200):
    return texto if len(texto) <= limite else texto[:limite] + "..."


def main():
    env = carregar_env()
    url = env.get("SUPABASE_URL", "").rstrip("/")
    chave = env.get("SUPABASE_ANON_KEY", "")
    if not url or not chave:
        sys.exit("Preencha SUPABASE_URL e SUPABASE_ANON_KEY em backend/.env")

    resultados = []

    # 1) A API REST pública não pode devolver dados
    status, corpo = requisitar("GET", f"{url}/rest/v1/categorias?select=*", chave)
    if status is None:
        resultados.append(("API REST pública bloqueada", False, f"sem resposta: {corpo}"))
    elif status == 200:
        try:
            linhas = json.loads(corpo)
        except ValueError:
            linhas = None
        if isinstance(linhas, list) and len(linhas) == 0:
            resultados.append(("API REST pública bloqueada", True, "voltou [] (RLS ativo)"))
        else:
            resultados.append(("API REST pública bloqueada", False,
                               "VOLTARAM DADOS! Confira o RLS e 'Automatically expose new tables'"))
    else:
        resultados.append(("API REST pública bloqueada", True,
                           f"status {status} (acesso negado), correto"))

    # 2) Login da CAE
    email = input("\nE-mail da conta da CAE (Enter para pular este teste): ").strip()
    if email:
        senha = getpass.getpass("Senha: ")
        status, corpo = requisitar(
            "POST", f"{url}/auth/v1/token?grant_type=password", chave,
            {"email": email, "password": senha},
        )
        if status == 200 and "access_token" in corpo:
            resultados.append(("Login da CAE", True, "recebeu access_token"))
        else:
            resultados.append(("Login da CAE", False, f"status {status}: {resumo(corpo)}"))

    # 3) Sign-up deve estar desativado
    email_teste = f"teste-{secrets.token_hex(4)}@example.com"
    status, corpo = requisitar(
        "POST", f"{url}/auth/v1/signup", chave,
        {"email": email_teste, "password": "Teste-" + secrets.token_hex(6)},
    )
    if status in (200, 201):
        resultados.append(("Sign-up desativado", False,
                           f"A CONTA FOI CRIADA ({email_teste})! Desative o sign-up e apague "
                           "esse usuário em Authentication → Users"))
    elif status is None:
        resultados.append(("Sign-up desativado", False, f"sem resposta: {corpo}"))
    else:
        resultados.append(("Sign-up desativado", True, f"status {status} (recusado), correto"))

    print("\n=== Resultado ===")
    for nome, ok, detalhe in resultados:
        print(f"[{'OK' if ok else 'FALHOU'}] {nome} — {detalhe}")

    if not all(ok for _, ok, _ in resultados):
        sys.exit(1)


if __name__ == "__main__":
    main()
