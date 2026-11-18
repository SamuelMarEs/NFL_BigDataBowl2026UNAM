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

### Windows (PowerShell)

Verifica el entorno con `.\.hackathon\setup.cmd --check`.

En Windows, Node está en `.hackathon\.tools\node` (sin `bin`). PowerShell suele bloquear `npm.ps1`
("la ejecución de scripts está deshabilitada en este sistema"); para evitarlo usa `npm.cmd` en lugar de `npm`,
o corre los comandos desde `cmd`.

```
# Terminal 1 (raíz del proyecto): API
.venv\Scripts\uvicorn backend.main:app --port 8000

# Terminal 2: dashboard
$env:Path = "$PWD\.hackathon\.tools\node;$env:Path"
cd dashboard
npm.cmd install   # solo si no existe node_modules
npm.cmd run dev
```

Para el modo de un solo servidor, usa `npm.cmd run build` en `dashboard` y luego el comando de la Terminal 1.

Si uvicorn falla con `[Errno 10048] ... solo se permite un uso de cada dirección de socket`, ya hay otro proceso
en el puerto 8000 (por ejemplo, una API anterior que sigue corriendo con código viejo). Búscalo y ciérralo:

```
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
Stop-Process -Id <PID>
```

### Notas

- Al arrancar, la API calcula los modelos (~50 s). Mientras tanto `/health` responde `ok` y las rutas `/api`
  responden 503; el dashboard funciona cuando termina.
- `backend/capturas.csv` ya está versionado. Solo hace falta regenerarlo si cambia la lógica de extracción:
  `.venv/bin/python backend/precompute.py` (~130 s, lee `data/tracking/`).
- En Windows usa `.venv\Scripts\uvicorn` y `.venv\Scripts\python` en lugar de `.venv/bin/...` (ver la sección Windows).
- La IA es opcional (ver la sección siguiente). La app funciona completa sin ella.
- Si el dashboard se abre mientras la API calcula, muestra "Cargando…" y reintenta solo cada 3 s.

## IA opcional (informe por defensor con Amazon Bedrock)
`GET api/defenders/{nflId}/informe` redacta un párrafo en español para coaches y reclutadores con Amazon Nova
(Bedrock) mediante Strands Agents (`backend/informe.py`). El modelo solo recibe las cifras del defensor (delta,
error estándar, man/zone, boxscore) y se le pide no inventar datos. La respuesta es
`{"texto": "...", "generado_con_ia": true|false}`.

Si la IA no está disponible (sin llaves, llaves caducadas, sin acceso al modelo, sin red o más de 20 s de espera),
la API devuelve una plantilla con las mismas cifras y `generado_con_ia: false`. La app nunca depende de la IA.

### Activarla en local
1. Copia `.env.example` a `.env` en la raíz y pega las llaves temporales del workshop
   (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`). Valen unas horas. `.env` no se versiona
   ni entra al .zip de entrega.
   Alternativa: exporta las tres variables en la misma terminal donde arrancas uvicorn
   (`export AWS_ACCESS_KEY_ID=...`). No valen para otras terminales.
2. Arranca la API (`.venv/bin/uvicorn backend.main:app --port 8000`) y espera a que termine de calcular (~50 s).
3. Prueba: `curl localhost:8000/api/defenders/<nflId>/informe`. Con `generado_con_ia: true` la IA funciona.

Variables opcionales: `AWS_REGION` (por defecto `us-east-1`) y `BEDROCK_MODEL_ID` (por defecto
`us.amazon.nova-pro-v1:0`). El código nunca lee ni escribe las llaves; boto3 las toma del entorno.
Si las llaves caducan, pega nuevas y reinicia la API. Cada informe generado con IA se guarda en memoria hasta reiniciar.

### En AWS
No se configura nada: el hosting define `BEDROCK_MODEL_ID` y el rol de la tarea firma las llamadas.

### Pendiente
El dashboard todavía no muestra el informe. Hace falta un bloque en el perfil del defensor que consuma
`fetch('api/defenders/' + id + '/informe')`.

## Entrega

```
sh .hackathon/setup.sh --entregar
```
