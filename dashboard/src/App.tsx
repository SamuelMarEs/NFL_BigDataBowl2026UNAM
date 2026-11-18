import { useEffect, useState } from 'react'
import Equipos from './Equipos'
import Metodologia from './Metodologia'
import Perfil from './Perfil'
import Ranking from './Ranking'
import VistaJugada from './VistaJugada'

// Rutas con hash (#/defensor/1001) para que funcione con base './' sin configurar el servidor.
const MENU = [
  { href: '#/defensor', texto: 'Defensores' },
  { href: '#/jugada', texto: 'Jugada' },
  { href: '#/equipos', texto: 'Equipos' },
  { href: '#/metodologia', texto: 'Metodología' },
]

function useHash() {
  const [hash, setHash] = useState(window.location.hash)
  useEffect(() => {
    const f = () => setHash(window.location.hash)
    window.addEventListener('hashchange', f)
    return () => window.removeEventListener('hashchange', f)
  }, [])
  return hash
}

export default function App() {
  const hash = useHash()
  const [, seccion = 'defensor', a, b] = hash.replace(/^#/, '').split('/')
  let pantalla
  if (seccion === 'jugada') pantalla = <VistaJugada gameId={a} playId={b} />
  else if (seccion === 'equipos') pantalla = <Equipos />
  else if (seccion === 'metodologia') pantalla = <Metodologia />
  else if (a) pantalla = <Perfil id={a} />
  else pantalla = <Ranking />
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-green-800 text-white">
        <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 p-3">
          <span className="font-bold">NFL Ghosts</span>
          {MENU.map((m) => (
            <a key={m.href} href={m.href} className={hash.startsWith(m.href) ? 'underline' : 'opacity-80 hover:opacity-100'}>
              {m.texto}
            </a>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl p-4">{pantalla}</main>
    </div>
  )
}
