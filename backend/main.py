"""API de la app. Ejecuta: .venv/bin/uvicorn backend.main:app --reload
T4: al arrancar calcula los modelos (backend/modelo.py) sobre backend/capturas.csv en un hilo (~50 s)
y une el boxscore de backend/eda/defensores_resultados.csv. No escribe archivos.
Mientras calcula, /health responde ok y las rutas /api responden 503.
Formato de cada ruta: backend/contrato_api.md (fuente de verdad con el frontend).
"""
import threading
from pathlib import Path
from typing import Literal
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from . import modelo
app = FastAPI(title="Hackathon NFL UNAM")
BOX_CSV = Path(__file__).resolve().parent / "eda" / "defensores_resultados.csv"
MIN_PLAYS = 15
MAX_DIST = 10
# ---------- Modelos de respuesta (reflejan el contrato) ----------
class Boxscore(BaseModel):
    intercepciones: int
    pases_defendidos: int
    fumbles_forzados: int
    tackles_completos: int
class Defensor(BaseModel):
    nflId: int
    nombre: str
    equipo: str
    posicion: str
    plays: int
    delta_total: float
    delta_medio: float
    error_estandar: float
    delta_man: float
    delta_zone: float
    boxscore: Boxscore | None = None
class Semana(BaseModel):
    semana: int
    plays: int
    delta_medio: float
class JugadaResumen(BaseModel):
    gameId: int
    playId: int
    semana: int
    descripcion: str
    delta: float
    cobertura: str
class PerfilDefensor(BaseModel):
    defensor: Defensor
    por_semana: list[Semana]
    mejores: list[JugadaResumen]
    peores: list[JugadaResumen]
class Equipo(BaseModel):
    equipo: str
    plays: int
    delta_medio: float
    yardas_esperadas_concedidas: float
class Receptor(BaseModel):
    nombre: str
    x: float
    y: float
    s: float
    dir: float
class DefensorEnJugada(BaseModel):
    nflId: int
    nombre: str
    x: float
    y: float
    s: float
    dir: float
class PuntoXY(BaseModel):
    x: float
    y: float
class Fantasma(BaseModel):
    x: float
    y: float
    peso: float
class Jugada(BaseModel):
    gameId: int
    playId: int
    descripcion: str
    cobertura: str
    resultado: Literal["C", "I", "IN"]
    receptor: Receptor
    defensor: DefensorEnJugada
    qb: PuntoXY
    fantasmas: list[Fantasma]
    valor_real_yds: float
    p_completo_real: float
    esperado_real: float
    p_completo_fantasma: float
    esperado_fantasma: float
    delta: float
    linea_scrimmage_x: float
    primer_down_x: float
class Metodologia(BaseModel):
    rmse_yardas: float
    brier_completo: float
    n_pases: int
    min_plays: int
    max_dist_defensor: int
    validacion: str
    momento: str
class Informe(BaseModel):
    texto: str
    generado_con_ia: bool
# ---------- Estado calculado al arrancar ----------
class Estado:
    listo = False
    error: str | None = None
    modelo = None
    res: pd.DataFrame
    defensores: dict[int, dict]
    por_semana: dict[int, list[dict]]
    equipos: list[dict]
    metodologia: dict
    indice: dict[tuple[int, int], int]
