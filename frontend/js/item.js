const mensagem = document.getElementById("mensagem");
const avisoCompartilhar = document.getElementById("aviso-compartilhar");

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = texto ? "msg " + tipo : ""; }

function preencher(item) {
  document.title = item.descricao + " — Achei Aqui";
  document.getElementById("item-descricao").textContent = item.descricao;
  const categoria = document.getElementById("item-categoria");
  categoria.hidden = !item.categoria;
  categoria.textContent = item.categoria || "";
  document.getElementById("item-local").textContent = item.local_encontrado;
  document.getElementById("item-quando").textContent = formatarQuando(item.encontrado_em);
  document.getElementById("item-campus").textContent = item.campus.nome;
  document.getElementById("item-retirada").textContent = textoRetirada(item.campus);
  guardarCampus(item.campus.sigla);
  mostrarCampus(item.campus);
  document.getElementById("item").hidden = false;
}

async function compartilhar() {
  const dados = { title: document.title, text: "Encontrado no campus: " + document.getElementById("item-descricao").textContent, url: location.href };
  if (navigator.share) {
    try { await navigator.share(dados); } catch (e) { /* a pessoa fechou a janela de compartilhar */ }
    return;
  }
  try {
    await navigator.clipboard.writeText(location.href);
    avisoCompartilhar.textContent = "Link copiado. É só colar na conversa.";
  } catch (e) {
    avisoCompartilhar.textContent = "Copie o endereço da barra do navegador para compartilhar.";
  }
}

async function iniciar() {
  const id = new URLSearchParams(location.search).get("id");
  if (!id || !/^\d+$/.test(id)) {
    mostrar("Link inválido. Volte para a busca e escolha um item.", "erro");
    return;
  }
  mostrar("Carregando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  try {
    preencher(await detalharItem(id));
    mostrar("", "");
  } catch (erro) {
    mostrar(erro.status === 404
      ? "Este item não está mais disponível. Talvez já tenha sido devolvido ao dono."
      : erro.message, erro.status === 404 ? "aviso" : "erro");
  }
}

document.getElementById("compartilhar").addEventListener("click", compartilhar);
iniciar();
