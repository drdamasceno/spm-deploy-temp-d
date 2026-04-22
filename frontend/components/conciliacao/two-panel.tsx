"use client";
import type { SugestaoOut } from "@/types/v2";
import { RowTransacao } from "./row-transacao";
import { RowOrcamento } from "./row-orcamento";
import type {
  TransacaoDetalhe,
  OrcamentoLinhaDetalhe,
} from "@/lib/api/conciliacao";

interface TwoPanelProps {
  sugestoes: SugestaoOut[];
  txDetalhes: Map<string, TransacaoDetalhe>;
  linhaDetalhes: Map<string, OrcamentoLinhaDetalhe>;
  selecionadas: Set<number>;
  onToggle: (idx: number) => void;
  empresaCodigo?: string;
}

export function TwoPanel({
  sugestoes,
  txDetalhes,
  linhaDetalhes,
  selecionadas,
  onToggle,
  empresaCodigo,
}: TwoPanelProps) {
  if (!sugestoes.length) {
    return (
      <div className="p-8 text-center text-slate-500 text-sm bg-white border border-slate-200 rounded-lg">
        Nenhuma sugestao pendente — tudo conciliado nesta competencia.
      </div>
    );
  }

  // Total de linhas de orcamento (para rodape)
  const totalOrcamento = sugestoes.reduce(
    (sum, s) => sum + (linhaDetalhes.get(s.orcamento_linha_id)?.valor_previsto ?? 0),
    0
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-slate-200 border border-slate-200 rounded-lg overflow-hidden min-h-[380px]">
      {/* Transacoes */}
      <div className="bg-white p-4 overflow-y-auto max-h-[70vh]">
        <div className="flex justify-between text-xs font-semibold uppercase text-slate-600 tracking-wide mb-3">
          <span>Transacoes nao conciliadas</span>
          <span className="text-slate-400">{sugestoes.length} sugestoes</span>
        </div>
        {sugestoes.map((s, idx) => {
          const tx = txDetalhes.get(s.transacao_id);
          const linha = linhaDetalhes.get(s.orcamento_linha_id);
          return (
            <RowTransacao
              key={`tx-${idx}-${s.transacao_id}`}
              titular={tx?.titular_pix ?? s.transacao_id.slice(0, 8)}
              valor={tx?.valor ?? s.valor_aplicado}
              data={tx?.data_extrato ?? ""}
              origemBanco={tx?.origem_banco ?? ""}
              origem={s.origem}
              confianca={s.confianca}
              linhaAlvo={linha?.titular_razao_social ?? null}
              selecionada={selecionadas.has(idx)}
              onToggle={() => onToggle(idx)}
            />
          );
        })}
      </div>

      {/* Orcamento */}
      <div className="bg-white p-4 overflow-y-auto max-h-[70vh]">
        <div className="flex justify-between text-xs font-semibold uppercase text-slate-600 tracking-wide mb-3">
          <span>Linhas de orcamento sugeridas</span>
          <span className="text-slate-400">
            {sugestoes.length} linhas ·{" "}
            {new Intl.NumberFormat("pt-BR", {
              style: "currency",
              currency: "BRL",
              maximumFractionDigits: 0,
            }).format(totalOrcamento)}
          </span>
        </div>
        {sugestoes.map((s, idx) => {
          const linha = linhaDetalhes.get(s.orcamento_linha_id);
          return (
            <RowOrcamento
              key={`linha-${idx}-${s.orcamento_linha_id}`}
              titularRazao={
                linha?.titular_razao_social ?? s.orcamento_linha_id.slice(0, 8)
              }
              valor={s.valor_aplicado}
              natureza={linha?.natureza ?? ""}
              observacao={linha?.observacao}
              empresaCodigo={empresaCodigo}
              origem={s.origem}
              selecionada={selecionadas.has(idx)}
              onToggle={() => onToggle(idx)}
            />
          );
        })}
      </div>
    </div>
  );
}
