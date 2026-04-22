"use client"
import { useState, useEffect, useRef } from "react"

/**
 * Input de valor em BRL com máscara de digitação estilo caixa eletrônico:
 * Digita "1" → R$ 0,01
 * Digita "12" → R$ 0,12
 * Digita "123" → R$ 1,23
 * Digita "12345" → R$ 123,45
 * Digita "1234567" → R$ 12.345,67
 *
 * O componente armazena os dígitos internamente como string e expõe
 * o valor numérico (Number) via onChange.
 *
 * `value` (prop) é o valor numérico atual. Quando muda externamente,
 * o display atualiza.
 */
interface Props {
  value: number
  onChange: (value: number) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  id?: string
}

function formatBR(centavos: string): string {
  // Pad esquerda com zeros para garantir ao menos 3 dígitos (1 centavo)
  const padded = centavos.replace(/\D/g, "").padStart(3, "0")
  const reais = padded.slice(0, -2)
  const dec = padded.slice(-2)
  // Formata milhares no int
  const reaisFmt = reais.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ".") || "0"
  return `R$ ${reaisFmt},${dec}`
}

function centavosDoValor(v: number): string {
  // v em reais → string de dígitos centavos
  const cents = Math.round(v * 100)
  return cents.toString()
}

export function InputDinheiro({ value, onChange, placeholder = "R$ 0,00", disabled, className, id }: Props) {
  const [digits, setDigits] = useState<string>(() => centavosDoValor(value || 0))
  const lastEmittedRef = useRef<number>(value || 0)

  // Se o value externo mudar (ex: reset, carregamento), sincroniza
  useEffect(() => {
    if (Math.abs(value - lastEmittedRef.current) > 0.005) {
      setDigits(centavosDoValor(value || 0))
      lastEmittedRef.current = value
    }
  }, [value])

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value.replace(/\D/g, "")
    // Limita a 13 dígitos (R$ 9.999.999.999,99 — mais que suficiente)
    const clamped = raw.slice(0, 13)
    setDigits(clamped)
    const num = parseFloat((parseInt(clamped || "0", 10) / 100).toFixed(2))
    lastEmittedRef.current = num
    onChange(num)
  }

  return (
    <input
      id={id}
      type="text"
      inputMode="numeric"
      value={digits === "" || digits === "0" ? "" : formatBR(digits)}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      className={className ?? "w-full border border-slate-300 rounded px-2.5 py-1.5 text-sm tabular-nums text-right"}
    />
  )
}
