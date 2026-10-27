const form = document.getElementById("form-registro");
const mensagem = document.getElementById("mensagem");
const campoData = document.getElementById("encontrado_em");
const detalhesQuando = document.getElementById("detalhes-quando");
const botao = document.getElementById("enviar");
const sucesso = document.getElementById("sucesso");
let campus = null;

function agoraLocal() { // "AAAA-MM-DDTHH:MM" no horário do aparelho
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

function prepararFormulario() {
  form.reset();
  campoData.max = agoraLocal();
  campoData.value = agoraLocal();
  detalhesQuando.open = false;
}

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = texto ? "msg " + tipo : ""; }

// Campo com erro dentro do "Encontrou em outro dia?" fechado: abre para a pessoa ver o aviso do navegador.
form.addEventListener("invalid", (e) => {
  const detalhes = e.target.closest("details");
  if (detalhes) detalhes.open = true;
}, true);

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!campus) {
    mostrar("Escolha no topo da página o campus em que você encontrou o item.", "erro");
    return;
  }
  botao.disabled = true;
  mostrar("Enviando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  const contato = document.getElementById("contato").value.trim();
  try {
    const item = await registrarItem({
      campus: campus.sigla,
      descricao: document.getElementById("descricao").value,
      local_encontrado: document.getElementById("local").value,
      encontrado_em: campoData.value,
      contato_achador: contato || null,
    });
    mostrar("", "");
    document.getElementById("sucesso-resumo").textContent = "“" + item.descricao + "” foi registrado no campus " + item.campus.nome +
      (item.categoria ? ", na categoria " + item.categoria + "." : ".");
    document.getElementById("sucesso-retirada").textContent = textoRetirada(item.campus);
    document.getElementById("ver-item").href = "item.html?id=" + encodeURIComponent(item.id) + "&campus=" + encodeURIComponent(item.campus.sigla);
    form.hidden = true;
    sucesso.hidden = false;
    sucesso.focus();
  } catch (erro) {
    mostrar(erro.message, "erro");
  } finally {
    botao.disabled = false;
  }
});

document.getElementById("registrar-outro").addEventListener("click", () => {
  prepararFormulario();
  sucesso.hidden = true;
  form.hidden = false;
  document.getElementById("descricao").focus();
});

prepararFormulario();
iniciarCampus(
  (escolhido) => {
    campus = escolhido;
    if (!form.hidden) mostrar(campus ? "" : "Escolha no topo da página o campus em que você encontrou o item.", "aviso");
  },
  (erro) => mostrar(erro.message, "erro"),
);
