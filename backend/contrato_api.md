# Contrato de la API (editar solo Samuel)

Todas las rutas bajo `/api`. El frontend las llama sin diagonal inicial: `fetch('api/defenders')`.
Borrador. Si cambia, actualizar aquí primero.

## GET api/defenders
Query opcionales: `position`, `team`, `coverage` (man|zone), `min_plays` (default 15), `sort` (default delta_medio).
Respuesta: lista de
```json
{"nflId": 123, "nombre": "Jaire Alexander", "equipo": "GB", "posicion": "CB",
 "plays": 25, "delta_total": 12.4, "delta_medio": 0.50, "error_estandar": 0.21,
 "delta_man": 0.8, "delta_zone": 0.2}
```
`delta` está en yardas esperadas concedidas por pase objetivo; positivo = mejor que el fantasma.
`plays` = pases en los que fue el defensor más cercano al receptor. Extra opcional: `boxscore` con `intercepciones`, `pases_defendidos`, `fumbles_forzados`, `tackles_completos` (de backend/eda/defensores_resultados.csv).

## GET api/defenders/{nflId}
```json
{"defensor": { ...mismo objeto que arriba... },
 "por_semana": [{"semana": 1, "plays": 3, "delta_medio": 0.4}],
 "mejores": [Jugada], "peores": [Jugada]}
```
Jugada: `{"gameId": 1, "playId": 2, "semana": 1, "descripcion": "...", "delta": 3.1, "cobertura": "Cover-3"}`

## GET api/teams
```json
[{"equipo": "CHI", "plays": 200, "delta_medio": 0.3, "yardas_esperadas_concedidas": 4.1}]
```

## GET api/plays/{gameId}/{playId}
Momento del lanzamiento (último frame del tracking). Coordenadas normalizadas (ataque hacia x creciente), en yardas.
```json
{"gameId": 1, "playId": 2, "descripcion": "...", "cobertura": "Cover-3", "resultado": "C",
 "receptor": {"nombre": "...", "x": 50.0, "y": 20.0, "s": 4.1, "dir": 90},
 "defensor": {"nflId": 123, "nombre": "...", "x": 52.0, "y": 21.0, "s": 3.2, "dir": 270},
 "qb": {"x": 40.0, "y": 26.0},
 "fantasmas": [{"x": 51.0, "y": 19.5, "peso": 0.03}],
 "valor_real_yds": 8.0, "p_completo_real": 0.62, "esperado_real": 5.0,
 "p_completo_fantasma": 0.58, "esperado_fantasma": 4.2, "delta": -0.8,
 "linea_scrimmage_x": 45.0, "primer_down_x": 55.0}
```

## GET api/metodologia
`{"rmse_yardas": 0.0, "brier_completo": 0.0, "n_pases": 0, "min_plays": 15, "max_dist_defensor": 10,
 "validacion": "leave-one-out", "momento": "lanzamiento (0.5 s tras pass_forward)"}`

## GET api/defenders/{nflId}/informe (opcional, IA)
`{"texto": "...", "generado_con_ia": true}`. Si la IA falla: plantilla con `generado_con_ia: false`.

## GET /health
`{"status": "ok"}` (ya existe)
