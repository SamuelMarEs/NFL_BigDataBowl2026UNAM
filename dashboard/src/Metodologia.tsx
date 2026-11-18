import { Metodologia as M, useApi } from './api'
import Estado from './Estado'

export default function Metodologia() {
  const { data, error } = useApi<M>('api/metodologia')
  return (
    <div className="max-w-3xl space-y-4">
      <h2 className="text-2xl font-bold">Metodología</h2>
      <section className="rounded border-l-4 border-yellow-500 bg-yellow-50 p-3 text-sm">
        <strong>Importante:</strong> evaluamos al defensor en el momento del lanzamiento del pase, no en la captura. Los datos de
        seguimiento de esta temporada terminan 0.5 segundos después del lanzamiento, así que no sabemos dónde ni cuándo se atrapó el balón.
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">La idea del defensor fantasma</h3>
        <ol className="list-decimal space-y-1 pl-5 text-gray-800">
          <li>En cada pase tomamos al receptor objetivo y al defensor más cercano a él (a 10 yardas o menos).</li>
          <li>Un primer modelo estima cuántas yardas espera ganar la ofensiva en jugadas parecidas, con el defensor donde estaba.</li>
          <li>Un segundo modelo dibuja al defensor "fantasma": dónde y a qué velocidad suele estar un defensor promedio en una situación similar.</li>
          <li>Colocamos al fantasma (unos 30 posibles) en lugar del defensor real y recalculamos las yardas esperadas.</li>
          <li>
            <strong>Delta</strong> = yardas esperadas con el fantasma − yardas esperadas con el defensor real. Positivo significa que el
            defensor limitó el pase mejor que el promedio.
          </li>
          <li>Sumamos y promediamos el delta por defensor, equipo, posición y tipo de cobertura (man o zone).</li>
        </ol>
      </section>
      <section className="space-y-1">
        <h3 className="text-lg font-semibold">Límites</h3>
        <ul className="list-disc space-y-1 pl-5 text-gray-800">
          <li>No medimos qué pasó después de la captura (yardas tras la recepción).</li>
          <li>Solo cuenta el defensor más cercano al receptor; otros defensores influyen y no reciben crédito.</li>
          <li>Los defensores con pocos pases tienen mucho error: por eso se pide un mínimo de jugadas y se muestra el error estándar.</li>
        </ul>
      </section>
      <section>
        <h3 className="mb-2 text-lg font-semibold">Datos del modelo</h3>
        <Estado data={data} error={error} />
        {data && (
          <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
            {[
              ['Pases evaluados', data.n_pases.toLocaleString()],
              ['RMSE de yardas', data.rmse_yardas.toFixed(2)],
              ['Brier de P(completo)', data.brier_completo.toFixed(3)],
              ['Mínimo de pases por defensor', String(data.min_plays)],
              ['Distancia máxima al defensor', `${data.max_dist_defensor} yardas`],
              ['Validación', data.validacion],
              ['Momento de evaluación', data.momento],
            ].map(([k, v]) => (
              <div key={k} className="rounded border bg-white p-3">
                <dt className="text-xs text-gray-500">{k}</dt>
                <dd className="font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>
    </div>
  )
}
