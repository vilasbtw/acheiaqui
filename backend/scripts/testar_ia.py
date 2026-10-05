"""
Teste manual da IA de categorização (Fase 4). Pode ser apagado depois.
Uso (venv ativo, de qualquer pasta):  python backend/scripts/testar_ia.py
Mostra a categoria sugerida para alguns exemplos e, se falhar, o motivo (sem mostrar a chave).
"""
import os
import pathlib
import sys
import time

import httpx
from dotenv import load_dotenv

pasta_backend = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pasta_backend))
load_dotenv(pasta_backend / ".env")

from app.services.ia_categoria import sugerir_categoria  # noqa: E402

CATEGORIAS = ["Documentos", "Eletrônicos", "Material escolar", "Roupas e acessórios",
              "Garrafas e marmitas", "Chaves", "Bolsas e mochilas", "Outros"]
EXEMPLOS = ["Carteira de identidade com foto", "Carregador de celular branco", "Garrafa térmica azul",
            "Moletom cinza tamanho M", "Chaveiro com três chaves", "Caderno de matemática com capa vermelha"]

faltando = [v for v in ("IA_API_KEY", "IA_BASE_URL", "IA_MODEL") if not os.getenv(v, "").strip()]
if faltando:
    sys.exit("Faltam no backend/.env: " + ", ".join(faltando))

for exemplo in EXEMPLOS:
    inicio = time.time()
    categoria = sugerir_categoria(exemplo, CATEGORIAS)
    print(f"{exemplo!r:45} -> {categoria}  ({time.time() - inicio:.1f}s)")

if sugerir_categoria(EXEMPLOS[0], CATEGORIAS) is None:
    print("\nSem resposta válida. Diagnóstico da chamada:")
    try:
        r = httpx.post(
            os.environ["IA_BASE_URL"].rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + os.environ["IA_API_KEY"]},
            json={"model": os.environ["IA_MODEL"], "messages": [{"role": "user", "content": "Diga apenas: ok"}]},
            timeout=15,
        )
        print("status:", r.status_code, "|", r.text[:300])
    except httpx.HTTPError as erro:
        print("erro de rede:", type(erro).__name__)
