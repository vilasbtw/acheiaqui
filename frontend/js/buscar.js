const POR_PAGINA = 20;
let termo = "";
let deslocamento = 0;

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
  mostrar("Buscando… se o servidor estava parado, a primeira busca pode levar até 1 minuto.", "aviso");
  try {
    const itens = await buscarItens(termo, POR_PAGINA, deslocamento);
    itens.forEach((item) => resultados.append(criarCard(item)));
    deslocamento += itens.length;
    botaoMais.hidden = itens.length < POR_PAGINA;
    mostrar(resultados.children.length ? "" : "Nenhum item encontrado. Tente outras palavras ou volte mais tarde.", "aviso");
  } catch (erro) {
    mostrar(erro.message, "erro");
  }
}

formBusca.addEventListener("submit", (e) => { e.preventDefault(); termo = campoBusca.value.trim(); carregar(true); });
botaoMais.addEventListener("click", () => carregar(false));
document.getElementById("info-cae").textContent = INFO_CAE;
carregar(true);
