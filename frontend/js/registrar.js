const form = document.getElementById("form-registro");
const mensagem = document.getElementById("mensagem");
const campoData = document.getElementById("encontrado_em");
const botao = document.getElementById("enviar");
let campus = null;

function agoraLocal() { // "AAAA-MM-DDTHH:MM" no horário do aparelho
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}
campoData.max = agoraLocal();
campoData.value = agoraLocal();

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = texto ? "msg " + tipo : ""; }

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
    form.reset();
    campoData.value = agoraLocal();
    mostrar("Item registrado no campus " + item.campus.nome + ", obrigado!" +
      (item.categoria ? " Categoria identificada: " + item.categoria + "." : ""), "ok");
  } catch (erro) {
    mostrar(erro.message, "erro");
  } finally {
    botao.disabled = false;
  }
});

iniciarCampus(
  (escolhido) => {
    campus = escolhido;
    mostrar(campus ? "" : "Escolha no topo da página o campus em que você encontrou o item.", "aviso");
  },
  (erro) => mostrar(erro.message, "erro"),
);
