# Achei Aqui

Portal web de achados e perdidos, desenvolvido como trabalho de faculdade.

## Stack

- **Backend:** Python (FastAPI) + SQLAlchemy
- **Banco de dados / Auth / Storage:** Supabase
- **Frontend:** HTML, CSS e JavaScript puro
- **Deploy:** Render (backend) + Vercel/Netlify (frontend) — free tier

## Estrutura do projeto

```
achei-aqui/
├── backend/        # API FastAPI
├── frontend/        # Portal web (HTML/CSS/JS)
└── docs/            # Memory bank e matriz de requisitos
```

## Como rodar o backend localmente

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # preencher com os dados do Supabase
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. Documentação automática em `http://localhost:8000/docs`.

## Como rodar o frontend localmente

Basta abrir os arquivos `.html` da pasta `frontend/` no navegador, ou servir a pasta com uma extensão tipo Live Server. Nenhum build é necessário.

## Convenções do time

- **Branches:** uma por funcionalidade, ex: `feature/registrar-item`, `feature/painel-cae`
- **Nomenclatura:** em português, já que o domínio do projeto é em português (`item`, `devolucao`, `categoria` etc.)
- **`.env`:** nunca commitado — cada integrante configura o próprio localmente a partir do `.env.example`

Mais detalhes de decisões de arquitetura em [`docs/memory-bank.md`](docs/memory-bank.md).
