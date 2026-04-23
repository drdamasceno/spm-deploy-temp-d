"use client"

interface StubEmConstrucaoProps {
  titulo: string
  descricao: string
  planoFuturo: string
}

/**
 * Placeholder para subpáginas cuja implementação completa está programada
 * para um plano futuro do Track B. Mantém a navegação consistente (cards
 * da home linkam para cá) e documenta explicitamente o que falta.
 */
export function StubEmConstrucao({ titulo, descricao, planoFuturo }: StubEmConstrucaoProps) {
  return (
    <div className="p-6 space-y-5">
      <div>
        <a href="/" className="text-xs text-slate-500 hover:text-slate-900">
          ← Voltar
        </a>
        <h1 className="mt-1 text-lg font-semibold text-slate-900">{titulo}</h1>
      </div>
      <div className="rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-6">
        <div className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">
          Em construção
        </div>
        <p className="text-sm text-slate-700 leading-relaxed">{descricao}</p>
        <p className="mt-3 text-xs italic text-slate-500">
          Entregue em: <span className="font-semibold text-slate-700">{planoFuturo}</span>
        </p>
      </div>
    </div>
  )
}
