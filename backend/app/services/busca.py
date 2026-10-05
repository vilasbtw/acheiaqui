"""
Busca por palavras-chave (D1): sem extensão do banco e sem API externa.

Um item é encontrado se ALGUMA palavra da busca aparece na descrição, no local ou no
nome da categoria. Quanto mais palavras batem, mais acima ele aparece.
Limitações conhecidas: não ignora acentos e não entende sinônimos além da categoria.
"""
import operator
import re
from functools import reduce

from sqlalchemy import case, false, or_

from app.models.categoria import Categoria
from app.models.item import Item

MIN_LETRAS = 3
MAX_PALAVRAS = 6


def extrair_palavras(texto: str) -> list[str]:
    """Palavras com letras/números (sem _ nem símbolos), minúsculas, sem repetir."""
    palavras: list[str] = []
    for palavra in re.findall(r"[^\W_]{%d,}" % MIN_LETRAS, texto.lower()):
        if palavra not in palavras:
            palavras.append(palavra)
    return palavras[:MAX_PALAVRAS]


def aplicar_busca(consulta, texto: str):
    """`consulta` precisa ter outerjoin com Categoria. Filtra e ordena por relevância."""
    palavras = extrair_palavras(texto)
    if not palavras:
        return consulta.filter(false())

    pontos = []
    for palavra in palavras:
        padrao = f"%{palavra}%"
        bate = or_(
            Item.descricao.ilike(padrao),
            Item.local_encontrado.ilike(padrao),
            Categoria.nome.ilike(padrao),
        )
        pontos.append(case((bate, 1), else_=0))

    total = reduce(operator.add, pontos)
    return consulta.filter(total > 0).order_by(total.desc(), Item.criado_em.desc(), Item.id.desc())
