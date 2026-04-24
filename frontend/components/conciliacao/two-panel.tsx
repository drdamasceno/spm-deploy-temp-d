"use client";
import { useMemo } from "react";
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

interface GrupoConcorrente {
  orcamentoLinhaId: string;
  sugestoes: Array<{ sug: SugestaoOut; idxOriginal: number }>;
}

/**
 * Agrupa sugestões por orcamento_linha_id.
 *
 * Duas sugestões diferentes (transações distintas) que apontam para A MESMA
 * linha de orçamento são "concorrentes": apenas uma pode ganhar. O pool backend
 * gera ambas porque ambas fazem match (ex: REGRA ou VALOR coincidente), e cabe
 * ao usuário escolher.
 *
 * Agrupamos mantendo a ordem natural (primeira ocorrência define a posição
 * do grupo) e dentro do grupo, ordenamos por confiança desc.
 */
function agruparConcorrentes(sugestoes: SugestaoOut[]): GrupoConcorrente[] {
  const map = new Map<string, GrupoConcorrente>();
  sugestoes.forEach((sug, idxOriginal) => {
    const key = sug.orcamento_linha_id;
    if (!map.has(key)) {
      map.set(key, { orcamentoLinhaId: key, sugestoes: [] });
    }
    map.get(key)!.sugestoes.push({ sug, idxOriginal });
  });
  // dentro de cada grupo, ordena por confiança desc (o melhor match em cima)
  for (const grupo of map.values()) {
    grupo.sugestoes.sort(
      (a, b) => (b.sug.confianca ?? 0) - (a.sug.confianca ?? 0)
    );
  }
  return Array.from(map.values());
}

export function TwoPanel({
  sugestoes,
  txDetalhes,
  linhaDetalhes,
  selecionadas,
  onToggle,
  empresaCodigo,
}: TwoPanelProps) {
  const grupos = useMemo(() => agruparConcorrentes(sugestoes), [sugestoes]);

  if (!sugestoes.length) {
    return (
      <div className="p-8 text-center text-slate-500 text-sm bg-white border border-slate-200 rounded-lg">
        Nenhuma sugestao pendente — tudo conciliado nesta competencia.
      </div>
    );
  }

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
        {grupos.map((grupo) => {
          const concorrente = grupo.sugestoes.length > 1;
          return (
            <div
              key={`g-tx-${grupo.orcamentoLinhaId}`}
              className={
                concorrente
                  ? "relative mb-3 pl-2 border-l-2 border-amber-400 bg-amber-50/40 rounded-r"
                  : "mb-0"
              }
            >
              {concorrente && (
                <div className="text-[10px] font-bold uppercase text-amber-700 px-1 py-0.5">
                  ⚠ {grupo.sugestoes.length} concorrentes para a mesma linha — só 1 ganha
                </div>
              )}
              {grupo.sugestoes.map(({ sug, idxOriginal }, posNoGrupo) => {
                const tx = txDetalhes.get(sug.transacao_id);
                const linha = linhaDetalhes.get(sug.orcamento_linha_id);
                return (
                  <RowTransacao
                    key={`tx-${idxOriginal}-${sug.transacao_id}`}
                    titular={tx?.titular_pix ?? sug.transacao_id.slice(0, 8)}
                    valor={tx?.valor ?? sug.valor_aplicado}
                    data={tx?.data_extrato ?? ""}
                    origemBanco={tx?.origem_banco ?? ""}
                    origem={sug.origem}
                    confianca={sug.confianca}
                    linhaAlvo={linha?.titular_razao_social ?? null}
                    selecionada={selecionadas.has(idxOriginal)}
                    onToggle={() => onToggle(idxOriginal)}
                    concorrente={
                      concorrente
                        ? {
                            posicao: posNoGrupo + 1,
                            total: grupo.sugestoes.length,
                          }
                        : null
                    }
                  />
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Orcamento */}
      <div className="bg-white p-4 overflow-y-auto max-h-[70vh]">
        <div className="flex justify-between text-xs font-semibold uppercase text-slate-600 tracking-wide mb-3">
          <span>Linhas de orcamento sugeridas</span>
          <span className="text-slate-400">
            {sugestoes.length} sugestoes ·{" "}
            {new Intl.NumberFormat("pt-BR", {
              style: "currency",
              currency: "BRL",
              maximumFractionDigits: 0,
            }).format(totalOrcamento)}
          </span>
        </div>
        {grupos.map((grupo) => {
          const concorrente = grupo.sugestoes.length > 1;
          return (
            <div
              key={`g-orc-${grupo.orcamentoLinhaId}`}
              className={
                concorrente
                  ? "relative mb-3 pl-2 border-l-2 border-amber-400 bg-amber-50/40 rounded-r"
                  : "mb-0"
              }
            >
              {concorrente && (
                <div className="text-[10px] font-bold uppercase text-amber-700 px-1 py-0.5">
                  ⚠ mesma linha sugerida {grupo.sugestoes.length}×
                </div>
              )}
              {grupo.sugestoes.map(({ sug, idxOriginal }, posNoGrupo) => {
                const linha = linhaDetalhes.get(sug.orcamento_linha_id);
                return (
                  <RowOrcamento
                    key={`linha-${idxOriginal}-${sug.orcamento_linha_id}`}
                    titularRazao={
                      linha?.titular_razao_social ??
                      sug.orcamento_linha_id.slice(0, 8)
                    }
                    valor={sug.valor_aplicado}
                    natureza={linha?.natureza ?? ""}
                    observacao={linha?.observacao}
                    empresaCodigo={empresaCodigo}
                    origem={sug.origem}
                    selecionada={selecionadas.has(idxOriginal)}
                    onToggle={() => onToggle(idxOriginal)}
                    concorrente={
                      concorrente
                        ? {
                            posicao: posNoGrupo + 1,
                            total: grupo.sugestoes.length,
                          }
                        : null
                    }
                  />
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
