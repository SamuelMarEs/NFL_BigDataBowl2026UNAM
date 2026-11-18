"""EDA inicial: evento de atrapada, normalizacion de direccion, completos por defensor y YAC.

Ejecuta desde la raiz del proyecto:
    .venv\\Scripts\\python.exe backend\\eda\\analisis_inicial.py
Solo lee data/ (no modifica nada).
"""
from pathlib import Path

import numpy as np
import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SALIDA = Path(__file__).resolve().parent / "resultados_analisis_inicial.txt"
sys.stdout = open(SALIDA, "w", encoding="utf-8")
sys.stderr = sys.stdout
print("inicio", flush=True)

TRACK_COLS = ["gameId", "playId", "nflId", "frameId", "team", "playDirection", "x", "y", "event"]
TRACK_DTYPES = {
    "gameId": "int32", "playId": "int16", "nflId": "float32", "frameId": "int16",
    "team": "category", "playDirection": "category", "x": "float32", "y": "float32",
    "event": "category",
}
FIN_JUGADA = {"tackle", "out_of_bounds", "touchdown", "fumble", "fumble_offense_recovered",
              "fumble_defense_recovered", "safety"}


def seccion(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


plays = pd.read_csv(DATA / "plays.csv", na_values=["NA"])
pff = pd.read_csv(DATA / "pffScoutingData.csv", na_values=["NA"],
                  usecols=["gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp"])
players = pd.read_csv(DATA / "players.csv", usecols=["nflId", "displayName", "officialPosition"])

eventos_total = {}
eventos_tras_catch = {}
snap_rows, catch_rows = [], []

for f in sorted((DATA / "tracking").glob("tracking_*.csv")):
    t = pd.read_csv(f, usecols=TRACK_COLS, dtype=TRACK_DTYPES, na_values=["NA"])
    t = t.merge(plays[["gameId", "playId", "possessionTeam", "absoluteYardlineNumber"]],
                on=["gameId", "playId"], how="left")
    ball = t[t["team"] == "football"]

    # 1) eventos: contados una vez por (jugada, frame) usando la fila del balon
    for ev, n in ball["event"].astype(str).value_counts().items():
        eventos_total[ev] = eventos_total.get(ev, 0) + n

    # frames de snap y catch por jugada
    ev_frames = ball[["gameId", "playId", "frameId", "event", "x", "y", "playDirection",
                      "absoluteYardlineNumber"]]
    snap = ev_frames[ev_frames["event"] == "ball_snap"].drop_duplicates(["gameId", "playId"])
    catch = ev_frames[ev_frames["event"] == "pass_outcome_caught"].drop_duplicates(["gameId", "playId"])

    # eventos que aparecen despues de la atrapada
    after = ball.merge(catch[["gameId", "playId", "frameId"]].rename(columns={"frameId": "fc"}),
                       on=["gameId", "playId"])
    after = after[after["frameId"] > after["fc"]]
    for ev, n in after["event"].astype(str).value_counts().items():
        eventos_tras_catch[ev] = eventos_tras_catch.get(ev, 0) + n

    # 2) direccion: posicion media de la ofensiva respecto al balon en el snap
    pl = t[t["team"] != "football"].copy()
    pl["ofensa"] = pl["team"].astype(str) == pl["possessionTeam"]
    s = pl.merge(snap[["gameId", "playId", "frameId", "x"]].rename(columns={"x": "ball_x"}),
                 on=["gameId", "playId", "frameId"])
    s_off = s[s["ofensa"]].groupby(["gameId", "playId"]).agg(
        off_x=("x", "mean"), ball_x=("ball_x", "first"), dirn=("playDirection", "first"),
        los=("absoluteYardlineNumber", "first")).reset_index()
    snap_rows.append(s_off)

    # 3) y 4) frame de atrapada: receptor, defensor mas cercano y YAC por tracking
    c = pl.merge(catch[["gameId", "playId", "frameId", "x", "y"]]
                 .rename(columns={"x": "bx", "y": "by"}), on=["gameId", "playId", "frameId"])
    c["d_ball"] = np.hypot(c["x"] - c["bx"], c["y"] - c["by"])
    rec = c[c["ofensa"]].sort_values("d_ball").drop_duplicates(["gameId", "playId"])
    rec = rec[["gameId", "playId", "frameId", "nflId", "x", "y", "playDirection",
               "absoluteYardlineNumber", "d_ball"]].rename(
        columns={"nflId": "rec_id", "x": "rx", "y": "ry", "frameId": "fc"})
    de = c[~c["ofensa"]].merge(rec[["gameId", "playId", "rx", "ry"]], on=["gameId", "playId"])
    de["d_rec"] = np.hypot(de["x"] - de["rx"], de["y"] - de["ry"])
    de = de.sort_values("d_rec").drop_duplicates(["gameId", "playId"])[
        ["gameId", "playId", "nflId", "d_rec"]].rename(columns={"nflId": "def_id"})
    rec = rec.merge(de, on=["gameId", "playId"], how="left")

    # fin de la jugada: primer evento de fin despues del catch; si no hay, ultimo frame
    fin = after[after["event"].astype(str).isin(FIN_JUGADA)].sort_values("frameId") \
        .drop_duplicates(["gameId", "playId"])[["gameId", "playId", "frameId"]] \
        .rename(columns={"frameId": "ff"})
    last = ball.groupby(["gameId", "playId"])["frameId"].max().rename("flast").reset_index()
    rec = rec.merge(fin, on=["gameId", "playId"], how="left").merge(last, on=["gameId", "playId"])
    rec["ff"] = rec["ff"].fillna(rec["flast"]).astype("int16")
    pos_fin = pl[["gameId", "playId", "frameId", "nflId", "x"]].rename(
        columns={"frameId": "ff", "nflId": "rec_id", "x": "rx_fin"})
    rec = rec.merge(pos_fin, on=["gameId", "playId", "ff", "rec_id"], how="left")
    catch_rows.append(rec)

snaps = pd.concat(snap_rows, ignore_index=True)
catches = pd.concat(catch_rows, ignore_index=True)

# ---------------------------------------------------------------- 1
seccion("1) EVENTOS EN TRACKING (frames con evento, fila del balon)")
print(pd.Series(eventos_total).sort_values(ascending=False).to_string())
seccion("1b) EVENTOS QUE OCURREN DESPUES DE 'pass_outcome_caught'")
print(pd.Series(eventos_tras_catch).sort_values(ascending=False).to_string())
comp = plays[plays["passResult"] == "C"]
print(f"\nJugadas con passResult == 'C' en plays.csv: {len(comp)}")
print(f"Jugadas con evento pass_outcome_caught en tracking: {len(catches)}")
cruce = comp.merge(catches[["gameId", "playId"]], on=["gameId", "playId"], how="left", indicator=True)
print("Cruce passResult=='C' vs catch en tracking:", cruce["_merge"].value_counts().to_dict())

# ---------------------------------------------------------------- 2
seccion("2) DIRECCION DE LA JUGADA")
print("Jugadas por playDirection:", snaps["dirn"].value_counts().to_dict())
snaps["off_menos_balon"] = snaps["off_x"] - snaps["ball_x"]
snaps["los_menos_balon"] = snaps["los"] - snaps["ball_x"]
print("\nx media de la ofensiva - x del balon en el snap (negativo = ofensiva a la izquierda):")
print(snaps.groupby("dirn", observed=True)["off_menos_balon"].describe().round(2).to_string())
print("\nabsoluteYardlineNumber - x del balon en el snap:")
print(snaps.groupby("dirn", observed=True)["los_menos_balon"].describe().round(2).to_string())

# ---------------------------------------------------------------- 3
seccion("3) PASES COMPLETADOS POR DEFENSOR (defensor mas cercano al receptor en la atrapada)")
cov = pff[pff["pff_role"] == "Coverage"][["gameId", "playId", "nflId"]].assign(cov=True)
catches = catches.merge(cov.rename(columns={"nflId": "def_id"}), on=["gameId", "playId", "def_id"],
                        how="left")
catches["cov"] = catches["cov"].fillna(False)
print(f"Atrapadas analizadas: {len(catches)}")
print(f"Distancia receptor-balon en la atrapada (yd): mediana {catches['d_ball'].median():.2f}, "
      f"p95 {catches['d_ball'].quantile(.95):.2f}")
print(f"Distancia defensor-receptor (yd): mediana {catches['d_rec'].median():.2f}, "
      f"p90 {catches['d_rec'].quantile(.9):.2f}")
print(f"% defensores mas cercanos con pff_role == 'Coverage': {catches['cov'].mean():.1%}")
por_def = catches.groupby("def_id").agg(completos=("playId", "size"),
                                        dist_media=("d_rec", "mean")).reset_index()
por_def = por_def.merge(players, left_on="def_id", right_on="nflId", how="left") \
    .sort_values("completos", ascending=False)
print(f"\nDefensores distintos: {len(por_def)}")
print("Distribucion de completos permitidos por defensor:")
print(por_def["completos"].describe().round(2).to_string())
print("\nTop 15:")
print(por_def.head(15)[["displayName", "officialPosition", "completos", "dist_media"]]
      .round(2).to_string(index=False))

# ---------------------------------------------------------------- 4
seccion("4) DISTRIBUCION DE YAC")
sign = np.where(catches["playDirection"].astype(str) == "right", 1, -1)
catches["yac_tracking"] = sign * (catches["rx_fin"] - catches["rx"])
catches["air_yards"] = sign * (catches["rx"] - catches["absoluteYardlineNumber"])
catches = catches.merge(plays[["gameId", "playId", "prePenaltyPlayResult"]], on=["gameId", "playId"])
catches["yac_resultado"] = catches["prePenaltyPlayResult"] - catches["air_yards"]
fin_evento = (catches["ff"] != catches["flast"]).mean()
print(f"% atrapadas con evento de fin (tackle/out_of_bounds/touchdown...): {fin_evento:.1%}")
for col in ["air_yards", "yac_tracking", "yac_resultado"]:
    print(f"\n{col}:")
    print(catches[col].describe(percentiles=[.1, .25, .5, .75, .9, .99]).round(2).to_string())
print("\nCorrelacion yac_tracking vs yac_resultado:",
      round(catches[["yac_tracking", "yac_resultado"]].corr().iloc[0, 1], 3))
bins = [-np.inf, 0, 2, 5, 10, 20, np.inf]
labels = ["<=0", "0-2", "2-5", "5-10", "10-20", ">20"]
print("\nHistograma yac_resultado (yd):")
print(pd.cut(catches["yac_resultado"], bins=bins, labels=labels).value_counts(sort=False)
      .to_string())
