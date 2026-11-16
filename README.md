# 📰 RAG News — Chat com Notícias

🔗 **Acesse o projeto online:** [https://ragnewsbbc.netlify.app/](https://ragnewsbbc.netlify.app/)

Projeto de faculdade: sistema de **Retrieval-Augmented Generation (RAG)** para responder perguntas sobre notícias atuais, usando **LangChain**, **Groq** e **PGVector (Supabase)**.

---

## 🗂️ Estrutura do Monorepo

```
faculdade-rag-news/
├── backend/          # FastAPI + LangChain + Groq
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/         # Vue 3 + Tailwind CSS
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
- Conta no [Groq](https://console.groq.com) (chave grátis)
- Projeto no [Supabase](https://supabase.com) com extensão **pgvector** habilitada

### 2. Configurar variáveis de ambiente
```bash
cd backend
cp .env.example .env
# Edite o .env com suas chaves
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

| Método | Rota              | Login       | Descrição                                                   |
|--------|-------------------|-------------|-------------------------------------------------------------|
| GET    | `/`               | —           | Health check                                                |
| POST   | `/ingest`         | —           | Lê os feeds da BBC (fixos em `topics.py`) e salva no PGVector |
| POST   | `/chat`           | opcional    | Pergunta → resposta via LangGraph + Groq                    |
| GET    | `/topics`         | —           | Lista os temas que o usuário pode escolher                  |
| GET    | `/me/preferences` | obrigatório | Temas preferidos do usuário logado                          |
| PUT    | `/me/preferences` | obrigatório | Salva os temas preferidos                                   |

#### Exemplo — `/chat`
```json
POST /chat
Authorization: Bearer <token do Supabase>   (opcional)
{ "question": "what happened in football today?" }

→ { "answer": "...", "sources": ["https://www.bbc.com/..."], "personalizado": true }
```

#### Exemplo — `/me/preferences`
```json
PUT /me/preferences
Authorization: Bearer <token do Supabase>
{ "topics": ["esportes", "politica"] }
```

---

## 👤 Login e temas de interesse

O usuário pode criar uma conta, entrar e escolher **temas de interesse**
(ex.: *Esportes* inteiro ou só *Futebol*, *Política*, *Tecnologia*...).
Logado, as respostas do chat **priorizam** notícias desses temas; perguntas
sobre outros assuntos continuam funcionando. Sem login, tudo funciona como antes.

### Como funciona

- **Autenticação:** Supabase Auth (o mesmo projeto Supabase do banco). O login
  acontece no frontend com `supabase-js`; o backend só valida o token recebido
  em `Authorization: Bearer` (`backend/auth.py`), via JWKS do projeto
  (chaves assimétricas) ou, em projetos com o segredo HS256 legado, consultando
  o próprio Supabase Auth.
- **Temas:** definidos em `backend/topics.py`. Cada feed RSS tem um tema, e cada
  notícia é gravada no PGVector com `category` na metadata. Temas são
  hierárquicos: escolher *Esportes* inclui *Futebol*, *Tênis*, *Fórmula 1* e *Basquete*.
- **Preferências:** tabela `public.user_preferences` (uma linha por usuário, com RLS).
- **Personalização no grafo LangGraph:**

  ```
  START → traduzir → recuperar → (evidência?) ─sim→ personalizar → montar_contexto → gerar_resposta → END
                                              └não→ sem_evidencia → END
  ```

  `traduzir` reescreve a pergunta em inglês (modelo `TRANSLATE_MODEL`, padrão
  `openai/gpt-oss-20b`) só para a busca: o modelo de embeddings e as notícias
  da BBC são em inglês, e perguntas em português traziam notícias de outros
  temas. A resposta continua usando a pergunta original, em PT-BR. Se a
  tradução falhar, a busca usa a pergunta original.

  Com usuário logado, `recuperar` busca 3× mais candidatos e `personalizar`
  soma `PREFERENCE_BOOST` (padrão 0.1) ao score das notícias dos temas
  preferidos antes de escolher os 5 melhores. A decisão de evidência usa o
  score **sem** bônus, então a preferência nunca faz uma pergunta sem resposta
  "passar".

### Configuração (uma vez)

1. **Banco:** no Supabase, abra *SQL Editor* e rode `backend/sql/001_user_preferences.sql`.
   Ele cria a tabela de preferências e categoriza as notícias antigas que já estavam
   no banco (as de esporte pela URL; as demais viram "geral"). Para categorizar tudo
   corretamente, apague a collection (comando no próprio arquivo) e clique em
   **Atualizar Notícias**.
   Depois do primeiro **Atualizar Notícias**, rode também `backend/sql/002_rls_noticias.sql`.
   Sem ele, as tabelas de notícias ficam abertas para leitura **e escrita** pela API
   pública do Supabase (a chave anon/publishable fica no frontend).
2. **Supabase Auth → URL Configuration:** *Site URL* = URL de produção
   (`https://ragnewsbbc.netlify.app`) e, em *Redirect URLs*, adicione também
   `http://localhost:5173`. Isso é usado nos links de confirmação de e-mail e de
   recuperação de senha.
3. **Supabase Auth → Providers:** *Email* já vem ligado. *Confirm email* ligado
   exige confirmar o e-mail antes de entrar (o frontend já trata os dois casos).
   Google é opcional (precisa de credenciais OAuth do Google Cloud).
4. **Backend (Render / `.env`):** `SUPABASE_URL` e, só para projetos com segredo
   legado, `SUPABASE_ANON_KEY`. Veja `backend/.env.example`.
5. **Frontend (Netlify / `.env.local`):** `VITE_SUPABASE_URL` e
   `VITE_SUPABASE_ANON_KEY` (chave **pública**). Veja `frontend/.env.example`.

---

## 🎨 Frontend — Setup

```bash
cd frontend
npm install
npm run dev
# Acesse: http://localhost:5173
```

> O Vite está configurado com proxy: chamadas para `/chat`, `/ingest`, `/topics`
> e `/me` são redirecionadas automaticamente para `http://localhost:8000`.

---

## 🚀 Deploy no Render

### Backend
1. Crie um **Web Service** apontando para `/backend`
2. Runtime: **Docker**
3. Adicione as variáveis de ambiente (`GROQ_API_KEY`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `SUPABASE_URL`)

### Frontend
1. Crie um **Static Site** apontando para `/frontend`
2. Build command: `npm run build`
3. Publish directory: `dist`
4. Defina a variável `VITE_API_URL` se necessário

---

## 🛠️ Stack

| Camada     | Tecnologia                          |
|------------|-------------------------------------|
| LLM        | Groq — `qwen/qwen3.8-27b`           |
| Embeddings | HuggingFace `all-MiniLM-L6-v2`      |
| Vector DB  | PGVector via Supabase               |
| Orquestração | LangGraph (grafo RAG condicional) |
| Autenticação | Supabase Auth (JWT)               |
| API        | FastAPI + Uvicorn                   |
| Frontend   | Vue 3 · Tailwind CSS · Vite         |
