const form = document.getElementById("form-registro");
const mensagem = document.getElementById("mensagem");
const campoData = document.getElementById("encontrado_em");
const botao = document.getElementById("enviar");

function agoraLocal() { // "AAAA-MM-DDTHH:MM" no horário do aparelho
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}
campoData.max = agoraLocal();
campoData.value = agoraLocal();
document.getElementById("info-cae").textContent = INFO_CAE;

function mostrar(texto, tipo) { mensagem.textContent = texto; mensagem.className = "msg " + tipo; }

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  botao.disabled = true;
  mostrar("Enviando… se o servidor estava parado, pode levar até 1 minuto.", "aviso");
  const contato = document.getElementById("contato").value.trim();
  try {
    const item = await registrarItem({
      descricao: document.getElementById("descricao").value,
      local_encontrado: document.getElementById("local").value,
      encontrado_em: campoData.value,
      contato_achador: contato || null,
    });
    form.reset();
    campoData.value = agoraLocal();
    mostrar("Item registrado, obrigado!" + (item.categoria ? " Categoria identificada: " + item.categoria + "." : ""), "ok");
  } catch (erro) {
    mostrar(erro.message, "erro");
  } finally {
    botao.disabled = false;
  }
});
