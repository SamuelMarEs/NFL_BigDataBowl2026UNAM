"""API de la app. Ejecuta: .venv/bin/uvicorn backend.main:app --reload

T1: responde con datos de prueba de backend/mock.py. T4 los cambia por datos reales.
Formato de cada ruta: backend/contrato_api.md (fuente de verdad con el frontend).
"""
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from . import mock

app = FastAPI(title="Hackathon NFL UNAM")


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
    if sort not in CAMPOS_ORDEN:
        raise HTTPException(422, f"sort debe ser uno de: {sorted(CAMPOS_ORDEN)}")
    filas = []
    for d in mock.DEFENSORES.values():
        if d["plays"] < min_plays:
            continue
        if position and d["posicion"].upper() != position.upper():
            continue
        if team and d["equipo"].upper() != team.upper():
            continue
        fila = dict(d)
        if coverage:  # con filtro de cobertura, delta_medio es el de esa cobertura
            fila["delta_medio"] = d["delta_man"] if coverage == "man" else d["delta_zone"]
        filas.append(fila)
    return sorted(filas, key=lambda f: f[sort], reverse=True)


@app.get("/api/defenders/{nfl_id}/informe", response_model=Informe)
def informe_defensor(nfl_id: int) -> dict:
    # Plantilla sin IA. T8 (opcional) intentará primero con Bedrock.
    d = mock.DEFENSORES.get(nfl_id)
    if d is None:
        raise HTTPException(404, "Defensor no encontrado")
    signo = "mejor" if d["delta_medio"] >= 0 else "peor"
    texto = (
        f"{d['nombre']} ({d['posicion']}, {d['equipo']}) tuvo {d['plays']} pases como defensor más cercano. "
        f"Concedió en promedio {abs(d['delta_medio']):.2f} yardas esperadas {'menos' if d['delta_medio'] >= 0 else 'más'} "
        f"que un defensor promedio en las mismas jugadas ({signo} que el fantasma)."
    )
    return {"texto": texto, "generado_con_ia": False}


@app.get("/api/defenders/{nfl_id}", response_model=PerfilDefensor)
def perfil_defensor(nfl_id: int) -> dict:
    d = mock.DEFENSORES.get(nfl_id)
    if d is None:
        raise HTTPException(404, "Defensor no encontrado")
    mejores, peores = mock.mejores_peores()
    return {"defensor": d, "por_semana": mock.POR_SEMANA[nfl_id], "mejores": mejores, "peores": peores}


@app.get("/api/teams", response_model=list[Equipo])
def listar_equipos() -> list[dict]:
    return mock.EQUIPOS


@app.get("/api/plays/{game_id}/{play_id}", response_model=Jugada)
def ver_jugada(game_id: int, play_id: int) -> dict:
    j = mock.JUGADAS.get((game_id, play_id))
    if j is None:
        raise HTTPException(404, "Jugada no encontrada")
    return j


@app.get("/api/metodologia", response_model=Metodologia)
def metodologia() -> dict:
    return mock.METODOLOGIA
