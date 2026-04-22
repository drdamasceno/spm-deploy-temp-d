"use client"

import Link from "next/link"
import { LogOut } from "lucide-react"

import { logout } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"

export function Header() {
  return (
    <>
      <header className="w-full border-b bg-background">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
          <Link href="/rodadas" className="font-semibold tracking-tight">
            SPM — Sistema Financeiro
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/rodadas" className="text-sm text-muted-foreground hover:text-foreground transition">
              Rodadas
            </Link>
            <Separator orientation="vertical" className="h-6" />
            <Button variant="ghost" size="sm" onClick={logout} aria-label="Sair">
              <LogOut className="h-4 w-4 mr-2" />
              Sair
            </Button>
          </div>
        </div>
      </header>
    </>
  )
}
