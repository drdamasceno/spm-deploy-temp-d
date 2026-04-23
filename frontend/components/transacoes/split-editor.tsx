"use client"

import { useState, useMemo } from "react"
import { toast } from "sonner"
import { useRouter } from "next/navigation"
import { BolsoSelect } from "@/components/ui/bolso-select"
import { formatBRL } from "@/lib/format"
import { saveSplit, fetchSplitSugerido, deleteSplit } from "@/lib/api/transacoes"
import type { BolsoTipo, SplitResponse, TransacaoLinha } from "@/types/v2"

interface TransacaoInfo {
  id: string
  valor: number
  titular_pix: string | null
  descricao: string | null
  data_extrato: string | null
}

interface LinhaEdit {
  valor: number
  bolso: BolsoTipo
  descricao: string
}

interface Props {
  transacao: TransacaoInfo
  inicial: TransacaoLinha[]
}

const TOL = 0.01

function linhasDefault(valor: number): LinhaEdit[] {
  return [{ valor, bolso: "SPM_OPERACIONAL", descricao: "" }]
}

function fromResposta(linhas: TransacaoLinha[]): LinhaEdit[] {
  return linhas.map((l) => ({
    valor: l.valor,
    bolso: l.bolso,
    descricao: l.descricao ?? "",
  }))
}

