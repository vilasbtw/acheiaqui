"""
Avaliação da IA de categorização (D2): mede quanto ela acerta num conjunto de descrições rotuladas à mão.

Chama a MESMA função da produção (app.services.ia_categoria.sugerir_categoria), com as 8 categorias da
migração 0001, e calcula:
  - acurácia: acertos / total (resposta vazia conta como erro);
  - cobertura: quantas vezes a IA devolveu alguma categoria válida;
  - precisão quando responde: acertos / respostas válidas;
  - precisão e recall por categoria, e a matriz de confusão;
  - latência (mediana e p95) e acurácia só dos casos difíceis.

Uso (venv ativo, com IA_API_KEY, IA_BASE_URL e IA_MODEL no backend/.env):
    python backend/scripts/avaliar_ia.py                                # modelo do .env
    python backend/scripts/avaliar_ia.py --modelos modelo-a modelo-b    # compara modelos do mesmo provedor
    python backend/scripts/avaliar_ia.py --pausa 4                      # provedor com cota por minuto menor

O relatório vai para docs/avaliacao-ia/AAAA-MM-DD_<modelo>.md. As descrições são inventadas: nenhum dado real
de pessoa é enviado ao provedor.
"""
import argparse
import csv
import datetime
import os
import pathlib
import re
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass
from typing import Optional

PASTA_BACKEND = pathlib.Path(__file__).resolve().parents[1]
RAIZ = PASTA_BACKEND.parent
CONJUNTO_PADRAO = pathlib.Path(__file__).resolve().parent / "avaliacao_ia" / "conjunto.csv"
SAIDA_PADRAO = RAIZ / "docs" / "avaliacao-ia"
# As mesmas da migração 0001, na mesma ordem.
CATEGORIAS = ["Documentos", "Eletrônicos", "Material escolar", "Roupas e acessórios",
              "Garrafas e marmitas", "Chaves", "Bolsas e mochilas", "Outros"]
SEM_RESPOSTA = "(nenhuma)"


@dataclass
class Caso:
    descricao: str
    esperada: str
    dificil: bool


@dataclass
class Resultado:
    caso: Caso
    obtida: Optional[str]
    segundos: float

    @property
    def acertou(self) -> bool:
        return self.obtida == self.caso.esperada


# ---------- funções puras (testadas sem rede) ----------

def ler_conjunto(caminho: pathlib.Path) -> list[Caso]:
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return [Caso(linha["descricao"], linha["esperada"], linha["dificil"] == "sim") for linha in csv.DictReader(arquivo)]


def percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    if not ordenados:
        return 0.0
    posicao = (len(ordenados) - 1) * p
    baixo = int(posicao)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


def calcular_metricas(resultados: list[Resultado], categorias: list[str]) -> dict:
    total = len(resultados)
    acertos = sum(r.acertou for r in resultados)
    respondidos = [r for r in resultados if r.obtida is not None]
    dificeis = [r for r in resultados if r.caso.dificil]
    por_categoria = {}
    for categoria in categorias:
        previstos = [r for r in resultados if r.obtida == categoria]
        reais = [r for r in resultados if r.caso.esperada == categoria]
        certos = sum(r.acertou for r in reais)
        por_categoria[categoria] = {
            "casos": len(reais),
            "precisao": certos / len(previstos) if previstos else None,
            "recall": certos / len(reais) if reais else None,
        }
    matriz = Counter((r.caso.esperada, r.obtida or SEM_RESPOSTA) for r in resultados)
    tempos = [r.segundos for r in resultados]
    return {
        "total": total,
        "acertos": acertos,
        "acuracia": acertos / total if total else 0.0,
        "cobertura": len(respondidos) / total if total else 0.0,
        "precisao_quando_responde": sum(r.acertou for r in respondidos) / len(respondidos) if respondidos else None,
        "acuracia_dificeis": sum(r.acertou for r in dificeis) / len(dificeis) if dificeis else None,
        "dificeis": len(dificeis),
        "por_categoria": por_categoria,
        "matriz": matriz,
        "latencia_mediana": statistics.median(tempos) if tempos else 0.0,
        "latencia_p95": percentil(tempos, 0.95),
    }


def _pct(valor: Optional[float]) -> str:
    return "—" if valor is None else f"{valor * 100:.1f}%".replace(".", ",")


def _seg(valor: float) -> str:
    return f"{valor:.2f} s".replace(".", ",")


