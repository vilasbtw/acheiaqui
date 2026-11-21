// "Perdi um item" (Etapa 6). O segredo devolvido pela API vai no link depois do "#":
// o que vem depois do "#" nunca é enviado a servidor nenhum (nem à Vercel, nem no Referer).
const form = document.getElementById("form-perdido");
const mensagem = document.getElementById("mensagem");
const campoData = document.getElementById("perdido_em");
const botao = document.getElementById("enviar");
const sucesso = document.getElementById("sucesso");
const campoLink = document.getElementById("link-secreto");
let campus = null;

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = texto ? "msg " + tipo : ""; }

function hojeLocal() { // "AAAA-MM-DD" no horário do aparelho
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}

campoData.max = hojeLocal();
campoData.value = hojeLocal();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!campus) {
    mostrar("Escolha no topo da página o campus em que você perdeu o item.", "erro");
    return;
  }
  botao.disabled = true;
  mostrar("Enviando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  try {
    const criado = await registrarPerdido({
      campus: campus.sigla,
      descricao: document.getElementById("descricao").value,
      perdido_em: campoData.value,
      local_perdido: document.getElementById("local").value.trim() || null,
      contato: document.getElementById("contato").value,
    });
    const link = new URL("perdido.html", location.href);
    link.hash = "t=" + criado.token;
    campoLink.value = link.href;
    document.getElementById("abrir-link").href = link.href;
    document.getElementById("sucesso-retirada").textContent = textoRetirada(campus);
    mostrar("", "");
    form.hidden = true;
    sucesso.hidden = false;
    sucesso.focus();
  } catch (erro) {
    mostrar(erro.message, "erro");
  } finally {
    botao.disabled = false;
  }
});

document.getElementById("copiar").addEventListener("click", async () => {
  const aviso = document.getElementById("copiado");
  try {
    await navigator.clipboard.writeText(campoLink.value);
    aviso.textContent = "Link copiado. Guarde em um lugar seguro (ex.: mande para você mesmo).";
  } catch (e) {
    campoLink.select();
    aviso.textContent = "Não deu para copiar sozinho: o link está selecionado, copie com Ctrl+C.";
  }
});

iniciarCampus(
  (escolhido) => {
    campus = escolhido;
    if (!form.hidden) mostrar(campus ? "" : "Escolha no topo da página o campus em que você perdeu o item.", "aviso");
  },
  (erro) => mostrar(erro.message, "erro"),
);
