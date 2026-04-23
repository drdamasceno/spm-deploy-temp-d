"use client"

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
  fillGradient?: boolean
}

export function Sparkline({
  data,
  width = 200,
  height = 50,
  color = "#1e40af",
  fillGradient = true,
}: SparklineProps) {
  if (!data || data.length < 2) {
    return (
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height }} preserveAspectRatio="none">
        <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="#e2e8f0" strokeDasharray="3,3" />
      </svg>
    )
  }
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const pts = data.map((v, i) => ({
    x: (i / (data.length - 1)) * width,
    y: height - 4 - ((v - min) / range) * (height - 8),
  }))
  const pathLine = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ")
  const pathArea = `${pathLine} L${width},${height} L0,${height} Z`
  const last = pts[pts.length - 1]
  const gradId = `spark-grad-${Math.random().toString(36).slice(2, 9)}`
  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height }} preserveAspectRatio="none">
      {fillGradient && (
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
      )}
      {fillGradient && <path d={pathArea} fill={`url(#${gradId})`} />}
      <path d={pathLine} fill="none" stroke={color} strokeWidth={2} />
      <circle cx={last.x} cy={last.y} r={3} fill={color} />
    </svg>
  )
}
