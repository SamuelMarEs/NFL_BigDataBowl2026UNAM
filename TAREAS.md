# Tareas y prompts para agentes Kiro

Una sesión nueva por tarea. Antes de pegar el prompt, el agente ya lee .kiro/steering/ automáticamente.
Añade a cada prompt: "Lee backend/contrato_api.md y .kiro/steering/hallazgos.md".
Marca [x] al terminar y apunta en la Bitácora de .kiro/steering/proyecto.md.

## Samuel
- [ ] T1 API con mock. "Implementa en backend/main.py los endpoints de backend/contrato_api.md con datos de prueba en backend/mock.py (20 defensores inventados). Solo FastAPI y Pydantic. No toques dashboard/. Verifica cada endpoint con curl y muéstrame las respuestas."
- [ ] T2 Tabla de capturas. "Crea backend/precompute.py: lee data/tracking/*.csv uno por uno, plays.csv, players.csv y pffScoutingData.csv con pandas. Para cada pase completo toma el frame del evento de captura definido en hallazgos.md, normaliza x, y y dir según playDirection, identifica al defensor más cercano al receptor y guarda backend/capturas.csv con: ids de jugada, semana, receptor, defensor, posición, equipo, dx/dy relativos, velocidad y dirección de ambos, distancia a la línea de primer down y a la zona de anotación, down, yardas por jugar, cobertura PFF y YAC real. No modifiques data/. Ejecútalo y dime cuántas filas salieron y cuánto tardó."
- [ ] T3 Modelos. "Crea backend/modelo.py solo con numpy y pandas. (1) Distribución de YAC dado las variables de la captura con kNN ponderado por distancia (variables estandarizadas). (2) Distribución de offsets del defensor fantasma dado las variables sin las del defensor. Para cada captura calcula yardas esperadas con el defensor real y el promedio con 30 fantasmas muestreados; delta = fantasma - real. Entrena con semanas de train y reporta RMSE de YAC en test. Debe correr en menos de 60 s."
- [ ] T4 API real. "Reemplaza el mock de backend/main.py por datos calculados al arrancar desde backend/capturas.csv con backend/modelo.py, respetando backend/contrato_api.md. No escribas archivos en disco."
- [ ] T7 Cierre. "Revisa las reglas del proyecto: rutas relativas, base './' y proxy /api en vite.config.ts, GET /health, sin dependencias nuevas. Ejecuta npm run build en dashboard/ y sh .hackathon/setup.sh --check y corrige lo que falle."
- [ ] T8 IA opcional. "Añade api/defenders/{id}/informe con Strands Agents y Bedrock Nova según las reglas del proyecto. Si falla, devuelve texto de plantilla con las mismas cifras."

## Compañera
- [ ] T0 Llenar .kiro/steering/hallazgos.md con los resultados del EDA.
- [ ] T5 Ranking. "En dashboard/src crea la pantalla de ranking de defensores (React, TypeScript, Tailwind 3). Consume fetch('api/defenders'). Tabla ordenable, filtros de posición, equipo, cobertura y mínimo de jugadas, barra visual del delta. Sin dependencias nuevas. Ejecuta npm run build y corrige hasta que compile."
- [ ] T6a Perfil. "Añade la pantalla de perfil de defensor: KPIs, barras man vs zone y tendencia por semana con Recharts, y listas de mejores y peores jugadas. Consume api/defenders/{id}. Verifica con npm run build."
- [ ] T6b Vista de jugada. "Añade una vista de jugada con un campo de fútbol en SVG que muestre línea de scrimmage, primer down, receptor, defensor real y los puntos fantasma (tamaño según peso). Consume api/plays/{gameId}/{playId}."
- [ ] T6c Equipos y metodología. "Añade una pantalla de equipos (api/teams) y una de metodología (api/metodologia) con explicación en lenguaje simple del método de fantasmas."
- [ ] T9 Demo. Guion de 3 minutos: problema, idea del fantasma, ejemplo de jugada, ranking, conclusión.

## Orden y dependencias
T1 -> (T5, T6 en paralelo con T2, T3) -> T4 -> T7 -> T8 si sobra tiempo.
