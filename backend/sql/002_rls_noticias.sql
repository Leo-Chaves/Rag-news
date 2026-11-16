-- ============================================================================
-- RAG News — Fecha as tabelas de notícias para a API pública do Supabase.
-- Rode no Supabase: Dashboard > SQL Editor > New query > Run.
-- Pré-requisito: já ter rodado o /ingest ao menos uma vez (é ele que cria as
-- tabelas do LangChain). É idempotente.
-- ============================================================================
--
-- Problema: tabelas em "public" ficam expostas pela API REST do Supabase
-- (PostgREST) para a chave anon/publishable, que é pública (fica no frontend).
-- Sem RLS, qualquer pessoa com essa chave lê, insere, altera e apaga notícias,
-- podendo envenenar o RAG (notícias falsas ou prompt injection citadas como
-- fonte da BBC) ou apagar a base.
--
-- Correção: RLS ligado e NENHUMA política => a API pública não acessa nada.
-- O backend conecta como "postgres" (dono das tabelas, BYPASSRLS), então a
-- ingestão e a busca continuam funcionando normalmente.
-- Além disso, tira os privilégios diretos de anon/authenticated (defesa em
-- profundidade: protege mesmo se alguém desligar o RLS por engano).

do $$
declare
    t text;
begin
    foreach t in array array['langchain_pg_collection', 'langchain_pg_embedding'] loop
        if to_regclass('public.' || t) is null then
            raise notice 'Tabela public.% ainda não existe (rode o /ingest antes). Pulando.', t;
            continue;
        end if;
        execute format('alter table public.%I enable row level security', t);
        execute format('revoke all on table public.%I from anon, authenticated', t);
        raise notice 'public.%: RLS ligado e acesso público revogado.', t;
    end loop;
end
$$;

-- user_preferences: o frontend nunca acessa esta tabela direto (só via backend,
-- que valida o token e usa o role "postgres"). O Supabase concede por padrão
-- TODOS os privilégios a anon/authenticated, inclusive TRUNCATE, que o RLS não
-- cobre. Revogar deixa só o backend com acesso. As políticas RLS do 001
-- continuam como segunda barreira, caso alguém volte a conceder acesso.
revoke all on table public.user_preferences from anon, authenticated;
