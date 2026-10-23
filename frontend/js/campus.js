// Campus escolhido (D22): vem do ?campus= da URL ou da última escolha guardada no navegador.
// Se só existe um campus ativo, ele já vem escolhido.
const CHAVE_CAMPUS = "acheiaqui.campus";
const TEXTO_RETIRADA_PADRAO = "Para retirar ou entregar um item, procure a CAE do seu campus.";

function campusGuardado() {
  try { return localStorage.getItem(CHAVE_CAMPUS); } catch (e) { return null; }
}

function guardarCampus(sigla) {
  try { localStorage.setItem(CHAVE_CAMPUS, sigla); } catch (e) { /* sem armazenamento: vale só a URL */ }
  const url = new URL(location.href);
  url.searchParams.set("campus", sigla);
  history.replaceState(null, "", url);
  document.querySelectorAll("a[data-manter-campus]").forEach((link) => {
    const destino = new URL(link.href);
    destino.searchParams.set("campus", sigla);
    link.href = destino;
  });
}

function mostrarRetirada(campus) {
  const caixa = document.getElementById("info-cae");
  caixa.hidden = !campus;
  if (campus) caixa.textContent = campus.nome + ": " + (campus.info_retirada || TEXTO_RETIRADA_PADRAO);
}

// Preenche o seletor do cabeçalho e chama aoEscolher(campus) agora e a cada troca (campus = null se não há escolha).
async function iniciarCampus(aoEscolher, aoFalhar) {
  const seletor = document.getElementById("campus");
  let campi;
  try {
    campi = await listarCampi();
  } catch (erro) {
    seletor.replaceChildren(new Option("Indisponível", ""));
    aoFalhar(erro);
    return;
  }

  const pedido = new URLSearchParams(location.search).get("campus");
  const escolhido = campi.find((c) => c.sigla === pedido)
    || campi.find((c) => c.sigla === campusGuardado())
    || (campi.length === 1 ? campi[0] : null);

  seletor.replaceChildren();
  if (!escolhido) {
    const vazio = new Option("Escolha o seu campus", "");
    vazio.disabled = true;
    seletor.append(vazio);
  }
  campi.forEach((c) => seletor.append(new Option(c.nome, c.sigla)));
  seletor.value = escolhido ? escolhido.sigla : "";
  seletor.disabled = false;

  seletor.addEventListener("change", () => {
    const campus = campi.find((c) => c.sigla === seletor.value);
    guardarCampus(campus.sigla);
    mostrarRetirada(campus);
    aoEscolher(campus);
  });

  if (escolhido) guardarCampus(escolhido.sigla);
  mostrarRetirada(escolhido);
  aoEscolher(escolhido);
}
