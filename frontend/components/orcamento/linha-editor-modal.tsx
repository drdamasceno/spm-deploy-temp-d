"use client"
import { useEffect, useState } from "react"
import type {
  OrcamentoLinhaOut,
  CategoriaOut,
  BolsoTipo,
} from "@/types/v2"
import { patchLinha, deletarOrcamentoLinha } from "@/lib/api/orcamento"
import { BolsoSelect } from "@/components/ui/bolso-select"
import { EmpresaPagadoraSelect } from "@/components/ui/empresa-pagadora-select"
import { toast } from "sonner"

interface Props {
  linha: OrcamentoLinhaOut | null
  categoriaPorId?: Record<string, CategoriaOut>
  onClose: (linhaAtualizada?: OrcamentoLinhaOut) => void
  onDelete?: (linhaId: string) => void
}

export function LinhaEditorModal({
  linha,
  categoriaPorId,
  onClose,
  onDelete,
}: Props) {
  const [valor, setValor] = useState("")
  const [data, setData] = useState("")
  const [bolso, setBolso] = useState<BolsoTipo>("SPM_OPERACIONAL")
  const [empresaPagadoraId, setEmpresaPagadoraId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!linha) return
    setValor(String(linha.valor_previsto))
    setData(linha.data_previsao ?? "")
    setBolso(linha.bolso ?? "SPM_OPERACIONAL")
    setEmpresaPagadoraId(linha.empresa_pagadora_id ?? null)
  }, [linha])

  useEffect(() => {
    if (!linha) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [linha, onClose])

  if (!linha) return null

  const categoriaNome = linha.categoria_id
    ? categoriaPorId?.[linha.categoria_id]?.nome ?? linha.categoria_id
    : "—"

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!linha) return
    const valorNum = parseFloat(valor.replace(",", "."))
    if (!Number.isFinite(valorNum) || valorNum <= 0) {
      toast.error("Valor previsto deve ser maior que zero")
      return
    }
    setSubmitting(true)
    try {
      const nova = await patchLinha(linha.id, {
        valor_previsto: valorNum,
        data_previsao: data || null,
        bolso,
        empresa_pagadora_id: empresaPagadoraId,
      })
      toast.success("Linha atualizada")
      onClose(nova)
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!linha) return
    if (!confirm(`Deletar a linha "${linha.titular_razao_social}"?`)) return
    setSubmitting(true)
    try {
      await deletarOrcamentoLinha(linha.id)
      toast.success("Linha deletada")
      onDelete?.(linha.id)
      onClose()
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      onClick={() => onClose()}
    >
      <form
        className="bg-white rounded-lg shadow-lg p-6 w-full max-w-md mx-auto space-y-4"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSave}
      >
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Editar linha do orçamento
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Ajuste valor, bolso e empresa pagadora
          </p>
        </div>

        <div className="space-y-2 text-xs">
          <div>
            <span className="text-slate-500">Titular: </span>
            <span className="text-slate-900 font-medium">
              {linha.titular_razao_social}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Categoria: </span>
            <span className="text-slate-700">{categoriaNome}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-600 block mb-1">
              Valor previsto (R$)
            </label>
            <input
              type="number"
              step="0.01"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
              required
              min={0.01}
            />
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">
              Data prevista
            </label>
            <input
              type="date"
              value={data}
              onChange={(e) => setData(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
            />
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-600 block mb-1">Bolso</label>
          <BolsoSelect value={bolso} onChange={setBolso} disabled={submitting} />
        </div>

        <div>
          <label className="text-xs text-slate-600 block mb-1">
            Empresa pagadora
          </label>
          <EmpresaPagadoraSelect
            value={empresaPagadoraId}
            onChange={setEmpresaPagadoraId}
            disabled={submitting}
          />
        </div>

        <div className="flex gap-2 justify-between pt-2">
          {onDelete && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={submitting}
              className="text-xs px-3 py-1 rounded border border-red-300 text-red-700 hover:bg-red-50 disabled:opacity-50"
            >
              Deletar
            </button>
          )}
          <div className="flex gap-2 ml-auto">
            <button
              type="button"
              onClick={() => onClose()}
              disabled={submitting}
              className="px-3 py-1 text-sm rounded border border-slate-300 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-3 py-1 text-sm rounded bg-slate-900 text-white disabled:opacity-50"
            >
              {submitting ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
