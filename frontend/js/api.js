const API_URL = ["localhost", "127.0.0.1"].includes(location.hostname)
  ? "http://localhost:8000"
  : "https://acheiaqui-api.onrender.com";

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
    const erro = new Error(motivo);
    erro.status = resposta.status;
    throw erro;
  }
  return resposta.json();
}

function listarCampi() {
  return chamarApi("/campi");
}

function registrarItem(dados) {
  return chamarApi("/itens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
}

function buscarItens(campus, q, limit, offset) {
  const params = new URLSearchParams({ campus, limit, offset });
  if (q) params.set("q", q);
  return chamarApi("/itens?" + params.toString());
}
