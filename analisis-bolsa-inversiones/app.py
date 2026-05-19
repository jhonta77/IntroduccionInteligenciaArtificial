import streamlit as st

st.set_page_config(
    page_title="Celsia — Regresión Bursátil",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Celsia S.A. E.S.P. — Análisis de Regresión")

st.markdown("""
**Asignatura:** Introducción a Inteligencia Artificial
**Entrega:** Cuarta nota — Regresión lineal
**Acción:** Celsia (BVC: CELSIA | Yahoo Finance: CELSIA.CL)
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("¿Qué analiza este dashboard?")
    st.markdown("""
    Se identificaron **dos variables regresoras** que explican
    el comportamiento del precio de la acción de Celsia en COP:
    **Variable 1 — Precio de bolsa de energía (COP/MWh)**
    Celsia genera y vende energía eléctrica al precio de bolsa
    del mercado colombiano. Cuando ese precio sube, los ingresos
    de Celsia suben → precio de la acción tiende a subir.
    **Variable 2 — Precio del petróleo Brent (USD/barril)**
    El Brent es la referencia global de energía. Cuando sube,
    la energía renovable (que ofrece Celsia) se vuelve más
    competitiva → atrae inversión → acción sube.
    """)

with col2:
    st.subheader("Páginas del dashboard")
    st.markdown("""
    | Página | Contenido |
    |--------|-----------|
    | 📊 **analisis** | EDA: explorar y visualizar los datos |
    | 📈 **reportes** | Regresión: correlaciones y modelo |
    """)
    st.divider()
    st.subheader("Fuentes de datos")
    st.info("**CELSIA.CL** → Yahoo Finance via `yfinance` — gratis, sin registro")
    st.info("**Bolsa energía** → API pública XM (`servapibi.xm.com.co`) — gratis, sin registro")
    st.info("**Brent (BZ=F)** → Yahoo Finance via `yfinance` — gratis, sin registro")