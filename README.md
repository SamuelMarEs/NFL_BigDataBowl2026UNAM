# NFL Ghosts: evaluación de defensores en pase

App para coaches y reclutadores que evalúa a los defensores en jugadas de pase de la temporada 2021 (NFL Big Data Bowl).
Está inspirada en el paper "NFL Ghosts" (Yurko, Nguyen, Pelechrinis; `NFLghosts.pdf`).
Autores: Samuel Márquez Estrada y Keily Atziri Romo Nuñez.

## Método

Cada pase se compara contra un "defensor fantasma": un defensor promedio colocado según lo que hacen otros defensores en jugadas parecidas.

1. Se toma el último frame del tracking de cada pase (hasta 0.5 s después de `pass_forward`), al receptor objetivo y al defensor más cercano (a 10 yardas o menos).
2. Modelo A (scikit-learn): estima las yardas esperadas del pase para la ofensiva. Un `HistGradientBoostingClassifier` da P(completo) y un `HistGradientBoostingRegressor`, entrenado solo con pases completos, da las yardas si se completa.
3. Modelo B: un `RandomForestRegressor` usado como muestreador genera 30 posiciones y velocidades de fantasma a partir de las variables de la jugada sin el defensor real.
4. `delta = esperado con fantasmas - esperado con el defensor real`. Positivo significa que el defensor limitó el pase mejor que el promedio.
5. Se agrega por defensor, equipo, posición y tipo de cobertura (man o zone). El ranking exige mínimo 15 pases por defensor.

Validación: validación cruzada de 5 grupos por partido sobre 6626 pases. Cada pase y sus fantasmas se predicen con modelos que no vieron su partido.
RMSE de yardas 9.06 (base 10.15) y Brier de P(completo) 0.184 (base 0.229).

Límites: el tracking de este dataset termina 0.5 s después del lanzamiento, así que no hay posición de captura y se evalúa al defensor en el momento del lanzamiento. El delta de cada defensor es ruidoso con 15 a 25 pases (consistencia entre mitades de sus pases: 0.24). Los hallazgos del análisis exploratorio están en `.kiro/steering/hallazgos.md`.

## Estructura

- `backend/precompute.py`: lee `data/tracking/` y genera `backend/capturas.csv` (una fila por pase).
- `backend/modelo.py`: modelos A y B y cálculo del delta.
- `backend/main.py`: API FastAPI. Calcula los modelos al arrancar desde `capturas.csv`. Rutas y JSON en `backend/contrato_api.md`.
- `backend/eda/`: análisis exploratorio y `defensores_resultados.csv` (intercepciones, pases defendidos, etc., usado como boxscore).
- `dashboard/`: React + TypeScript + Tailwind 3 + Recharts (Vite). Pantallas: ranking, perfil de defensor, buscador y animación de jugadas con fantasmas, equipos y metodología.
- `data/`: datos originales del Big Data Bowl (solo lectura; ver `data/README.md`).

## Requisitos

- Python 3.12 y las dependencias de `requirements.txt` (FastAPI, Uvicorn, Pydantic, pandas, numpy, scikit-learn).
- Node 22 y npm, para el dashboard (las versiones están fijadas en `dashboard/package-lock.json`).

## Instalación

Desde la raíz del repositorio:

```
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd dashboard && npm install && cd ..
```

En Windows usa `.venv\Scripts\pip` y `.venv\Scripts\uvicorn` en lugar de `.venv/bin/...`.

## Ejecución

Un solo servidor, con la API y el dashboard en la misma URL:

```
cd dashboard && npm run build && cd ..
.venv/bin/uvicorn backend.main:app --port 8000
```

Abre `http://localhost:8000`. Al arrancar, la API calcula los modelos (~20 s). Mientras tanto `/health` responde `ok` y las rutas `/api` responden 503; el dashboard reintenta solo.

Modo desarrollo, con dos procesos (Vite hace proxy de `/api` a `localhost:8000`):

```
.venv/bin/uvicorn backend.main:app --port 8000 --reload
cd dashboard && npm run dev
```

## Reproducir los resultados

- Métricas y ranking de los modelos, sin API: `.venv/bin/python -m backend.modelo` (~20 s). Los resultados son deterministas.
- Regenerar `backend/capturas.csv` desde el tracking (~130 s, solo hace falta si cambia la extracción): `.venv/bin/python backend/precompute.py`. El CSV ya está versionado.
- Análisis exploratorio: `.venv/bin/python backend/eda/analisis_inicial.py` y `backend/eda/resultados_defensivos.py`. Sus salidas están en `backend/eda/*.txt` y `*.csv`.
- Verificar el frontend: `cd dashboard && npm run build`.
