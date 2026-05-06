// Redirect server-side de /orcamento → /despesas-fixas
//
// A aba foi renomeada na re-arquitetura de 2026-05-06 (escopo: extrair
// FATURAMENTO e DESPESA_PROFISSIONAIS pra abas próprias e renomear o que
// sobrou pra "Despesas Fixas"). Mantemos esta page como redirect server-side
// para não quebrar bookmarks, links históricos e o cache de CDN durante a
// transição.
//
// Quando todos os clientes tiverem migrado e os logs do Render confirmarem
// zero hits em /orcamento, esta page pode ser removida.
import { redirect } from "next/navigation";

export default function OrcamentoLegacyRedirect() {
  redirect("/despesas-fixas");
}
