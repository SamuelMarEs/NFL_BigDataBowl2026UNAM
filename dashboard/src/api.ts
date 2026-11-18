import { useEffect, useState } from 'react'

export interface Boxscore {
  intercepciones: number
  pases_defendidos: number
  fumbles_forzados: number
  tackles_completos: number
}
export interface Defensor {
  nflId: number
  nombre: string
  equipo: string
  posicion: string
  plays: number
  delta_total: number
  delta_medio: number
  error_estandar: number
  delta_man: number
  delta_zone: number
  boxscore?: Boxscore
}
export interface JugadaResumen {
  gameId: number
  playId: number
  semana: number
  descripcion: string
  delta: number
  cobertura: string
}
export interface PerfilDefensor {
  defensor: Defensor
  por_semana: { semana: number; plays: number; delta_medio: number }[]
  mejores: JugadaResumen[]
  peores: JugadaResumen[]
}
export interface Equipo {
  equipo: string
  plays: number
  delta_medio: number
  yardas_esperadas_concedidas: number
}
export interface Punto { x: number; y: number }
export interface Jugador extends Punto { nombre: string; s: number; dir: number }
export interface Jugada {
  gameId: number
  playId: number
  descripcion: string
  cobertura: string
  resultado: string
  receptor: Jugador
  defensor: Jugador & { nflId: number }
  qb: Punto
  fantasmas: (Punto & { peso: number })[]
  valor_real_yds: number
  p_completo_real: number
  esperado_real: number
  p_completo_fantasma: number
  esperado_fantasma: number
  delta: number
  linea_scrimmage_x: number
  primer_down_x: number
}
export interface Metodologia {
  rmse_yardas: number
  brier_completo: number
  n_pases: number
  min_plays: number
  max_dist_defensor: number
  validacion: string
  momento: string
}

// Rutas relativas, sin diagonal inicial (regla del proyecto).
export function useApi<T>(ruta: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!ruta) return
    let vigente = true
    setData(null)
    setError(null)
    fetch(ruta)
      .then((r) => {
        if (!r.ok) throw new Error(`Error ${r.status} en ${ruta}`)
        return r.json() as Promise<T>
      })
      .then((d) => vigente && setData(d))
      .catch((e: Error) => vigente && setError(e.message))
    return () => {
      vigente = false
    }
  }, [ruta])
  return { data, error }
}

export const fmt = (n: number, d = 2) => (n > 0 ? '+' : '') + n.toFixed(d)
export const colorDelta = (n: number) => (n >= 0 ? 'text-green-700' : 'text-red-600')
