import streamlit as st


st.set_page_config(
    page_title="Celsia - Modelo diario",
    page_icon="⚡",
    layout="wide",
)

st.title("Celsia S.A. E.S.P. - Modelo diario de regresion")

st.markdown("""
**Asignatura:** Introduccion a Inteligencia Artificial

**Entrega:** Regresion lineal

**Accion:** Celsia (BVC: CELSIA | Yahoo Finance: CELSIA.CL)
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Que analiza este dashboard")
    st.markdown("""
    El modelo diario explica el precio de la accion de Celsia usando variables
    observadas cada dia y relacionadas directamente con el mercado electrico
    colombiano:

    - Precio de bolsa de energia
    - Demanda diaria del SIN
    - Volumen util de embalses
    - Aportes hidricos
    - TRM USD/COP

    Se descarta Brent como variable principal porque su relacion con Celsia es
    indirecta y mostro baja capacidad explicativa en el analisis inicial.
    """)

with col2:
    st.subheader("Paginas del dashboard")
    st.markdown("""
    | Pagina | Contenido |
    |--------|-----------|
    | **analisis** | EDA: explorar y visualizar los datos diarios |
    | **reportes** | Regresion, modelo multiple y rezagos temporales |
    """)

    st.divider()
    st.subheader("Fuentes de datos")
    st.info("**CELSIA.CL**: Yahoo Finance via `yfinance`")
    st.info("**TRM USD/COP**: Yahoo Finance via `USDCOP=X`")
    st.info("**XM**: API publica `servapibi.xm.com.co` para energia, demanda, embalses y aportes")
