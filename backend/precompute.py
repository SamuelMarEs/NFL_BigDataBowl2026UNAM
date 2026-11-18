"""Genera backend/capturas.csv: una fila por pase objetivo, en el momento del lanzamiento.

Momento de evaluacion: ultimo frame de tracking de la jugada (pass_forward + 5 frames).
Coordenadas normalizadas a ataque hacia x creciente. data/ es solo lectura.
Ejecutar desde la raiz:  .venv/bin/python backend/precompute.py
"""
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SALIDA = RAIZ / "backend" / "capturas.csv"
MAX_DIST = 10.0  # yardas, receptor-defensor

# --- nombres (copiado de backend/eda/resultados_defensivos.py: ese modulo ejecuta el EDA al importarse) ---
SUFIJOS = {"jr", "sr", "ii", "iii", "iv", "v"}


def letras(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def partes_nombre(display: str):
    toks = [t for t in display.split() if letras(t) not in SUFIJOS]
    return letras(toks[0]), letras("".join(toks[1:]))


def resolver(abrev: str, candidatos: dict):
    """abrev 'Ju.Reid' -> nflId entre los candidatos de la jugada, o None."""
    pre, _, ape = abrev.partition(".")
    pre, ape = letras(pre), letras(ape)
    mismo_ape = [i for i, (f, l) in candidatos.items() if l == ape]
    exacto = [i for i in mismo_ape if candidatos[i][0].startswith(pre)]
    if len(exacto) == 1:
        return exacto[0]
    if len(mismo_ape) == 1:
        return mismo_ape[0]
    return None


NAME = r"[A-Z][A-Za-z']*\.\s?[A-Z][A-Za-z'\-]+"
RE_RECEPTOR = re.compile(rf"\b(?:to|intended for) ({NAME})")


def normalizar(df: pd.DataFrame, izquierda: bool) -> pd.DataFrame:
    df = df.copy()
    if izquierda:
        df["x"] = 120.0 - df["x"]
        df["y"] = 53.3 - df["y"]
        df["dir"] = (df["dir"] + 180.0) % 360.0
        df["o"] = (df["o"] + 180.0) % 360.0
    return df


def main():
    t0 = time.time()
    plays = pd.read_csv(DATA / "plays.csv", na_values=["NA"])
    games = pd.read_csv(DATA / "games.csv", usecols=["gameId", "week"])
    players = pd.read_csv(DATA / "players.csv", usecols=["nflId", "displayName", "officialPosition"])
    pff = pd.read_csv(DATA / "pffScoutingData.csv", na_values=["NA"],
                      usecols=["gameId", "playId", "nflId", "pff_role"])
    nombre = players.set_index("nflId")["displayName"].to_dict()
    posicion = players.set_index("nflId")["officialPosition"].to_dict()
    semana = games.set_index("gameId")["week"].to_dict()

    anulada = plays["playDescription"].astype(str).str.contains("No Play")
    objetivo = plays[plays["passResult"].isin(["C", "I", "IN"]) & ~anulada]
    print(f"Jugadas con passResult C/I/IN sin 'No Play': {len(objetivo)}")
    roles_def = pff[pff["pff_role"].isin(["Coverage", "Pass Rush"])]
    ids_def = {k: set(g["nflId"]) for k, g in roles_def.groupby(["gameId", "playId"])}
    ids_qb = {k: g["nflId"].iloc[0] for k, g in pff[pff["pff_role"] == "Pass"].groupby(["gameId", "playId"])}
    por_juego = {g: d for g, d in objetivo.groupby("gameId")}

    filas = []
    desc = {"sin_tracking": 0, "sin_pass_forward": 0, "sin_descripcion_receptor": 0,
            "receptor_no_resuelto": 0, "receptor_sin_tracking": 0, "sin_defensor": 0,
            "defensor_lejos": 0, "sin_qb_o_balon": 0}
    frames_ok = frames_mal = 0

    for archivo in sorted((DATA / "tracking").glob("tracking_*.csv")):
        gid = int(archivo.stem.split("_")[1])
        if gid not in por_juego:
            continue
        trk = pd.read_csv(archivo, usecols=["gameId", "playId", "nflId", "frameId", "x", "y", "s",
                                            "o", "dir", "event", "playDirection", "team"])
        grupos = {k: g for k, g in trk.groupby("playId")}
        for p in por_juego[gid].itertuples():
            g = grupos.get(p.playId)
            if g is None:
                desc["sin_tracking"] += 1
                continue
            pf = g.loc[g["event"] == "pass_forward", "frameId"]
            if pf.empty:
                desc["sin_pass_forward"] += 1
                continue
            ultimo = g["frameId"].max()
            if ultimo == pf.min() + 5:
                frames_ok += 1
            else:
                frames_mal += 1
            izq = g["playDirection"].iat[0] == "left"
            g = normalizar(g, izq)
            snap = g[(g["event"] == "ball_snap") & g["nflId"].isna()]
            bal = snap["x"].iat[0] if len(snap) else np.nan
            f = g[g["frameId"] == ultimo]
            jug = f[f["nflId"].notna()].set_index("nflId")
            jug.index = jug.index.astype(int)

            m = RE_RECEPTOR.search(str(p.playDescription).split("REVERSED.")[-1])
            if not m:
                desc["sin_descripcion_receptor"] += 1
                continue
            ofensivos = jug[jug["team"] == p.possessionTeam]
            cand = {i: partes_nombre(str(nombre.get(i, ""))) for i in ofensivos.index if i in nombre}
            rid = resolver(m.group(1), {i: v for i, v in cand.items() if v[0] or v[1]})
            if rid is None:
                desc["receptor_no_resuelto"] += 1
                continue
            rec = jug.loc[rid]
            qid = ids_qb.get((gid, p.playId))
            if qid is None or qid not in jug.index or np.isnan(bal):
                desc["sin_qb_o_balon"] += 1
                continue
            qb = jug.loc[qid]
            defs = [i for i in ids_def.get((gid, p.playId), ()) if i in jug.index]
            if not defs:
                desc["sin_defensor"] += 1
                continue
            dd = jug.loc[defs]
            dist = np.hypot(dd["x"] - rec["x"], dd["y"] - rec["y"])
            did = int(dist.idxmin())
            if dist.min() > MAX_DIST:
                desc["defensor_lejos"] += 1
                continue
            d = jug.loc[did]
            filas.append({
                "gameId": gid, "playId": p.playId, "semana": semana.get(gid),
                "resultado": p.passResult,
                "valor": float(p.prePenaltyPlayResult) if p.passResult == "C" else 0.0,
                "receptor_id": rid, "receptor_x": rec["x"], "receptor_y": rec["y"],
                "receptor_s": rec["s"], "receptor_dir": rec["dir"],
                "defensor_id": did, "defensor_x": d["x"], "defensor_y": d["y"],
                "defensor_s": d["s"], "defensor_dir": d["dir"],
                "dx": d["x"] - rec["x"], "dy": d["y"] - rec["y"], "distancia": float(dist.min()),
                "qb_x": qb["x"], "qb_y": qb["y"],
                "dist_linea_scrimmage": rec["x"] - bal, "linea_scrimmage_x": bal,
                "down": p.down, "yardas_por_jugar": p.yardsToGo,
                "cobertura": p.pff_passCoverage, "tipo_cobertura": p.pff_passCoverageType,
                "defenders_in_box": p.defendersInBox,
                "receptor_nombre": nombre.get(rid), "defensor_nombre": nombre.get(did),
                "defensor_posicion": posicion.get(did), "equipo_defensa": p.defensiveTeam,
                "descripcion": p.playDescription,
            })
        print(f"{archivo.name}: acumulado {len(filas)} filas", flush=True)

    df = pd.DataFrame(filas)
    df.to_csv(SALIDA, index=False, float_format="%.4f")
    print("\n=== RESUMEN ===")
    print(f"Filas escritas: {len(df)} -> {SALIDA.relative_to(RAIZ)}")
    print(f"Descartes: {desc}  (total {sum(desc.values())})")
    print(f"Receptor no resuelto (incluye sin 'to X.Apellido'): "
          f"{desc['receptor_no_resuelto'] + desc['sin_descripcion_receptor']}")
    print(f"Ultimo frame == pass_forward + 5: {frames_ok} jugadas; distinto: {frames_mal}")
    print(f"Tiempo: {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
