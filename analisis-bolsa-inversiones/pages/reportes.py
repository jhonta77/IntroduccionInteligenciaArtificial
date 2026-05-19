import sys
from pathlib import Path
import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import construir_dataset
from utils.stats import regresion_simple, regresion_multiple, interpretar_correlacion
from utils.plots import grafico_scatter_regresion, grafico_real_vs_estimado

st.set_page_config(page_title="Regresión — Celsia", layout="wide")
st.title("📈 Análisis de Regresión")

# ── Sidebar ──────────────────────────────────────────────────────
st.sidebar.header("Rango de fechas")
fecha_inicio = st.sidebar.date_input("Inicio", value=pd.to_datetime("2024-01-01"))
fecha_fin    = st.sidebar.date_input("Fin",    value=pd.to_datetime("today"))

with st.spinner("Cargando datos..."):
    try:
        df = construir_dataset(fecha_inicio.isoformat(), fecha_fin.isoformat())
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

if df.empty:
    st.warning("Sin datos. Amplía el rango de fechas.")
    st.stop()

n = len(df)
estado = "✅ Cumple requisito de ≥ 90 registros" if n >= 90 else f"⚠️  Solo {n} registros — se necesitan 90"
st.info(f"**{n} registros** · {df['fecha'].min().strftime('%d/%m/%Y')} → {df['fecha'].max().strftime('%d/%m/%Y')} · {estado}")

# ── Calcular regresiones ──────────────────────────────────────────
reg_bolsa = regresion_simple(df["precio_bolsa_energia"], df["precio_celsia"])
reg_brent  = regresion_simple(df["precio_brent"],        df["precio_celsia"])

tab1, tab2, tab3 = st.tabs([
    "Variable 1 — Bolsa Energía",
    "Variable 2 — Brent",
    "Modelo Múltiple",
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — BOLSA ENERGÍA
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Precio de bolsa de energía vs Precio Celsia")
    st.markdown("""
    **¿Por qué esta variable?**
    Celsia genera energía (solar, hidráulica, térmica) y la vende al precio de bolsa
    del mercado eléctrico colombiano. Si ese precio sube → ingresos de Celsia suben
    → precio de la acción tiende a subir.
    **Fuente:** API pública de XM — `servapibi.xm.com.co` — Métrica: `PrecBolsNaci`
    """)

    st.altair_chart(
        grafico_scatter_regresion(
            df, "precio_bolsa_energia", "precio_celsia",
            "Bolsa Energía (COP/MWh)", "Precio Celsia (COP)",
            reg_bolsa["r"], reg_bolsa["pendiente"], reg_bolsa["intercepto"],
        ),
        use_container_width=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Correlación r",  f"{reg_bolsa['r']:.3f}")
    c2.metric("R²",             f"{reg_bolsa['r2']:.3f}")
    c3.metric("Pendiente",      f"{reg_bolsa['pendiente']:.4f}")
    c4.metric("Intercepto",     f"{reg_bolsa['intercepto']:.2f}")
    st.success(interpretar_correlacion(reg_bolsa["r"]))
    st.code(
        f"Precio Celsia (COP) = {reg_bolsa['intercepto']:.2f}  +  "
        f"{reg_bolsa['pendiente']:.4f} × Bolsa Energía (COP/MWh)",
        language="text",
    )

# ══════════════════════════════════════════════════════════════════
# TAB 2 — BRENT
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Precio del petróleo Brent vs Precio Celsia")
    st.markdown("""
    **¿Por qué esta variable?**
    El Brent es la referencia internacional de energía. Cuando sube, la energía
    renovable que ofrece Celsia se vuelve más competitiva frente a los combustibles
    fósiles → los inversionistas favorecen empresas renovables → precio de la acción sube.
    **Fuente:** Yahoo Finance via `yfinance` — Ticker: `BZ=F`
    """)

    st.altair_chart(
        grafico_scatter_regresion(
            df, "precio_brent", "precio_celsia",
            "Precio Brent (USD/barril)", "Precio Celsia (COP)",
            reg_brent["r"], reg_brent["pendiente"], reg_brent["intercepto"],
        ),
        use_container_width=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Correlación r",  f"{reg_brent['r']:.3f}")
    c2.metric("R²",             f"{reg_brent['r2']:.3f}")
    c3.metric("Pendiente",      f"{reg_brent['pendiente']:.4f}")
    c4.metric("Intercepto",     f"{reg_brent['intercepto']:.2f}")

    st.success(interpretar_correlacion(reg_brent["r"]))
    st.code(
        f"Precio Celsia (COP) = {reg_brent['intercepto']:.2f}  +  "
        f"{reg_brent['pendiente']:.4f} × Brent (USD/barril)",
        language="text",
    )

# ══════════════════════════════════════════════════════════════════
# TAB 3 — MODELO MÚLTIPLE
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Modelo de regresión múltiple")
    st.markdown("Combina las dos variables para explicar mejor el precio de Celsia:")
    st.latex(r"\text{Precio Celsia} = b_0 + b_1 \times \text{Bolsa Energía} + b_2 \times \text{Brent}")
    reg_m = regresion_multiple(df, ["precio_bolsa_energia", "precio_brent"], "precio_celsia")
    c = reg_m["coeficientes"]
    
    st.code(
        f"Precio Celsia = {c['intercepto']:.2f}"
        f"  +  {c['precio_bolsa_energia']:.4f} × Bolsa Energía"
        f"  +  {c['precio_brent']:.4f} × Brent",
        language="text",
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("R² del modelo", f"{reg_m['r2']:.3f}",
              help="Proporción del precio de Celsia explicada por las dos variables")
    
    c2.metric("MAE",  f"{reg_m['mae']:.2f} COP")
    c3.metric("RMSE", f"{reg_m['rmse']:.2f} COP")
    df["precio_estimado"] = reg_m["y_pred"]
    st.altair_chart(grafico_real_vs_estimado(df), use_container_width=True)
    st.caption("Verde: precio real · Rojo punteado: precio estimado por el modelo")

    st.divider()
    st.subheader("Tabla completa")
    st.dataframe(
        df.rename(columns={
            "fecha":               "Fecha",
            "precio_celsia":       "Celsia (COP)",
            "precio_brent":        "Brent (USD)",
            "precio_bolsa_energia":"Bolsa Energía (COP/MWh)",
            "precio_estimado":     "Estimado (COP)",
        }).round(2),
        hide_index=True,
        use_container_width=True,
    )





