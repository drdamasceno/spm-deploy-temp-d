"use client"
import { useState } from "react"
import type { ContratoDadosExtras } from "@/types/v2"
import { editarDadosContrato } from "@/lib/api/contratos-competencia"
import { toast } from "sonner"

interface Props {
  contratoId: string
  inicial: ContratoDadosExtras
  onSaved: (novos: ContratoDadosExtras) => void
}

export function EditorDadosContrato({ contratoId, inicial, onSaved }: Props) {
  const [nomeOficial, setNomeOficial] = useState(inicial.nome_oficial ?? "")
  const [cnpj, setCnpj] = useState(inicial.cnpj ?? "")
  const [tipo, setTipo] = useState(inicial.tipo ?? "PUBLICO")
  const [valorFat, setValorFat] = useState(inicial.valor_faturamento_mensal?.toString() ?? "")
  const [retencao, setRetencao] = useState(inicial.retencao_tributaria_pct?.toString() ?? "")
  const [obs, setObs] = useState(inicial.observacoes ?? "")
  const [saving, setSaving] = useState(false)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const patch: ContratoDadosExtras = {
        nome_oficial: nomeOficial || null,
        cnpj: cnpj || null,
        tipo: (tipo as "PUBLICO" | "PRIVADO") || null,
        valor_faturamento_mensal: valorFat ? parseFloat(valorFat.replace(",", ".")) : null,
        retencao_tributaria_pct: retencao ? parseFloat(retencao.replace(",", ".")) : null,
        observacoes: obs || null,
      }
      const saved = await editarDadosContrato(contratoId, patch)
      toast.success("Dados salvos")
      onSaved(saved)
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave} className="space-y-3 max-w-2xl">
      <div>
        <label className="text-xs text-slate-600 block mb-1">Nome oficial</label>
        <input value={nomeOficial} onChange={e => setNomeOficial(e.target.value)} placeholder="Prefeitura Municipal de…" className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-slate-600 block mb-1">CNPJ</label>
          <input value={cnpj} onChange={e => setCnpj(e.target.value)} placeholder="00.000.000/0000-00" className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">Tipo</label>
          <select value={tipo ?? "PUBLICO"} onChange={e => setTipo(e.target.value as "PUBLICO" | "PRIVADO")} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm">
            <option value="PUBLICO">Público</option>
            <option value="PRIVADO">Privado</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-xs text-slate-600 block mb-1">Valor faturamento mensal (R$)</label>
          <input type="number" step="0.01" value={valorFat} onChange={e => setValorFat(e.target.value)} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">Retenção tributária (%)</label>
          <input type="number" step="0.01" value={retencao} onChange={e => setRetencao(e.target.value)} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>
      </div>
      <div>
        <label className="text-xs text-slate-600 block mb-1">Observações</label>
        <textarea value={obs} onChange={e => setObs(e.target.value)} rows={3} className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
      </div>
      <div className="flex justify-end">
        <button type="submit" disabled={saving} className="px-3.5 py-1.5 bg-slate-900 text-white rounded text-sm disabled:opacity-50">
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </div>
    </form>
  )
}
