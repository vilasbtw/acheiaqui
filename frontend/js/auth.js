// Login da CAE via Supabase Auth. Os endereços e a chave pública ficam em js/config.js.
const supabaseCliente = window.supabase.createClient(CONFIG.supabaseUrl, CONFIG.supabaseChave);

async function tokenAtual() {
  const { data } = await supabaseCliente.auth.getSession();
  return data.session ? data.session.access_token : null;
}
