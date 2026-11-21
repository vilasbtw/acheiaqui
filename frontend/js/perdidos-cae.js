// Itens perdidos na área da CAE (Etapa 6, D27): sugestões por regras + IA, e a CAE sempre confirma.
const POR_PAGINA = 20;
let deslocamento = 0;

const lista = document.getElementById("resultados");
const mensagem = document.getElementById("mensagem");
const botaoMais = document.getElementById("mais");

const ETIQUETAS = {
  procurando: ["etiqueta", "Procurando"],
  encontrado: ["etiqueta encontrado", "Encontrado"],
  entregue: ["etiqueta devolvido", "Entregue"],
  encerrado: ["etiqueta devolvido", "Encerrado"],
};
const NOTAS = {
  alta: "IA: provavelmente é o mesmo item",
  media: "IA: pode ser o mesmo item",
  baixa: "IA: provavelmente é outro item",
};

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = texto ? "msg " + tipo : ""; }
function formatarDia(iso) { return iso.slice(0, 10).split("-").reverse().join("/"); }

// Etapa 7 (D28): o e-mail sai em segundo plano depois da confirmação; aqui a CAE vê o resultado.
function textoDoAviso(perdido) {
  if (!perdido.aviso_consentido) return "Aviso por e-mail: não pediu";
  const base = "Aviso por e-mail (" + perdido.email_aviso + "): ";
  if (perdido.aviso_enviado_em) return base + "enviado em " + formatarQuando(perdido.aviso_enviado_em);
  if (perdido.status === "procurando") return base + "será enviado quando a CAE confirmar";
  if (perdido.status !== "encontrado") return base + "não enviado";
  if (perdido.aviso_erro) return base + "falhou (" + perdido.aviso_erro + ")";
  return base + "enviando… atualize a lista para ver o resultado";
}

function botaoAcao(texto, classe, aoClicar) {
  const botao = criar("button", classe, texto);
  botao.type = "button";
  botao.addEventListener("click", async () => {
    botao.disabled = true;
    try { await aoClicar(); } catch (erro) { mostrar(erro.message, "erro"); } finally { botao.disabled = false; }
  });
  return botao;
}

