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
- T1 hecha (Samuel): backend/main.py sirve todos los endpoints del contrato con datos de prueba de backend/mock.py (20 defensores, 3 jugadas con 30 fantasmas); respuestas validadas con Pydantic.
- T6a/T6b/T6c hechas (Keily): dashboard/src con Perfil, VistaJugada (campo SVG), Equipos y Metodologia; navegación por hash (#/defensor/1001, #/jugada/g/p, #/equipos, #/metodologia). T5 (ranking) pendiente; se registra en App.tsx.
- Proxy '/api' -> http://localhost:8000 añadido en dashboard/vite.config.ts. npm run build OK; endpoints probados vía proxy con el mock. Rutas con datos: /api/plays/2021090900/97, /2021091200/410, /2021091900/1203; defensores 1001 a 1020.
- T1 decisiones: con coverage=man|zone el ranking devuelve en delta_medio el delta de esa cobertura; sort siempre de mayor a menor; /informe responde plantilla (generado_con_ia false). Contrato sin cambios.
- T2 hecha (Samuel): backend/precompute.py (~130 s) genera backend/capturas.csv con 6626 filas (C 4276, I 2182, IN 168). Descartes: 233 sin receptor en la descripción, 58 receptor no resuelto, 168 defensor a más de 10 yd, 20 sin QB/balón, 24 sin pass_forward. Receptor: "to X" o "intended for X". `resolver` está copiado (el módulo del EDA corre todo al importarse). Se añadieron columnas de nombre, equipo, posición, descripción y linea_scrimmage_x para T4.
- T2 hallazgo: el último frame es pass_forward + 5 solo en ~58% de jugadas (+4 en ~34%, +3 en ~8%); nunca más de 5. El momento de evaluación sigue siendo el último frame (≤0.5 s tras el lanzamiento).
- T3 hecha (Samuel): backend/modelo.py (clase `Modelo`, `correr()`; solo numpy/pandas) con kNN ponderado: A (k=40, 15 variables) y B (k=60, fantasmas dx, dy, vx, vy, 30 por pase). Leave-one-out sobre 6626 pases: RMSE yardas 9.32 (base media 10.15), Brier P(completo) 0.190 (base 0.229). Tarda ~47 s con 8 núcleos (límite 60 s); delta medio ≈ 0, 178 defensores con ≥15 pases.
- T3 nota para T4: `Modelo.fantasmas_jugada(i)` da x, y absolutos y peso (1/30) de cada fantasma; `ejecutar()` devuelve un DataFrame con esperado/p real y fantasma y delta por pase. Cuidado: el tiempo de arranque de la API será ~50 s si se calcula todo al iniciar.
- T0 hecha (Keily): defensores_resultados.csv revisado contra 2021 (sin duplicados ni nulos; 32 equipos; 176 de 190 INT atribuidas). Muestra parece semanas 1-8: Diggs 6 INT, Byard 4. Ranking muestra CB, FS, SS, ILB, MLB, OLB (por defecto CB/FS/SS); se excluyen DE, DT, NT, DB y RB.
- Proxy '/api' -> http://localhost:8000 en dashboard/vite.config.ts. Con el mock, npm run build OK (antes de T5) y endpoints probados vía proxy.
- T5 escrita (Keily): dashboard/src/Ranking.tsx con tabla ordenable, filtros (posición múltiple, equipo, cobertura, mínimo de pases), barra de delta con ±error estándar y aviso si EE >= |delta|; es la pantalla por defecto de #/defensor (App.tsx). Cobertura y min_plays van a la API; posición y equipo se filtran en el cliente. Falta correr npm run build (npm no estaba en el PATH de la sesión) y marcar T5 en TAREAS.md.
- Merge de main resuelto (commit 3d8b2bd): se conservó la Bitácora de Samuel (T1 a T3) y se reescribieron las líneas de Keily que se habían perdido en el conflicto.
- T5 verificada (Samuel): Ranking.tsx de Keily sin cambios; `npm run build` OK (Node está en .hackathon/.tools/node/bin, hay que añadirlo al PATH) y /api/defenders probado vía proxy de Vite (sin filtros, coverage=man&min_plays=20, min_plays=999 vacío). Nota: con coverage el mock cambia delta_medio pero no delta_total; decidir en T4.
- T4 hecha (Samuel): backend/main.py calcula al arrancar (modelo.correr() en un hilo, ~50 s) y ya no usa mock.py; /health responde de inmediato y las rutas /api dan 503 hasta que termina. Boxscore unido desde defensores_resultados.csv (pases_defendidos = incompletos_defendidos, tackles_completos = completos_tacleados). Con coverage=man|zone ahora cambian plays, delta_total, delta_medio y error_estandar (y min_plays se aplica a esa cobertura). primer_down_x = linea_scrimmage_x + yardas_por_jugar. Contrato sin cambios.
- T8 hecha (Samuel): backend/informe.py (Strands + BedrockModel; modelo de BEDROCK_MODEL_ID, región de AWS_REGION, timeouts 5/20 s, caché en memoria). main.py carga .env y /informe cae a plantilla con las mismas cifras si algo falla. Verificada la plantilla sin llaves (~4 s); la ruta con IA falta probarla con llaves. Contrato sin cambios.
- T7 hecha (Samuel): revisión de reglas OK (fetch('api/...') relativo, base './', proxy /api, /health, sin dependencias nuevas); `npm run build` y `setup.sh --check` pasan. Único cambio: backend/main.py monta dashboard/dist en "/" (si existe) para servir app y API en la misma URL/puerto; probado con uvicorn (/, assets, /health, /api).
