-- 0007_empresa_projeto_categoria.sql
-- Tabelas-catálogo do sistema v2: empresa, projeto, categoria_despesa
-- Base para orcamento (0008) e conciliacao (0009)

-- ============================================================
-- Tabela: empresa
-- ============================================================
CREATE TABLE empresa (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE,
  razao_social text NOT NULL,
  cnpj text,
  ativa boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_empresa_codigo ON empresa(codigo);

-- ============================================================
-- Tabela: categoria_despesa
-- ============================================================
CREATE TABLE categoria_despesa (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome text NOT NULL UNIQUE,
  descricao text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_categoria_nome ON categoria_despesa(lower(nome));

-- ============================================================
-- Tabela: projeto
-- ============================================================
CREATE TABLE projeto (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo text NOT NULL UNIQUE,
  descricao text,
  empresa_id uuid NOT NULL REFERENCES empresa(id),
  ativo boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_projeto_empresa ON projeto(empresa_id);
CREATE INDEX idx_projeto_codigo ON projeto(codigo);

-- ============================================================
-- RLS
-- ============================================================
ALTER TABLE empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE categoria_despesa ENABLE ROW LEVEL SECURITY;
ALTER TABLE projeto ENABLE ROW LEVEL SECURITY;

CREATE POLICY empresa_select ON empresa FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY empresa_insert ON empresa FOR INSERT WITH CHECK (fn_is_ceo());
CREATE POLICY empresa_update ON empresa FOR UPDATE USING (fn_is_ceo());
CREATE POLICY empresa_delete ON empresa FOR DELETE USING (fn_is_ceo());

CREATE POLICY categoria_select ON categoria_despesa FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY categoria_insert ON categoria_despesa FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY categoria_update ON categoria_despesa FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY categoria_delete ON categoria_despesa FOR DELETE USING (fn_is_ceo());

CREATE POLICY projeto_select ON projeto FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY projeto_insert ON projeto FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY projeto_update ON projeto FOR UPDATE USING (auth.uid() IS NOT NULL);
CREATE POLICY projeto_delete ON projeto FOR DELETE USING (fn_is_ceo());

-- ============================================================
-- Triggers de log_auditoria (reaproveita fn_log_auditoria da 0001)
-- ============================================================
CREATE TRIGGER trg_audit_empresa AFTER INSERT OR UPDATE OR DELETE ON empresa
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_categoria AFTER INSERT OR UPDATE OR DELETE ON categoria_despesa
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();
CREATE TRIGGER trg_audit_projeto AFTER INSERT OR UPDATE OR DELETE ON projeto
  FOR EACH ROW EXECUTE FUNCTION fn_log_auditoria();

-- ============================================================
-- Trigger de updated_at em empresa
-- ============================================================
CREATE TRIGGER trg_updated_at_empresa BEFORE UPDATE ON empresa
  FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- ============================================================
-- Grants
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON empresa, categoria_despesa, projeto TO authenticated;
