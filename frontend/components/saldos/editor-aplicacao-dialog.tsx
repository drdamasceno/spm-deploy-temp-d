"use client"
import { useState, useEffect } from "react"
import type { AplicacaoOut, AplicacaoCreate, ModoAplicacao, TipoAplicacao, LiquidezAplicacao } from "@/types/v2"
import { criarAplicacao, editarAplicacao } from "@/lib/api/saldos"
import { InputDinheiro } from "@/components/ui/input-dinheiro"
import { toast } from "sonner"

interface Props {
  open: boolean
  aplicacao: AplicacaoOut | null
  onClose: () => void
  onSaved: () => void
}

const TIPOS: TipoAplicacao[] = ["CDB", "LCA", "LCI", "FUNDO", "POUPANCA", "TESOURO", "ACOES", "FII", "OUTROS"]
const TIPOS_LABEL: Record<TipoAplicacao, string> = {
  CDB: "CDB", LCA: "LCA", LCI: "LCI", FUNDO: "Fundo",
  POUPANCA: "Poupança", TESOURO: "Tesouro Direto",
  ACOES: "Ações", FII: "FII", OUTROS: "Outros",
}

const LIQUIDEZ_OPTS: { value: LiquidezAplicacao; label: string }[] = [
  { value: "DIARIA", label: "Diária (D+0/D+1)" },
  { value: "VENCIMENTO", label: "No vencimento" },
  { value: "D30", label: "30 dias" },
  { value: "D90", label: "90 dias" },
  { value: "D180", label: "180 dias" },
]

export function EditorAplicacaoDialog({ open, aplicacao, onClose, onSaved }: Props) {
  const [nome, setNome] = useState("")
  const [tipo, setTipo] = useState<TipoAplicacao>("CDB")
  const [valor, setValor] = useState<number>(0)
  const [modo, setModo] = useState<ModoAplicacao>("MANUAL")
  const [instituicao, setInstituicao] = useState("")
  const [rentabilidade, setRentabilidade] = useState("")
  const [vencimento, setVencimento] = useState("")
  const [liquidez, setLiquidez] = useState<string>("")
  const [obs, setObs] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (aplicacao) {
      setNome(aplicacao.nome)
      setTipo(aplicacao.tipo)
      setValor(aplicacao.valor_atual)
      setModo(aplicacao.modo)
      setInstituicao(aplicacao.instituicao ?? "")
      setRentabilidade(aplicacao.rentabilidade ?? "")
      setVencimento(aplicacao.data_vencimento ?? "")
      setLiquidez(aplicacao.liquidez ?? "")
      setObs(aplicacao.observacoes ?? "")
    } else {
      setNome("")
      setTipo("CDB")
      setValor(0)
      setModo("MANUAL")
      setInstituicao("")
      setRentabilidade("")
      setVencimento("")
      setLiquidez("")
      setObs("")
    }
  }, [aplicacao, open])

  if (!open) return null

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!Number.isFinite(valor) || valor < 0) { toast.error("Valor aplicado inválido"); return }
    if (!nome.trim()) { toast.error("Nome é obrigatório"); return }
    setSaving(true)
    try {
      const payload: AplicacaoCreate = {
        nome: nome.trim(),
        tipo,
        valor_atual: valor,
        modo,
        instituicao: instituicao || null,
        rentabilidade: rentabilidade || null,
        data_vencimento: vencimento || null,
        liquidez: (liquidez as LiquidezAplicacao) || null,
        observacoes: obs || null,
      }
      if (aplicacao) {
        await editarAplicacao(aplicacao.id, payload)
        toast.success("Aplicação atualizada")
      } else {
        await criarAplicacao(payload)
        toast.success("Aplicação criada")
      }
      onSaved()
      onClose()
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <form
        onClick={e => e.stopPropagation()}
        onSubmit={handleSave}
        className="bg-white rounded-lg p-5 w-[540px] max-w-[95vw] max-h-[90vh] overflow-auto space-y-3"
      >
        <h2 className="text-base font-semibold text-slate-900">
          {aplicacao ? "Editar aplicação" : "Nova aplicação"}
        </h2>

        <div>
          <label className="text-xs text-slate-600 block mb-1">Nome *</label>
          <input value={nome} onChange={e => setNome(e.target.value)} placeholder="Ex: CDB Bradesco 120% CDI"
            className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-600 block mb-1">Tipo *</label>
            <select value={tipo} onChange={e => setTipo(e.target.value as TipoAplicacao)}
              className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm">
              {TIPOS.map(t => <option key={t} value={t}>{TIPOS_LABEL[t]}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">Valor aplicado *</label>
            <InputDinheiro value={valor} onChange={setValor} />
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-600 block mb-1">Vinculação à conta corrente *</label>
          <div className="flex gap-2">
            <label className={`flex-1 p-2.5 rounded border-2 cursor-pointer flex items-start gap-2 ${modo === "AUTOMATICA" ? "border-emerald-500 bg-emerald-50" : "border-slate-200 bg-white"}`}>
              <input type="radio" name="modo" checked={modo === "AUTOMATICA"} onChange={() => setModo("AUTOMATICA")} className="mt-0.5" />
              <div>
                <div className="text-xs font-bold text-emerald-900">Automática</div>
                <div className="text-[11px] text-emerald-700 mt-0.5 leading-tight">Aplica e resgata sozinha conforme o saldo. Ex: varredura overnight, CDB liquidez diária</div>
              </div>
            </label>
            <label className={`flex-1 p-2.5 rounded border-2 cursor-pointer flex items-start gap-2 ${modo === "MANUAL" ? "border-purple-400 bg-purple-50" : "border-slate-200 bg-white"}`}>
              <input type="radio" name="modo" checked={modo === "MANUAL"} onChange={() => setModo("MANUAL")} className="mt-0.5" />
              <div>
                <div className="text-xs font-bold text-purple-900">Manual</div>
                <div className="text-[11px] text-purple-700 mt-0.5 leading-tight">Precisa ação pra aplicar/resgatar. Ex: CDB travado, Tesouro, FII, LCI com carência</div>
              </div>
            </label>
          </div>
        </div>

        <hr className="border-slate-200" />
        <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wide">Detalhes (opcional)</div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-600 block mb-1">Instituição</label>
            <input value={instituicao} onChange={e => setInstituicao(e.target.value)} placeholder="Bradesco, BTG, XP…"
              className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">Rentabilidade</label>
            <input value={rentabilidade} onChange={e => setRentabilidade(e.target.value)} placeholder="120% CDI, IPCA+5%…"
              className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-600 block mb-1">Data de vencimento</label>
            <input type="date" value={vencimento} onChange={e => setVencimento(e.target.value)}
              className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">Liquidez</label>
            <select value={liquidez} onChange={e => setLiquidez(e.target.value)}
              className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm">
              <option value="">—</option>
              {LIQUIDEZ_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-600 block mb-1">Observações</label>
          <textarea value={obs} onChange={e => setObs(e.target.value)} rows={2}
            className="w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm" />
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 border border-slate-300 rounded text-sm">Cancelar</button>
          <button type="submit" disabled={saving}
            className="px-3 py-1.5 bg-purple-600 text-white rounded text-sm disabled:opacity-50">
            {saving ? "Salvando…" : "Salvar"}
          </button>
        </div>
      </form>
    </div>
  )
}
