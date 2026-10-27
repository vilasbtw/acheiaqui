// Endereços de cada ambiente. No localhost o site usa a API local e, se preenchido, o Supabase do banco de testes;
// no endereço publicado, a produção. As chaves do Supabase aqui são PÚBLICAS por design (publishable key).
// Nunca coloque aqui a "secret key" nem a "service_role".
const PRODUCAO = {
  apiUrl: "https://acheiaqui-api.onrender.com",
  supabaseUrl: "https://ltfdwsvxhgunifdzaclt.supabase.co",
  supabaseChave: "sb_publishable_9pMe1E7mE8-KCpRxcRDhEg_curzxD7_",
};

// Banco de testes: Supabase, Project Settings, API. Vazio = o login local usa o Supabase de produção.
// O backend local precisa apontar para o MESMO projeto (SUPABASE_URL e SUPABASE_ANON_KEY no backend/.env).
const TESTES = {
  apiUrl: "http://localhost:8000",
  supabaseUrl: "",
  supabaseChave: "",
};

const LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);
const CONFIG = LOCAL
  ? {
    apiUrl: TESTES.apiUrl,
    supabaseUrl: TESTES.supabaseUrl || PRODUCAO.supabaseUrl,
    supabaseChave: TESTES.supabaseChave || PRODUCAO.supabaseChave,
  }
  : PRODUCAO;
