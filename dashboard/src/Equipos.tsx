import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { colorDelta, Equipo, fmt, nombreEquipo, useApi } from './api'
import Estado from './Estado'

export default function Equipos() {
  const { data, error } = useApi<Equipo[]>('api/teams')
  const filas = data ? [...data].sort((a, b) => b.delta_medio - a.delta_medio) : []
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Equipos</h2>
      <p className="text-sm text-gray-600">Delta medio por pase objetivo. Positivo: la defensa del equipo limita más que el defensor fantasma.</p>
      <Estado data={data} error={error} />
      {data && (
        <>
          <section className="rounded border bg-white p-3">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={filas}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="equipo" />
                <YAxis />
                <Tooltip labelFormatter={(l) => nombreEquipo(String(l))} />
                <ReferenceLine y={0} stroke="#666" />
                <Bar dataKey="delta_medio" fill="#2F7D4F" />
              </BarChart>
            </ResponsiveContainer>
          </section>
          <table className="w-full border bg-white text-left text-sm">
            <thead className="bg-gray-100">
              <tr><th className="p-2">Equipo</th><th className="p-2">Pases</th><th className="p-2">Delta medio</th><th className="p-2">Yardas esperadas concedidas</th></tr>
            </thead>
            <tbody>
              {filas.map((e) => (
                <tr key={e.equipo} className="border-t">
                  <td className="p-2 font-medium">{nombreEquipo(e.equipo)}</td>
                  <td className="p-2">{e.plays}</td>
                  <td className={`p-2 ${colorDelta(e.delta_medio)}`}>{fmt(e.delta_medio)}</td>
                  <td className="p-2">{e.yardas_esperadas_concedidas.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
