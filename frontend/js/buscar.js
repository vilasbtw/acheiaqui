const POR_PAGINA = 20;
let campus = null;
let termo = "";
let categoriaId = "";
let deslocamento = 0;
let consultaAtual = 0; // ignora respostas antigas quando a pessoa troca de campus ou de filtro no meio de uma busca

const formBusca = document.getElementById("form-busca");
const campoBusca = document.getElementById("q");
const campoCategoria = document.getElementById("categoria");
const tituloResultados = document.getElementById("titulo-resultados");
const resultados = document.getElementById("resultados");
const mensagem = document.getElementById("mensagem");
const botaoMais = document.getElementById("mais");

function mostrar(texto, tipo, acao) {
  mensagem.replaceChildren();
  mensagem.className = texto ? "msg " + tipo : "";
  if (!texto) return;
  mensagem.append(criar("span", "", texto));
  if (acao) {
    const botao = criar("button", "secundario", acao.texto);
    botao.type = "button";
    botao.addEventListener("click", acao.executar);
    mensagem.append(botao);
  }
}

function criarCard(item) {
  const card = criar("a", "cartao cartao-link");
  card.href = "item.html?id=" + encodeURIComponent(item.id) + "&campus=" + encodeURIComponent(campus.sigla);
  card.append(criar("span", "cartao-titulo", item.descricao));
  if (item.categoria) card.append(criar("span", "etiqueta", item.categoria));
  card.append(criar("span", "meta", "Encontrado em: " + item.local_encontrado + " · " + formatarQuando(item.encontrado_em)));
  return card;
}

function atualizarTitulo() {
  const nomeCategoria = categoriaId ? campoCategoria.selectedOptions[0].text : "";
  if (termo) tituloResultados.textContent = "Resultados para “" + termo + "”" + (nomeCategoria ? " em " + nomeCategoria : "");
  else if (nomeCategoria) tituloResultados.textContent = "Itens em " + nomeCategoria;
  else tituloResultados.textContent = "Encontrados recentemente";
}

function limparBusca() {
  termo = "";
  categoriaId = "";
  campoBusca.value = "";
  campoCategoria.value = "";
  carregar(true);
}

async function carregar(reiniciar) {
  if (reiniciar) { deslocamento = 0; resultados.replaceChildren(); }
  botaoMais.hidden = true;
  atualizarTitulo();
  if (!campus) {
    mostrar("Escolha o seu campus no topo da página para ver os itens.", "aviso");
    return;
  }
  const consulta = ++consultaAtual;
  mostrar(deslocamento ? "Carregando mais itens…" : "Buscando… se o servidor estava parado, a primeira busca pode levar até 1 minuto.", "aviso");
  try {
    const itens = await buscarItens(campus.sigla, { q: termo, categoriaId, limit: POR_PAGINA, offset: deslocamento });
    if (consulta !== consultaAtual) return;
    itens.forEach((item) => resultados.append(criarCard(item)));
    deslocamento += itens.length;
    botaoMais.hidden = itens.length < POR_PAGINA;
    if (resultados.children.length) {
      mostrar("", "");
    } else if (termo || categoriaId) {
      mostrar("Nenhum item encontrado com essa busca. Tente outras palavras ou outra categoria. Novos itens chegam todo dia.",
        "aviso", { texto: "Ver todos os itens", executar: limparBusca });
    } else {
      mostrar("Ainda não há itens disponíveis neste campus. Volte mais tarde.", "aviso");
    }
  } catch (erro) {
    if (consulta === consultaAtual) mostrar(erro.message, "erro", { texto: "Tentar de novo", executar: () => carregar(true) });
  }
}

async function carregarCategorias() {
  try {
    const categorias = await listarCategorias();
    categorias.forEach((c) => campoCategoria.append(new Option(c.nome, c.id)));
  } catch (erro) {
    campoCategoria.disabled = true; // a busca continua funcionando sem o filtro
  }
}

formBusca.addEventListener("submit", (e) => { e.preventDefault(); termo = campoBusca.value.trim(); carregar(true); });
campoCategoria.addEventListener("change", () => { categoriaId = campoCategoria.value; carregar(true); });
botaoMais.addEventListener("click", () => carregar(false));

carregarCategorias();
iniciarCampus(
  (escolhido) => {
    campus = escolhido;
    if (campus) document.getElementById("passo-retirada").textContent = textoRetirada(campus);
    carregar(true);
  },
  (erro) => mostrar(erro.message, "erro", { texto: "Tentar de novo", executar: () => location.reload() }),
);
