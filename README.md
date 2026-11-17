# 📰 RAG News — Chat com Notícias

🔗 **Acesse o projeto online:** [https://ragnewsbbc.netlify.app/](https://ragnewsbbc.netlify.app/)

Projeto de faculdade: sistema de **Retrieval-Augmented Generation (RAG)** para responder perguntas sobre notícias atuais, usando **LangChain**, **LangGraph**, **OpenRouter** e **PGVector (Supabase)**.

---

## 🗂️ Estrutura do Monorepo

```
faculdade-rag-news/
├── backend/                  # FastAPI (Monólito Modular) + LangChain + LangGraph + OpenRouter
│   ├── main.py               # Entrypoint de compatibilidade (uvicorn main:app)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── app/
│       ├── main.py           # Factory create_app(), lifespan e registro de routers
│       ├── core/             # Config, SQLAlchemy, segurança JWT/PBKDF2, PGVector, LLM
│       ├── shared/           # Contratos (DTOs) e dependências de autenticação (get_current_user)
│       └── modules/          # Domínios isolados
│           ├── auth/         # Cadastro, login por e-mail/senha e emissão de JWT
│           ├── users/        # Perfil e persistência de usuários
│           ├── news/         # Feed BBC global, notícias salvas e fontes personalizadas
│           └── rag_chat/     # Grafo LangGraph isolado por escopo/usuário + histórico
└── frontend/                 # Vue 3 + Tailwind CSS
    ├── src/
    │   ├── App.vue
    │   ├── main.js
    │   ├── style.css
    │   └── components/
    │       ├── ChatSidebar.vue
    │       └── ChatMessage.vue
    ├── index.html
    └── vite.config.js
```

---

## ⚙️ Backend — Setup

### 1. Pré-requisitos
- Python 3.11+
- Chave de API no [OpenRouter](https://openrouter.ai/keys)
- Projeto no [Supabase](https://supabase.com) com extensão **pgvector** habilitada

### 2. Configurar variáveis de ambiente
```bash
cd backend
cp .env.example .env
# Edite o .env com sua OPENROUTER_API_KEY e credenciais do Supabase
```

### 3. Instalar dependências e rodar
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Rotas da API

#### Públicas / Compatibilidade
| Método | Rota           | Descrição                                                                       |
|--------|----------------|---------------------------------------------------------------------------------|
| GET    | `/`            | Health check, modelos ativos e arquitetura                                      |
| POST   | `/ingest`      | Busca notícias da BBC, gera embeddings e salva no PGVector (atalho legado)      |
| POST   | `/reset`       | Reseta tabelas do PGVector no Supabase (usar se trocar o modelo de embeddings) |
| POST   | `/chat`        | Pergunta ao RAG (`scope`: `global`, `saved`, `custom`, `personal_all`)         |

#### Autenticação & Usuários (`/auth`, `/users`)
| Método | Rota             | Descrição                                                                 |
|--------|------------------|---------------------------------------------------------------------------|
| POST   | `/auth/register` | Cadastro com nome, e-mail e senha (retorna JWT)                           |
| POST   | `/auth/login`    | Login com e-mail e senha (retorna JWT)                                    |
| GET    | `/auth/me`       | Valida JWT e retorna usuário autenticado                                  |
| GET    | `/users/me`      | Perfil do usuário autenticado                                             |
| PATCH  | `/users/me`      | Atualiza dados de perfil do usuário autenticado                           |

#### Notícias & Fontes Personalizadas (`/news`)
| Método | Rota                         | Descrição                                                        |
|--------|------------------------------|------------------------------------------------------------------|
| GET    | `/news/feed`                 | Lista artigos recentes dos feeds globais (BBC)                   |
| POST   | `/news/ingest`               | Executa ingestão global dos feeds da BBC                         |
| GET    | `/news/saved`                | Lista notícias salvas pelo usuário autenticado                   |
| POST   | `/news/saved`                | Salva notícia (feed ou URL externa) e indexa vetores do usuário  |
| DELETE | `/news/saved/{news_id}`      | Remove notícia salva e seus embeddings                           |
| GET    | `/news/sources`              | Lista fontes personalizadas do usuário                           |
| POST   | `/news/sources`              | Cadastra fonte personalizada (`rss_feed`, `article_url`, `topic`)|
| POST   | `/news/sources/{id}/sync`    | Sincroniza e indexa conteúdos da fonte personalizada             |
| DELETE | `/news/sources/{id}`         | Remove fonte personalizada e seus embeddings                     |

#### Histórico de Chat (`/chat`)
| Método | Rota                   | Descrição                                              |
|--------|------------------------|--------------------------------------------------------|
| GET    | `/chat/sessions`       | Lista sessões de chat do usuário autenticado           |
| GET    | `/chat/sessions/{id}`  | Detalhes da sessão com histórico completo de mensagens |
| DELETE | `/chat/sessions/{id}`  | Remove uma sessão de chat e suas mensagens             |

---

## 🎨 Frontend — Setup

```bash
cd frontend
npm install
npm run dev
# Acesse: http://localhost:5173
```

> O Vite está configurado com proxy: chamadas para `/chat`, `/ingest`, `/reset`, `/auth`, `/users` e `/news`
> são redirecionadas automaticamente para `http://localhost:8000`.

---

## 🐳 Docker Compose (Local & Raspberry Pi)

A forma mais simples de subir o projeto completo (PostgreSQL com **pgvector**, **Backend FastAPI** e **Frontend Nginx**) tanto localmente quanto em um **Raspberry Pi (ARM64)**:

### Subir toda a stack com Docker
```bash
# 1. Configure o ambiente do backend
cp backend/.env.example backend/.env
# Edite backend/.env com sua OPENROUTER_API_KEY, credenciais do banco e JWT_SECRET_KEY

# 2. Suba banco + backend + frontend
docker compose up -d --build
```
- Frontend: `http://localhost:5173` (ou `http://<IP_DO_RASPBERRY>:5173` na rede local)
- API / Docs: `http://localhost:8000/docs`

### Modo Dev Híbrido (apenas o banco no Docker)
Se preferir rodar backend (`uvicorn`) e frontend (`npm run dev`) diretamente no terminal sem instalar o `pgvector` no sistema operacional:
```bash
docker compose up -d db
```
No `backend/.env`, utilize `DB_HOST=127.0.0.1` e `DB_SSLMODE=disable`.

---

## 🚀 Deploy no Render

### Backend
1. Crie um **Web Service** apontando para `/backend`
2. Runtime: **Docker**
3. Adicione as variáveis de ambiente (`OPENROUTER_API_KEY`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`)

### Frontend
1. Crie um **Static Site** apontando para `/frontend`
2. Build command: `npm run build`
3. Publish directory: `dist`

---

## 🛠️ Stack

| Camada       | Tecnologia                                                   |
|--------------|--------------------------------------------------------------|
| LLM          | OpenRouter (`nvidia/nemotron-3.5-super-vl:free`)             |
| Embeddings   | OpenRouter (`nvidia/nemotron-3.5-embed-1b:free`)             |
| Vector DB    | PGVector via Supabase                                        |
| Orquestração | LangChain + LangGraph                                        |
| API          | FastAPI + Uvicorn                                            |
| Frontend     | Vue 3 · Tailwind CSS · Vite                                  |