E = Estado()
def _stats(g: pd.DataFrame) -> dict:
    n = len(g)
    se = float(g["delta"].std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    return {"plays": n, "delta_total": float(g["delta"].sum()),
            "delta_medio": float(g["delta"].mean()), "error_estandar": se}
def _calcular() -> None:
    m, res, met = modelo.correr()
    res = res.reset_index(drop=True)
    box = pd.read_csv(BOX_CSV).set_index("nflId")
    defensores, por_semana = {}, {}
    for did, g in res.groupby("defensor_id"):
        did = int(did)
        st = _stats(g)
        for t, clave in (("Man", "man"), ("Zone", "zone")):
            sub = g[g["tipo_cobertura"] == t]
            st[f"delta_{clave}"] = float(sub["delta"].mean()) if len(sub) else 0.0
        b = None
        if did in box.index:
            r = box.loc[did]
            b = {"intercepciones": int(r["intercepciones"]), "pases_defendidos": int(r["incompletos_defendidos"]),
                 "fumbles_forzados": int(r["fumbles_forzados"]), "tackles_completos": int(r["completos_tacleados"])}
        defensores[did] = {
            "nflId": did, "nombre": str(g["defensor_nombre"].iloc[0]),
            "equipo": str(g["equipo_defensa"].mode().iloc[0]), "posicion": str(g["defensor_posicion"].iloc[0]),
            **st, "boxscore": b}
        por_semana[did] = [{"semana": int(s), "plays": len(x), "delta_medio": float(x["delta"].mean())}
                           for s, x in g.groupby("semana")]
    E.defensores, E.por_semana = defensores, por_semana
    E.equipos = [{"equipo": str(t), "plays": len(g), "delta_medio": float(g["delta"].mean()),
                  "yardas_esperadas_concedidas": float(g["esperado_real"].mean())}
                 for t, g in res.groupby("equipo_defensa")]
    E.metodologia = {"rmse_yardas": met["rmse_yardas"], "brier_completo": met["brier_completo"],
                     "n_pases": met["n_pases"], "min_plays": MIN_PLAYS, "max_dist_defensor": MAX_DIST,
                     "validacion": "leave-one-out", "momento": "lanzamiento (0.5 s tras pass_forward)"}
    E.indice = {(int(a), int(b)): i for i, (a, b) in enumerate(zip(res["gameId"], res["playId"]))}
    E.modelo, E.res = m, res
    E.listo = True
def _arrancar() -> None:
    try:
        _calcular()
    except Exception as e:  # se informa en las rutas /api
        E.error = repr(e)
@app.on_event("startup")
def al_arrancar() -> None:
    threading.Thread(target=_arrancar, daemon=True).start()
def _listo() -> None:
    if not E.listo:
        raise HTTPException(503, f"Error al calcular: {E.error}" if E.error else "Calculando modelos, intenta en unos segundos")
# ---------- Rutas ----------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
# Campos por los que se puede ordenar el ranking (siempre de mayor a menor).
CAMPOS_ORDEN = {"delta_medio", "delta_total", "error_estandar", "delta_man", "delta_zone", "plays"}
@app.get("/api/defenders", response_model=list[Defensor])
def listar_defensores(
    position: str | None = None,
    team: str | None = None,
    coverage: Literal["man", "zone"] | None = None,
    min_plays: int = Query(15, ge=0),
    sort: str = "delta_medio",
) -> list[dict]:
    _listo()
    if sort not in CAMPOS_ORDEN:
        raise HTTPException(422, f"sort debe ser uno de: {sorted(CAMPOS_ORDEN)}")
    filas = []
    for d in E.defensores.values():
        fila = dict(d)
        if coverage:  # con filtro de cobertura, plays y delta son los de esa cobertura
            t = "Man" if coverage == "man" else "Zone"
            g = E.res[(E.res["defensor_id"] == d["nflId"]) & (E.res["tipo_cobertura"] == t)]
            if len(g) == 0:
                continue
            fila.update(_stats(g))
        if fila["plays"] < min_plays:
            continue
        if position and d["posicion"].upper() != position.upper():
            continue
        if team and d["equipo"].upper() != team.upper():
            continue
        filas.append(fila)
    return sorted(filas, key=lambda f: f[sort], reverse=True)
@app.get("/api/defenders/{nfl_id}/informe", response_model=Informe)
def informe_defensor(nfl_id: int) -> dict:
    # Plantilla sin IA. T8 (opcional) intentará primero con Bedrock.
    _listo()
    d = E.defensores.get(nfl_id)
    if d is None:
        raise HTTPException(404, "Defensor no encontrado")
    signo = "mejor" if d["delta_medio"] >= 0 else "peor"
    texto = (
        f"{d['nombre']} ({d['posicion']}, {d['equipo']}) tuvo {d['plays']} pases como defensor más cercano. "
        f"Concedió en promedio {abs(d['delta_medio']):.2f} yardas esperadas {'menos' if d['delta_medio'] >= 0 else 'más'} "
        f"que un defensor promedio en las mismas jugadas ({signo} que el fantasma)."
    )
    return {"texto": texto, "generado_con_ia": False}
def _resumen(r) -> dict:
    return {"gameId": int(r.gameId), "playId": int(r.playId), "semana": int(r.semana),
            "descripcion": str(r.descripcion), "delta": float(r.delta),
            "cobertura": "" if pd.isna(r.cobertura) else str(r.cobertura)}
@app.get("/api/defenders/{nfl_id}", response_model=PerfilDefensor)
def perfil_defensor(nfl_id: int) -> dict:
    _listo()
    d = E.defensores.get(nfl_id)
    if d is None:
        raise HTTPException(404, "Defensor no encontrado")
    g = E.res[E.res["defensor_id"] == nfl_id].sort_values("delta", ascending=False)
    mejores = [_resumen(r) for r in g.head(5).itertuples()]
    peores = [_resumen(r) for r in g.tail(5).iloc[::-1].itertuples()]
    return {"defensor": d, "por_semana": E.por_semana[nfl_id], "mejores": mejores, "peores": peores}
@app.get("/api/teams", response_model=list[Equipo])
def listar_equipos() -> list[dict]:
    _listo()
    return E.equipos
@app.get("/api/plays/{game_id}/{play_id}", response_model=Jugada)
def ver_jugada(game_id: int, play_id: int) -> dict:
    _listo()
    i = E.indice.get((game_id, play_id))
    if i is None:
        raise HTTPException(404, "Jugada no encontrada")
    r = E.modelo.d.iloc[i]
    o = E.res.iloc[i]
    return {
        "gameId": game_id, "playId": play_id, "descripcion": str(r["descripcion"]),
        "cobertura": "" if pd.isna(r["cobertura"]) else str(r["cobertura"]), "resultado": str(r["resultado"]),
        "receptor": {"nombre": str(r["receptor_nombre"]), "x": float(r["receptor_x"]), "y": float(r["receptor_y"]),
                     "s": float(r["receptor_s"]), "dir": float(r["receptor_dir"])},
        "defensor": {"nflId": int(r["defensor_id"]), "nombre": str(r["defensor_nombre"]),
                     "x": float(r["defensor_x"]), "y": float(r["defensor_y"]),
                     "s": float(r["defensor_s"]), "dir": float(r["defensor_dir"])},
        "qb": {"x": float(r["qb_x"]), "y": float(r["qb_y"])},
        "fantasmas": E.modelo.fantasmas_jugada(i),
        "valor_real_yds": float(r["valor"]), "p_completo_real": float(o["p_completo_real"]),
        "esperado_real": float(o["esperado_real"]), "p_completo_fantasma": float(o["p_completo_fantasma"]),
        "esperado_fantasma": float(o["esperado_fantasma"]), "delta": float(o["delta"]),
        "linea_scrimmage_x": float(r["linea_scrimmage_x"]),
        "primer_down_x": float(r["linea_scrimmage_x"] + r["yardas_por_jugar"]),
    }
@app.get("/api/metodologia", response_model=Metodologia)
def metodologia() -> dict:
    _listo()
    return E.metodologia
# Sirve el build del dashboard en la misma URL y puerto que la API (al final, para no tapar /api ni /health).
_DIST = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
if _DIST.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="dashboard")