def _celula(texto: str) -> str:
    return texto.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def montar_relatorio(modelo: str, provedor: str, resultados: list[Resultado], categorias: list[str], data: str,
                     rotulo: str = "") -> str:
    m = calcular_metricas(resultados, categorias)
    abreviar = {c: c.split()[0][:6] for c in categorias} | {SEM_RESPOSTA: "nenhuma"}
    linhas = [
        f"# Avaliação da IA de categorização: `{modelo}`" + (f" ({rotulo})" if rotulo else ""),
        "",
        f"Data: {data} · Provedor: {provedor} · Casos: {m['total']} ({m['dificeis']} difíceis) · "
        "Gerado por `backend/scripts/avaliar_ia.py`",
        "",
        "## Resumo",
        "",
        "| Métrica | Valor |",
        "| --- | --- |",
        f"| Acurácia (acertos / total) | **{_pct(m['acuracia'])}** ({m['acertos']} de {m['total']}) |",
        f"| Cobertura (devolveu uma categoria válida) | {_pct(m['cobertura'])} |",
        f"| Precisão quando responde | {_pct(m['precisao_quando_responde'])} |",
        f"| Acurácia nos casos difíceis | {_pct(m['acuracia_dificeis'])} |",
        f"| Latência mediana | {_seg(m['latencia_mediana'])} |",
        f"| Latência p95 | {_seg(m['latencia_p95'])} |",
        "",
        "## Por categoria",
        "",
        "| Categoria | Casos | Precisão | Recall |",
        "| --- | --- | --- | --- |",
    ]
    for categoria, valores in m["por_categoria"].items():
        linhas.append(f"| {categoria} | {valores['casos']} | {_pct(valores['precisao'])} | {_pct(valores['recall'])} |")
    colunas = categorias + [SEM_RESPOSTA]
    linhas += [
        "",
        "## Matriz de confusão",
        "",
        "Linhas: categoria esperada. Colunas: o que a IA respondeu.",
        "",
        "| Esperada \\ Obtida | " + " | ".join(abreviar[c] for c in colunas) + " |",
        "| --- |" + " --- |" * len(colunas),
    ]
    for esperada in categorias:
        celulas = []
        for obtida in colunas:
            n = m["matriz"].get((esperada, obtida), 0)
            celulas.append(f"**{n}**" if obtida == esperada else (str(n) if n else "·"))
        linhas.append(f"| {esperada} | " + " | ".join(celulas) + " |")
    erros = [r for r in resultados if not r.acertou]
    linhas += ["", f"## Erros ({len(erros)})", ""]
    if erros:
        linhas += ["| Descrição | Esperada | Obtida | Difícil |", "| --- | --- | --- | --- |"]
        for r in erros:
            linhas.append(f"| {_celula(r.caso.descricao)} | {r.caso.esperada} | {r.obtida or SEM_RESPOSTA} | "
                          f"{'sim' if r.caso.dificil else 'não'} |")
    else:
        linhas.append("Nenhum.")
    return "\n".join(linhas) + "\n"


def nome_de_arquivo(modelo: str, data: str, rotulo: str = "") -> str:
    nome = re.sub(r"[^a-z0-9]+", "-", f"{modelo} {rotulo}".lower()).strip("-")
    return f"{data}_{nome}.md"


# ---------- execução ----------

def avaliar(modelo: str, casos: list[Caso], pausa: float) -> list[Resultado]:
    from app.services.ia_categoria import sugerir_categoria

    os.environ["IA_MODEL"] = modelo  # sugerir_categoria lê o .env a cada chamada
    resultados = []
    for numero, caso in enumerate(casos, 1):
        inicio = time.perf_counter()
        obtida = sugerir_categoria(caso.descricao, CATEGORIAS)
        resultados.append(Resultado(caso, obtida, time.perf_counter() - inicio))
        marca = "ok  " if obtida == caso.esperada else "ERRO"
        print(f"  [{numero:3}/{len(casos)}] {marca} {caso.descricao[:45]!r:48} -> {obtida}")
        if numero < len(casos):
            time.sleep(pausa)
    return resultados


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mede a acurácia da IA de categorização.")
    ap.add_argument("--modelos", nargs="+", help="modelos a comparar (padrão: IA_MODEL do .env)")
    ap.add_argument("--pausa", type=float, default=2.5, help="segundos entre chamadas (cota por minuto do provedor)")
    ap.add_argument("--rotulo", default="", help="vai no título e no nome do arquivo (ex.: prompt-v2)")
    ap.add_argument("--conjunto", default=str(CONJUNTO_PADRAO))
    ap.add_argument("--saida", default=str(SAIDA_PADRAO))
    args = ap.parse_args(argv)

    sys.path.insert(0, str(PASTA_BACKEND))
    from dotenv import load_dotenv

    load_dotenv(PASTA_BACKEND / ".env")
    faltando = [v for v in ("IA_API_KEY", "IA_BASE_URL", "IA_MODEL") if not os.getenv(v, "").strip()]
    if faltando and not (args.modelos and faltando == ["IA_MODEL"]):
        sys.exit("Faltam no backend/.env: " + ", ".join(faltando))

    casos = ler_conjunto(pathlib.Path(args.conjunto))
    modelos = args.modelos or [os.environ["IA_MODEL"]]
    provedor = re.sub(r"^https?://([^/]+).*$", r"\1", os.environ["IA_BASE_URL"])
    data = datetime.date.today().isoformat()
    saida = pathlib.Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    resumo = []
    for modelo in modelos:
        print(f"\nModelo {modelo} ({len(casos)} casos):")
        resultados = avaliar(modelo, casos, args.pausa)
        if not any(r.obtida for r in resultados):
            # Nenhuma resposta válida: quase sempre é configuração (modelo inexistente, chave, cota), não a IA errando.
            print(f"  NENHUMA resposta válida de {modelo}: relatório não gravado. Veja os avisos 'IA:' acima.")
            continue
        relatorio = montar_relatorio(modelo, provedor, resultados, CATEGORIAS, data, args.rotulo)
        arquivo = saida / nome_de_arquivo(modelo, data, args.rotulo)
        arquivo.write_text(relatorio, encoding="utf-8")
        m = calcular_metricas(resultados, CATEGORIAS)
        resumo.append((modelo, m))
        print(f"  -> {arquivo.relative_to(RAIZ) if arquivo.is_relative_to(RAIZ) else arquivo}")

    print("\nModelo                                    Acurácia  Cobertura  Mediana   p95")
    for modelo, m in resumo:
        print(f"{modelo:40}  {_pct(m['acuracia']):>8}  {_pct(m['cobertura']):>9}  "
              f"{_seg(m['latencia_mediana']):>7}  {_seg(m['latencia_p95']):>7}")


if __name__ == "__main__":
    main()
