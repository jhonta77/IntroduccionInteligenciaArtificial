import numpy as np
import pandas as pd

def regresion_simple(x: pd.Series, y:pd.Series)-> dict:
    """Regresión lineal simple: y = pendiente * x + intercepto
      Usa mínimos cuadrados ordinarios (OLS) con numpy. """
    x_arr = x.astype(float).to_numpy()
    y_arr = y.astype(float).to_numpy()

    # Correlacion de Pearson
    r = float(x.astype(float).corr(y.astype(float)))

    # OLS: [intercepto, pendiente] = (XᵀX)⁻¹ Xᵀy
    X_design = np.column_stack((np.ones(len(x_arr)), x_arr))
    beta, *_ = np.linalg.lstsq(X_design, y_arr, rcond=None)
    intercepto, pendiente = float(beta[0]), float(beta[1])

    y_pred = intercepto + pendiente * x_arr
    residuos = y_arr - y_pred
    mae = float(np.abs(residuos).mean())
    rmse = float(np.sqrt((residuos ** 2).mean()))

    return {
        "pendiente":  pendiente,
          "intercepto": intercepto,
          "r":          r,
          "r2":         r ** 2,
          "mae":        mae,
          "rmse":       rmse,
          "n":          len(x_arr),
    }

def regresion_multiple(df:pd.DataFrame, vars_x: list, var_y:str) -> dict:
    """Regresion lineal multiple:  y = b0 + b1*x1 + b2*x2 """
    X = df[vars_x].astype(float).to_numpy()
    y = df[var_y].astype(float).to_numpy()
    X_design = np.column_stack((np.ones(len(X)), X))
    beta, *_ = np.linalg.lstsq(X_design, y, rcond=None)

    y_pred = X_design @ beta
    resduos = y - y_pred
    ss_res = (resduos ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = float(1 - ss_res / ss_tot) if ss_tot else 0.0
    mae = float(np.abs(resduos).mean())
    rmse = float(np.sqrt((resduos ** 2).mean()))

    coeficientes = {"intercepto": float(beta[0])}
    for nombre, coef in zip(vars_x, beta[1:]):
          coeficientes[nombre] = float(coef)

    return {
          "coeficientes": coeficientes,
          "r2":    r2,
          "mae":   mae,
          "rmse":  rmse,
          "n":     len(y),
          "y_pred": y_pred,
      }

def interpretar_correlacion(r: float) -> str:
    """Interpreta la fuerza de la correlación de Pearson."""
    abs_r = abs(r)
    direccion = "positiva" if r >= 0 else "negativa"
    if abs_r >= 0.8:   fuerza = "muy fuerte"
    elif abs_r >= 0.6: fuerza = "fuerte"
    elif abs_r >= 0.4: fuerza = "moderada"
    elif abs_r >= 0.2: fuerza = "débil"
    else:              fuerza = "muy débil o nula"
    return f"Correlación {direccion} {fuerza}  |  r = {r:.3f}"