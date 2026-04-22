"use client"
import { useState } from "react"
import type { AplicacaoOut } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import { deletarAplicacao } from "@/lib/api/saldos"
import { EditorAplicacaoDialog } from "./editor-aplicacao-dialog"
import { toast } from "sonner"

interface Props {
  aplicacoes: AplicacaoOut[]
  onChanged: () => void
}

const TIPO_LABEL: Record<string, string> = {
  CDB: "CDB", LCA: "LCA", LCI: "LCI", FUNDO: "FUNDO",
  POUPANCA: "POUPANÇA", TESOURO: "TESOURO",
  ACOES: "AÇÕES", FII: "FII", OUTROS: "OUTROS",
}

export function AplicacoesSection({ aplicacoes, onChanged }: Props) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editando, setEditando] = useState<AplicacaoOut | null>(null)

  async function handleDelete(id: string, nome: string) {
    if (!confirm(`Remover a aplicação "${nome}"?`)) return
    try {
      await deletarAplicacao(id)
      toast.success("Aplicação removida")
      onChanged()
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"))
    }
  }

  return (
    <div className="bg-white p-4 space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-[3px] h-4 rounded" style={{ background: "#8b5cf6" }} />
        <h3 className="text-xs font-bold uppercase tracking-wide text-slate-900">Aplicações</h3>
        <button
          onClick={() => { setEditando(null); setDialogOpen(true) }}
          className="ml-auto text-[11px] text-purple-700 bg-purple-100 border border-purple-200 rounded-full px-2.5 py-0.5 font-semibold hover:bg-purple-200"
        >
          + Nova
        </button>
      </div>

      {aplicacoes.length === 0 ? (
        <div className="text-xs text-slate-500 py-4 text-center">Nenhuma aplicação cadastrada.</div>
      ) : (
        aplicacoes.map(a => (
          <div key={a.id} className="p-2.5 border border-slate-200 rounded flex items-center gap-2.5">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-slate-900 truncate">{a.nome}</div>
              <div className="text-[11px] mt-0.5 flex items-center gap-1 flex-wrap">
                {a.instituicao && <span className="text-slate-600">{a.instituicao}</span>}
                {a.instituicao && <span className="text-slate-400">·</span>}
                <span className="inline-block px-1.5 py-[1px] rounded bg-violet-100 text-violet-800 text-[10px] font-semibold">
                  {TIPO_LABEL[a.tipo] ?? a.tipo}
                </span>
                <span className={`inline-block px-1.5 py-[1px] rounded text-[10px] font-semibold ${a.modo === "AUTOMATICA" ? "bg-emerald-100 text-emerald-800" : "bg-purple-100 text-purple-800"}`}>
                  {a.modo === "AUTOMATICA" ? "● AUTO" : "◆ MANUAL"}
                </span>
                <span className="text-slate-500 ml-1">atualizado {formatDataCurta(a.data_atualizacao)}</span>
              </div>
            </div>
            <div className="text-[15px] font-bold tabular-nums">{formatBRL(a.valor_atual)}</div>
            <button
              onClick={() => { setEditando(a); setDialogOpen(true) }}
              className="text-[11px] text-slate-500 hover:text-slate-800 bg-transparent border-0 cursor-pointer"
              title="Editar"
            >✎</button>
            <button
              onClick={() => handleDelete(a.id, a.nome)}
              className="text-[11px] text-red-400 hover:text-red-600 bg-transparent border-0 cursor-pointer"
              title="Remover"
            >×</button>
          </div>
        ))
      )}

      <EditorAplicacaoDialog
        open={dialogOpen}
        aplicacao={editando}
        onClose={() => { setDialogOpen(false); setEditando(null) }}
        onSaved={onChanged}
      />
    </div>
  )
}

function formatDataCurta(s: string): string {
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y.slice(2)}`
}
