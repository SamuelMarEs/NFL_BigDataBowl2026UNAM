# Reglas del proyecto: NFL Ghosts

El hackathon terminó. Se eliminó todo lo del hackathon de Amazon (instalador, entrega, despliegue en AWS, IA con Bedrock). Ya no hay stack fijo.

## Dependencias
- Antes de instalar cualquier paquete, explicar a Samuel qué es y para qué se necesita, e instalar solo si lo aprueba.
- Python dentro de `.venv`. Las dependencias están en `requirements.txt` en la raíz (versiones fijas); si se agrega una, actualizar ese archivo.
- Instalada fuera del stack original: scikit-learn (modelos). Frontend: React 18, Vite 5, TypeScript, Tailwind 3 (sin sintaxis de Tailwind 4) y Recharts, fijados en `dashboard/package-lock.json`.
- Entorno local de esta máquina: el `.venv` apunta a Python y Node que viven en `.hackathon/.tools/` (carpeta ignorada por git, solo local). Node: `export PATH="$PWD/.hackathon/.tools/node/bin:$PATH"`. Instalar con `.hackathon/.tools/uv/uv pip install --python .venv/bin/python <paquete>`. No borrar `.hackathon/.tools/` sin antes recrear `.venv` y tener Node instalado en el sistema.

## Convenciones que se conservan
- `backend/main.py` expone `app` con `GET /health` y la API bajo `/api/...`; sirve `dashboard/dist` en la misma URL y puerto.
- El dashboard llama a la API con rutas relativas sin diagonal inicial (`fetch('api/...')`), nunca `localhost`. `vite.config.ts` conserva `base: './'` y el proxy de `/api`.
- `data/` es solo lectura. La API no escribe archivos en disco.
- `backend/contrato_api.md` es la fuente de verdad entre backend y frontend: se actualiza antes de cambiar la API.
- No hay llaves ni credenciales en el proyecto; no agregar ninguna al código.
