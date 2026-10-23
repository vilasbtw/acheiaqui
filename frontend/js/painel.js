const POR_PAGINA = 20;
let deslocamento = 0;

const lista = document.getElementById("resultados");
const mensagem = document.getElementById("mensagem");
const botaoMais = document.getElementById("mais");

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = texto ? "msg " + tipo : ""; }
function formatarData(iso) { return iso.split("-").reverse().join("/"); } // evita deslocar o dia por fuso

// Chama a API enviando o token. Se a sessão acabou (401), volta para o login.
async function chamarCae(caminho, opcoes = {}) {
  const token = await tokenAtual();
  if (!token) { location.href = "login.html"; throw new Error("Sessão expirada."); }
  try {
    return await chamarApi(caminho, { ...opcoes, headers: { ...(opcoes.headers || {}), Authorization: "Bearer " + token } });
  } catch (erro) {
    if (erro.status === 401) {
      await supabaseCliente.auth.signOut();
      location.href = "login.html";
    }
    throw erro;
  }
}

function criarCard(item) {
  const card = document.createElement("div");
  card.className = "card";
  const titulo = document.createElement("strong");
  titulo.textContent = item.descricao;
  const quando = new Date(item.encontrado_em).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  const linhas = [
    "Local: " + item.local_encontrado + " · Encontrado em: " + quando + (item.categoria ? " · Categoria: " + item.categoria : ""),
    "Contato de quem achou: " + (item.contato_achador || "não informado"),
    item.devolucao
      ? "Devolvido a " + item.devolucao.nome_retirante + " em " + formatarData(item.devolucao.data_devolucao)
      : "Status: disponível",
  ];
  card.append(titulo);
  linhas.forEach((texto) => { const p = document.createElement("p"); p.className = "meta"; p.textContent = texto; card.append(p); });
  if (item.status === "disponivel") {
    const botao = document.createElement("button");
    botao.textContent = "Registrar devolução";
    botao.addEventListener("click", () => devolver(item, card, botao));
    card.append(botao);
  }
  return card;
}

async function devolver(item, card, botao) {
  const nome = (prompt("Nome de quem está retirando o item:") || "").trim();
  if (!nome) return;
  botao.disabled = true;
  try {
    const atualizado = await chamarCae("/cae/itens/" + item.id + "/devolucao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome_retirante: nome }),
    });
    card.replaceWith(criarCard(atualizado));
    mostrar("Devolução registrada: o item foi entregue a " + atualizado.devolucao.nome_retirante + ".", "ok");
  } catch (erro) {
    mostrar(erro.message, "erro");
    botao.disabled = false;
  }
}

async function carregar(reiniciar) {
  if (reiniciar) { deslocamento = 0; lista.replaceChildren(); }
  botaoMais.hidden = true;
  mostrar("Carregando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  const params = new URLSearchParams({ limit: POR_PAGINA, offset: deslocamento });
  ["status", "data_inicio", "data_fim"].forEach((campo) => {
    const valor = document.getElementById(campo).value;
    if (valor) params.set(campo, valor);
  });
  try {
    const itens = await chamarCae("/cae/itens?" + params.toString());
    itens.forEach((item) => lista.append(criarCard(item)));
    deslocamento += itens.length;
    botaoMais.hidden = itens.length < POR_PAGINA;
    mostrar(lista.children.length ? "" : "Nenhum item encontrado com esses filtros.", "aviso");
  } catch (erro) {
    mostrar(erro.message, "erro");
  }
}

document.getElementById("form-filtros").addEventListener("submit", (e) => { e.preventDefault(); carregar(true); });
botaoMais.addEventListener("click", () => carregar(false));
document.getElementById("sair").addEventListener("click", async (e) => {
  e.preventDefault();
  await supabaseCliente.auth.signOut();
  location.href = "login.html";
});

// Primeiro descobre o campus da pessoa (D21). Logado sem vínculo com a CAE (403): explica e não mostra o painel.
async function iniciar() {
  mostrar("Carregando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  let campus;
  try {
    campus = await chamarCae("/cae/campus");
  } catch (erro) {
    if (erro.status === 403) document.getElementById("form-filtros").hidden = true;
    mostrar(erro.message, "erro");
    return;
  }
  document.getElementById("campus-cae").textContent = "Campus " + campus.nome;
  document.getElementById("site-publico").href = "../index.html?campus=" + encodeURIComponent(campus.sigla);
  carregar(true);
}

tokenAtual().then((token) => { if (!token) location.href = "login.html"; else iniciar(); });
