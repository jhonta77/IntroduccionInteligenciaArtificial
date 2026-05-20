import altair as alt
import pandas as pd
import numpy as np

def grafico_serie_temporal(df, col_y, titulo, color="#0f766e"):
    """ Gráfico de serie temporal con Altair."""
    return (
          alt.Chart(df)
          .mark_line(strokeWidth=2.5, color=color)
          .encode(
              x=alt.X("fecha:T", title="Fecha"),
              y=alt.Y(f"{col_y}:Q", title=titulo, scale=alt.Scale(zero=False)),
              tooltip=[
                  alt.Tooltip("fecha:T",     title="Fecha"),
                  alt.Tooltip(f"{col_y}:Q", title=titulo, format=",.2f"),
              ],
          )
          .properties(height=300, title=titulo)
      )

def grafico_scatter_regresion(df, col_x, col_y, titulo_x, titulo_y, r, pendiente, intercepto):
    puntos = (
        alt.Chart(df)
        .mark_circle(size=55, opacity=0.6, color="#a16207")
        .encode(
            x=alt.X(f"{col_x}:Q", title=titulo_x),
            y=alt.Y(f"{col_y}:Q", title=titulo_y, scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("fecha:T",     title="Fecha"),
                alt.Tooltip(f"{col_x}:Q", title=titulo_x, format=",.2f"),
                alt.Tooltip(f"{col_y}:Q", title=titulo_y, format=",.2f"),
            ],
        )
    )
    x_min, x_max = df[col_x].min(), df[col_x].max()
    linea_df = pd.DataFrame({
        col_x:   [x_min, x_max],
        "y_reg": [intercepto + pendiente * x_min, intercepto + pendiente * x_max],
    })
    linea = (
        alt.Chart(linea_df)
        .mark_line(strokeWidth=2, color="#ef4444", strokeDash=[6, 3])
        .encode(
            x=alt.X(f"{col_x}:Q"),
            y=alt.Y("y_reg:Q", scale=alt.Scale(zero=False)),
        )
    )
    return (puntos + linea).properties(
        height=370,
        title=f"{titulo_y} vs {titulo_x}   |   r = {r:.3f}",
    )

def grafico_real_vs_estimado(df):
    real = (
        alt.Chart(df)
        .mark_line(strokeWidth=2.5, color="#0f766e")
        .encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("precio_celsia:Q", title="Precio Celsia (COP)",
                    scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("fecha:T", title="Fecha"),
                alt.Tooltip("precio_celsia:Q", title="Real", format=",.2f"),
            ],
        )
    )
    estimado = (
        alt.Chart(df)
        .mark_line(strokeWidth=2, strokeDash=[5, 3], color="#ef4444")
        .encode(
            x=alt.X("fecha:T"),
            y=alt.Y("precio_estimado:Q", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("fecha:T", title="Fecha"),
                alt.Tooltip("precio_estimado:Q", title="Estimado", format=",.2f"),
            ],
        )
    )
    return (real + estimado).properties(
        height=350,
        title="Precio real vs estimado por el modelo",
    )

def grafico_correlaciones(df, columnas):
    labels = {
        "precio_celsia": "Celsia (COP)",
        "precio_bolsa_energia": "Bolsa Energia (COP/kWh)",
        "demanda_energia": "Demanda SIN (kWh)",
        "embalse_util_pct": "Embalses (%)",
        "aportes_pct": "Aportes (%)",
        "trm_usd_cop": "TRM USD/COP",
    }
    corr = df[columnas].rename(columns=labels).corr()
    corr_long = corr.reset_index().melt("index")
    corr_long.columns = ["X", "Y", "r"]
    return (
        alt.Chart(corr_long)
        .mark_rect()
        .encode(
            x=alt.X("X:N", title=None),
            y=alt.Y("Y:N", title=None),
            color=alt.Color("r:Q",
                scale=alt.Scale(scheme="redyellowgreen", domain=[-1, 1]),
                legend=alt.Legend(title="r"),
            ),
            tooltip=["X:N", "Y:N", alt.Tooltip("r:Q", format=".3f")],
        )
        .properties(height=220, title="Matriz de correlaciones de Pearson")
    )


def grafico_rezagos(df, titulo):
    """Grafico de correlacion por rezago temporal."""
    base = alt.Chart(df).encode(
        x=alt.X("rezago_dias:Q", title="Rezago futuro (dias)"),
        y=alt.Y(
            "correlacion:Q",
            title="Correlacion de retornos",
            scale=alt.Scale(domain=[-1, 1]),
        ),
        tooltip=[
            alt.Tooltip("rezago_dias:Q", title="Dias", format=".0f"),
            alt.Tooltip("correlacion:Q", title="r", format=".3f"),
            alt.Tooltip("r2:Q", title="R2", format=".3f"),
            alt.Tooltip("n:Q", title="Registros", format=".0f"),
        ],
    )

    linea = base.mark_line(strokeWidth=2.5, color="#2563eb")
    puntos = base.mark_circle(size=55, color="#0f766e")
    cero = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color="#64748b", strokeDash=[4, 3])
        .encode(y="y:Q")
    )

    return (linea + puntos + cero).properties(height=320, title=titulo)