async function trocarStatus(perdido, card, acao, corpo, aviso) {
  const atualizado = await chamarCae("/cae/perdidos/" + perdido.id + "/" + acao, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  card.replaceWith(criarCard(atualizado));
  mostrar(aviso, "ok");
}

function criarSugestao(sugestao, perdido, card) {
  const item = sugestao.item;
  const caixa = criar("div", "sugestao");
  caixa.append(criar("span", "cartao-titulo", item.descricao));
  caixa.append(criar("span", "meta", "Encontrado em: " + item.local_encontrado + " · " + formatarQuando(item.encontrado_em) +
    (item.categoria ? " · " + item.categoria : "") + (item.tem_foto ? " · tem foto (veja em Itens achados)" : "")));
  const nota = criar("span", "meta nota-ia " + (sugestao.nota_ia || ""),
    (NOTAS[sugestao.nota_ia] || "IA indisponível: sugestão só pelas regras") + " · " + sugestao.pontos + " pontos nas regras");
  caixa.append(nota);
  const acoes = criar("div", "acoes");
  acoes.append(botaoAcao("Confirmar: é este", "", async () => {
    if (!confirm("Confirmar que “" + item.descricao + "” é o item perdido? Quem perdeu vai ver \"Seu item pode estar na CAE\".")) return;
    await trocarStatus(perdido, card, "confirmar", { item_id: item.id },
      "Confirmado. Quem perdeu já vê pelo link que o item pode estar na CAE.");
  }));
  caixa.append(acoes);
  return caixa;
}

async function verSugestoes(perdido, card, area, botao) {
  if (!area.hidden && area.children.length) { // já aberto: fecha
    area.hidden = true;
    botao.textContent = "Ver sugestões";
    return;
  }
  area.hidden = false;
  area.replaceChildren(criar("p", "meta", "Procurando achados parecidos… a IA pode levar alguns segundos."));
  const sugestoes = await chamarCae("/cae/perdidos/" + perdido.id + "/sugestoes");
  area.replaceChildren();
  if (!sugestoes.length) {
    area.append(criar("p", "meta", "Nenhum achado parecido por enquanto. Volte a olhar quando chegarem itens novos."));
  }
  sugestoes.forEach((s) => area.append(criarSugestao(s, perdido, card)));
  botao.textContent = "Esconder sugestões";
}

function criarCard(perdido) {
  const card = criar("article", "cartao cartao-cae");
  const cabeca = criar("div", "cabeca");
  cabeca.append(criar("span", "cartao-titulo", perdido.descricao));
  const [classe, texto] = ETIQUETAS[perdido.status] || ETIQUETAS.procurando;
  cabeca.append(criar("span", classe, texto));
  card.append(cabeca);
  card.append(criar("span", "meta", "Perdido em: " + formatarDia(perdido.perdido_em) +
    (perdido.local_perdido ? " · " + perdido.local_perdido : "") + (perdido.categoria ? " · " + perdido.categoria : "")));
  card.append(criar("span", "meta", "Contato de quem perdeu: " + perdido.contato));
  if (perdido.item) {
    card.append(criar("span", "meta", "Achado confirmado: " + perdido.item.descricao +
      (perdido.confirmado_em ? " (em " + formatarDia(perdido.confirmado_em) + ")" : "")));
  }
  card.append(criar("span", "meta", textoDoAviso(perdido)));

  const acoes = criar("div", "acoes");
  const area = criar("div", "sugestoes");
  area.hidden = true;
  if (perdido.status === "procurando") {
    const botaoSugestoes = criar("button", "", "Ver sugestões");
    botaoSugestoes.type = "button";
    botaoSugestoes.addEventListener("click", async () => {
      botaoSugestoes.disabled = true;
      try { await verSugestoes(perdido, card, area, botaoSugestoes); }
      catch (erro) { area.hidden = true; mostrar(erro.message, "erro"); }
      finally { botaoSugestoes.disabled = false; }
    });
    acoes.append(botaoSugestoes);
    acoes.append(botaoAcao("Encerrar pedido", "secundario", async () => {
      if (!confirm("Encerrar o pedido de “" + perdido.descricao + "”? Dá para reabrir depois.")) return;
      await trocarStatus(perdido, card, "encerrar", null, "Pedido encerrado.");
    }));
  } else {
    if (perdido.status === "encontrado" && perdido.aviso_consentido) {
      acoes.append(botaoAcao(perdido.aviso_enviado_em ? "Reenviar aviso" : "Enviar aviso de novo", "secundario", () =>
        trocarStatus(perdido, card, "reenviar-aviso", null, "Aviso por e-mail reenviado. Atualize a lista em alguns segundos para ver o resultado.")));
    }
    if (perdido.status !== "entregue") { // entregue: o item já foi retirado, não tem volta
      acoes.append(botaoAcao("Reabrir", "secundario", () =>
        trocarStatus(perdido, card, "reabrir", null, "Pedido reaberto: voltou para \"Procurando\".")));
    }
  }
  card.append(acoes);
  card.append(area);
  return card;
}

async function carregar(reiniciar) {
  if (reiniciar) { deslocamento = 0; lista.replaceChildren(); }
  botaoMais.hidden = true;
  mostrar("Carregando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  const params = new URLSearchParams({ limit: POR_PAGINA, offset: deslocamento });
  const status = document.getElementById("status").value;
  if (status) params.set("status", status);
  try {
    const perdidos = await chamarCae("/cae/perdidos?" + params.toString());
    perdidos.forEach((p) => lista.append(criarCard(p)));
    deslocamento += perdidos.length;
    botaoMais.hidden = perdidos.length < POR_PAGINA;
    mostrar(lista.children.length ? "" : "Nenhum pedido com esse filtro.", "aviso");
  } catch (erro) {
    mostrar(erro.message, "erro");
  }
}

async function iniciar() {
  try {
    const campus = await chamarCae("/cae/campus");
    document.getElementById("campus-cae").textContent = "Campus " + campus.nome;
    document.getElementById("site-publico").href = "../index.html?campus=" + encodeURIComponent(campus.sigla);
  } catch (erro) {
    if (erro.status === 403) document.getElementById("form-filtros").hidden = true;
    mostrar(erro.message, "erro");
    return;
  }
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
