import { useState } from 'react'
import { colorDelta, fmt, Jugada, useApi } from './api'
import Estado from './Estado'

const pct = (p: number) => `${(p * 100).toFixed(0)}%`
const RESULTADO: Record<string, string> = { C: 'Completo', I: 'Incompleto', IN: 'Intercepción' }

function Campo({ j }: { j: Jugada }) {
  const xs = [j.qb.x, j.receptor.x, j.defensor.x, j.linea_scrimmage_x, j.primer_down_x, ...j.fantasmas.map((f) => f.x)]
  const x0 = Math.floor(Math.min(...xs) - 6)
  const x1 = Math.ceil(Math.max(...xs) + 6)
  const maxPeso = Math.max(...j.fantasmas.map((f) => f.peso), 0.0001)
  const lineas: number[] = []
  for (let x = Math.ceil(x0 / 5) * 5; x <= x1; x += 5) lineas.push(x)
  // El eje y del campo crece hacia arriba; en SVG crece hacia abajo, se invierte con 53.3 - y.
  const Y = (y: number) => 53.3 - y
  return (
    <svg viewBox={`${x0} 0 ${x1 - x0} 53.3`} className="w-full rounded border bg-green-700" role="img" aria-label="Campo de fútbol">
      {lineas.map((x) => (
        <g key={x}>
          <line x1={x} x2={x} y1={0} y2={53.3} stroke="white" strokeOpacity={0.35} strokeWidth={0.15} />
          <text x={x} y={52} fontSize={1.8} fill="white" fillOpacity={0.6} textAnchor="middle">{x}</text>
        </g>
      ))}
      <line x1={j.linea_scrimmage_x} x2={j.linea_scrimmage_x} y1={0} y2={53.3} stroke="#2563eb" strokeWidth={0.35} />
      <line x1={j.primer_down_x} x2={j.primer_down_x} y1={0} y2={53.3} stroke="#facc15" strokeWidth={0.35} />
      {j.fantasmas.map((f, i) => (
        <circle key={i} cx={f.x} cy={Y(f.y)} r={0.3 + (f.peso / maxPeso) * 0.9} fill="white" fillOpacity={0.55} stroke="white" strokeWidth={0.1} />
      ))}
      <line x1={j.receptor.x} y1={Y(j.receptor.y)} x2={j.defensor.x} y2={Y(j.defensor.y)} stroke="white" strokeDasharray="0.6 0.6" strokeWidth={0.15} />
      <rect x={j.qb.x - 0.9} y={Y(j.qb.y) - 0.9} width={1.8} height={1.8} fill="#111827" stroke="white" strokeWidth={0.15} />
      <circle cx={j.receptor.x} cy={Y(j.receptor.y)} r={1.1} fill="#f97316" stroke="white" strokeWidth={0.2} />
      <circle cx={j.defensor.x} cy={Y(j.defensor.y)} r={1.1} fill="#dc2626" stroke="white" strokeWidth={0.2} />
    </svg>
  )
}

function Leyenda() {
  const item = (color: string, texto: string, forma: 'c' | 'q' | 'l' = 'c') => (
    <span className="flex items-center gap-1">
      <span className={`inline-block h-3 w-3 ${forma === 'c' ? 'rounded-full' : ''}`} style={{ background: color, border: '1px solid #999' }} />
      {texto}
    </span>
  )
  return (
    <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-700">
      {item('#111827', 'QB', 'q')}
      {item('#f97316', 'Receptor')}
      {item('#dc2626', 'Defensor real')}
      {item('#ffffff', 'Fantasmas (tamaño = peso)')}
      {item('#2563eb', 'Línea de scrimmage', 'l')}
      {item('#facc15', 'Primer down', 'l')}
    </div>
  )
}

function Detalle({ gameId, playId }: { gameId: string; playId: string }) {
  const { data: j, error } = useApi<Jugada>(`api/plays/${gameId}/${playId}`)
  if (!j) return <Estado data={j} error={error} />
  return (
    <div className="space-y-3">
      <p className="text-gray-700">{j.descripcion}</p>
      <p className="text-sm text-gray-600">
        Cobertura: {j.cobertura} · Resultado: {RESULTADO[j.resultado] ?? j.resultado} · Defensor:{' '}
        <a className="text-green-800 underline" href={`#/defensor/${j.defensor.nflId}`}>{j.defensor.nombre}</a> · Receptor: {j.receptor.nombre}
      </p>
      <Campo j={j} />
      <Leyenda />
      <p className="text-xs text-gray-500">Momento del lanzamiento (0.5 s después de pass_forward). Ataque hacia la derecha; coordenadas en yardas.</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded border bg-white p-3">
          <div className="text-xs text-gray-500">Delta (yds esperadas)</div>
          <div className={`text-xl font-bold ${colorDelta(j.delta)}`}>{fmt(j.delta)}</div>
        </div>
        <div className="rounded border bg-white p-3">
          <div className="text-xs text-gray-500">P(completo) real</div>
          <div className="text-xl font-bold">{pct(j.p_completo_real)}</div>
        </div>
        <div className="rounded border bg-white p-3">
          <div className="text-xs text-gray-500">P(completo) con fantasma</div>
          <div className="text-xl font-bold">{pct(j.p_completo_fantasma)}</div>
        </div>
        <div className="rounded border bg-white p-3">
          <div className="text-xs text-gray-500">Yardas esperadas real / fantasma</div>
          <div className="text-xl font-bold">{j.esperado_real.toFixed(1)} / {j.esperado_fantasma.toFixed(1)}</div>
        </div>
      </div>
      <p className="text-sm text-gray-600">Yardas reales del pase: {j.valor_real_yds.toFixed(1)}. Delta positivo: el defensor real limitó el pase mejor que el fantasma promedio.</p>
    </div>
  )
}

export default function VistaJugada({ gameId, playId }: { gameId?: string; playId?: string }) {
  const [g, setG] = useState(gameId ?? '2021090900')
  const [p, setP] = useState(playId ?? '97')
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Vista de jugada</h2>
      <form
        className="flex flex-wrap items-end gap-2 text-sm"
        onSubmit={(e) => {
          e.preventDefault()
          window.location.hash = `#/jugada/${g}/${p}`
        }}
      >
        <label className="flex flex-col">gameId
          <input className="rounded border px-2 py-1" value={g} onChange={(e) => setG(e.target.value)} />
        </label>
        <label className="flex flex-col">playId
          <input className="rounded border px-2 py-1" value={p} onChange={(e) => setP(e.target.value)} />
        </label>
        <button className="rounded bg-green-700 px-3 py-1 text-white" type="submit">Ver jugada</button>
      </form>
      {gameId && playId ? <Detalle key={`${gameId}-${playId}`} gameId={gameId} playId={playId} /> : <p className="text-gray-500">Escribe un gameId y un playId, o entra desde el perfil de un defensor.</p>}
    </div>
  )
}
