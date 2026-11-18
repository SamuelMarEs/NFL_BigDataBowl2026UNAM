"""Datos de prueba (T1). Todo es inventado y determinista (semilla fija).

Se calcula al importar, en memoria. No lee ni escribe archivos.
En T4 este módulo se reemplaza por datos reales calculados desde capturas.csv.
"""
import numpy as np

_rng = np.random.default_rng(2021)

# (nflId, nombre, equipo, posicion)
_BASE = [
    (1001, "Marcus Hale", "GB", "CB"),
    (1002, "Darnell Price", "NE", "CB"),
    (1003, "Tyrese Boone", "TEN", "FS"),
    (1004, "Jalen Whitaker", "DAL", "CB"),
    (1005, "Cole Brannigan", "CHI", "SS"),
    (1006, "Andre Lacroix", "LAR", "CB"),
    (1007, "Devin Okafor", "BUF", "FS"),
    (1008, "Reggie Tolliver", "PIT", "OLB"),
    (1009, "Isaiah Montrose", "SF", "CB"),
    (1010, "Trevor Kingsley", "KC", "SS"),
    (1011, "Malik Deveraux", "MIA", "CB"),
    (1012, "Brandon Achebe", "NO", "ILB"),
    (1013, "Corey Winslow", "DEN", "CB"),
    (1014, "Terrell Ayers", "BAL", "FS"),
    (1015, "Quinn Hargrove", "SEA", "MLB"),
    (1016, "Xavier Delacroix", "PHI", "CB"),
    (1017, "Elijah Strand", "MIN", "SS"),
    (1018, "Dominic Farraday", "CLE", "CB"),
    (1019, "Hakeem Orsini", "LV", "OLB"),
    (1020, "Wesley Thornbury", "CHI", "CB"),
]

_COBERTURAS = ["Cover-3", "Cover-1", "Cover-2", "Quarters", "Cover-0"]


def _construir_defensores() -> dict[int, dict]:
    out = {}
    for nfl_id, nombre, equipo, pos in _BASE:
        plays = int(_rng.integers(15, 61))
        delta_medio = round(float(_rng.normal(0.0, 0.6)), 2)
        out[nfl_id] = {
            "nflId": nfl_id,
            "nombre": nombre,
            "equipo": equipo,
            "posicion": pos,
            "plays": plays,
            "delta_total": round(delta_medio * plays, 2),
            "delta_medio": delta_medio,
            "error_estandar": round(float(_rng.uniform(0.1, 0.45)), 2),
            "delta_man": round(delta_medio + float(_rng.normal(0, 0.3)), 2),
            "delta_zone": round(delta_medio + float(_rng.normal(0, 0.3)), 2),
            "boxscore": {
                "intercepciones": int(_rng.integers(0, 5)),
                "pases_defendidos": int(_rng.integers(0, 12)),
                "fumbles_forzados": int(_rng.integers(0, 3)),
                "tackles_completos": int(_rng.integers(2, 30)),
            },
        }
    return out


