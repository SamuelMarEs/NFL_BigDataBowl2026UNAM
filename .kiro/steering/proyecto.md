# Contexto del proyecto (leer siempre)

## Objetivo
App para coaches y reclutadores que evalúa el desempeño de defensores en pase, inspirada en el paper
"NFL Ghosts" (Yurko, Nguyen, Pelechrinis; NFLghosts.pdf en la raíz). Datos: Big Data Bowl, temporada 2021 (ver data/README.md).

## Idea del método (adaptada a nuestros datos, solo numpy y pandas)
IMPORTANTE: el tracking de este dataset termina 5 frames (0.5 s) después de `pass_forward`. El momento de la
captura NO está en el tracking (solo 23 de 4620 pases completos tienen `pass_outcome_caught`). Por eso el paper
(que usa el momento de la captura) se adapta al momento del lanzamiento. Ver .kiro/steering/hallazgos.md.

1. Momento de evaluación: el último frame de tracking de cada pase (pass_forward + 5 frames). Se toma al receptor
   objetivo (nombre en playDescription, "to X.Apellido") y al defensor más cercano a él, solo si está a 10 yardas o menos.
2. Modelo A: resultado esperado del pase para la ofensiva dado el estado de la jugada. Valor = prePenaltyPlayResult si
   es completo, 0 si es incompleto o intercepción. Se estima con kNN ponderado (sin scikit-learn): da P(completo) y yardas esperadas.
   Variables: posición relativa receptor-defensor (dx, dy, distancia), velocidades, posición del receptor y del QB,
   distancia a la línea de scrimmage, down, yardas por jugar, cobertura PFF (man/zone), defendersInBox.
3. Modelo B: distribución del defensor "fantasma" (dx, dy relativos al receptor, velocidad y dirección) dado las
   variables de la jugada SIN las del defensor real. También kNN ponderado.
4. Se muestrean ~30 fantasmas, se recalcula el valor esperado con cada uno y se promedia.
5. `delta = esperado_fantasma - esperado_real` (yardas esperadas concedidas). Positivo = el defensor limitó mejor que el promedio.
6. Se agrega por defensor, equipo, posición y cobertura. Mínimo de jugadas por defensor: 15.
7. Complemento "boxscore" (de backend/eda/defensores_resultados.csv): intercepciones, pases defendidos, fumbles forzados, tackles.
Validación: leave-one-out (el pase evaluado se excluye de sus propios vecinos); reportar RMSE de yardas y Brier de P(completo). Sin división por semanas.

## Arquitectura
- `backend/precompute.py` (se corre una vez, local): lee data/tracking, genera `backend/capturas.csv` (una fila por pase objetivo, momento del lanzamiento). Se versiona ese CSV.
- `backend/modelo.py`: modelos kNN y delta. `backend/main.py`: FastAPI, calcula en memoria al arrancar desde capturas.csv.
- `backend/contrato_api.md`: endpoints y JSON. Es la única fuente de verdad entre backend y frontend.
- `dashboard/src/`: React + TS + Tailwind 3 + Recharts. Pantallas: ranking, perfil de defensor, vista de jugada (campo SVG con fantasmas), equipos, metodología.
- Sin dependencias nuevas, sin Docker, sin escribir archivos en runtime, `data/` solo lectura.

## Reparto (2 personas)
- Samuel (tú, técnico): backend/ (precompute, modelo, API), integración, despliegue.
- Keily (NFL): dashboard/src/, definiciones de fútbol, revisar que los rankings sean plausibles, textos, guion de demo.
- Cada quien edita solo su carpeta. El contrato lo edita Samuel; los cambios se piden a él.
- Ramas: `backend` (Samuel) y `frontend` (Keily), merge a `main` cada 30 a 40 min con la app corriendo.

## Reglas para agentes
- Una tarea por sesión. Lee este archivo, `hallazgos.md` y `backend/contrato_api.md` antes de empezar.
- Toca solo los archivos de tu tarea. Verifica con algo ejecutable (curl, pytest, npm run build) y muestra el resultado.
- Frontend: `fetch('api/...')` sin diagonal inicial; ninguna ruta absoluta ni localhost.
- Al terminar, añade 1 o 2 líneas en "Bitácora" abajo con lo que cambió o decidiste.

## Hechos verificados
- Eventos en tracking: ball_snap, pass_forward, pass_arrived, pass_outcome_caught, pass_outcome_incomplete, qb_sack, run, fumble, etc.
- Tracking: columnas gameId, playId, nflId, frameId, x, y, s, a, dis, o, dir, event, playDirection (left/right), team.
- Tracking termina 0.5 s tras pass_forward (verificado en 25 de 122 archivos: último frame = pass_forward + 5 en todos los pases).
- EDA en backend/eda/: analisis_inicial.py, resultados_defensivos.py y sus .txt/.csv (613 defensores con resultados atribuidos).
- 122 archivos de tracking (~811 MB): procesar uno a la vez.

## Bitácora
- EDA leído: se cambia el momento de evaluación de captura a lanzamiento (tracking truncado). Tareas actualizadas.
