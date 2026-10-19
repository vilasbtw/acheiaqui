# Achei Aqui

Portal web para registro e consulta de itens achados e perdidos. O sistema traz transparência no processo de devolução e conta com um agente de Inteligência Artificial para identificar correspondências automáticas entre itens perdidos e encontrados.

## Tecnologias

O projeto utiliza Python, FastAPI, SQLAlchemy e Supabase no backend. O frontend é construído com HTML, CSS e JavaScript. A inteligência artificial atua na comparação semântica de descrições para gerar alertas automáticos.

## Como rodar pela primeira vez

Abra o seu terminal para clonar o repositório e configurar o backend.

git clone https://github.com/vilasbtw/acheiaqui.git
cd C:/acheiaqui/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

Abra um novo terminal para iniciar o frontend.

cd C:\Pagani\acheiaqui\frontend
python -m http.server 5500

Acesse o endereço localhost:5500 no seu navegador.

## Como rodar pela segunda vez

Para rodar o projeto novamente em outras ocasiões, o processo é mais curto.

No terminal do backend, execute os comandos de ativação.

cd C:/acheiaqui/backend
venv\Scripts\activate
uvicorn app.main:app --reload

Em outro terminal, inicie o servidor do frontend.

cd C:\Pagani\acheiaqui\frontend
python -m http.server 5500

Acesse o endereço localhost:5500 no seu navegador.