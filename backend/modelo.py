"""Modelos con scikit-learn y delta contra defensores fantasma.
A: valor esperado y P(completo) dado el estado de la jugada (incluye al defensor).
   P(completo) = HistGradientBoostingClassifier; yardas esperadas = P(completo) * E[yardas | completo]
   (HistGradientBoostingRegressor entrenado solo con pases completos).
B: distribucion del defensor fantasma (dx, dy, vx, vy relativos al receptor) dado variables de la
   jugada SIN las del defensor real. Bosque aleatorio usado como muestreador (estilo quantile regression forest):
   cada fantasma se saca de una hoja de un arbol elegido al azar.
Validacion: validacion cruzada de 5 grupos por partido (gameId). Cada pase se predice con modelos que
no vieron su partido, y esos mismos modelos generan sus fantasmas.
"""
from pathlib import Path
import time
import numpy as np
import pandas as pd
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestRegressor)
from sklearn.model_selection import GroupKFold

CSV = Path(__file__).resolve().parent / "capturas.csv"
N_FANTASMAS = 30
N_GRUPOS = 5
SEED = 7

# ---------------------------------------------------------------- datos
def cargar(path=CSV) -> pd.DataFrame:
    d = pd.read_csv(path)
    d["completo"] = (d["resultado"] == "C").astype(float)
    d["man"] = (d["tipo_cobertura"] == "Man").astype(float)
    d["defenders_in_box"] = d["defenders_in_box"].fillna(d["defenders_in_box"].median())
    for p in ("receptor", "defensor"):
        r = np.deg2rad(d[f"{p}_dir"])
        d[f"{p}_vx"] = d[f"{p}_s"] * np.sin(r)
        d[f"{p}_vy"] = d[f"{p}_s"] * np.cos(r)
    d["qb_dx"] = d["qb_x"] - d["receptor_x"]
    d["qb_dy"] = d["qb_y"] - d["receptor_y"]
    d["profundidad"] = d["receptor_x"] - d["linea_scrimmage_x"]
    d["pase_dist"] = np.hypot(d["qb_dx"], d["qb_dy"])
    d["gol"] = 120.0 - d["receptor_x"]
    return d.reset_index(drop=True)

# variables de la jugada que no dependen del defensor
JUGADA = ["receptor_vx", "receptor_vy", "receptor_y", "qb_dx", "qb_dy",
          "dist_linea_scrimmage", "down", "yardas_por_jugar", "man", "defenders_in_box",
          "profundidad", "pase_dist", "gol", "receptor_s"]
# variables extra del modelo B (posicion absoluta; no entran al A, que ya tiene profundidad y gol)
JUGADA_B = JUGADA + ["receptor_x", "qb_x"]
# columnas objetivo del fantasma (relativas al receptor)
GHOST = ["dx", "dy", "defensor_vx", "defensor_vy"]
# variables del defensor que usa el modelo A, calculadas igual para el real y para cada fantasma
FEATURES_A = JUGADA + ["dx", "dy", "distancia", "defensor_vx", "defensor_vy", "rvx", "rvy", "defensor_s"]

def features_a(base: pd.DataFrame, g: np.ndarray) -> np.ndarray:
    """Matriz del modelo A para la jugada `base` (N filas) con defensor g (N, 4): dx, dy, vx, vy."""
    f = base[JUGADA].copy()
    f["dx"], f["dy"] = g[:, 0], g[:, 1]
    f["distancia"] = np.hypot(g[:, 0], g[:, 1])
    f["defensor_vx"], f["defensor_vy"] = g[:, 2], g[:, 3]
    f["rvx"] = g[:, 2] - base["receptor_vx"].to_numpy()
    f["rvy"] = g[:, 3] - base["receptor_vy"].to_numpy()
    f["defensor_s"] = np.hypot(g[:, 2], g[:, 3])
    return f[FEATURES_A].to_numpy(float)

# ---------------------------------------------------------------- muestreo por hojas del bosque
def muestrear_hojas(rf, Xtr, Gtr, Xq, n, rng):
    """n muestras de Gtr por fila de Xq: se elige un arbol al azar y una fila al azar de la hoja de Xq."""
    Ltr, Lq = rf.apply(Xtr), rf.apply(Xq)
    T = Ltr.shape[1]
    out = np.zeros((len(Xq), n, Gtr.shape[1]))
    arbol = rng.integers(0, T, (len(Xq), n))
    for t in range(T):
        qi, ni = np.nonzero(arbol == t)
        if len(qi) == 0:
            continue
        orden = np.argsort(Ltr[:, t], kind="stable")
        hojas = Ltr[orden, t]
        lq = Lq[qi, t]
        lo = np.searchsorted(hojas, lq, "left")
        hi = np.searchsorted(hojas, lq, "right")
        pick = lo + (rng.random(len(qi)) * (hi - lo)).astype(int)
        out[qi, ni] = Gtr[orden[np.minimum(pick, len(orden) - 1)]]
    return out

