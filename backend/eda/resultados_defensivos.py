"""Resultados del pase atribuidos a cada defensor a partir de playDescription.

- Intercepcion:        "INTERCEPTED by X"                 -> X intercepta
- Pase incompleto:     "pass incomplete ... to REC (X)"   -> X desvia el pase
- Balon suelto:        "FUMBLES (X)"                      -> X fuerza el fumble
                       "RECOVERED by TEAM-Y" (TEAM = defensa) -> Y lo recupera
- Pase completo:       "pass ... to REC ... (X; Z)"       -> X, Z taclean al receptor
                       (aproximacion de "completo permitido")

Los nombres abreviados (p. ej. "Ju.Reid") se resuelven a nflId contra los defensores
de esa misma jugada en pffScoutingData. Las jugadas anuladas ("No Play") se excluyen.

Ejecuta desde la raiz:  .venv\\Scripts\\python.exe backend\\eda\\resultados_defensivos.py
Escribe resultados_defensivos.txt y defensores_resultados.csv en esta carpeta.
"""
import re
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
DATA = AQUI.parents[1] / "data"
sys.stdout = open(AQUI / "resultados_defensivos.txt", "w", encoding="utf-8")
sys.stderr = sys.stdout

NAME = r"[A-Z][A-Za-z']*\.\s?[A-Z][A-Za-z'\-]+"
LISTA = rf"{NAME}(?:;\s?{NAME})*"
SIN_CAMBIO_FRASE = r"(?:(?!\.\s[A-Z])[^()])*?"
RE_INT = re.compile(rf"INTERCEPTED by ({NAME})")
RE_INC = re.compile(rf"pass incomplete {SIN_CAMBIO_FRASE}\(({LISTA})\)")
RE_COMP = re.compile(rf"pass (?:short|deep) (?:left|right|middle) to {NAME}{SIN_CAMBIO_FRASE}\(({LISTA})\)")
RE_FF = re.compile(rf"FUMBLES \(({NAME})\)")
RE_FR = re.compile(rf"RECOVERED by ([A-Z]{{2,3}})-({NAME})")
SUFIJOS = {"jr", "sr", "ii", "iii", "iv", "v"}


