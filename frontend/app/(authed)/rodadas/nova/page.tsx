import { UploadForm } from "@/components/rodada/UploadForm"

export default function NovaRodadaPage() {
  return (
    <main className="mx-auto max-w-3xl w-full px-6 py-8 flex-1">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Nova rodada</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Envie o PP XLSX + OFX e o periodo do extrato. O sistema cria a rodada,
          faz upload para o Storage e executa a conciliacao automaticamente.
        </p>
      </div>
      <UploadForm />
    </main>
  )
}
