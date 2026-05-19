import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import construir_dataset
from utils.plots import grafico_serie_temporal, grafico_correlaciones

st.set_page_config(page_title="EDA — Datos", layout="wide")
st.title("📊 Exploración de Datos (EDA)")

# ── Sidebar ──────────────────────────────────────────────────────
st.sidebar.header("Rango de fechas")
fecha_inicio = st.sidebar.date_input("Inicio", value=pd.to_datetime("2024-01-01"))
fecha_fin    = st.sidebar.date_input("Fin",    value=pd.to_datetime("today"))

if fecha_inicio >= fecha_fin:
    st.error("La fecha inicio debe ser anterior a la fecha fin.")
    st.stop()

# ── Descarga ──────────────────────────────────────────────────────
with st.spinner("Descargando datos de Yahoo Finance y XM..."):
    try:
        df = construir_dataset(fecha_inicio.isoformat(), fecha_fin.isoformat())
    except Exception as e:
        st.error(f"Error al descargar: {e}")
        st.stop()

if df.empty:
    st.warning("Sin datos para ese rango. Amplía el período (mínimo 6 meses recomendado).")
    st.stop()

# ── Métricas rápidas ──────────────────────────────────────────────
n = len(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros",    f"{n:,}")
c2.metric("Fecha inicio", df["fecha"].min().strftime("%d/%m/%Y"))
c3.metric("Fecha fin",    df["fecha"].max().strftime("%d/%m/%Y"))
c4.metric("✅ ≥ 90 reg.", "Sí" if n >= 90 else f"No ({n})")

st.divider()

# ── Vista previa ──────────────────────────────────────────────────
st.subheader("Vista previa del dataset")
st.dataframe(
    df.head(10).rename(columns={
        "fecha":               "Fecha",
        "precio_celsia":       "Precio Celsia (COP)",
        "precio_brent":        "Precio Brent (USD)",
        "precio_bolsa_energia":"Precio Bolsa Energía (COP/MWh)",
    }),
    hide_index=True,
    use_container_width=True,
)

# ── Estadísticas descriptivas ────────────────────────────────────
st.subheader("Estadísticas descriptivas")
desc = df[["precio_celsia", "precio_brent", "precio_bolsa_energia"]].describe()
desc.index = ["N", "Media", "Desv. estándar", "Mínimo", "Q1", "Mediana", "Q3", "Máximo"]
desc.columns = ["Celsia (COP)", "Brent (USD)", "Bolsa Energía (COP/MWh)"]
st.dataframe(desc.round(2), use_container_width=True)

st.divider()

# ── Series temporales ─────────────────────────────────────────────
st.subheader("Series temporales")
tab1, tab2, tab3 = st.tabs(["Precio Celsia", "Precio Brent", "Bolsa Energía"])

with tab1:
    st.altair_chart(
        grafico_serie_temporal(df, "precio_celsia", "Precio Celsia (COP)", "#0f766e"),
        use_container_width=True,
    )
    st.caption("Precio de cierre diario de CELSIA.CL en la Bolsa de Valores de Colombia.")

with tab2:
    st.altair_chart(
        grafico_serie_temporal(df, "precio_brent", "Precio Brent (USD/barril)", "#b45309"),
        use_container_width=True,
    )
    st.caption("Precio spot del petróleo Brent. Fuente: Yahoo Finance (ticker BZ=F).")

with tab3:
    st.altair_chart(
        grafico_serie_temporal(df, "precio_bolsa_energia", "Precio Bolsa Energía (COP/MWh)", "#6d28d9"),
        use_container_width=True,
    )
    st.caption("Precio promedio diario de bolsa de energía eléctrica colombiana. Fuente: XM.")

st.divider()

# ── Correlaciones ─────────────────────────────────────────────────
st.subheader("Matriz de correlaciones")
st.altair_chart(
    grafico_correlaciones(df, ["precio_celsia", "precio_brent", "precio_bolsa_energia"]),
    use_container_width=True,
)
st.caption("r = 1 → relación positiva perfecta · r = 0 → sin relación · r = −1 → relación negativa perfecta")

# ── Calidad de datos ──────────────────────────────────────────────
with st.expander("Verificación de calidad de datos"):
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

