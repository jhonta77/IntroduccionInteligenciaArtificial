import numpy as np
import pandas as pd


def regresion_simple(x: pd.Series, y: pd.Series) -> dict:
    """Regresion lineal simple: y = pendiente * x + intercepto."""
    x_arr = x.astype(float).to_numpy()
    y_arr = y.astype(float).to_numpy()

    r = float(x.astype(float).corr(y.astype(float)))

    x_design = np.column_stack((np.ones(len(x_arr)), x_arr))
    beta, *_ = np.linalg.lstsq(x_design, y_arr, rcond=None)
    intercepto, pendiente = float(beta[0]), float(beta[1])

    y_pred = intercepto + pendiente * x_arr
    residuos = y_arr - y_pred
    mae = float(np.abs(residuos).mean())
    rmse = float(np.sqrt((residuos ** 2).mean()))

    return {
        "pendiente": pendiente,
        "intercepto": intercepto,
        "r": r,
        "r2": r ** 2,
        "mae": mae,
        "rmse": rmse,
        "n": len(x_arr),
    }


def regresion_multiple(df: pd.DataFrame, vars_x: list, var_y: str) -> dict:
    """Regresion lineal multiple: y = b0 + b1*x1 + b2*x2."""
    x = df[vars_x].astype(float).to_numpy()
    y = df[var_y].astype(float).to_numpy()
    x_design = np.column_stack((np.ones(len(x)), x))
    beta, *_ = np.linalg.lstsq(x_design, y, rcond=None)

    y_pred = x_design @ beta
    residuos = y - y_pred
    ss_res = (residuos ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = float(1 - ss_res / ss_tot) if ss_tot else 0.0
    mae = float(np.abs(residuos).mean())
    rmse = float(np.sqrt((residuos ** 2).mean()))

    coeficientes = {"intercepto": float(beta[0])}
    for nombre, coef in zip(vars_x, beta[1:]):
        coeficientes[nombre] = float(coef)

    return {
        "coeficientes": coeficientes,
        "r2": r2,
        "mae": mae,
        "rmse": rmse,
        "n": len(y),
        "y_pred": y_pred,
    }


def interpretar_correlacion(r: float) -> str:
    """Interpreta la fuerza de la correlacion de Pearson."""
    abs_r = abs(r)
    direccion = "positiva" if r >= 0 else "negativa"
    if abs_r >= 0.8:
        fuerza = "muy fuerte"
    elif abs_r >= 0.6:
        fuerza = "fuerte"
    elif abs_r >= 0.4:
        fuerza = "moderada"
    elif abs_r >= 0.2:
        fuerza = "debil"
    else:
        fuerza = "muy debil o nula"
    return f"Correlacion {direccion} {fuerza} | r = {r:.3f}"


def construir_retornos(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula retornos porcentuales diarios para analizar cambios, no niveles."""
    retornos = df.copy()
    columnas = [col for col in retornos.columns if col != "fecha"]

    for col in columnas:
        nombre = col.replace("precio_", "")
        retornos[f"retorno_{nombre}"] = retornos[col].pct_change()

    return retornos.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)


def analizar_rezagos(
    df: pd.DataFrame,
    col_origen: str,
    col_destino: str,
    max_lag: int = 30,
) -> pd.DataFrame:
    """
    Mide que tan fuerte se relaciona un cambio actual con un cambio futuro.

    lag = 0 compara origen(t) con destino(t).
    lag = 5 compara origen(t) con destino(t + 5).
    """
    resultados = []

    for lag in range(max_lag + 1):
        temp = df[[col_origen, col_destino]].copy()
        temp["destino_futuro"] = temp[col_destino].shift(-lag)
        temp = temp.dropna()

        if len(temp) < 3:
            continue

        r = float(temp[col_origen].corr(temp["destino_futuro"]))
        if np.isnan(r):
            continue

        resultados.append({
            "rezago_dias": lag,
            "correlacion": r,
            "r2": r ** 2,
            "n": len(temp),
        })

    return pd.DataFrame(resultados)


def mejor_rezago(resultados: pd.DataFrame) -> dict:
    """Devuelve el rezago con mayor fuerza explicativa segun R2."""
    if resultados.empty:
        return {"rezago_dias": None, "correlacion": 0.0, "r2": 0.0, "n": 0}

    fila = resultados.sort_values(["r2", "n"], ascending=[False, False]).iloc[0]
    return {
        "rezago_dias": int(fila["rezago_dias"]),
        "correlacion": float(fila["correlacion"]),
        "r2": float(fila["r2"]),
        "n": int(fila["n"]),
    }
