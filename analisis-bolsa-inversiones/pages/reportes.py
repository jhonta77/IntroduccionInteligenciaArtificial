import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import construir_dataset
from utils.plots import grafico_real_vs_estimado, grafico_rezagos, grafico_scatter_regresion
from utils.stats import (
    analizar_rezagos,
    construir_retornos,
    interpretar_correlacion,
    mejor_rezago,
    regresion_multiple,
    regresion_simple,
)


VARIABLES_X = {
    "precio_bolsa_energia": "Precio bolsa energia",
    "demanda_energia": "Demanda energia SIN",
    "embalse_util_pct": "Volumen util embalses",
    "aportes_pct": "Aportes hidricos",
    "trm_usd_cop": "TRM USD/COP",
}

RETORNOS_X = {
    "retorno_bolsa_energia": "Bolsa energia -> Celsia",
    "retorno_demanda_energia": "Demanda -> Celsia",
    "retorno_embalse_util_pct": "Embalses -> Celsia",
    "retorno_aportes_pct": "Aportes -> Celsia",
    "retorno_trm_usd_cop": "TRM -> Celsia",
}


st.set_page_config(page_title="Regresion - Celsia", layout="wide")
st.title("Modelo diario de Celsia")

st.sidebar.header("Rango de fechas")
fecha_inicio = st.sidebar.date_input("Inicio", value=pd.to_datetime("2024-01-01"))
fecha_fin = st.sidebar.date_input("Fin", value=pd.to_datetime("today"))
max_lag = st.sidebar.slider("Maximo rezago a evaluar (dias)", 5, 60, 30)

with st.spinner("Cargando datos diarios..."):
    try:
        df = construir_dataset(fecha_inicio.isoformat(), fecha_fin.isoformat())
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

if df.empty:
    st.warning("Sin datos. Amplia el rango de fechas.")
    st.stop()

n = len(df)
estado = "Cumple requisito de >= 90 registros" if n >= 90 else f"Solo {n} registros; se necesitan 90"
st.info(
    f"**{n} registros** | "
    f"{df['fecha'].min().strftime('%d/%m/%Y')} -> "
    f"{df['fecha'].max().strftime('%d/%m/%Y')} | {estado}"
)

tab1, tab2, tab3, tab4 = st.tabs([
    "Variables individuales",
    "Modelo multiple diario",
    "Rezagos temporales",
    "Tabla",
])

with tab1:
    st.subheader("Relacion individual con el precio de Celsia")
    variable = st.selectbox(
        "Variable explicativa",
        list(VARIABLES_X),
        format_func=lambda col: VARIABLES_X[col],
    )

    reg = regresion_simple(df[variable], df["precio_celsia"])
    st.altair_chart(
        grafico_scatter_regresion(
            df,
            variable,
            "precio_celsia",
            VARIABLES_X[variable],
            "Precio Celsia (COP)",
            reg["r"],
            reg["pendiente"],
            reg["intercepto"],
        ),
        use_container_width=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Correlacion r", f"{reg['r']:.3f}")
    c2.metric("R2", f"{reg['r2']:.3f}")
    c3.metric("Pendiente", f"{reg['pendiente']:.4f}")
    c4.metric("Registros", f"{reg['n']:,}")
    st.success(interpretar_correlacion(reg["r"]))

with tab2:
    st.subheader("Regresion multiple con variables diarias")
    st.markdown("""
    Este modelo usa variables observadas diariamente: precio de bolsa de energia,
    demanda del SIN, embalses, aportes hidricos y TRM. Es mas coherente para explicar
    el precio diario que usar indicadores financieros trimestrales.
    """)

    reg_m = regresion_multiple(df, list(VARIABLES_X), "precio_celsia")
    c = reg_m["coeficientes"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("R2 del modelo", f"{reg_m['r2']:.3f}")
    c2.metric("MAE", f"{reg_m['mae']:.2f} COP")
    c3.metric("RMSE", f"{reg_m['rmse']:.2f} COP")
    c4.metric("Variables", f"{len(VARIABLES_X)}")

    coeficientes = pd.DataFrame({
        "Variable": ["Intercepto"] + [VARIABLES_X[col] for col in VARIABLES_X],
        "Coeficiente": [c["intercepto"]] + [c[col] for col in VARIABLES_X],
    })
    st.dataframe(coeficientes, hide_index=True, use_container_width=True)

    df_modelo = df.copy()
    df_modelo["precio_estimado"] = reg_m["y_pred"]
    st.altair_chart(grafico_real_vs_estimado(df_modelo), use_container_width=True)
    st.caption("Verde: precio real. Rojo punteado: precio estimado por el modelo.")

with tab3:
    st.subheader("Rezagos temporales contra el retorno futuro de Celsia")
    st.markdown("""
    Este analisis usa retornos porcentuales diarios. Para cada variable se busca
    el rezago futuro con mayor R2 frente al retorno de Celsia.
    """)

    retornos = construir_retornos(df)
    if len(retornos) < max_lag + 3:
        st.warning("No hay suficientes registros para evaluar tantos dias de rezago.")
    else:
        resultados = []
        detalle = {}
        for col_retorno, nombre in RETORNOS_X.items():
            rezagos = analizar_rezagos(retornos, col_retorno, "retorno_celsia", max_lag=max_lag)
            mejor = mejor_rezago(rezagos)
            resultados.append({
                "Variable": nombre,
                "Mejor rezago (dias)": mejor["rezago_dias"],
                "Correlacion": mejor["correlacion"],
                "R2": mejor["r2"],
                "Registros": mejor["n"],
            })
            detalle[nombre] = rezagos

        resumen = pd.DataFrame(resultados).sort_values("R2", ascending=False)
        st.dataframe(resumen.round(4), hide_index=True, use_container_width=True)

        mejor_global = resumen.iloc[0]
        st.info(
            f"La mejor senal fue {mejor_global['Variable']} con rezago de "
            f"{int(mejor_global['Mejor rezago (dias)'])} dias y R2 "
            f"{mejor_global['R2']:.4f}. Si el R2 es bajo, la senal debe tratarse "
            "como exploratoria, no como evidencia causal."
        )

        nombre_grafico = st.selectbox("Grafico de rezagos", list(detalle))
        st.altair_chart(
            grafico_rezagos(detalle[nombre_grafico], nombre_grafico),
            use_container_width=True,
        )

with tab4:
    st.subheader("Dataset del modelo diario")
    st.dataframe(
        df.rename(columns={
            "fecha": "Fecha",
            "precio_celsia": "Celsia (COP)",
            "precio_bolsa_energia": "Bolsa energia (COP/kWh)",
            "demanda_energia": "Demanda SIN (kWh)",
            "embalse_util_pct": "Embalses (%)",
            "aportes_pct": "Aportes (%)",
            "trm_usd_cop": "TRM USD/COP",
        }).round(2),
        hide_index=True,
        use_container_width=True,
    )
