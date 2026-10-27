async function chamarApi(caminho, opcoes) {
  let resposta;
  try {
    resposta = await fetch(CONFIG.apiUrl + caminho, opcoes);
  } catch (e) {
    throw new Error("Não foi possível conectar ao servidor. Se ele estava parado, aguarde cerca de 1 minuto e tente de novo.");
  }
  if (!resposta.ok) {
    let motivo = "Erro inesperado (" + resposta.status + ").";
    try {
      const corpo = await resposta.json();
      if (typeof corpo.detail === "string") motivo = corpo.detail;
      else if (Array.isArray(corpo.detail)) motivo = corpo.detail.map((d) => d.msg).join(" ");
    } catch (e) { /* mantém a mensagem padrão */ }
    const erro = new Error(motivo);
    erro.status = resposta.status;
    throw erro;
  }
  return resposta.json();
}

function listarCampi() {
  return chamarApi("/campi");
}

function listarCategorias() {
  return chamarApi("/categorias");
}

function registrarItem(dados) {
  return chamarApi("/itens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
}

function buscarItens(campus, { q, categoriaId, limit, offset }) {
  const params = new URLSearchParams({ campus, limit, offset });
  if (q) params.set("q", q);
  if (categoriaId) params.set("categoria_id", categoriaId);
  return chamarApi("/itens?" + params.toString());
}

function detalharItem(id) {
  return chamarApi("/itens/" + encodeURIComponent(id));
}

// "2026-10-20T10:00:00" -> "20/10/2026 às 10:00" (hora do campus, sem conversão de fuso: D7)
function formatarQuando(iso) {
  const [data, hora] = iso.split("T");
  return data.split("-").reverse().join("/") + " às " + hora.slice(0, 5);
}

function criar(tag, classe, texto) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (texto !== undefined) elemento.textContent = texto; // textContent: nunca interpreta HTML
  return elemento;
}
