import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { colorDelta, Defensor, fmt, JugadaResumen, PerfilDefensor, useApi } from './api'
import Estado from './Estado'

function Kpi({ titulo, valor, clase = '' }: { titulo: string; valor: string; clase?: string }) {
  return (
    <div className="rounded border bg-white p-3">
      <div className="text-xs text-gray-500">{titulo}</div>
      <div className={`text-xl font-bold ${clase}`}>{valor}</div>
    </div>
  )
}

function ListaJugadas({ titulo, jugadas }: { titulo: string; jugadas: JugadaResumen[] }) {
  return (
    <section className="rounded border bg-white p-3">
      <h3 className="mb-2 font-semibold">{titulo}</h3>
      <ul className="space-y-2 text-sm">
        {jugadas.map((j) => (
          <li key={`${j.gameId}-${j.playId}`}>
            <a className="text-green-800 underline" href={`#/jugada/${j.gameId}/${j.playId}`}>
              Semana {j.semana} · {j.cobertura} · <span className={colorDelta(j.delta)}>{fmt(j.delta)} yds</span>
            </a>
            <div className="text-gray-600">{j.descripcion}</div>
          </li>
        ))}
        {jugadas.length === 0 && <li className="text-gray-500">Sin jugadas.</li>}
      </ul>
    </section>
  )
}

function Selector() {
  const { data, error } = useApi<Defensor[]>('api/defenders?min_plays=1')
  return (
    <div>
      <h2 className="mb-3 text-xl font-bold">Elige un defensor</h2>
      <Estado data={data} error={error} />
      <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {data?.map((d) => (
          <li key={d.nflId}>
            <a className="block rounded border bg-white p-2 hover:bg-green-50" href={`#/defensor/${d.nflId}`}>
              {d.nombre} <span className="text-gray-500">({d.equipo} · {d.posicion})</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Perfil({ id }: { id?: string }) {
  const { data, error } = useApi<PerfilDefensor>(id ? `api/defenders/${id}` : null)
  if (!id) return <Selector />
  if (!data) return <Estado data={data} error={error} />
  const d = data.defensor
  const manZone = [
    { cobertura: 'Man', delta: d.delta_man },
    { cobertura: 'Zone', delta: d.delta_zone },
  ]
  const b = d.boxscore
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold">{d.nombre}</h2>
        <p className="text-gray-600">{d.equipo} · {d.posicion}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Kpi titulo="Pases como defensor más cercano" valor={String(d.plays)} />
        <Kpi titulo="Delta medio (yds por pase)" valor={fmt(d.delta_medio)} clase={colorDelta(d.delta_medio)} />
        <Kpi titulo="Delta total (yds)" valor={fmt(d.delta_total, 1)} clase={colorDelta(d.delta_total)} />
        <Kpi titulo="Error estándar" valor={`±${d.error_estandar.toFixed(2)}`} />
        <Kpi titulo="Delta man / zone" valor={`${fmt(d.delta_man, 1)} / ${fmt(d.delta_zone, 1)}`} />
      </div>
      <p className="text-sm text-gray-600">
        Delta positivo: el defensor concedió menos yardas esperadas que el defensor fantasma (promedio).
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded border bg-white p-3">
          <h3 className="mb-2 font-semibold">Man vs zone (delta medio)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={manZone}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="cobertura" />
              <YAxis />
              <Tooltip />
              <ReferenceLine y={0} stroke="#666" />
              <Bar dataKey="delta" fill="#2F7D4F" />
            </BarChart>
          </ResponsiveContainer>
        </section>
        <section className="rounded border bg-white p-3">
          <h3 className="mb-2 font-semibold">Tendencia por semana (delta medio)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.por_semana}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="semana" />
              <YAxis />
              <Tooltip />
              <ReferenceLine y={0} stroke="#666" />
              <Line type="monotone" dataKey="delta_medio" stroke="#2F7D4F" />
            </LineChart>
          </ResponsiveContainer>
        </section>
      </div>
      <section className="rounded border bg-white p-3">
        <h3 className="mb-2 font-semibold">Boxscore</h3>
        {b ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi titulo="Intercepciones" valor={String(b.intercepciones)} />
            <Kpi titulo="Pases defendidos" valor={String(b.pases_defendidos)} />
            <Kpi titulo="Fumbles forzados" valor={String(b.fumbles_forzados)} />
            <Kpi titulo="Tackles en pases completos" valor={String(b.tackles_completos)} />
          </div>
        ) : (
          <p className="text-gray-500">Sin datos de boxscore.</p>
        )}
        <p className="mt-2 text-xs text-gray-500">
          Los tackles en completos son una aproximación de pases completos permitidos, no de cobertura real.
        </p>
      </section>
      <div className="grid gap-4 md:grid-cols-2">
        <ListaJugadas titulo="Mejores jugadas" jugadas={data.mejores} />
        <ListaJugadas titulo="Peores jugadas" jugadas={data.peores} />
      </div>
    </div>
  )
}
