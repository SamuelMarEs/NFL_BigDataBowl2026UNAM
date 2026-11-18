"""Modelos kNN (solo numpy y pandas) y delta contra defensores fantasma.

A: valor esperado y P(completo) dado el estado de la jugada (incluye al defensor).
B: distribucion del defensor fantasma (dx, dy, vx, vy relativos al receptor) dado
   variables de la jugada SIN las del defensor real.
Validacion: leave-one-out (el pase evaluado se excluye de sus vecinos).
"""
from pathlib import Path
import time

import numpy as np
import pandas as pd

CSV = Path(__file__).resolve().parent / "capturas.csv"
K_A = 40          # vecinos del modelo A
K_B = 60          # vecinos del modelo B (de ahi se muestrean los fantasmas)
N_FANTASMAS = 30
SEED = 7
EPS = 1e-3


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
    return d.reset_index(drop=True)


# variables de la jugada que no dependen del defensor
JUGADA = ["receptor_vx", "receptor_vy", "receptor_y", "qb_dx", "qb_dy",
          "dist_linea_scrimmage", "down", "yardas_por_jugar", "man", "defenders_in_box"]
# variables del defensor respecto al receptor
DEFENSOR = ["dx", "dy", "distancia", "defensor_vx", "defensor_vy"]
# columnas objetivo del fantasma
GHOST = ["dx", "dy", "defensor_vx", "defensor_vy"]
# pesos por variable (tras estandarizar): el defensor pesa mas en A
PESO_A = {"dx": 2.0, "dy": 2.0, "distancia": 1.5, "defensor_vx": 1.0, "defensor_vy": 1.0}


def _matriz(d, cols, mu, sd, pesos=None):
    X = (d[cols].to_numpy(float) - mu) / sd
    if pesos:
        X = X * np.array([pesos.get(c, 1.0) for c in cols])
    return X.astype(np.float32)


# ---------------------------------------------------------------- kNN
def _knn(Q, X, k, excluir=None, bloque=2000):
    """Devuelve (indices, pesos normalizados) de los k vecinos de cada fila de Q.
    excluir: indice en X que se descarta para cada fila de Q (leave-one-out)."""
    n = len(Q)
    idx = np.empty((n, k), dtype=np.int32)
    w = np.empty((n, k), dtype=np.float32)
    x2 = (X ** 2).sum(1)
    for i in range(0, n, bloque):
        q = Q[i:i + bloque]
        d2 = (q ** 2).sum(1)[:, None] + x2[None, :] - 2 * q @ X.T
        np.maximum(d2, 0, out=d2)
        if excluir is not None:
            d2[np.arange(len(q)), excluir[i:i + bloque]] = np.inf
        part = np.argpartition(d2, k, axis=1)[:, :k]
        dd = np.sqrt(np.take_along_axis(d2, part, 1))
        ww = 1.0 / (dd + EPS)
        idx[i:i + bloque] = part
        w[i:i + bloque] = ww / ww.sum(1, keepdims=True)
    return idx, w


class Modelo:
    def __init__(self, d: pd.DataFrame | None = None):
        self.d = cargar() if d is None else d
        d = self.d
        self.cols_a = JUGADA + DEFENSOR
        self.mu_a = d[self.cols_a].mean().to_numpy(float)
        self.sd_a = d[self.cols_a].std().replace(0, 1).to_numpy(float)
        self.XA = _matriz(d, self.cols_a, self.mu_a, self.sd_a, PESO_A)
        self.mu_b = d[JUGADA].mean().to_numpy(float)
        self.sd_b = d[JUGADA].std().replace(0, 1).to_numpy(float)
        self.XB = _matriz(d, JUGADA, self.mu_b, self.sd_b)
        self.valor = d["valor"].to_numpy(np.float32)
        self.comp = d["completo"].to_numpy(np.float32)
        self.G = d[GHOST].to_numpy(np.float32)

    # ----- Modelo A
    def predecir_a(self, Q, excluir):
        idx, w = _knn(Q, self.XA, K_A, excluir)
        return (w * self.valor[idx]).sum(1), (w * self.comp[idx]).sum(1)

    # ----- Modelo B
    def muestrear_fantasmas(self, excluir, n=N_FANTASMAS, rng=None):
        """Devuelve array (N, n, 4) con dx, dy, vx, vy de n fantasmas por pase."""
        rng = rng or np.random.default_rng(SEED)
        idx, w = _knn(self.XB, self.XB, K_B, excluir)
        c = np.cumsum(w, 1)
        u = rng.random((len(idx), n), dtype=np.float32) * c[:, -1:]
        pick = np.minimum((u[:, :, None] > c[:, None, :]).sum(2), idx.shape[1] - 1)
        return self.G[np.take_along_axis(idx, pick, 1)]

    def _consulta_a(self, g, base):
        """Construye features del modelo A para fantasmas g (N, n, 4) en los pases base."""
        N, n, _ = g.shape
        df = pd.DataFrame(np.repeat(self.d[JUGADA].to_numpy(float), n, 0), columns=JUGADA)
        df["dx"] = g[:, :, 0].ravel()
        df["dy"] = g[:, :, 1].ravel()
        df["distancia"] = np.hypot(df["dx"], df["dy"])
        df["defensor_vx"] = g[:, :, 2].ravel()
        df["defensor_vy"] = g[:, :, 3].ravel()
        return _matriz(df, self.cols_a, self.mu_a, self.sd_a, PESO_A)

    def ejecutar(self):
        """Calcula esperado real y fantasma para todos los pases (leave-one-out)."""
        N = len(self.d)
        yo = np.arange(N)
        er, pr = self.predecir_a(self.XA, yo)
        g = self.muestrear_fantasmas(yo)
        Q = self._consulta_a(g, None)
        ef, pf = self.predecir_a(Q, np.repeat(yo, N_FANTASMAS))
        ef = ef.reshape(N, -1)
        pf = pf.reshape(N, -1)
        out = self.d[["gameId", "playId", "semana", "resultado", "valor", "defensor_id",
                      "defensor_nombre", "defensor_posicion", "equipo_defensa",
                      "tipo_cobertura", "cobertura", "descripcion"]].copy()
        out["esperado_real"] = er
        out["p_completo_real"] = pr
        out["esperado_fantasma"] = ef.mean(1)
        out["p_completo_fantasma"] = pf.mean(1)
        out["delta"] = out["esperado_fantasma"] - out["esperado_real"]
        self.fantasmas = g
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
    print(ag.head(8).to_string())
    print(ag.tail(8).to_string())
