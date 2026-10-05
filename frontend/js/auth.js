// Login da CAE via Supabase Auth. Esta chave é PÚBLICA por design (publishable key): não é segredo.
// Nunca coloque aqui a "secret key" nem a "service_role".
const SUPABASE_URL = "https://ltfdwsvxhgunifdzaclt.supabase.co";
const SUPABASE_CHAVE_PUBLICA = "sb_publishable_9pMe1E7mE8-KCpRxcRDhEg_curzxD7_";
const supabaseCliente = window.supabase.createClient(SUPABASE_URL, SUPABASE_CHAVE_PUBLICA);

async function tokenAtual() {
  const { data } = await supabaseCliente.auth.getSession();
  return data.session ? data.session.access_token : null;
}
