// Funções comuns às páginas da CAE (painel e perdidos). Depende de api.js e auth.js.

// Chama a API enviando o token. Se a sessão acabou (401), volta para o login.
async function chamarCae(caminho, opcoes = {}) {
  const token = await tokenAtual();
  if (!token) { location.href = "login.html"; throw new Error("Sessão expirada."); }
  try {
    return await chamarApi(caminho, { ...opcoes, headers: { ...(opcoes.headers || {}), Authorization: "Bearer " + token } });
  } catch (erro) {
    if (erro.status === 401) {
      await supabaseCliente.auth.signOut();
      location.href = "login.html";
    }
    throw erro;
  }
}
