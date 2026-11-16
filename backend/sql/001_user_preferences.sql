-- ============================================================================
-- RAG News — Login/Perfil: preferências de tema por usuário
-- Rode UMA vez no Supabase: Dashboard > SQL Editor > New query > Run.
-- ============================================================================

-- Preferências do usuário. Os usuários em si ficam em auth.users (Supabase Auth).
create table if not exists public.user_preferences (
    user_id    uuid primary key references auth.users (id) on delete cascade,
    topics     text[] not null default '{}',
    updated_at timestamptz not null default now()
);

-- O backend acessa com o usuário "postgres" (ignora RLS). Ainda assim ativamos
-- RLS para que a API pública do Supabase (chave anon/publishable, que fica no
-- frontend) não permita ler/alterar preferências de outras pessoas.
alter table public.user_preferences enable row level security;

drop policy if exists "dono le suas preferencias" on public.user_preferences;
create policy "dono le suas preferencias"
    on public.user_preferences for select
    using ((select auth.uid()) = user_id);

drop policy if exists "dono altera suas preferencias" on public.user_preferences;
create policy "dono altera suas preferencias"
    on public.user_preferences for all
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);


-- ============================================================================
-- (Opcional) Categorizar notícias que já estavam no banco antes desta mudança.
-- Links de esporte da BBC trazem a modalidade na URL; links de news atuais são
-- "/news/articles/<id>" e não indicam a seção, então viram "geral".
-- A alternativa mais limpa é apagar a collection e clicar em "Atualizar Notícias":
--   delete from langchain_pg_embedding e using langchain_pg_collection c
--   where e.collection_id = c.uuid and c.name = 'rag_news';
-- Num banco novo as tabelas do LangChain ainda não existem (são criadas no
-- primeiro /ingest); nesse caso o bloco abaixo só avisa e não faz nada, em vez
-- de quebrar o script inteiro (o SQL Editor roda tudo numa transação).
-- ============================================================================
do $$
begin
    if to_regclass('public.langchain_pg_embedding') is null then
        raise notice 'Tabelas do LangChain ainda não existem: nada para categorizar.';
        return;
    end if;
    update langchain_pg_embedding e
    set cmetadata = e.cmetadata || jsonb_build_object('category',
        case
            when e.cmetadata->>'source' like '%/sport/football/%'   then 'futebol'
            when e.cmetadata->>'source' like '%/sport/tennis/%'     then 'tenis'
            when e.cmetadata->>'source' like '%/sport/formula1/%'   then 'formula1'
            when e.cmetadata->>'source' like '%/sport/basketball/%' then 'basquete'
            when e.cmetadata->>'source' like '%/sport/%'            then 'esportes'
            else 'geral'
        end)
    from langchain_pg_collection c
    where e.collection_id = c.uuid
      and c.name = 'rag_news'
      and e.cmetadata->>'category' is null;
end
$$;
