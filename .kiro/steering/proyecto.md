# Contexto del proyecto (leer siempre)

## Objetivo
App para coaches y reclutadores que evalúa el desempeño de defensores en pase, inspirada en el paper
"NFL Ghosts" (Yurko, Nguyen, Pelechrinis; NFLghosts.pdf en la raíz). Datos: Big Data Bowl, temporada 2021 (ver data/README.md).

## Idea del método (versión simplificada, solo numpy y pandas)
1. En el momento de la captura (evento `pass_outcome_caught` en el tracking) se toma al receptor y al defensor más cercano.
2. Modelo A: distribución de yardas después de la captura (YAC) dadas las características de la jugada,
   con kNN ponderado (sin scikit-learn). Da yardas esperadas y P(primer down).
3. Modelo B: distribución de dónde estaría un defensor "fantasma" (promedio) en situaciones parecidas,
   también con kNN ponderado, SIN usar las variables del defensor real.
4. Se muestrean ~30 fantasmas, se recalcula el valor esperado y se promedia.
5. `delta = esperado_fantasma - esperado_real` (yardas esperadas). Positivo = el defensor lo hizo mejor que el promedio.
6. Se agrega por defensor, equipo, posición y cobertura (man/zone de PFF). Mínimo de jugadas por defensor: ver hallazgos.md.
Validación: entrenar con las primeras semanas, probar con las últimas, reportar RMSE de YAC.

## Arquitectura
- `backend/precompute.py` (se corre una vez, local): lee data/tracking, genera `backend/capturas.csv` (una fila por captura). Se versiona ese CSV.
- `backend/modelo.py`: modelos kNN y delta. `backend/main.py`: FastAPI, calcula en memoria al arrancar desde capturas.csv.
- `backend/contrato_api.md`: endpoints y JSON. Es la única fuente de verdad entre backend y frontend.
- `dashboard/src/`: React + TS + Tailwind 3 + Recharts. Pantallas: ranking, perfil de defensor, vista de jugada (campo SVG con fantasmas), equipos, metodología.
- Sin dependencias nuevas, sin Docker, sin escribir archivos en runtime, `data/` solo lectura.

## Reparto (2 personas)
- Samuel (técnico): backend/ (precompute, modelo, API), integración, despliegue.
- Compañera (NFL): dashboard/src/, definiciones de fútbol, revisar que los rankings sean plausibles, textos, guion de demo.
- Cada quien edita solo su carpeta. El contrato lo edita Samuel; los cambios se piden a él.
- Ramas: `backend` y `frontend`, merge a `main` cada 30 a 40 min con la app corriendo.

## Reglas para agentes
- Una tarea por sesión. Lee este archivo, `hallazgos.md` y `backend/contrato_api.md` antes de empezar.
- Toca solo los archivos de tu tarea. Verifica con algo ejecutable (curl, pytest, npm run build) y muestra el resultado.
- Frontend: `fetch('api/...')` sin diagonal inicial; ninguna ruta absoluta ni localhost.
- Al terminar, añade 1 o 2 líneas en "Bitácora" abajo con lo que cambió o decidiste.

## Hechos verificados
- Eventos en tracking: ball_snap, pass_forward, pass_arrived, pass_outcome_caught, pass_outcome_incomplete, qb_sack, run, fumble, etc.
- Tracking: columnas gameId, playId, nflId, frameId, x, y, s, a, dis, o, dir, event, playDirection (left/right), team.
- 122 archivos de tracking (~811 MB): procesar uno a la vez.

## Bitácora
- (vacía)
