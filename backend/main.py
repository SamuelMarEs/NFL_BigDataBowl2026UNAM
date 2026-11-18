"""API de la app. Ejecuta: .venv/bin/uvicorn backend.main:app --reload
T4: al arrancar calcula los modelos (backend/modelo.py) sobre backend/capturas.csv en un hilo (~50 s)
y une el boxscore de backend/eda/defensores_resultados.csv. No escribe archivos.
Mientras calcula, /health responde ok y las rutas /api responden 503.
Formato de cada ruta: backend/contrato_api.md (fuente de verdad con el frontend).
"""
import os
import threading
from pathlib import Path
from functools import lru_cache
from typing import Literal
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


def cargar_env():
    f = Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


cargar_env()
from . import informe, modelo  # noqa: E402
from .precompute import normalizar  # noqa: E402
DATA = Path(__file__).resolve().parent.parent / "data"
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
class JugadorTray(BaseModel):
    nflId: int
    nombre: str
    equipo: str
    lado: Literal["ataque", "defensa"]
    posicion: str
    rol: Literal["qb", "receptor", "defensor", "otro"]
    x: list[float]
    y: list[float]
class Trayectoria(BaseModel):
    gameId: int
    playId: int
    equipo_ataque: str
    equipo_defensa: str
    frame_snap: int
    frame_lanzamiento: int
    n_frames: int
    fps: int
    balon: list[PuntoXY]
    jugadores: list[JugadorTray]
class Partido(BaseModel):
    gameId: int
    semana: int
    local: str
    visitante: str
    jugadas: int
class JugadaLista(BaseModel):
    gameId: int
    playId: int
    semana: int
    local: str
    visitante: str
    cuarto: int
    reloj: str
    down: int
    yardas_por_jugar: int
    equipo_ataque: str
    equipo_defensa: str
    receptor: str
    defensor: str
    resultado: Literal["C", "I", "IN"]
    descripcion: str
    delta: float
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
    # Intenta Bedrock (backend/informe.py); si falla, plantilla con las mismas cifras.
    _listo()
    d = E.defensores.get(nfl_id)
    if d is None:
        raise HTTPException(404, "Defensor no encontrado")
    return informe.generar(d)


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
@lru_cache(maxsize=1)
def _catalogo() -> pd.DataFrame:
    """Una fila por jugada evaluada, con partido, cuarto, reloj y down (de games.csv y plays.csv)."""
    r = E.modelo.d
    juegos = pd.read_csv(DATA / "games.csv", usecols=["gameId", "homeTeamAbbr", "visitorTeamAbbr"])
    plays = pd.read_csv(DATA / "plays.csv", usecols=["gameId", "playId", "quarter", "gameClock", "possessionTeam"])
    c = r[["gameId", "playId", "semana", "resultado", "down", "yardas_por_jugar", "receptor_nombre",
           "defensor_nombre", "equipo_defensa", "descripcion"]].copy()
    c["delta"] = E.res["delta"].to_numpy()
    c = c.merge(juegos, on="gameId", how="left").merge(plays, on=["gameId", "playId"], how="left")
    return c.sort_values(["gameId", "quarter", "gameClock"], ascending=[True, True, False]).reset_index(drop=True)
@app.get("/api/games", response_model=list[Partido])
def listar_partidos() -> list[dict]:
    _listo()
    c = _catalogo()
    g = c.groupby(["gameId", "semana", "homeTeamAbbr", "visitorTeamAbbr"]).size().reset_index(name="n")
    g = g.sort_values(["semana", "gameId"])
    return [{"gameId": int(a.gameId), "semana": int(a.semana), "local": str(a.homeTeamAbbr),
             "visitante": str(a.visitorTeamAbbr), "jugadas": int(a.n)} for a in g.itertuples()]