def _clasificador():
    return HistGradientBoostingClassifier(learning_rate=0.03, max_iter=200, min_samples_leaf=40,
                                          max_depth=4, l2_regularization=1.0, random_state=SEED)

def _regresor():
    return HistGradientBoostingRegressor(learning_rate=0.03, max_iter=200, min_samples_leaf=40,
                                         max_depth=4, l2_regularization=1.0, random_state=SEED)

def _bosque():
    return RandomForestRegressor(n_estimators=100, min_samples_leaf=10, max_features=0.5, bootstrap=True,
                                 max_samples=0.7, n_jobs=-1, random_state=SEED)

class Modelo:
    def __init__(self, d: pd.DataFrame | None = None):
        self.d = cargar() if d is None else d
        self.G = self.d[GHOST].to_numpy(float)
        self.fantasmas = None

    def ejecutar(self):
        """Calcula esperado real y fantasma para todos los pases con validacion cruzada por partido."""
        d, G = self.d, self.G
        N = len(d)
        y, c = d["valor"].to_numpy(float), d["completo"].to_numpy(float)
        rng = np.random.default_rng(SEED)
        XA = features_a(d, G)
        XB = d[JUGADA_B].to_numpy(float)
        er, pr = np.zeros(N), np.zeros(N)
        ef, pf = np.zeros(N), np.zeros(N)
        fant = np.zeros((N, N_FANTASMAS, 4))
        for tr, te in GroupKFold(N_GRUPOS).split(XA, c, d["gameId"].to_numpy()):
            clf = _clasificador().fit(XA[tr], c[tr])
            comp = tr[c[tr] == 1]
            reg = _regresor().fit(XA[comp], y[comp])
            bosque = _bosque().fit(XB[tr], G[tr])

            def predecir(X):
                p = clf.predict_proba(X)[:, 1]
                return p * reg.predict(X), p

            er[te], pr[te] = predecir(XA[te])
            g = muestrear_hojas(bosque, XB[tr], G[tr], XB[te], N_FANTASMAS, rng)
            fant[te] = g
            base = d.iloc[te]
            rep = base.loc[base.index.repeat(N_FANTASMAS)]
            e, p = predecir(features_a(rep, g.reshape(-1, 4)))
            ef[te] = e.reshape(len(te), -1).mean(1)
            pf[te] = p.reshape(len(te), -1).mean(1)
        out = d[["gameId", "playId", "semana", "resultado", "valor", "defensor_id",
                 "defensor_nombre", "defensor_posicion", "equipo_defensa",
                 "tipo_cobertura", "cobertura", "descripcion"]].copy()
        out["esperado_real"] = er
        out["p_completo_real"] = pr
        out["esperado_fantasma"] = ef
        out["p_completo_fantasma"] = pf
        out["delta"] = ef - er
        self.fantasmas = fant
        return out

    def metricas(self, res):
        y = self.d["valor"].to_numpy(float)
        c = self.d["completo"].to_numpy(float)
        return {
            "rmse_yardas": float(np.sqrt(np.mean((res["esperado_real"] - y) ** 2))),
            "rmse_base_media": float(np.sqrt(np.mean((y - y.mean()) ** 2))),
            "brier_completo": float(np.mean((res["p_completo_real"] - c) ** 2)),
            "brier_base_media": float(np.mean((c - c.mean()) ** 2)),
            "n_pases": int(len(y)),
        }

    def fantasmas_jugada(self, i):
        """Fantasmas absolutos de la fila i: x, y, peso (1/n cada uno)."""
        r = self.d.iloc[i]
        g = self.fantasmas[i]
        n = len(g)
        return [{"x": float(r.receptor_x + a), "y": float(r.receptor_y + b), "peso": 1.0 / n}
                for a, b, _, _ in g]

def correr():
    t = time.time()
    m = Modelo()
    res = m.ejecutar()
    met = m.metricas(res)
    met["segundos"] = time.time() - t
    return m, res, met

if __name__ == "__main__":
    m, res, met = correr()
    for k, v in met.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")
    print("delta medio:", round(res["delta"].mean(), 4), "sd:", round(res["delta"].std(), 4))
    ag = (res.groupby(["defensor_id", "defensor_nombre", "defensor_posicion"])["delta"]
          .agg(["count", "mean"]).query("count >= 15").sort_values("mean", ascending=False))
    print("defensores con >=15 pases:", len(ag))
    print(ag.head(5)); print(ag.tail(5))
