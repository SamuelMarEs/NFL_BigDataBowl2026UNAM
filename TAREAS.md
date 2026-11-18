# Tareas y prompts para agentes Kiro

Reparto: **Samuel** = backend, integración y despliegue. **Keily** = frontend, definiciones de fútbol, contenido y demo.
Una sesión nueva por tarea. Los archivos de `.kiro/steering/` se cargan solos.
Añade a cada prompt: "Lee backend/contrato_api.md y .kiro/steering/hallazgos.md".
Marca [x] al terminar y apunta 1 o 2 líneas en la Bitácora de `.kiro/steering/proyecto.md`.

Cambio clave por el EDA: el tracking termina 0.5 s después del lanzamiento, así que evaluamos al defensor en el
momento del lanzamiento y no en la captura. Detalle en `.kiro/steering/hallazgos.md`.

## Samuel (backend)
- [x] **T1 API con datos de prueba.** "Implementa en backend/main.py los endpoints de backend/contrato_api.md con datos de prueba en backend/mock.py (20 defensores inventados y 3 jugadas con fantasmas). Solo FastAPI y Pydantic. No toques dashboard/. Verifica cada endpoint con curl y muéstrame las respuestas."
- [x] **T2 Tabla de pases.** "Crea backend/precompute.py. Para cada jugada con passResult C, I o IN (excluye 'No Play'), lee data/tracking/*.csv uno por uno y toma el último frame (pass_forward + 5 frames). Normaliza x, y, dir y o según playDirection (ver hallazgos.md). Identifica al receptor objetivo desde playDescription ('to X.Apellido') con la función resolver de backend/eda/resultados_defensivos.py, y al defensor más cercano a él (pff_role Coverage o Pass Rush). Guarda backend/capturas.csv con: gameId, playId, semana, resultado, valor (prePenaltyPlayResult si C, 0 si no), receptor y defensor (nflId, x, y, velocidad, dirección), dx/dy relativos, distancia, posición del QB, distancia a la línea de scrimmage, down, yardas por jugar, cobertura PFF, tipo de cobertura, defendersInBox. No modifiques data/. Ejecútalo, dime cuántas filas salieron, cuántas jugadas se descartaron por no resolver al receptor y cuánto tardó."
- [x] **T3 Modelos.** "Crea backend/modelo.py solo con numpy y pandas. (A) Valor esperado y P(completo) con kNN ponderado por distancia sobre variables estandarizadas. (B) Distribución del defensor fantasma (dx, dy, velocidad, dirección relativos al receptor) con kNN usando solo variables sin las del defensor real. Para cada pase calcula esperado_real y el promedio de 30 fantasmas muestreados; delta = esperado_fantasma - esperado_real. Evalúa con leave-one-out (excluye el pase evaluado de sus vecinos), sin división por semanas, y reporta RMSE de yardas y Brier de P(completo). Una intercepción vale 0 yardas. Debe correr en menos de 60 s."
- [ ] **T4 API real.** "Reemplaza el mock de backend/main.py por datos calculados al arrancar desde backend/capturas.csv con backend/modelo.py y backend/eda/defensores_resultados.csv (campo boxscore), respetando backend/contrato_api.md. No escribas archivos en disco."
- [ ] **T7 Cierre.** "Revisa las reglas del proyecto: rutas relativas, base './' y proxy /api en vite.config.ts, GET /health, sin dependencias nuevas. Ejecuta npm run build en dashboard/ y sh .hackathon/setup.sh --check y corrige lo que falle."
- [ ] **T8 IA opcional.** "Añade api/defenders/{id}/informe con Strands Agents y Bedrock Nova según las reglas del proyecto. Si falla, devuelve texto de plantilla con las mismas cifras."

## Keily (frontend y contenido)
- [x] **T0 Revisión de fútbol.** Las decisiones ya están en `.kiro/steering/hallazgos.md` (mínimo 15 pases, defensor a 10 yardas o menos, intercepción = 0). Queda decidir qué posiciones mostrar y revisar que `defensores_resultados.csv` coincida con lo que conoce de la temporada 2021.
- [ ] **T5 Ranking.** "En dashboard/src crea la pantalla de ranking de defensores (React, TypeScript, Tailwind 3). Consume fetch('api/defenders'). Tabla ordenable, filtros de posición, equipo, cobertura (man/zone) y mínimo de jugadas, barra visual del delta e indicador del error estándar. Sin dependencias nuevas. Ejecuta npm run build y corrige hasta que compile."
- [x] **T6a Perfil.** "Añade la pantalla de perfil de defensor: KPIs, barras man vs zone y tendencia por semana con Recharts, panel boxscore (intercepciones, pases defendidos, fumbles forzados) y listas de mejores y peores jugadas. Consume api/defenders/{id}. Verifica con npm run build."
- [x] **T6b Vista de jugada.** "Añade una vista de jugada con un campo de fútbol en SVG que muestre línea de scrimmage, primer down, QB, receptor, defensor real y los puntos fantasma (tamaño según peso), con el delta y las probabilidades de completo. Consume api/plays/{gameId}/{playId}. Rutas relativas sin diagonal inicial."
- [x] **T6c Equipos y metodología.** "Añade una pantalla de equipos (api/teams) y una de metodología (api/metodologia) que explique en lenguaje simple el método de fantasmas y avise que se evalúa al defensor en el momento del lanzamiento porque el tracking termina 0.5 s después."
- [ ] **T9 Demo.** Guion de 3 minutos: problema, idea del fantasma, ejemplo de jugada, ranking, límites del método, conclusión para coaches y reclutadores.

## Orden y dependencias
T1 -> (T5, T6 de Keily en paralelo con T2, T3 de Samuel) -> T4 -> T7 -> T8 si sobra tiempo.
T0 se hace en paralelo con T1.

