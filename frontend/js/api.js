const API_URL = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? "http://localhost:8000"
  : "https://acheiaqui-api.onrender.com";

const INFO_CAE = "Para retirar ou entregar um item, procure a CAE.";

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
