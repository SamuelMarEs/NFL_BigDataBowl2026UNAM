import { useEffect, useState } from 'react'
import { colorDelta, fmt, Jugada, JugadorTray, nombreEquipo, Trayectoria, useApi } from './api'
import Estado from './Estado'

const pct = (p: number) => `${(p * 100).toFixed(0)}%`
const RESULTADO: Record<string, string> = { C: 'Completo', I: 'Incompleto', IN: 'Intercepción' }

const lerp = (a: number[], f: number) => {
  const i = Math.min(Math.floor(f), a.length - 1)
  const k = Math.min(i + 1, a.length - 1)
  return a[i] + (a[k] - a[i]) * (f - i)
}
const suave = (u: number) => u * u * (3 - 2 * u)
function Campo({ j, tray, f }: { j: Jugada; tray: Trayectoria | null; f: number }) {
  const xs = [j.qb.x, j.receptor.x, j.defensor.x, j.linea_scrimmage_x, j.primer_down_x, ...j.fantasmas.map((p) => p.x)]
  if (tray) for (const p of tray.jugadores) xs.push(...p.x)
  const x0 = Math.floor(Math.min(...xs) - 6)
  const x1 = Math.ceil(Math.max(...xs) + 6)
  const maxPeso = Math.max(...j.fantasmas.map((p) => p.peso), 0.0001)
  const lineas: number[] = []
  for (let x = Math.ceil(x0 / 5) * 5; x <= x1; x += 5) lineas.push(x)
  // El eje y del campo crece hacia arriba; en SVG crece hacia abajo, se invierte con 53.3 - y.
  const Y = (y: number) => 53.3 - y
  const def = tray?.jugadores.find((p) => p.rol === 'defensor')
  const rec = tray?.jugadores.find((p) => p.rol === 'receptor')
  // Fantasma: parte de la posición del defensor real y se desplaza hacia su posición final muestreada.
  const u = tray ? suave(Math.min(1, f / Math.max(1, tray.n_frames - 1))) : 1
  const dxF = def ? lerp(def.x, f) : j.defensor.x
  const dyF = def ? lerp(def.y, f) : j.defensor.y
  const dxL = def ? def.x[def.x.length - 1] : j.defensor.x
  const dyL = def ? def.y[def.y.length - 1] : j.defensor.y
  const fant = j.fantasmas.map((p) => ({ ...p, px: dxF + u * (p.x - dxL), py: dyF + u * (p.y - dyL) }))
  const rx = rec ? lerp(rec.x, f) : j.receptor.x
  const ry = rec ? lerp(rec.y, f) : j.receptor.y
  const balon = tray ? { x: lerp(tray.balon.map((p) => p.x), f), y: lerp(tray.balon.map((p) => p.y), f) } : null
  const color = (p: JugadorTray) =>
    p.rol === 'receptor' ? '#f97316' : p.rol === 'defensor' ? '#dc2626' : p.rol === 'qb' ? '#111827' : p.lado === 'ataque' ? '#93c5fd' : '#fca5a5'
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
      {fant.map((p, i) => (
        <circle key={i} cx={p.px} cy={Y(p.py)} r={0.3 + (p.peso / maxPeso) * 0.9} fill="white" fillOpacity={0.55} stroke="white" strokeWidth={0.1} />
      ))}
      <line x1={rx} y1={Y(ry)} x2={dxF} y2={Y(dyF)} stroke="white" strokeDasharray="0.6 0.6" strokeWidth={0.15} />
      {tray ? (
        <>
          {tray.jugadores.filter((p) => p.rol === 'otro').map((p) => (
            <circle key={p.nflId} cx={lerp(p.x, f)} cy={Y(lerp(p.y, f))} r={0.8} fill={color(p)} stroke="white" strokeWidth={0.15}>
              <title>{`${p.nombre} (${p.posicion})`}</title>
            </circle>
          ))}
          {tray.jugadores.filter((p) => p.rol !== 'otro').map((p) => (
            p.rol === 'qb' ? (
              <rect key={p.nflId} x={lerp(p.x, f) - 0.9} y={Y(lerp(p.y, f)) - 0.9} width={1.8} height={1.8} fill={color(p)} stroke="white" strokeWidth={0.15}>
                <title>{`${p.nombre} (QB)`}</title>
              </rect>
            ) : (
              <circle key={p.nflId} cx={lerp(p.x, f)} cy={Y(lerp(p.y, f))} r={1.1} fill={color(p)} stroke="white" strokeWidth={0.2}>
                <title>{`${p.nombre} (${p.posicion})`}</title>
              </circle>
            )
          ))}
          {balon && <ellipse cx={balon.x} cy={Y(balon.y)} rx={0.9} ry={0.55} fill="#78350f" stroke="white" strokeWidth={0.15} />}
        </>
      ) : (
        <>
          <rect x={j.qb.x - 0.9} y={Y(j.qb.y) - 0.9} width={1.8} height={1.8} fill="#111827" stroke="white" strokeWidth={0.15} />
          <circle cx={j.receptor.x} cy={Y(j.receptor.y)} r={1.1} fill="#f97316" stroke="white" strokeWidth={0.2} />
          <circle cx={j.defensor.x} cy={Y(j.defensor.y)} r={1.1} fill="#dc2626" stroke="white" strokeWidth={0.2} />
        </>
      )}
    </svg>
  )
}
function Animacion({ j }: { j: Jugada }) {
  const { data: tray } = useApi<Trayectoria>(`api/plays/${j.gameId}/${j.playId}/trayectoria`)
  const [f, setF] = useState(0)
  const [jugando, setJugando] = useState(true)
  const [vel, setVel] = useState(1)
  const n = tray ? tray.n_frames - 1 : 0
  useEffect(() => {
    if (!tray || !jugando) return
    let id = 0
    let previo = performance.now()
    const paso = (t: number) => {
      const dt = (t - previo) / 1000
      previo = t
      setF((a) => {
        const b = a + dt * tray.fps * vel
        return b >= n ? n : b
      })
      id = requestAnimationFrame(paso)
    }
    id = requestAnimationFrame(paso)
    return () => cancelAnimationFrame(id)
  }, [tray, jugando, vel, n])
  useEffect(() => {
    if (jugando && f >= n && n > 0) setJugando(false)
  }, [f, jugando, n])
  const reiniciar = () => {
    setF(0)
    setJugando(true)
  }
  const lanz = tray?.frame_lanzamiento ?? 0
  const fase = !tray ? '' : f < lanz ? 'Antes del lanzamiento' : 'Balón en el aire'
  return (
    <div>
      <Campo j={j} tray={tray} f={f} />
      {tray && (
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
          <button className="rounded bg-green-700 px-3 py-1 text-white" onClick={() => (f >= n ? reiniciar() : setJugando(!jugando))}>
            {f >= n ? 'Repetir' : jugando ? 'Pausa' : 'Reproducir'}
          </button>
          <input
            type="range" min={0} max={n} step={0.1} value={f} className="min-w-[10rem] flex-1" aria-label="Tiempo de la jugada"
            onChange={(e) => {
              setJugando(false)
              setF(Number(e.target.value))
            }}
          />
          <select className="rounded border p-1" value={vel} onChange={(e) => setVel(Number(e.target.value))} aria-label="Velocidad">
            <option value={0.25}>0.25x</option>
            <option value={0.5}>0.5x</option>
            <option value={1}>1x</option>
          </select>
          <span className="text-gray-600">{(f / tray.fps).toFixed(1)} s desde el snap · {fase}</span>
        </div>
      )}
      {tray && (
        <p className="mt-1 text-sm text-gray-600">
          Ataque: {nombreEquipo(tray.equipo_ataque)} · Defensa: {nombreEquipo(tray.equipo_defensa)}
        </p>
      )}
    </div>
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
      {item('#93c5fd', 'Ofensiva')}
      {item('#fca5a5', 'Defensiva')}
      {item('#78350f', 'Balón')}
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
      <Animacion j={j} />
      <Leyenda />
      <p className="text-xs text-gray-500">Animación del snap al último frame del tracking (0.5 s después de pass_forward). Los fantasmas parten de la posición del defensor real y se desplazan suavemente a su posición final; el recorrido intermedio es una interpolación, no un dato medido. Ataque hacia la derecha; coordenadas en yardas.</p>
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
