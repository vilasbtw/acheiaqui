const POR_PAGINA = 20;
let campus = null;
let termo = "";
let deslocamento = 0;
let consultaAtual = 0; // ignora respostas antigas quando a pessoa troca de campus no meio de uma busca

const formBusca = document.getElementById("form-busca");
const campoBusca = document.getElementById("q");
const resultados = document.getElementById("resultados");
const mensagem = document.getElementById("mensagem");
const botaoMais = document.getElementById("mais");

function mostrar(texto, tipo) {
  mensagem.textContent = texto;
  mensagem.className = texto ? "msg " + tipo : "";
}

function criarCard(item) {
  const card = document.createElement("div");
  card.className = "card";
  const titulo = document.createElement("strong");
  titulo.textContent = item.descricao; // textContent evita injeção de HTML
  const quando = new Date(item.encontrado_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = "Local: " + item.local_encontrado + " · Encontrado em: " + quando +
    (item.categoria ? " · Categoria: " + item.categoria : "");
  card.append(titulo, meta);
  return card;
}

async function carregar(reiniciar) {
  if (reiniciar) { deslocamento = 0; resultados.replaceChildren(); }
  botaoMais.hidden = true;
  if (!campus) {
    mostrar("Escolha o seu campus no topo da página para ver os itens.", "aviso");
    return;
  }
  const consulta = ++consultaAtual;
  mostrar("Buscando… se o servidor estava parado, a primeira busca pode levar até 1 minuto.", "aviso");
  try {
    const itens = await buscarItens(campus.sigla, termo, POR_PAGINA, deslocamento);
    if (consulta !== consultaAtual) return;
    itens.forEach((item) => resultados.append(criarCard(item)));
    deslocamento += itens.length;
    botaoMais.hidden = itens.length < POR_PAGINA;
    mostrar(resultados.children.length ? "" : "Nenhum item encontrado neste campus. Tente outras palavras ou volte mais tarde.", "aviso");
  } catch (erro) {
    if (consulta === consultaAtual) mostrar(erro.message, "erro");
  }
}

formBusca.addEventListener("submit", (e) => { e.preventDefault(); termo = campoBusca.value.trim(); carregar(true); });
botaoMais.addEventListener("click", () => carregar(false));
iniciarCampus(
  (escolhido) => { campus = escolhido; carregar(true); },
  (erro) => mostrar(erro.message, "erro"),
);
