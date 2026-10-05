const form = document.getElementById("form-login");
const mensagem = document.getElementById("mensagem");
const botao = document.getElementById("entrar");

tokenAtual().then((token) => { if (token) location.href = "painel.html"; });

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  botao.disabled = true;
  mensagem.className = "msg aviso";
  mensagem.textContent = "Entrando…";
  const { error } = await supabaseCliente.auth.signInWithPassword({
    email: document.getElementById("email").value.trim(),
    password: document.getElementById("senha").value,
  });
  if (error) {
    mensagem.className = "msg erro";
    mensagem.textContent = "E-mail ou senha incorretos.";
    botao.disabled = false;
    return;
  }
  location.href = "painel.html";
});
