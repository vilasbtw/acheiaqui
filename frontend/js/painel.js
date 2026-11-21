const POR_PAGINA = 20;
let deslocamento = 0;

const lista = document.getElementById("resultados");
const mensagem = document.getElementById("mensagem");
const botaoMais = document.getElementById("mais");
const dialogo = document.getElementById("dialogo-devolucao");
const formDevolucao = document.getElementById("form-devolucao");
const campoNome = document.getElementById("nome_retirante");
const erroDialogo = document.getElementById("dialogo-erro");
const botaoConfirmar = document.getElementById("confirmar-devolucao");
let devolucaoAtual = null; // { item, card } do item que está no diálogo

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

// A foto exige o token, e <img src> não manda o header Authorization. Então: fetch com o token,
// e a imagem vira um endereço blob: local (só existe nesta aba).
async function baixarFoto(itemId) {
  const token = await tokenAtual();
  if (!token) { location.href = "login.html"; throw new Error("Sessão expirada."); }
  let resposta;
  try {
    resposta = await fetch(CONFIG.apiUrl + "/cae/itens/" + encodeURIComponent(itemId) + "/foto", {
      headers: { Authorization: "Bearer " + token },
    });
  } catch (e) {
    throw new Error("Não foi possível carregar a foto. Tente de novo.");
  }
  if (resposta.status === 401) {
    await supabaseCliente.auth.signOut();
    location.href = "login.html";
    throw new Error("Sessão expirada.");
  }
  if (!resposta.ok) throw new Error("Não foi possível carregar a foto (" + resposta.status + ").");
  return URL.createObjectURL(await resposta.blob());
}

function adicionarBotaoFoto(item, card, acoes) {
  const botao = criar("button", "secundario", "Ver foto");
  botao.type = "button";
  let figura = null;
  botao.addEventListener("click", async () => {
    if (figura) { // já carregada: só mostra ou esconde
      figura.hidden = !figura.hidden;
      botao.textContent = figura.hidden ? "Ver foto" : "Esconder foto";
      return;
    }
    botao.disabled = true;
    try {
      const imagem = criar("img");
      imagem.alt = "Foto de: " + item.descricao;
      imagem.src = await baixarFoto(item.id);
      figura = criar("div", "foto-cae");
      figura.append(imagem);
      card.insertBefore(figura, acoes);
      botao.textContent = "Esconder foto";
    } catch (erro) {
      mostrar(erro.message, "erro");
    } finally {
      botao.disabled = false;
    }
  });
  acoes.append(botao);
}

// Arquivar (spam) e desarquivar (D23). `pergunta`: confirmação antes de agir, ou null para agir direto.
function botaoDeStatus(item, card, texto, acao, pergunta) {
  const botao = criar("button", "secundario", texto);
  botao.type = "button";
  botao.addEventListener("click", async () => {
    if (pergunta && !confirm(pergunta)) return;
    botao.disabled = true;
    try {
      const atualizado = await chamarCae("/cae/itens/" + item.id + "/" + acao, { method: "POST" });
      card.replaceWith(criarCard(atualizado));
      mostrar(acao === "arquivar"
        ? "“" + atualizado.descricao + "” foi arquivado e saiu da busca pública."
        : "“" + atualizado.descricao + "” voltou para a busca pública.", "ok");
    } catch (erro) {
      mostrar(erro.message, "erro");
      botao.disabled = false;
    }
  });
  return botao;
}

function criarCard(item) {
  const card = criar("article", "cartao cartao-cae");
  const cabeca = criar("div", "cabeca");
  cabeca.append(criar("span", "cartao-titulo", item.descricao));
  const etiquetas = {
    disponivel: criar("span", "etiqueta", "Disponível"),
    devolvido: criar("span", "etiqueta devolvido", "Devolvido"),
    arquivado: criar("span", "etiqueta arquivado", "Arquivado"),
  };
  cabeca.append(etiquetas[item.status] || etiquetas.disponivel);
  card.append(cabeca);
  card.append(criar("span", "meta", "Encontrado em: " + item.local_encontrado + " · " + formatarQuando(item.encontrado_em) +
    (item.categoria ? " · " + item.categoria : "")));
  card.append(criar("span", "meta", "Contato de quem achou: " + (item.contato_achador || "não informado")));
  if (item.devolucao) {
    card.append(criar("span", "meta", "Retirado por " + item.devolucao.nome_retirante + " em " + formatarData(item.devolucao.data_devolucao)));
  }
  const acoes = criar("div", "acoes");
  if (item.status === "disponivel") {
    const botao = criar("button", "", "Registrar devolução");
    botao.type = "button";
    botao.addEventListener("click", () => abrirDevolucao(item, card));
    acoes.append(botao);
    acoes.append(botaoDeStatus(item, card, "Arquivar (spam)", "arquivar",
      "Arquivar “" + item.descricao + "”? Ele some da busca pública. Dá para desfazer depois."));
  }
  if (item.status === "arquivado") {
    card.append(criar("span", "meta", "Arquivado: não aparece na busca pública."));
    acoes.append(botaoDeStatus(item, card, "Desarquivar", "desarquivar", null));
  }
  if (item.tem_foto) adicionarBotaoFoto(item, card, acoes);
  if (acoes.children.length) card.append(acoes);
  return card;
}

function abrirDevolucao(item, card) {
  devolucaoAtual = { item, card };
  document.getElementById("dialogo-item").textContent = "Item: " + item.descricao;
  formDevolucao.reset();
  erroDialogo.hidden = true;
  botaoConfirmar.disabled = false;
  dialogo.showModal();
  campoNome.focus();
}

formDevolucao.addEventListener("submit", async (e) => {
  e.preventDefault(); // só fecha depois que a API confirmar
  const { item, card } = devolucaoAtual;
  botaoConfirmar.disabled = true;
  erroDialogo.hidden = true;
  try {
    const atualizado = await chamarCae("/cae/itens/" + item.id + "/devolucao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome_retirante: campoNome.value }),
    });
    dialogo.close();
    card.replaceWith(criarCard(atualizado));
    mostrar("Devolução registrada: “" + atualizado.descricao + "” foi entregue a " + atualizado.devolucao.nome_retirante + ".", "ok");
  } catch (erro) {
    erroDialogo.textContent = erro.message;
    erroDialogo.hidden = false;
    botaoConfirmar.disabled = false;
  }
});
document.getElementById("cancelar-devolucao").addEventListener("click", () => dialogo.close());

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

document.getElementById("form-filtros").addEventListener("submit", (e) => { e.preventDefault(); carregar(true); });
botaoMais.addEventListener("click", () => carregar(false));
document.getElementById("sair").addEventListener("click", async (e) => {
  e.preventDefault();
  await supabaseCliente.auth.signOut();
  location.href = "login.html";
});

tokenAtual().then((token) => { if (!token) location.href = "login.html"; else iniciar(); });