@app.get("/api/plays", response_model=list[JugadaLista])
def buscar_jugadas(
    game_id: int | None = None,
    quarter: int | None = Query(None, ge=1, le=5),
    down: int | None = Query(None, ge=1, le=4),
    resultado: Literal["C", "I", "IN"] | None = None,
    team: str | None = None,
    defensor: str | None = None,
    limit: int = Query(200, ge=1, le=500),
) -> list[dict]:
    """Busca jugadas por partido, cuarto, down, resultado, equipo (ataque o defensa) o nombre de defensor/receptor."""
    _listo()
    c = _catalogo()
    if game_id is not None:
        c = c[c["gameId"] == game_id]
    if quarter is not None:
        c = c[c["quarter"] == quarter]
    if down is not None:
        c = c[c["down"] == down]
    if resultado:
        c = c[c["resultado"] == resultado]
    if team:
        c = c[(c["possessionTeam"] == team) | (c["equipo_defensa"] == team)]
    if defensor:
        q = defensor.lower()
        c = c[c["defensor_nombre"].str.lower().str.contains(q, regex=False) | c["receptor_nombre"].str.lower().str.contains(q, regex=False)]
    return [{"gameId": int(a.gameId), "playId": int(a.playId), "semana": int(a.semana), "local": str(a.homeTeamAbbr),
             "visitante": str(a.visitorTeamAbbr), "cuarto": int(a.quarter), "reloj": str(a.gameClock)[:5],
             "down": int(a.down), "yardas_por_jugar": int(a.yardas_por_jugar), "equipo_ataque": str(a.possessionTeam),
             "equipo_defensa": str(a.equipo_defensa), "receptor": str(a.receptor_nombre), "defensor": str(a.defensor_nombre),
             "resultado": str(a.resultado), "descripcion": str(a.descripcion), "delta": float(a.delta)}
            for a in c.head(limit).itertuples()]
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
@lru_cache(maxsize=1)
def _tablas_estaticas():
    d = Path(__file__).resolve().parent.parent / "data"
    pj = pd.read_csv(d / "players.csv", usecols=["nflId", "displayName", "officialPosition"]).set_index("nflId")
    return pj
@app.get("/api/plays/{game_id}/{play_id}/trayectoria", response_model=Trayectoria)
def trayectoria(game_id: int, play_id: int) -> dict:
    """Tracking completo de la jugada (del snap al ultimo frame), normalizado a ataque hacia x creciente."""
    _listo()
    i = E.indice.get((game_id, play_id))
    if i is None:
        raise HTTPException(404, "Jugada no encontrada")
    r = E.modelo.d.iloc[i]
    f = DATA / "tracking" / f"tracking_{game_id}.csv"
    if not f.exists():
        raise HTTPException(404, "Tracking no disponible")
    t = pd.read_csv(f)
    t = t[t["playId"] == play_id]
    if t.empty:
        raise HTTPException(404, "Tracking no disponible")
    t = normalizar(t, bool((t["playDirection"] == "left").iloc[0]))
    eventos = t[t["event"].isin(["ball_snap"])]["frameId"]
    ultimo = int(t["frameId"].max())
    snap = int(eventos.min()) if len(eventos) else int(t["frameId"].min())
    lanz = t[t["event"] == "pass_forward"]["frameId"]
    lanz = int(lanz.min()) if len(lanz) else ultimo
    t = t[(t["frameId"] >= snap) & (t["frameId"] <= ultimo)]
    frames = list(range(snap, ultimo + 1))
    pos = _tablas_estaticas()
    pff = pd.read_csv(DATA / "pffScoutingData.csv", usecols=["gameId", "playId", "nflId", "pff_role"])
    roles = pff[(pff["gameId"] == game_id) & (pff["playId"] == play_id)].set_index("nflId")["pff_role"]
    eq_def = str(r["equipo_defensa"])
    equipos = [e for e in t["team"].dropna().unique() if e != "football"]
    eq_atq = next((e for e in equipos if e != eq_def), "")
    b = t[t["team"] == "football"].set_index("frameId").reindex(frames).ffill().bfill()
    balon = [{"x": float(x), "y": float(y)} for x, y in zip(b["x"], b["y"])]
    jug = []
    for nid, g in t[t["team"] != "football"].dropna(subset=["nflId"]).groupby("nflId"):
        g = g.set_index("frameId").reindex(frames).ffill().bfill()
        nid = int(nid)
        rol = "otro"
        if nid == int(r["receptor_id"]):
            rol = "receptor"
        elif nid == int(r["defensor_id"]):
            rol = "defensor"
        elif roles.get(nid) == "Pass":
            rol = "qb"
        eq = str(g["team"].iloc[0])
        jug.append({"nflId": nid, "nombre": str(pos["displayName"].get(nid, "")), "equipo": eq,
                    "lado": "defensa" if eq == eq_def else "ataque",
                    "posicion": str(pos["officialPosition"].get(nid, "")), "rol": rol,
                    "x": [round(float(v), 2) for v in g["x"]], "y": [round(float(v), 2) for v in g["y"]]})
    return {"gameId": game_id, "playId": play_id, "equipo_ataque": eq_atq, "equipo_defensa": eq_def,
            "frame_snap": 0, "frame_lanzamiento": max(0, min(lanz - snap, len(frames) - 1)),
            "n_frames": len(frames), "fps": 10, "balon": balon, "jugadores": jug}
@app.get("/api/metodologia", response_model=Metodologia)
def metodologia() -> dict:
    _listo()
    return E.metodologia
# Sirve el build del dashboard en la misma URL y puerto que la API (al final, para no tapar /api ni /health).
_DIST = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
if _DIST.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="dashboard")
