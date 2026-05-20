import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import construir_dataset
from utils.plots import grafico_correlaciones, grafico_serie_temporal


VARIABLES = {
    "precio_celsia": "Precio Celsia (COP)",
    "precio_bolsa_energia": "Precio bolsa energia (COP/kWh)",
    "demanda_energia": "Demanda energia SIN (kWh)",
    "embalse_util_pct": "Volumen util embalses (%)",
    "aportes_pct": "Aportes hidricos (%)",
    "trm_usd_cop": "TRM USD/COP",
}

COLORES = {
    "precio_celsia": "#0f766e",
    "precio_bolsa_energia": "#6d28d9",
    "demanda_energia": "#2563eb",
    "embalse_util_pct": "#0891b2",
    "aportes_pct": "#65a30d",
    "trm_usd_cop": "#b45309",
}


st.set_page_config(page_title="EDA - Datos", layout="wide")
st.title("Exploracion de Datos")

st.sidebar.header("Rango de fechas")
fecha_inicio = st.sidebar.date_input("Inicio", value=pd.to_datetime("2024-01-01"))
fecha_fin = st.sidebar.date_input("Fin", value=pd.to_datetime("today"))

if fecha_inicio >= fecha_fin:
    st.error("La fecha inicio debe ser anterior a la fecha fin.")
    st.stop()

with st.spinner("Descargando datos de Yahoo Finance y XM..."):
    try:
        df = construir_dataset(fecha_inicio.isoformat(), fecha_fin.isoformat())
    except Exception as e:
        st.error(f"Error al descargar: {e}")
        st.stop()

if df.empty:
    st.warning("Sin datos para ese rango. Amplia el periodo.")
    st.stop()

n = len(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros", f"{n:,}")
c2.metric("Fecha inicio", df["fecha"].min().strftime("%d/%m/%Y"))
c3.metric("Fecha fin", df["fecha"].max().strftime("%d/%m/%Y"))
c4.metric(">= 90 reg.", "Si" if n >= 90 else f"No ({n})")

st.divider()
st.subheader("Vista previa del dataset")
st.dataframe(
    df.head(10).rename(columns={"fecha": "Fecha", **VARIABLES}),
    hide_index=True,
    use_container_width=True,
)

st.subheader("Estadisticas descriptivas")
desc = df[list(VARIABLES)].describe()
desc.index = ["N", "Media", "Desv. estandar", "Minimo", "Q1", "Mediana", "Q3", "Maximo"]
desc.columns = [VARIABLES[col] for col in desc.columns]
st.dataframe(desc.round(2), use_container_width=True)

st.divider()
st.subheader("Series temporales")
tabs = st.tabs(list(VARIABLES.values()))

for tab, col in zip(tabs, VARIABLES):
    with tab:
        st.altair_chart(
            grafico_serie_temporal(df, col, VARIABLES[col], COLORES[col]),
            use_container_width=True,
        )

st.divider()
st.subheader("Matriz de correlaciones")
st.altair_chart(grafico_correlaciones(df, list(VARIABLES)), use_container_width=True)
st.caption("r = 1 relacion positiva perfecta; r = 0 sin relacion lineal; r = -1 relacion negativa perfecta.")

with st.expander("Verificacion de calidad de datos"):
    nulos = df.isnull().sum()
    st.dataframe(
        pd.DataFrame({
            "Columna": nulos.index,
            "Valores nulos": nulos.values,
            "% del total": (nulos.values / len(df) * 100).round(2),
        }),
        hide_index=True,
        use_container_width=True,
    )
    st.dataframe(df.dtypes.rename("Tipo de dato"), use_container_width=True)
