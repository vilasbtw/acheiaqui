// Prepara a foto do item no navegador, antes de enviar (D25).
// Redesenha a imagem num canvas e gera um JPEG menor. Isso:
//   - deixa o envio rápido no 4G e cabe no limite da API (600 KB);
//   - apaga os metadados (EXIF), que podem ter a localização GPS de onde a foto foi tirada;
//   - converte HEIC (iPhone) e outros formatos que o navegador consiga abrir.
const FOTO_LIMITE_BYTES = 500 * 1000; // abaixo dos 600 KB da API, com folga
const FOTO_TENTATIVAS = [ // lado maior em pixels, qualidade do JPEG
  [1280, 0.8], [1280, 0.65], [1024, 0.6], [800, 0.55], [640, 0.5],
];

function abrirImagem(arquivo) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(arquivo);
    const imagem = new Image();
    imagem.onload = () => { URL.revokeObjectURL(url); resolve(imagem); };
    imagem.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Não foi possível abrir essa imagem. Tente outra foto.")); };
    imagem.src = url;
  });
}

function desenharJpeg(imagem, ladoMaior, qualidade) {
  const escala = Math.min(1, ladoMaior / Math.max(imagem.naturalWidth, imagem.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(imagem.naturalWidth * escala);
  canvas.height = Math.round(imagem.naturalHeight * escala);
  const contexto = canvas.getContext("2d");
  contexto.fillStyle = "#fff"; // PNG com fundo transparente não fica preto no JPEG
  contexto.fillRect(0, 0, canvas.width, canvas.height);
  contexto.drawImage(imagem, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", qualidade);
}

// Bytes reais de um data URL em base64 (cada 4 caracteres = 3 bytes).
function tamanhoDataUrl(dataUrl) {
  const base64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
  return Math.floor(base64.length * 3 / 4) - (base64.endsWith("==") ? 2 : base64.endsWith("=") ? 1 : 0);
}

async function prepararFoto(arquivo) {
  if (arquivo.type && !arquivo.type.startsWith("image/")) throw new Error("Escolha um arquivo de imagem.");
  const imagem = await abrirImagem(arquivo);
  for (const [ladoMaior, qualidade] of FOTO_TENTATIVAS) {
    const dataUrl = desenharJpeg(imagem, ladoMaior, qualidade);
    if (tamanhoDataUrl(dataUrl) <= FOTO_LIMITE_BYTES) return dataUrl;
  }
  throw new Error("Não foi possível reduzir essa foto. Tente outra imagem.");
}
