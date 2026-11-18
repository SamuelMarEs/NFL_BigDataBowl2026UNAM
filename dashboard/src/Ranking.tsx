import { useMemo, useState } from 'react'
import { colorDelta, Defensor, fmt, useApi } from './api'
import Estado from './Estado'

const POSICIONES = ['CB', 'FS', 'SS', 'ILB', 'MLB', 'OLB']
const POSICIONES_INICIALES = ['CB', 'FS', 'SS']

type Clave = 'nombre' | 'equipo' | 'posicion' | 'plays' | 'delta_medio' | 'delta_total' | 'error_estandar'
const COLUMNAS: { clave: Clave; texto: string }[] = [
  { clave: 'nombre', texto: 'Defensor' },
  { clave: 'equipo', texto: 'Equipo' },
  { clave: 'posicion', texto: 'Pos.' },
  { clave: 'plays', texto: 'Pases' },
  { clave: 'delta_medio', texto: 'Delta medio' },
  { clave: 'delta_total', texto: 'Delta total' },
  { clave: 'error_estandar', texto: 'Error est.' },
]

export default function Ranking() {
  const [posiciones, setPosiciones] = useState<string[]>(POSICIONES_INICIALES)
  const [equipo, setEquipo] = useState('')
  const [cobertura, setCobertura] = useState('')
  const [minPlays, setMinPlays] = useState(15)
  const [orden, setOrden] = useState<{ clave: Clave; desc: boolean }>({ clave: 'delta_medio', desc: true })

  // Cobertura y mínimo de jugadas se filtran en la API; posición y equipo en el cliente
  // (la API acepta una sola posición y queremos varias a la vez).
  const params = new URLSearchParams({ min_plays: String(minPlays) })
  if (cobertura) params.set('coverage', cobertura)
  const { data, error } = useApi<Defensor[]>(`api/defenders?${params.toString()}`)

  const equipos = useMemo(() => Array.from(new Set((data ?? []).map((d) => d.equipo))).sort(), [data])

  const filas = useMemo(() => {
    const f = (data ?? []).filter((d) => posiciones.includes(d.posicion) && (!equipo || d.equipo === equipo))
    const { clave, desc } = orden
    return f.sort((a, b) => {
      const va = a[clave]
      const vb = b[clave]
      const c = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number)
      return desc ? -c : c
    })
  }, [data, posiciones, equipo, orden])

  const maxAbs = Math.max(0.01, ...filas.map((d) => Math.abs(d.delta_medio)))

  const alternarPos = (p: string) =>
    setPosiciones((act) => (act.includes(p) ? act.filter((x) => x !== p) : [...act, p]))
  const ordenarPor = (clave: Clave) =>
    setOrden((o) => (o.clave === clave ? { clave, desc: !o.desc } : { clave, desc: clave !== 'nombre' && clave !== 'equipo' && clave !== 'posicion' }))

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Ranking de defensores</h2>
      <p className="text-sm text-gray-600">
        Delta medio: yardas esperadas que el defensor ahorró por pase frente al defensor fantasma (promedio). Positivo es mejor.
        {cobertura && ` Con el filtro de cobertura, el delta es solo el de pases contra ${cobertura === 'man' ? 'man' : 'zone'}.`}
      </p>

      <section className="flex flex-wrap items-end gap-4 rounded border bg-white p-3 text-sm">
        <div>
          <p className="mb-1 font-medium">Posición</p>
          <div className="flex flex-wrap gap-1">
            {POSICIONES.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => alternarPos(p)}
                aria-pressed={posiciones.includes(p)}
                className={`rounded border px-2 py-1 ${posiciones.includes(p) ? 'border-green-800 bg-green-800 text-white' : 'bg-white hover:bg-green-50'}`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        <label>
          <span className="mb-1 block font-medium">Equipo</span>
          <select className="rounded border p-1" value={equipo} onChange={(e) => setEquipo(e.target.value)}>
            <option value="">Todos</option>
            {equipos.map((e) => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1 block font-medium">Cobertura</span>
          <select className="rounded border p-1" value={cobertura} onChange={(e) => setCobertura(e.target.value)}>
            <option value="">Todas</option>
            <option value="man">Man</option>
            <option value="zone">Zone</option>
          </select>
        </label>
        <label>
          <span className="mb-1 block font-medium">Mínimo de pases</span>
          <input
            type="number"
            min={1}
            className="w-20 rounded border p-1"
            value={minPlays}
            onChange={(e) => setMinPlays(Math.max(1, Number(e.target.value) || 1))}
          />
        </label>
      </section>

      <Estado data={data} error={error} />
      {data && (
        <>
          <p className="text-sm text-gray-600">{filas.length} defensores</p>
          <div className="overflow-x-auto">
            <table className="w-full border bg-white text-left text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="p-2">#</th>
                  {COLUMNAS.map((c) => (
                    <th key={c.clave} className="p-2" aria-sort={orden.clave === c.clave ? (orden.desc ? 'descending' : 'ascending') : 'none'}>
                      <button type="button" className="font-semibold hover:underline" onClick={() => ordenarPor(c.clave)}>
                        {c.texto}
                        {orden.clave === c.clave ? (orden.desc ? ' ▼' : ' ▲') : ''}
                      </button>
                    </th>
                  ))}
                  <th className="p-2">Barra de delta (±1 error est.)</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((d, i) => {
                  const ancho = (Math.abs(d.delta_medio) / maxAbs) * 50
                  const ee = (d.error_estandar / maxAbs) * 50
                  const positivo = d.delta_medio >= 0
                  // El intervalo ±1 EE que cruza el cero indica que la diferencia no es clara.
                  const dudoso = Math.abs(d.delta_medio) <= d.error_estandar
                  return (
                    <tr key={d.nflId} className="border-t hover:bg-green-50">
                      <td className="p-2 text-gray-500">{i + 1}</td>
                      <td className="p-2 font-medium">
                        <a className="text-green-800 underline" href={`#/defensor/${d.nflId}`}>{d.nombre}</a>
                      </td>
                      <td className="p-2">{d.equipo}</td>
                      <td className="p-2">{d.posicion}</td>
                      <td className="p-2">{d.plays}</td>
                      <td className={`p-2 font-semibold ${colorDelta(d.delta_medio)}`}>{fmt(d.delta_medio)}</td>
                      <td className={`p-2 ${colorDelta(d.delta_total)}`}>{fmt(d.delta_total, 1)}</td>
                      <td className="p-2">
                        ±{d.error_estandar.toFixed(2)}
                        {dudoso && <span title="El error estándar es mayor o igual al delta: diferencia poco clara" className="ml-1 text-amber-600">⚠</span>}
                      </td>
                      <td className="p-2" style={{ minWidth: 160 }}>
                        <div
                          className="relative h-4 w-full"
                          role="img"
                          aria-label={`Delta ${fmt(d.delta_medio)} con error estándar ${d.error_estandar.toFixed(2)}`}
                        >
                          <div className="absolute inset-y-0 left-1/2 w-px bg-gray-400" />
                          <div
                            className={`absolute inset-y-1 ${positivo ? 'bg-green-600' : 'bg-red-500'}`}
                            style={positivo ? { left: '50%', width: `${ancho}%` } : { left: `${50 - ancho}%`, width: `${ancho}%` }}
                          />
                          <div
                            className="absolute top-1/2 h-px bg-gray-800"
                            style={{ left: `${Math.max(0, 50 + (positivo ? ancho : -ancho) - ee)}%`, width: `${Math.min(100, 2 * ee)}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {filas.length === 0 && <p className="text-gray-500">Ningún defensor cumple los filtros.</p>}
        </>
      )}
    </div>
  )
}
