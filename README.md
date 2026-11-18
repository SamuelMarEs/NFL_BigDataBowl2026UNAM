# Defensores NFL: evaluación en pase con "fantasmas"

Hackathon NFL Big Data Bowl, UNAM.

**Autores:** Samuel Márquez Estrada y Keily Atziri Romo Nuñez.

## Descripción

App para coaches y reclutadores que evalúa el desempeño de defensores en jugadas de pase de la temporada 2021
(Big Data Bowl). Está inspirada en el paper "NFL Ghosts" (Yurko, Nguyen, Pelechrinis; `NFLghosts.pdf`).

Para cada pase se compara al defensor real con un "defensor fantasma": un defensor promedio colocado según lo que
suelen hacer otros defensores en jugadas parecidas. Dos modelos kNN (solo numpy y pandas) estiman las yardas
esperadas del pase con el defensor real y con ~30 fantasmas. La diferencia es el `delta`: positivo significa que el
defensor limitó el pase mejor que el promedio.

Límite del método: el tracking de este dataset termina 0.5 s después del lanzamiento, así que se evalúa al defensor
en el último frame disponible y no en la captura. La validación es leave-one-out sobre 6626 pases
(RMSE de yardas 9.32, Brier de P(completo) 0.190).

Pantallas: ranking de defensores, perfil, vista de jugada (campo SVG con fantasmas), equipos y metodología.

## Estructura

- `backend/`: FastAPI. `precompute.py` genera `capturas.csv`, `modelo.py` tiene los modelos, `main.py` es la API
  (contrato en `backend/contrato_api.md`).
- `dashboard/`: React + TypeScript + Tailwind 3 + Recharts (Vite).
- `data/`: datos originales (solo lectura).

## Cómo correrlo

Requisitos: el entorno del hackathon ya instalado (`.venv/` con Python 3.12 y Node 22). Verifica con:

```
sh .hackathon/setup.sh --check
```

Los comandos se ejecutan desde la raíz del proyecto. En Linux, si `npm` no está en el PATH:
`export PATH="$PWD/.hackathon/.tools/node/bin:$PATH"`.

### Opción 1: un solo servidor (como en el despliegue)

```
cd dashboard && npm install && npm run build && cd ..
.venv/bin/uvicorn backend.main:app --port 8000
```

Abre `http://localhost:8000`. La API y el dashboard comparten URL y puerto.

### Opción 2: desarrollo (dos procesos)

```
# Terminal 1: API
.venv/bin/uvicorn backend.main:app --port 8000 --reload

# Terminal 2: dashboard (proxy /api -> localhost:8000)
cd dashboard && npm install && npm run dev
```

Abre la URL que muestra Vite (usa `localhost`, no `127.0.0.1`).

### Notas

- Al arrancar, la API calcula los modelos (~50 s). Mientras tanto `/health` responde `ok` y las rutas `/api`
  responden 503; el dashboard funciona cuando termina.
- `backend/capturas.csv` ya está versionado. Solo hace falta regenerarlo si cambia la lógica de extracción:
  `.venv/bin/python backend/precompute.py` (~130 s, lee `data/tracking/`).
- En Windows usa `.venv\Scripts\uvicorn` en lugar de `.venv/bin/uvicorn`.
- La IA (informe por defensor con Bedrock) es opcional y todavía no está implementada. La app no la necesita.

## Entrega

```
sh .hackathon/setup.sh --entregar
```
