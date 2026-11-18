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
export interface JugadorTray {
  nflId: number
  nombre: string
  equipo: string
  lado: 'ataque' | 'defensa'
  posicion: string
  rol: 'qb' | 'receptor' | 'defensor' | 'otro'
  x: number[]
  y: number[]
}
export interface Trayectoria {
  gameId: number
  playId: number
  equipo_ataque: string
  equipo_defensa: string
  frame_snap: number
  frame_lanzamiento: number
  n_frames: number
  fps: number
  balon: Punto[]
  jugadores: JugadorTray[]
}
export interface Partido {
  gameId: number
  semana: number
  local: string
  visitante: string
  jugadas: number
}
export interface JugadaLista {
  gameId: number
  playId: number
  semana: number
  local: string
  visitante: string
  cuarto: number
  reloj: string
  down: number
  yardas_por_jugar: number
  equipo_ataque: string
  equipo_defensa: string
  receptor: string
  defensor: string
  resultado: 'C' | 'I' | 'IN'
  descripcion: string
  delta: number
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
    let temporizador: ReturnType<typeof setTimeout> | undefined
    setData(null)
    setError(null)
    // Al arrancar, el servidor calcula los modelos (~50 s) y responde 503: se reintenta cada 3 s (máx. 3 min).
    const intentar = (n: number) => {
      fetch(ruta)
        .then((r) => {
          if (r.status === 503 && n < 60) {
            temporizador = setTimeout(() => vigente && intentar(n + 1), 3000)
            return null
          }
          if (!r.ok) throw new Error(`Error ${r.status} en ${ruta}`)
          return r.json() as Promise<T>
        })
        .then((d) => d !== null && vigente && setData(d))
        .catch((e: Error) => vigente && setError(e.message))
    }
    intentar(0)
    return () => {
      vigente = false
      clearTimeout(temporizador)
    }
  }, [ruta])
  return { data, error }
}

export const fmt = (n: number, d = 2) => (n > 0 ? '+' : '') + n.toFixed(d)
export const colorDelta = (n: number) => (n >= 0 ? 'text-green-700' : 'text-red-600')

export const EQUIPOS: Record<string, string> = {
  ARI: 'Arizona Cardinals', ATL: 'Atlanta Falcons', BAL: 'Baltimore Ravens', BUF: 'Buffalo Bills',
  CAR: 'Carolina Panthers', CHI: 'Chicago Bears', CIN: 'Cincinnati Bengals', CLE: 'Cleveland Browns',
  DAL: 'Dallas Cowboys', DEN: 'Denver Broncos', DET: 'Detroit Lions', GB: 'Green Bay Packers',
  HOU: 'Houston Texans', IND: 'Indianapolis Colts', JAX: 'Jacksonville Jaguars', KC: 'Kansas City Chiefs',
  LA: 'Los Angeles Rams', LAC: 'Los Angeles Chargers', LV: 'Las Vegas Raiders', MIA: 'Miami Dolphins',
  MIN: 'Minnesota Vikings', NE: 'New England Patriots', NO: 'New Orleans Saints', NYG: 'New York Giants',
  NYJ: 'New York Jets', PHI: 'Philadelphia Eagles', PIT: 'Pittsburgh Steelers', SEA: 'Seattle Seahawks',
  SF: 'San Francisco 49ers', TB: 'Tampa Bay Buccaneers', TEN: 'Tennessee Titans', WAS: 'Washington Commanders',
}
// "Dallas Cowboys (DAL)"; si la abreviatura no se conoce, se deja tal cual.
export const nombreEquipo = (abrev: string) => (EQUIPOS[abrev] ? `${EQUIPOS[abrev]} (${abrev})` : abrev)
