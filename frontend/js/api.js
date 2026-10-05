// Comunicação com o backend. Depois do deploy, troque API_URL pela URL do Render.
const API_URL = "http://localhost:8000";
// Texto fixo exibido ao público (RF04). AJUSTEM com os dados reais da CAE.
const INFO_CAE = "Para retirar ou entregar um item, procure a CAE (sala X, segunda a sexta, 8h às 17h).";

async function chamarApi(caminho, opcoes) {
  let resposta;
  try {
    resposta = await fetch(API_URL + caminho, opcoes);
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
    throw new Error(motivo);
  }
  return resposta.json();
}

function registrarItem(dados) {
  return chamarApi("/itens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
}

function buscarItens(q, limit, offset) {
  const params = new URLSearchParams({ limit, offset });
  if (q) params.set("q", q);
  return chamarApi("/itens?" + params.toString());
}