export function SplitEditor({ transacao, inicial }: Props) {
  const router = useRouter()
  const [linhas, setLinhas] = useState<LinhaEdit[]>(
    inicial.length > 0 ? fromResposta(inicial) : linhasDefault(transacao.valor)
  )
  const [salvando, setSalvando] = useState(false)

  const somaLinhas = useMemo(() => linhas.reduce((acc, l) => acc + l.valor, 0), [linhas])
  const diferenca = transacao.valor - somaLinhas
  const somaBate = Math.abs(diferenca) <= TOL

  function atualizarLinha(idx: number, patch: Partial<LinhaEdit>) {
    setLinhas((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)))
  }

  function removerLinha(idx: number) {
    setLinhas((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev))
  }

  function adicionarLinha() {
    const resto = Math.max(0, Math.round(diferenca * 100) / 100)
    setLinhas((prev) => [...prev, { valor: resto, bolso: "SPM_OPERACIONAL", descricao: "" }])
  }

  function aplicar5050() {
    const metade = Math.round((transacao.valor / 2) * 100) / 100
    const outra = Math.round((transacao.valor - metade) * 100) / 100
    setLinhas([
      { valor: metade, bolso: "SPM_OPERACIONAL", descricao: "Metade SPM" },
      { valor: outra, bolso: "HUGO_PESSOAL", descricao: "Metade Hugo pessoal" },
    ])
  }

  async function copiarMesAnterior() {
    try {
      const sug = await fetchSplitSugerido(transacao.id)
      if (sug.linhas.length === 0) {
        toast.info("Nenhum split anterior encontrado para esse titular")
        return
      }
      setLinhas(fromResposta(sug.linhas))
      toast.success(`Divisão copiada de split anterior (${sug.linhas.length} linhas, proporcionalizada)`)
    } catch (err) {
      toast.error("Falha ao buscar sugestão: " + (err instanceof Error ? err.message : "erro"))
    }
  }

  async function salvar() {
    if (!somaBate) {
      toast.error("Soma das linhas não bate com o valor da transação")
      return
    }
    setSalvando(true)
    try {
      await saveSplit(transacao.id, {
        linhas: linhas.map((l) => ({
          valor: l.valor,
          bolso: l.bolso,
          descricao: l.descricao || null,
        })),
      })
      toast.success(`Split salvo — ${linhas.length} linhas`)
      router.back()
    } catch (err) {
      toast.error("Falha ao salvar: " + (err instanceof Error ? err.message : "erro"))
    } finally {
      setSalvando(false)
    }
  }

  async function removerSplit() {
    if (!confirm("Remover o split desta transação?")) return
    try {
      await deleteSplit(transacao.id)
      toast.success("Split removido")
      router.back()
    } catch (err) {
      toast.error("Falha ao remover: " + (err instanceof Error ? err.message : "erro"))
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Transação</div>
        <div className="mt-1 text-base font-semibold text-slate-900">
          {transacao.descricao || transacao.titular_pix || "(sem descrição)"}
        </div>
        <div className="mt-1 text-xs text-slate-500">
          {transacao.titular_pix ? `${transacao.titular_pix} · ` : ""}
          {transacao.data_extrato ?? "—"}
        </div>
        <div className="mt-3 text-xl font-bold tabular-nums text-slate-900">
          {formatBRL(transacao.valor)}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={aplicar5050}
          className="px-3 py-1.5 text-xs font-medium bg-blue-50 border border-blue-200 text-blue-800 rounded hover:bg-blue-100"
        >
          Dividir 50/50 SPM / Hugo pessoal
        </button>
        <button
          type="button"
          onClick={copiarMesAnterior}
          className="px-3 py-1.5 text-xs font-medium bg-violet-50 border border-violet-200 text-violet-800 rounded hover:bg-violet-100"
        >
          Copiar divisão do mês anterior
        </button>
        {inicial.length > 0 && (
          <button
            type="button"
            onClick={removerSplit}
            className="ml-auto px-3 py-1.5 text-xs font-medium bg-red-50 border border-red-200 text-red-800 rounded hover:bg-red-100"
          >
            Remover split
          </button>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="text-left px-3 py-2 w-32">Valor (R$)</th>
              <th className="text-left px-3 py-2">Bolso</th>
              <th className="text-left px-3 py-2">Descrição (opcional)</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="px-3 py-2">
                  <input
                    type="number"
                    step="0.01"
                    value={l.valor}
                    onChange={(e) => atualizarLinha(idx, { valor: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2 py-1 text-sm border border-slate-300 rounded tabular-nums"
                  />
                </td>
                <td className="px-3 py-2">
                  <BolsoSelect value={l.bolso} onChange={(b) => atualizarLinha(idx, { bolso: b })} />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="text"
                    value={l.descricao}
                    onChange={(e) => atualizarLinha(idx, { descricao: e.target.value })}
                    placeholder="ex: metade SPM"
                    className="w-full px-2 py-1 text-sm border border-slate-300 rounded"
                  />
                </td>
                <td className="px-3 py-2">
                  {linhas.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removerLinha(idx)}
                      className="text-slate-400 hover:text-red-600"
                      title="Remover linha"
                    >
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="border-t border-slate-100 px-3 py-2 bg-slate-50 flex justify-between items-center">
          <button
            type="button"
            onClick={adicionarLinha}
            className="text-xs text-blue-700 hover:underline"
          >
            + Adicionar linha
          </button>
          <div className="text-xs text-slate-500">
            {linhas.length} {linhas.length === 1 ? "linha" : "linhas"}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-xs text-slate-500">Valor da transação</div>
            <div className="text-base font-semibold tabular-nums">{formatBRL(transacao.valor)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Soma das linhas</div>
            <div className="text-base font-semibold tabular-nums">{formatBRL(somaLinhas)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Diferença</div>
            <div
              className={`text-base font-semibold tabular-nums ${
                somaBate ? "text-green-700" : "text-red-700"
              }`}
            >
              {formatBRL(diferenca)}
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={() => router.back()}
          className="px-4 py-2 text-sm border border-slate-300 rounded hover:bg-slate-50"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={salvar}
          disabled={!somaBate || salvando}
          className="px-4 py-2 text-sm bg-blue-700 text-white rounded hover:bg-blue-800 disabled:bg-slate-300 disabled:cursor-not-allowed"
        >
          {salvando ? "Salvando…" : "Salvar split"}
        </button>
      </div>
    </div>
  )
}
