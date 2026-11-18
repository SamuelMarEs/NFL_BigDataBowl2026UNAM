# Contrato de la API (editar solo Samuel)

Todas las rutas bajo `/api`. El frontend las llama sin diagonal inicial: `fetch('api/defenders')`.
Borrador. Si cambia, actualizar aquí primero.

## GET api/defenders
Query opcionales: `position`, `team`, `coverage` (man|zone), `min_plays` (default 10), `sort` (default delta_medio).
Respuesta: lista de
```json
{"nflId": 123, "nombre": "Jaire Alexander", "equipo": "GB", "posicion": "CB",
 "plays": 25, "delta_total": 12.4, "delta_medio": 0.50, "error_estandar": 0.21,
 "delta_man": 0.8, "delta_zone": 0.2}
```
`delta` está en yardas esperadas; positivo = mejor que el fantasma.

## GET api/defenders/{nflId}
```json
{"defensor": { ...mismo objeto que arriba... },
 "por_semana": [{"semana": 1, "plays": 3, "delta_medio": 0.4}],
 "mejores": [Jugada], "peores": [Jugada]}
```
Jugada: `{"gameId": 1, "playId": 2, "semana": 1, "descripcion": "...", "delta": 3.1, "cobertura": "Cover-3"}`

## GET api/teams
```json
[{"equipo": "CHI", "plays": 200, "delta_medio": 0.3, "yardas_permitidas_yac": 4.1}]
```

## GET api/plays/{gameId}/{playId}
Para dibujar el campo. Coordenadas ya normalizadas (ataque hacia x creciente), en yardas.
```json
{"gameId": 1, "playId": 2, "descripcion": "...", "cobertura": "Cover-3",
 "receptor": {"x": 50.0, "y": 20.0, "s": 4.1, "dir": 90},
 "defensor": {"nflId": 123, "nombre": "...", "x": 52.0, "y": 21.0, "s": 3.2, "dir": 270},
 "fantasmas": [{"x": 51.0, "y": 19.5, "peso": 0.03}],
 "yac_real": 5, "esperado_real": 4.2, "esperado_fantasma": 5.0, "delta": 0.8,
 "linea_scrimmage_x": 45.0, "primer_down_x": 55.0}
```

## GET api/metodologia
`{"rmse_yac": 0.0, "n_capturas": 0, "semanas_train": [1,2,3,4,5,6], "semanas_test": [7,8]}`

## GET api/defenders/{nflId}/informe (opcional, IA)
`{"texto": "...", "generado_con_ia": true}`. Si la IA falla: plantilla con `generado_con_ia: false`.

## GET /health
`{"status": "ok"}` (ya existe)
