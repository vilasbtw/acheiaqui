// Acompanhamento pelo link secreto (perdido.html#t=SEGREDO). D27: só o status; o achado só aparece
// depois que a CAE confirmou. O segredo é lido do "#" e enviado no corpo do POST, nunca na URL da API.
const mensagem = document.getElementById("mensagem");
const secao = document.getElementById("pedido");
const botaoEncerrar = document.getElementById("encerrar");
const token = new URLSearchParams(location.hash.slice(1)).get("t");

const STATUS = {
  procurando: { etiqueta: "Procurando", classe: "etiqueta",
    texto: "A CAE está comparando o seu pedido com os itens encontrados no campus. Volte a este link de vez em quando." },
  encontrado: { etiqueta: "Pode estar na CAE", classe: "etiqueta encontrado", texto: "" },
  entregue: { etiqueta: "Entregue", classe: "etiqueta encontrado", texto: "" },
  encerrado: { etiqueta: "Encerrado", classe: "etiqueta devolvido",
    texto: "Este pedido foi encerrado e não está mais em busca." },
};

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = texto ? "msg " + tipo : ""; }
function formatarDia(iso) { return iso.slice(0, 10).split("-").reverse().join("/"); }

function exibir(pedido) {
  const status = STATUS[pedido.status] || STATUS.procurando;
  document.getElementById("descricao").textContent = pedido.descricao;
  const etiqueta = document.getElementById("etiqueta");
  etiqueta.textContent = status.etiqueta;
  etiqueta.className = status.classe;
  document.getElementById("perdido-em").textContent = formatarDia(pedido.perdido_em);
  document.getElementById("campus-nome").textContent = pedido.campus.nome;
  document.getElementById("criado-em").textContent = pedido.criado_em ? formatarDia(pedido.criado_em) : "—";
  const explicacoes = {
    encontrado: "A CAE encontrou um item que parece ser o seu: “" + pedido.item_encontrado + "”. Vá até a CAE com um documento para conferir e retirar.",
    entregue: "Item entregue: “" + pedido.item_encontrado + "”. Que bom que você o encontrou!",
  };
  document.getElementById("explicacao").textContent = explicacoes[pedido.status] || status.texto;
  mostrarCampus(pedido.status === "encontrado" ? pedido.campus : null);
  document.getElementById("rodape-campus").textContent = "Campus " + pedido.campus.nome;
  document.getElementById("ver-busca").href = "index.html?campus=" + encodeURIComponent(pedido.campus.sigla);
  botaoEncerrar.hidden = pedido.status !== "procurando";
  secao.hidden = false;
}

botaoEncerrar.addEventListener("click", async () => {
  if (!confirm("Encerrar o pedido? A CAE deixa de procurar o seu item.")) return;
  botaoEncerrar.disabled = true;
  try {
    exibir(await encerrarPerdido(token));
    mostrar("Pedido encerrado.", "ok");
  } catch (erro) {
    mostrar(erro.message, "erro");
  } finally {
    botaoEncerrar.disabled = false;
  }
});

async function carregar() {
  if (!token) {
    mostrar("Este endereço está incompleto. Abra o link inteiro que você recebeu ao registrar o item perdido.", "erro");
    return;
  }
  mostrar("Carregando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  try {
    exibir(await acompanharPerdido(token));
    mostrar("", "");
  } catch (erro) {
    mostrar(erro.message, "erro");
  }
}

carregar();