def letras(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def partes_nombre(display: str):
    toks = [t for t in display.split() if letras(t) not in SUFIJOS]
    return letras(toks[0]), letras("".join(toks[1:]))


def resolver(abrev: str, candidatos: dict):
    """abrev 'Ju.Reid' -> nflId entre los defensores de la jugada, o None."""
    pre, _, ape = abrev.partition(".")
    pre, ape = letras(pre), letras(ape)
    mismo_ape = [i for i, (f, l) in candidatos.items() if l == ape]
    exacto = [i for i in mismo_ape if candidatos[i][0].startswith(pre)]
    if len(exacto) == 1:
        return exacto[0]
    if len(mismo_ape) == 1:
        return mismo_ape[0]
    return None


plays = pd.read_csv(DATA / "plays.csv", na_values=["NA"])
pff = pd.read_csv(DATA / "pffScoutingData.csv", na_values=["NA"],
                  usecols=["gameId", "playId", "nflId", "pff_role"])
players = pd.read_csv(DATA / "players.csv", usecols=["nflId", "displayName", "officialPosition"])

defensa = pff[pff["pff_role"].isin(["Coverage", "Pass Rush", "Pass rush"])] \
    .merge(players[["nflId", "displayName"]], on="nflId", how="left")
cand_por_jugada = {
    k: {r.nflId: partes_nombre(str(r.displayName)) for r in g.itertuples()}
    for k, g in defensa.groupby(["gameId", "playId"])
}

desc = plays["playDescription"].astype(str)
anuladas = desc.str.contains("No Play")
print("=" * 70 + "\nRESUMEN DE RESULTADOS DEL PASE (plays.csv)\n" + "=" * 70)
print("passResult (todas):", plays["passResult"].value_counts(dropna=False).to_dict())
print(f"Jugadas anuladas por castigo ('No Play'), excluidas: {anuladas.sum()}")

registros, sin_resolver = [], []
for row, d in zip(plays[~anuladas].itertuples(), desc[~anuladas]):
    if "REVERSED." in d:                       # quedarse con la decision final del replay
        d = d.split("REVERSED.")[-1]
    cands = cand_por_jugada.get((row.gameId, row.playId), {})
    eventos = []
    if row.passResult == "IN":
        eventos += [("intercepciones", n) for n in RE_INT.findall(d)[:1]]
    if row.passResult == "I":
        m = RE_INC.search(d)
        if m:
            eventos += [("incompletos_defendidos", n.strip()) for n in m.group(1).split(";")]
    if row.passResult == "C":
        m = RE_COMP.search(d)
        if m:
            eventos += [("completos_tacleados", n.strip()) for n in m.group(1).split(";")]
    eventos += [("fumbles_forzados", n) for n in dict.fromkeys(RE_FF.findall(d))]
    eventos += [("fumbles_recuperados", n) for t, n in dict.fromkeys(RE_FR.findall(d))
                if t == row.defensiveTeam]
    for tipo, nombre in eventos:
        nid = resolver(nombre, cands)
        if nid is None:
            sin_resolver.append((tipo, nombre, row.gameId, row.playId))
            continue
        registros.append({"gameId": row.gameId, "playId": row.playId, "nflId": int(nid),
                          "tipo": tipo, "passResult": row.passResult,
                          "defensiveTeam": row.defensiveTeam})

ev = pd.DataFrame(registros)
validas = plays[~anuladas]
print("\n" + "=" * 70 + "\nCOBERTURA DE LA ATRIBUCION\n" + "=" * 70)
for res, tipo in [("IN", "intercepciones"), ("I", "incompletos_defendidos"),
                  ("C", "completos_tacleados")]:
    n_tot = (validas["passResult"] == res).sum()
    n_con = ev.loc[ev["tipo"] == tipo, "playId"].groupby(ev["gameId"]).nunique().sum()
    print(f"{res:>3}: {n_tot:5d} jugadas validas, {n_con:5d} con defensor atribuido "
          f"({n_con / max(n_tot, 1):.1%})")
n_ff = desc[~anuladas].str.contains(r"FUMBLES \(").sum()
n_fum = desc[~anuladas].str.contains("FUMBLES").sum()
print(f"Fumbles: {n_fum} jugadas con FUMBLES, {n_ff} forzados por un defensor; "
      f"{(ev['tipo'] == 'fumbles_recuperados').sum()} recuperados por la defensa")
print("Fumbles forzados por passResult de la jugada:",
      ev.loc[ev["tipo"] == "fumbles_forzados", "passResult"].value_counts().to_dict())
print(f"Nombres sin resolver a nflId: {len(sin_resolver)} de {len(sin_resolver) + len(ev)}")
for s in sin_resolver[:10]:
    print("   ", s)

tabla = ev.pivot_table(index="nflId", columns="tipo", values="playId", aggfunc="count",
                       fill_value=0)
for c in ["intercepciones", "incompletos_defendidos", "fumbles_forzados",
          "fumbles_recuperados", "completos_tacleados"]:
    if c not in tabla:
        tabla[c] = 0
tabla["jugadas_negativas_para_ofensiva"] = (tabla["intercepciones"]
                                            + tabla["incompletos_defendidos"]
                                            + tabla["fumbles_forzados"])
equipo = ev.groupby("nflId")["defensiveTeam"].agg(lambda s: s.mode().iat[0])
tabla = tabla.join(equipo).reset_index().merge(players, on="nflId", how="left")
cols = ["nflId", "displayName", "officialPosition", "defensiveTeam", "intercepciones",
        "incompletos_defendidos", "fumbles_forzados", "fumbles_recuperados",
        "jugadas_negativas_para_ofensiva", "completos_tacleados"]
tabla = tabla[cols].sort_values(["jugadas_negativas_para_ofensiva", "intercepciones"],
                                ascending=False)
tabla.to_csv(AQUI / "defensores_resultados.csv", index=False)

print("\n" + "=" * 70 + "\nPOR DEFENSOR\n" + "=" * 70)
print(f"Defensores con al menos un evento: {len(tabla)}")
print("\nTotales:", tabla[cols[4:]].sum().to_dict())
print("\nTop 20 por intercepciones + incompletos defendidos + fumbles forzados:")
print(tabla.head(20).drop(columns="nflId").to_string(index=False))
print("\nTop 10 intercepciones:")
print(tabla.sort_values("intercepciones", ascending=False).head(10)
      [["displayName", "officialPosition", "defensiveTeam", "intercepciones"]].to_string(index=False))
print("\nTop 10 fumbles forzados:")
print(tabla.sort_values("fumbles_forzados", ascending=False).head(10)
      [["displayName", "officialPosition", "defensiveTeam", "fumbles_forzados"]].to_string(index=False))
print("\nPor posicion oficial (suma):")
print(tabla.groupby("officialPosition")[cols[4:]].sum()
      .sort_values("jugadas_negativas_para_ofensiva", ascending=False).to_string())
