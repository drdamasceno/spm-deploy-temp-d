"use client";
import { cn } from "@/lib/utils";
import { formatBRL } from "@/lib/format";
import type { OrigemSugestao } from "@/types/v2";

interface RowOrcamentoProps {
  titularRazao: string;
  valor: number;
  natureza: string;
  observacao?: string | null;
  empresaCodigo?: string;
  origem?: OrigemSugestao;
  selecionada: boolean;
  onToggle: () => void;
  concorrente?: { posicao: number; total: number } | null;
}

function corPorOrigem(origem?: OrigemSugestao): string {
  if (origem === "REGRA") return "border-l-emerald-500 bg-emerald-50";
  if (origem === "SIMILARIDADE") return "border-l-yellow-500 bg-yellow-50";
  if (origem === "VALOR") return "border-l-slate-400";
  return "border-l-slate-200";
}

function labelNatureza(n: string): string {
  return (
    {
      DESPESA_FIXA: "Despesa Fixa",
      TRIBUTO: "Tributo",
      SALARIO_VARIAVEL: "Salario Variavel",
      COMISSAO: "Comissao",
      VALOR_VARIAVEL: "Valor Variavel",
      DESPESA_PROFISSIONAIS: "Despesa Profissionais",
    }[n] || n
  );
}

export function RowOrcamento({
  titularRazao,
  valor,
  natureza,
  observacao,
  empresaCodigo,
  origem,
  selecionada,
  onToggle,
  concorrente,
}: RowOrcamentoProps) {
  return (
    <div
      className={cn(
        "flex gap-2 items-start p-2 border border-slate-200 rounded-md mb-1.5 bg-white text-[13px] border-l-[3px]",
        corPorOrigem(origem)
      )}
    >
      <input
        type="checkbox"
        className="mt-1"
        checked={selecionada}
        onChange={onToggle}
      />
      <div className="flex-1 min-w-0">
        <div className="flex gap-1.5 items-center text-[11px] text-slate-600 mb-0.5 flex-wrap">
          {empresaCodigo && (
            <span className="font-medium">{empresaCodigo} ·</span>
          )}
          <span>{labelNatureza(natureza)}</span>
          {concorrente && (
            <span
              className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-200 text-amber-900"
              title="Esta linha de orçamento aparece como sugestão para N transações — só uma pode ser aplicada"
            >
              ⚠ concorrente {concorrente.posicao}/{concorrente.total}
            </span>
          )}
        </div>
        <div className="font-medium text-slate-900 truncate">
          {titularRazao}
        </div>
        {observacao && (
          <div className="text-[11px] text-slate-500 mt-0.5 truncate">
            {observacao}
          </div>
        )}
      </div>
      <div className="text-right font-semibold tabular-nums text-slate-900 whitespace-nowrap">
        {formatBRL(valor)}
      </div>
    </div>
  );
}
