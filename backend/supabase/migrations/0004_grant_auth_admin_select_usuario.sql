-- Passo 3 Bloco A: GRANT SELECT em public.usuario para o role supabase_auth_admin
-- Motivo: o GoTrue consulta public.usuario durante sign-in para popular claims.
-- Sem este GRANT, sign_in_with_password retorna 500 "Database error querying schema".
-- Aplicado em producao em 2026-04-19 apos diagnostico do Bloco A.

GRANT USAGE ON SCHEMA public TO supabase_auth_admin;  -- idempotente
GRANT SELECT ON public.usuario TO supabase_auth_admin;
