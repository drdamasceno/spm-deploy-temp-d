"use client";
import { cn } from "@/lib/utils";
import { formatBRL, formatDate } from "@/lib/format";
import type { OrigemSugestao } from "@/types/v2";

interface RowTransacaoProps {
  titular: string | null;
  valor: number;
  data: string;
  origemBanco: string;
  origem?: OrigemSugestao;
  confianca?: number;
  linhaAlvo?: string | null;
  selecionada: boolean;
  onToggle: () => void;
}

function corPorOrigem(origem?: OrigemSugestao): string {
  if (origem === "REGRA") return "border-l-emerald-500 bg-emerald-50";
  if (origem === "SIMILARIDADE") return "border-l-yellow-500 bg-yellow-50";
  if (origem === "VALOR") return "border-l-slate-400";
  return "border-l-slate-200";
}

function tagConfianca(origem?: OrigemSugestao, confianca?: number) {
  if (!origem || confianca === undefined) return null;
  const pct = Math.round(confianca * 100);
  const cls =
    origem === "REGRA"
      ? "bg-emerald-600 text-white"
      : origem === "SIMILARIDADE"
      ? "bg-yellow-500 text-white"
      : "bg-slate-400 text-white";
  return (
    <span
      className={cn(
        "text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded tracking-wide",
        cls
      )}
    >
      SUG {pct}%
    </span>
  );
}

function tagBanco(origemBanco: string) {
  const banco = (origemBanco || "").toUpperCase();
  const cls =
    banco === "BRADESCO"
      ? "bg-red-100 text-red-800"
      : banco === "UNICRED"
      ? "bg-blue-100 text-blue-800"
      : "bg-slate-100 text-slate-700";
  return (
    <span
      className={cn(
        "text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded tracking-wide",
        cls
      )}
    >
      {banco || "?"}
    </span>
  );
}

export function RowTransacao({
  titular,
  valor,
  data,
  origemBanco,
  origem,
  confianca,
  linhaAlvo,
  selecionada,
  onToggle,
}: RowTransacaoProps) {
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
          {tagBanco(origemBanco)}
          <span>{formatDate(data)}</span>
          {tagConfianca(origem, confianca)}
        </div>
        <div className="font-medium text-slate-900 truncate">
          {titular || <span className="italic text-slate-400">(sem titular)</span>}
          {linhaAlvo && (
            <>
              <span className="text-emerald-600 font-semibold mx-1.5">→</span>
              <span className="text-slate-700">{linhaAlvo}</span>
            </>
          )}
        </div>
        {origem && (
          <div className="text-[11px] text-slate-500 mt-0.5">
            {origem === "REGRA"
              ? "regra salva"
              : origem === "SIMILARIDADE"
              ? "nome+valor parciais — revisar"
              : origem === "VALOR"
              ? "match apenas por valor"
              : "sem sugestao"}
          </div>
        )}
      </div>
      <div className="text-right font-semibold tabular-nums text-red-600 whitespace-nowrap">
        {formatBRL(valor < 0 ? valor : -Math.abs(valor))}
      </div>
    </div>
  );
}