def _construir_por_semana(plays_total: int) -> list[dict]:
    semanas = sorted(int(s) for s in _rng.choice(np.arange(1, 19), size=6, replace=False))
    reparto = np.full(6, plays_total // 6)
    reparto[: plays_total % 6] += 1
    return [
        {"semana": s, "plays": int(p), "delta_medio": round(float(_rng.normal(0, 0.7)), 2)}
        for s, p in zip(semanas, reparto)
    ]


def _fantasmas(rx: float, ry: float, n: int = 30) -> list[dict]:
    """30 puntos alrededor del receptor. Los pesos suman 1."""
    pesos = _rng.dirichlet(np.ones(n))
    return [
        {
            "x": round(rx + float(_rng.normal(1.5, 1.2)), 2),
            "y": round(ry + float(_rng.normal(0.0, 1.5)), 2),
            "peso": round(float(p), 4),
        }
        for p in pesos
    ]


def _jugada(game_id, play_id, semana, desc, cob, resultado, valor, receptor, defensor_id,
            def_pos, qb, los_x, primer_x, p_real, e_real, p_fan, e_fan) -> dict:
    d = DEFENSORES[defensor_id]
    return {
        "gameId": game_id,
        "playId": play_id,
        "semana": semana,
        "descripcion": desc,
        "cobertura": cob,
        "resultado": resultado,
        "receptor": receptor,
        "defensor": {"nflId": defensor_id, "nombre": d["nombre"], **def_pos},
        "qb": qb,
        "fantasmas": _fantasmas(receptor["x"], receptor["y"]),
        "valor_real_yds": valor,
        "p_completo_real": p_real,
        "esperado_real": e_real,
        "p_completo_fantasma": p_fan,
        "esperado_fantasma": e_fan,
        "delta": round(e_fan - e_real, 2),
        "linea_scrimmage_x": los_x,
        "primer_down_x": primer_x,
    }


DEFENSORES: dict[int, dict] = _construir_defensores()
POR_SEMANA: dict[int, list[dict]] = {i: _construir_por_semana(d["plays"]) for i, d in DEFENSORES.items()}

JUGADAS: dict[tuple[int, int], dict] = {}
for _j in (
    _jugada(2021090900, 97, 1, "(13:20) T.Brady pass short right to R.Gronkowski for 8 yards (M.Hale).",
            "Cover-3", "C", 8.0,
            {"nombre": "R.Gronkowski", "x": 50.0, "y": 20.0, "s": 4.1, "dir": 90},
            1001, {"x": 52.0, "y": 21.0, "s": 3.2, "dir": 270},
            {"x": 40.0, "y": 26.0}, 45.0, 55.0, 0.62, 5.0, 0.58, 4.2),
    _jugada(2021091200, 410, 1, "(9:41) A.Rodgers pass deep left to D.Adams is incomplete. Defended by D.Price.",
            "Cover-1", "I", 0.0,
            {"nombre": "D.Adams", "x": 62.0, "y": 14.0, "s": 7.5, "dir": 80},
            1002, {"x": 63.0, "y": 14.8, "s": 7.0, "dir": 85},
            {"x": 41.0, "y": 27.0}, 38.0, 48.0, 0.31, 3.9, 0.44, 5.6),
    _jugada(2021091900, 1203, 2, "(2:15) D.Prescott pass short middle to C.Lamb for 22 yards (J.Whitaker).",
            "Quarters", "C", 22.0,
            {"nombre": "C.Lamb", "x": 71.0, "y": 30.0, "s": 5.0, "dir": 100},
            1004, {"x": 69.5, "y": 29.0, "s": 4.4, "dir": 120},
            {"x": 58.0, "y": 26.5}, 60.0, 70.0, 0.74, 9.8, 0.66, 7.3),
):
    JUGADAS[(_j["gameId"], _j["playId"])] = _j

# Cada defensor muestra estas 3 jugadas como mejores/peores (solo para prueba).
_ORDENADAS = sorted(JUGADAS.values(), key=lambda j: j["delta"], reverse=True)

METODOLOGIA = {
    "rmse_yardas": 0.0,
    "brier_completo": 0.0,
    "n_pases": 0,
    "min_plays": 15,
    "max_dist_defensor": 10,
    "validacion": "leave-one-out",
    "momento": "lanzamiento (0.5 s tras pass_forward)",
}


def jugada_resumen(j: dict) -> dict:
    return {k: j[k] for k in ("gameId", "playId", "semana", "descripcion", "delta", "cobertura")}


def mejores_peores() -> tuple[list[dict], list[dict]]:
    mejores = [jugada_resumen(j) for j in _ORDENADAS[:2]]
    peores = [jugada_resumen(j) for j in _ORDENADAS[::-1][:2]]
    return mejores, peores


def _construir_equipos() -> list[dict]:
    """Agrega los defensores por equipo (promedio ponderado por plays)."""
    acum: dict[str, dict] = {}
    for d in DEFENSORES.values():
        e = acum.setdefault(d["equipo"], {"plays": 0, "suma": 0.0})
        e["plays"] += d["plays"]
        e["suma"] += d["delta_total"]
    return [
        {
            "equipo": eq,
            "plays": v["plays"],
            "delta_medio": round(v["suma"] / v["plays"], 2),
            "yardas_esperadas_concedidas": round(float(_rng.uniform(3.0, 6.0)), 2),
        }
        for eq, v in sorted(acum.items())
    ]


EQUIPOS: list[dict] = _construir_equipos()
