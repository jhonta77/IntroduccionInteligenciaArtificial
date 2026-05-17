import io
import os
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

from fondo import FondoAcciones

try:
    import yfinance as yf
except ImportError:
    yf = None


ARCHIVO_LOCAL = Path("movimientos_acciones.csv")
ARCHIVO_ENV = Path(".env")
ARCHIVO_X_POSTS = Path("x_posts_cache.csv")
ARCHIVO_X_CUENTAS = Path("x_cuentas_monitoreadas.csv")
X_BASE_URL = "https://api.x.com/2"
TICKERS_YFINANCE = {
    "ECOPETROL": "ECOPETROL.CL",
    "MINEROS": "MINEROS.CL",
    "NUCO": "NUCO.CL",
    "PFCIBEST": "PFCIBEST.CL",
    "IBITCO": "IBITCO.CL",
}
ACCIONES_COLOMBIANAS = ["ECOPETROL", "MINEROS", "NUCO", "PFCIBEST"]


def cargar_env_local():
    if not ARCHIVO_ENV.exists():
        return

    for linea in ARCHIVO_ENV.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue

        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def aplicar_estilos():
    st.markdown(
        """
        <style>
        :root {
            --bg: #f6f1e7;
            --panel: #fffaf0;
            --ink: #1d2a24;
            --muted: #6b7280;
            --accent: #a16207;
            --accent-2: #0f766e;
            --line: rgba(29, 42, 36, 0.10);
        }
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(161, 98, 7, 0.18), transparent 28%),
                radial-gradient(circle at left center, rgba(15, 118, 110, 0.12), transparent 24%),
                linear-gradient(180deg, #f4eddc 0%, var(--bg) 100%);
            color: var(--ink);
        }
        .stApp, [data-testid="stMarkdownContainer"] p, label, .stCaption,
        [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"],
        [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
            font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
            color: var(--ink) !important;
        }
        h1, h2, h3, .stTabs [data-baseweb="tab"] {
            font-family: "Trebuchet MS", "Gill Sans", sans-serif;
            letter-spacing: 0.02em;
            color: var(--ink) !important;
        }
        .stTabs [data-baseweb="tab"] p,
        .stTabs [data-baseweb="tab"] span,
        .stTabs [data-baseweb="tab-list"] button,
        .stTabs [role="tab"] {
            color: var(--ink) !important;
            opacity: 1 !important;
            font-weight: 700;
        }
        .stTabs [aria-selected="true"] p,
        .stTabs [aria-selected="true"] span {
            color: #7c2d12 !important;
        }
        [data-testid="stExpander"] *,
        [data-testid="stSelectbox"] *,
        [data-testid="stTextInput"] *,
        [data-testid="stDateInput"] *,
        [data-testid="stMultiSelect"] *,
        [data-testid="stCheckbox"] * {
            color: var(--ink) !important;
        }
        [data-testid="stSidebar"] {
            background: #252630;
        }
        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] [data-baseweb="input"],
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="tag"],
        [data-testid="stSidebar"] [data-baseweb="popover"],
        [data-testid="stSidebar"] [data-baseweb="base-input"] {
            background-color: #0f1117 !important;
            color: #f8fafc !important;
            border-color: rgba(248, 250, 252, 0.26) !important;
        }
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
        }
        [data-testid="stSidebar"] [data-baseweb="tag"] {
            background-color: #ef4444 !important;
        }
        [data-testid="stSidebar"] [data-baseweb="tag"] span,
        [data-testid="stSidebar"] [data-baseweb="tag"] svg {
            color: #ffffff !important;
            fill: #ffffff !important;
        }
        [data-testid="stSidebar"] svg {
            color: #f8fafc !important;
            fill: currentColor !important;
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(248, 250, 252, 0.22) !important;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(255,250,240,0.95), rgba(255,255,255,0.86));
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 0.9rem 1rem;
            box-shadow: 0 10px 24px rgba(29, 42, 36, 0.06);
        }
        [data-testid="stMetricLabel"] {
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-size: 0.72rem;
        }
        [data-testid="stMetricValue"] {
            color: var(--ink);
        }
        .stButton button,
        .stDownloadButton button,
        [data-testid="stDownloadButton"] button {
            background-color: #111827 !important;
            color: #f8fafc !important;
            border: 1px solid rgba(17, 24, 39, 0.20) !important;
            font-weight: 700;
        }
        .stButton button *,
        .stDownloadButton button *,
        [data-testid="stDownloadButton"] button * {
            color: #f8fafc !important;
        }
        .stButton button:hover,
        .stDownloadButton button:hover,
        [data-testid="stDownloadButton"] button:hover {
            background-color: #1f2937 !important;
            color: #ffffff !important;
            border-color: rgba(31, 41, 55, 0.35) !important;
        }
        .hero {
            background:
                linear-gradient(135deg, rgba(161,98,7,0.92), rgba(15,118,110,0.88));
            border-radius: 28px;
            padding: 1.4rem 1.6rem;
            color: #fffdf8;
            margin-bottom: 1rem;
            box-shadow: 0 16px 34px rgba(29, 42, 36, 0.16);
        }
        .hero, .hero * {
            color: #fffdf8 !important;
        }
        .hero-kicker {
            text-transform: uppercase;
            letter-spacing: 0.10em;
            font-size: 0.72rem;
            opacity: 0.9;
            margin-bottom: 0.4rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.2rem;
            line-height: 1.05;
        }
        .hero p {
            margin: 0.65rem 0 0 0;
            max-width: 50rem;
            font-size: 1.02rem;
            opacity: 0.96;
        }
        [data-testid="stDataFrame"], [data-testid="stSidebar"] section {
            border-radius: 18px;
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cargar_archivo_silencioso(fondo, ruta_archivo):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fondo.importar_excel(str(ruta_archivo))


def construir_fondo(origen, archivo_subido):
    fondo = FondoAcciones()
    descripcion = "Usando los movimientos integrados en fondo.py."

    if origen == "CSV local" and ARCHIVO_LOCAL.exists():
        cargar_archivo_silencioso(fondo, ARCHIVO_LOCAL)
        descripcion = f"Datos cargados desde {ARCHIVO_LOCAL.name}."
    elif origen == "Archivo subido":
        if archivo_subido is None:
            raise ValueError("Sube un archivo CSV o XLSX para continuar.")

        sufijo = Path(archivo_subido.name).suffix or ".csv"
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as archivo:
                archivo.write(archivo_subido.getvalue())
                temporal = Path(archivo.name)

            cargar_archivo_silencioso(fondo, temporal)
            descripcion = f"Datos cargados desde {archivo_subido.name}."
        finally:
            if temporal and temporal.exists():
                temporal.unlink()

    return fondo, descripcion


def construir_movimientos_df(fondo):
    filas = []
    for movimiento in fondo.movimientos:
        fecha_dt = fondo._fecha_a_datetime(movimiento["fecha"])
        filas.append(
            {
                "Accion": movimiento["nombre_accion"],
                "Tipo": movimiento["tipo"].capitalize(),
                "TipoKey": movimiento["tipo"],
                "Estado": movimiento["estado"].capitalize(),
                "EstadoKey": movimiento["estado"],
                "Cantidad": movimiento["cantidad"],
                "Precio unidad": movimiento["precio_unidad"],
                "Inversion": fondo._calcular_inversion_bruta(
                    movimiento["cantidad"],
                    movimiento["precio_unidad"],
                    movimiento["estado"],
                ),
                "Comision": movimiento["comision"],
                "Total": movimiento["precio_total"],
                "Fecha": fecha_dt,
                "Fecha texto": fondo._formatear_fecha(movimiento["fecha"]),
            }
        )

    if not filas:
        return pd.DataFrame()

    return pd.DataFrame(filas).sort_values("Fecha").reset_index(drop=True)


def construir_resumen_general(df):
    resumen = {}

    for fila in df.to_dict("records"):
        accion = fila["Accion"]
        if accion not in resumen:
            resumen[accion] = {
                "Accion": accion,
                "Cantidad comprada": 0,
                "Cantidad vendida": 0,
                "Total comprado": 0.0,
                "Ventas netas": 0.0,
                "Dividendos netos": 0.0,
                "Cantidad cancelada": 0,
                "Total cancelado": 0.0,
            }

        if fila["EstadoKey"] == "cancelada":
            resumen[accion]["Cantidad cancelada"] += fila["Cantidad"]
            resumen[accion]["Total cancelado"] += fila["Cantidad"] * fila["Precio unidad"]
            continue

        if fila["TipoKey"] == "compra":
            resumen[accion]["Cantidad comprada"] += fila["Cantidad"]
            resumen[accion]["Total comprado"] += fila["Total"]
        elif fila["TipoKey"] == "venta":
            resumen[accion]["Cantidad vendida"] += fila["Cantidad"]
            resumen[accion]["Ventas netas"] += fila["Total"]
        elif fila["TipoKey"] == "dividendo":
            resumen[accion]["Dividendos netos"] += fila["Total"]

    filas_resumen = []
    for fila in resumen.values():
        acciones_vigentes = fila["Cantidad comprada"] - fila["Cantidad vendida"]
        costo_promedio_compra = (
            fila["Total comprado"] / fila["Cantidad comprada"]
            if fila["Cantidad comprada"] > 0
            else 0.0
        )
        costo_portafolio_actual = acciones_vigentes * costo_promedio_compra
        resultado_realizado = fila["Ventas netas"] - (
            fila["Cantidad vendida"] * costo_promedio_compra
        )

        filas_resumen.append(
            {
                "Accion": fila["Accion"],
                "Cantidad comprada": fila["Cantidad comprada"],
                "Total comprado": fila["Total comprado"],
                "Cantidad vendida": fila["Cantidad vendida"],
                "Ventas netas": fila["Ventas netas"],
                "Dividendos netos": fila["Dividendos netos"],
                "Acciones vigentes": acciones_vigentes,
                "Costo promedio compra": costo_promedio_compra,
                "Costo portafolio actual": costo_portafolio_actual,
                "Resultado realizado": resultado_realizado,
                "Cantidad cancelada": fila["Cantidad cancelada"],
                "Total cancelado": fila["Total cancelado"],
            }
        )

    if not filas_resumen:
        return pd.DataFrame()

    return pd.DataFrame(filas_resumen).sort_values(
        ["Costo portafolio actual", "Accion"], ascending=[False, True]
    )


def construir_resumen_financiero(fondo, df, resumen_general):
    aprobados = df[df["EstadoKey"] == "aprobada"].copy()
    compras = aprobados[aprobados["TipoKey"] == "compra"]
    ventas = aprobados[aprobados["TipoKey"] == "venta"]
    dividendos = aprobados[aprobados["TipoKey"] == "dividendo"]

    inversion_compras = compras["Inversion"].sum()
    total_comprado = compras["Total"].sum()
    ventas_netas = ventas["Total"].sum()
    dividendos_netos = dividendos["Total"].sum()
    comisiones = aprobados["Comision"].sum()
    flujo_neto_invertido = total_comprado - ventas_netas - dividendos_netos
    acciones_vigentes = (
        resumen_general["Acciones vigentes"].sum() if not resumen_general.empty else 0
    )
    costo_portafolio_actual = (
        resumen_general["Costo portafolio actual"].sum()
        if not resumen_general.empty
        else 0.0
    )
    resultado_realizado = (
        resumen_general["Resultado realizado"].sum()
        if not resumen_general.empty
        else 0.0
    )
    valor_real_menos_comisiones = fondo.VALOR_REAL_HOY - comisiones

    indicadores = {
        "Inversion compras": inversion_compras,
        "Total comprado": total_comprado,
        "Ventas netas": ventas_netas,
        "Dividendos netos": dividendos_netos,
        "Comisiones acumuladas": comisiones,
        "Flujo neto invertido": flujo_neto_invertido,
        "Costo portafolio actual": costo_portafolio_actual,
        "Resultado realizado": resultado_realizado,
        "Acciones vigentes": acciones_vigentes,
        "Valor real hoy": fondo.VALOR_REAL_HOY,
        "Valor real en acciones menos comisiones": valor_real_menos_comisiones,
        "Retiro personal": fondo.RETIRO_PERSONAL,
        "Fondos": fondo.FONDOS_ACTUALES,
        "Disponible para invertir (dinero a favor)": fondo.DISPONIBLE_PARA_INVERTIR,
    }

    resumen = pd.DataFrame(
        [{"Concepto": concepto, "Valor": valor} for concepto, valor in indicadores.items()]
    )
    return indicadores, resumen


def construir_balance_actual(resumen_general, precios_actuales):
    filas = []
    for fila in resumen_general.to_dict("records"):
        if fila["Acciones vigentes"] <= 0:
            continue

        precio_actual = precios_actuales.get(
            fila["Accion"], fila["Costo promedio compra"]
        )
        valor_actual = fila["Acciones vigentes"] * precio_actual
        balance = valor_actual - fila["Costo portafolio actual"]
        rentabilidad = (
            (balance / fila["Costo portafolio actual"]) * 100
            if fila["Costo portafolio actual"] > 0
            else 0.0
        )

        filas.append(
            {
                "Accion": fila["Accion"],
                "Acciones vigentes": fila["Acciones vigentes"],
                "Costo promedio compra": fila["Costo promedio compra"],
                "Costo portafolio actual": fila["Costo portafolio actual"],
                "Precio actual": precio_actual,
                "Valor actual": valor_actual,
                "Balance": balance,
                "Rentabilidad %": rentabilidad,
            }
        )

    if not filas:
        return pd.DataFrame()

    return pd.DataFrame(filas).sort_values(
        ["Valor actual", "Accion"], ascending=[False, True]
    )


def obtener_fechas_inicio_yfinance(df):
    compras = df[
        (df["EstadoKey"] == "aprobada")
        & (df["TipoKey"] == "compra")
    ].copy()
    if compras.empty:
        return {}

    return {
        accion: fecha.date()
        for accion, fecha in compras.groupby("Accion")["Fecha"].min().items()
    }


def construir_operaciones_precio_df(df, acciones=None):
    operaciones = df[
        (df["EstadoKey"] == "aprobada")
        & (df["TipoKey"].isin(["compra", "venta"]))
    ].copy()
    if acciones:
        operaciones = operaciones[operaciones["Accion"].isin(acciones)]
    if operaciones.empty:
        return pd.DataFrame()

    operaciones["Operacion"] = operaciones["Tipo"].str.capitalize()
    operaciones["Etiqueta"] = operaciones.apply(
        lambda fila: (
            f"{fila['Operacion']} | "
            f"{fila['Fecha'].strftime('%Y-%m-%d')} | "
            f"{fila['Precio unidad']:,.2f}"
        ),
        axis=1,
    )
    return operaciones[
        [
            "Accion",
            "Operacion",
            "Fecha",
            "Cantidad",
            "Precio unidad",
            "Total",
            "Etiqueta",
        ]
    ]


@st.cache_data(ttl=1800, show_spinner=False)
def descargar_historicos_yfinance(tickers_por_accion, fechas_inicio):
    if yf is None:
        raise RuntimeError("yfinance no esta instalado en el entorno.")

    historicos = []
    precios = []
    errores = []

    for accion, ticker in tickers_por_accion.items():
        ticker = str(ticker).strip().upper()
        fecha_inicio = fechas_inicio.get(accion)
        if not ticker or fecha_inicio is None:
            continue

        try:
            datos = yf.Ticker(ticker).history(
                start=fecha_inicio.isoformat(),
                auto_adjust=False,
            )
        except Exception as error:
            errores.append(f"{accion} ({ticker}): {error}")
            continue

        if datos.empty or "Close" not in datos:
            errores.append(f"{accion} ({ticker}): sin datos disponibles.")
            continue

        datos = datos.reset_index()
        columna_fecha = "Date" if "Date" in datos.columns else datos.columns[0]
        fechas = pd.to_datetime(datos[columna_fecha])
        if fechas.dt.tz is not None:
            fechas = fechas.dt.tz_convert(None)
        datos["Fecha"] = fechas
        datos["Accion"] = accion
        datos["Ticker"] = ticker
        datos = datos.dropna(subset=["Close"])

        if datos.empty:
            errores.append(f"{accion} ({ticker}): sin precios de cierre.")
            continue

        ultimo = datos.iloc[-1]
        precios.append(
            {
                "Accion": accion,
                "Ticker": ticker,
                "Fecha inicio": pd.to_datetime(fecha_inicio),
                "Ultima fecha": ultimo["Fecha"],
                "Precio actual": float(ultimo["Close"]),
            }
        )
        historicos.append(datos[["Fecha", "Accion", "Ticker", "Close"]])

    historico_df = pd.concat(historicos, ignore_index=True) if historicos else pd.DataFrame()
    precios_df = pd.DataFrame(precios)
    return historico_df, precios_df, errores


def grafico_historico_precios(historico_df):
    return (
        alt.Chart(historico_df)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("Fecha:T", title="Fecha"),
            y=alt.Y("Close:Q", title="Precio cierre"),
            color=alt.Color("Accion:N", legend=alt.Legend(title="Accion")),
            tooltip=[
                alt.Tooltip("Fecha:T", title="Fecha"),
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Ticker:N", title="Ticker"),
                alt.Tooltip("Close:Q", title="Cierre", format=",.2f"),
            ],
        )
        .properties(height=360)
    )


def grafico_historico_vs_operaciones(historico_df, operaciones_df):
    historico = historico_df.rename(columns={"Close": "Precio"}).copy()
    operaciones = operaciones_df.rename(columns={"Precio unidad": "Precio"}).copy()
    historico["Clase"] = "Historico"
    historico["Operacion"] = ""
    historico["Cantidad"] = None
    historico["Total"] = None
    historico["Etiqueta"] = ""
    operaciones["Clase"] = "Operacion"
    operaciones["Ticker"] = ""
    datos = pd.concat(
        [
            historico[
                [
                    "Fecha",
                    "Accion",
                    "Ticker",
                    "Precio",
                    "Clase",
                    "Operacion",
                    "Cantidad",
                    "Total",
                    "Etiqueta",
                ]
            ],
            operaciones[
                [
                    "Fecha",
                    "Accion",
                    "Ticker",
                    "Precio",
                    "Clase",
                    "Operacion",
                    "Cantidad",
                    "Total",
                    "Etiqueta",
                ]
            ],
        ],
        ignore_index=True,
    )

    base = alt.Chart(datos).encode(
        x=alt.X("Fecha:T", title="Fecha"),
        y=alt.Y("Precio:Q", title="Precio", scale=alt.Scale(zero=False)),
    )

    linea = base.transform_filter(
        alt.datum.Clase == "Historico"
    ).mark_line(strokeWidth=2.8, color="#60a5fa").encode(
        tooltip=[
            alt.Tooltip("Fecha:T", title="Fecha"),
            alt.Tooltip("Accion:N", title="Accion"),
            alt.Tooltip("Ticker:N", title="Ticker"),
            alt.Tooltip("Precio:Q", title="Cierre", format=",.2f"),
        ]
    )

    puntos = (
        base.transform_filter(alt.datum.Clase == "Operacion")
        .mark_point(filled=True, size=115, stroke="#f8fafc", strokeWidth=1.1)
        .encode(
            shape=alt.Shape(
                "Operacion:N",
                scale=alt.Scale(
                    domain=["Compra", "Venta"],
                    range=["triangle-up", "triangle-down"],
                ),
                legend=alt.Legend(title="Operacion"),
            ),
            color=alt.Color(
                "Operacion:N",
                scale=alt.Scale(
                    domain=["Compra", "Venta"],
                    range=["#22c55e", "#ef4444"],
                ),
                legend=alt.Legend(title="Tipo"),
            ),
            tooltip=[
                alt.Tooltip("Fecha:T", title="Fecha"),
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Operacion:N", title="Operacion"),
                alt.Tooltip("Cantidad:Q", title="Cantidad", format=",.0f"),
                alt.Tooltip("Precio:Q", title="Precio operacion", format=",.2f"),
                alt.Tooltip("Total:Q", title="Total", format=",.2f"),
            ],
        )
    )

    textos = (
        base.transform_filter(alt.datum.Clase == "Operacion")
        .mark_text(
            align="left",
            dx=7,
            dy=-9,
            fontSize=10,
            color="#f8fafc",
            opacity=0.85,
        )
        .encode(
            text=alt.Text("Etiqueta:N"),
        )
    )

    return (
        alt.layer(linea, puntos, textos)
        .properties(height=150)
        .facet(
            row=alt.Row(
                "Accion:N",
                title=None,
                header=alt.Header(labelColor="#f8fafc", labelFontSize=13),
            )
        )
        .resolve_scale(y="independent", color="independent")
    )


def grafico_valor_actual_por_accion(balance_actual):
    base = balance_actual[["Accion", "Valor actual", "Balance"]].copy()
    base["Resultado"] = base["Balance"].apply(
        lambda valor: "Ganancia" if valor >= 0 else "Perdida"
    )
    return (
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X("Accion:N", sort="-y", title=None),
            y=alt.Y("Valor actual:Q", title="Valor actual"),
            color=alt.Color(
                "Resultado:N",
                scale=alt.Scale(
                    domain=["Ganancia", "Perdida"],
                    range=["#0f766e", "#b91c1c"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Valor actual:Q", title="Valor actual", format=",.2f"),
                alt.Tooltip("Balance:Q", title="Balance", format=",.2f"),
            ],
        )
        .properties(height=280)
    )


def grafico_costo_vs_valor_actual(balance_actual):
    base = balance_actual[
        [
            "Accion",
            "Costo portafolio actual",
            "Valor actual",
            "Balance",
            "Rentabilidad %",
        ]
    ].copy()
    base = base.melt(
        id_vars=["Accion", "Balance", "Rentabilidad %"],
        value_vars=["Costo portafolio actual", "Valor actual"],
        var_name="Concepto",
        value_name="Valor",
    )
    base["Concepto"] = base["Concepto"].replace(
        {
            "Costo portafolio actual": "Costo",
            "Valor actual": "Valor actual",
        }
    )

    return (
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7)
        .encode(
            x=alt.X("Accion:N", title=None),
            xOffset=alt.XOffset("Concepto:N"),
            y=alt.Y("Valor:Q", title="Valor"),
            color=alt.Color(
                "Concepto:N",
                scale=alt.Scale(
                    domain=["Costo", "Valor actual"],
                    range=["#a16207", "#0f766e"],
                ),
                legend=alt.Legend(title="Comparacion"),
            ),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Concepto:N", title="Concepto"),
                alt.Tooltip("Valor:Q", title="Valor", format=",.2f"),
                alt.Tooltip("Balance:Q", title="Diferencia", format=",.2f"),
                alt.Tooltip("Rentabilidad %:Q", title="Rentabilidad %", format=",.2f"),
            ],
        )
        .properties(height=330)
    )


def grafico_precio_promedio_vs_actual(balance_actual):
    base = balance_actual[
        [
            "Accion",
            "Costo promedio compra",
            "Precio actual",
            "Rentabilidad %",
        ]
    ].copy()
    base = base.melt(
        id_vars=["Accion", "Rentabilidad %"],
        value_vars=["Costo promedio compra", "Precio actual"],
        var_name="Concepto",
        value_name="Precio por unidad",
    )
    base["Concepto"] = base["Concepto"].replace(
        {
            "Costo promedio compra": "Promedio compra",
            "Precio actual": "Precio actual",
        }
    )
    return (
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7)
        .encode(
            x=alt.X("Accion:N", title=None),
            xOffset=alt.XOffset("Concepto:N"),
            y=alt.Y("Precio por unidad:Q", title="Precio por unidad"),
            color=alt.Color(
                "Concepto:N",
                scale=alt.Scale(
                    domain=["Promedio compra", "Precio actual"],
                    range=["#a16207", "#0f766e"],
                ),
                legend=alt.Legend(title="Comparacion"),
            ),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Concepto:N", title="Concepto"),
                alt.Tooltip("Precio por unidad:Q", title="Precio por unidad", format=",.2f"),
                alt.Tooltip("Rentabilidad %:Q", title="Rentabilidad %", format=",.2f"),
            ],
        )
        .properties(height=330)
    )


def construir_serie_tiempo(df):
    aprobados = df[df["EstadoKey"] == "aprobada"].copy()
    if aprobados.empty:
        return pd.DataFrame()

    aprobados["Concepto"] = aprobados["TipoKey"].map(
        {
            "compra": "Compra",
            "venta": "Venta",
            "dividendo": "Dividendo",
        }
    )
    aprobados["Movimiento"] = aprobados.apply(
        lambda fila: fila["Total"] if fila["TipoKey"] == "compra" else -fila["Total"],
        axis=1,
    )
    aprobados["Dia"] = aprobados["Fecha"].dt.normalize()

    movimientos = aprobados.groupby(
        ["Dia", "Concepto"],
        as_index=False,
    )["Movimiento"].sum()
    acumulado = aprobados.groupby("Dia", as_index=False)["Movimiento"].sum()
    acumulado = acumulado.sort_values("Dia")
    acumulado["Capital neto invertido"] = acumulado["Movimiento"].cumsum()

    return movimientos.merge(
        acumulado[["Dia", "Capital neto invertido"]],
        on="Dia",
        how="left",
    )


def aplicar_filtros(df, acciones_seleccionadas, rango_fechas):
    filtrado = df.copy()
    if acciones_seleccionadas:
        filtrado = filtrado[filtrado["Accion"].isin(acciones_seleccionadas)]

    fecha_inicio, fecha_fin = rango_fechas
    mascara_fechas = (
        filtrado["Fecha"].dt.date.between(fecha_inicio, fecha_fin)
        if not filtrado.empty
        else []
    )
    filtrado = filtrado[mascara_fechas] if not filtrado.empty else filtrado
    return filtrado


def formatear_tabla(df, fondo, columnas_numericas, columna_fecha=None):
    if df.empty:
        return df

    tabla = df.copy()
    for columna in columnas_numericas:
        if columna in tabla.columns:
            tabla[columna] = tabla[columna].map(fondo._formatear_numero)

    if columna_fecha and columna_fecha in tabla.columns:
        tabla[columna_fecha] = tabla[columna_fecha].dt.strftime("%Y-%m-%d %H:%M")

    return tabla


def filtrar_eventos_por_rango(eventos, fecha_inicio, fecha_fin):
    if eventos.empty or "Fecha" not in eventos.columns:
        return eventos

    filtrado = eventos.copy()
    fechas = pd.to_datetime(filtrado["Fecha"], errors="coerce")
    if getattr(fechas.dt, "tz", None) is not None:
        fechas = fechas.dt.tz_convert(None)
    filtrado["Fecha"] = fechas
    return filtrado[
        filtrado["Fecha"].dt.date.between(fecha_inicio, fecha_fin)
    ].copy()


def mostrar_tabla_movimientos(titulo, df, fondo):
    st.subheader(titulo)
    if df.empty:
        st.info("Sin registros en esta categoria.")
        return

    tabla = df[
        [
            "Accion",
            "Tipo",
            "Estado",
            "Cantidad",
            "Precio unidad",
            "Inversion",
            "Comision",
            "Total",
            "Fecha texto",
        ]
    ].rename(columns={"Fecha texto": "Fecha"})
    tabla = formatear_tabla(
        tabla,
        fondo,
        ["Cantidad", "Precio unidad", "Inversion", "Comision", "Total"],
    )
    st.dataframe(tabla, width="stretch", hide_index=True)


def grafico_inversion_por_accion(resumen_general):
    base = resumen_general[["Accion", "Costo portafolio actual"]].copy()
    return (
        alt.Chart(base)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X("Accion:N", sort="-y", title=None),
            y=alt.Y("Costo portafolio actual:Q", title="Costo portafolio actual"),
            color=alt.Color(
                "Costo portafolio actual:Q",
                scale=alt.Scale(scheme="goldorange"),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip(
                    "Costo portafolio actual:Q", title="Costo", format=",.2f"
                ),
            ],
        )
        .properties(height=280)
    )


def grafico_acciones_por_accion(resumen_general):
    base = resumen_general[["Accion", "Acciones vigentes"]].copy()
    return (
        alt.Chart(base)
        .mark_arc(innerRadius=65, outerRadius=115)
        .encode(
            theta=alt.Theta("Acciones vigentes:Q"),
            color=alt.Color("Accion:N", legend=alt.Legend(title="Accion")),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Acciones vigentes:Q", title="Cantidad", format=",.0f"),
            ],
        )
        .properties(height=280)
    )


def grafico_ganancia_perdida(resumen_general):
    base = resumen_general[
        resumen_general["Cantidad vendida"] > 0
    ][["Accion", "Cantidad vendida", "Ventas netas", "Resultado realizado"]].copy()
    base["Resultado"] = base["Resultado realizado"].apply(
        lambda valor: "Ganancia" if valor >= 0 else "Perdida"
    )
    return (
        alt.Chart(base)
        .mark_bar(cornerRadiusEnd=7)
        .encode(
            y=alt.Y("Accion:N", sort="-x", title=None),
            x=alt.X("Resultado realizado:Q", title="Resultado"),
            color=alt.Color(
                "Resultado:N",
                scale=alt.Scale(
                    domain=["Ganancia", "Perdida"],
                    range=["#0f766e", "#b91c1c"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Cantidad vendida:Q", title="Cantidad vendida", format=",.0f"),
                alt.Tooltip("Ventas netas:Q", title="Ventas netas", format=",.2f"),
                alt.Tooltip("Resultado realizado:Q", title="Resultado", format=",.2f"),
            ],
        )
        .properties(height=280)
    )


def grafico_flujo(serie_tiempo):
    base = alt.Chart(serie_tiempo).encode(x=alt.X("Dia:T", title="Fecha"))

    barras = base.mark_bar(opacity=0.88).encode(
        y=alt.Y("Movimiento:Q", title="Movimiento diario"),
        color=alt.Color(
            "Concepto:N",
            scale=alt.Scale(
                domain=["Compra", "Venta", "Dividendo"],
                range=["#a16207", "#b91c1c", "#0f766e"],
            ),
            legend=alt.Legend(title="Tipo"),
        ),
        tooltip=[
            alt.Tooltip("Dia:T", title="Fecha"),
            alt.Tooltip("Concepto:N", title="Tipo"),
            alt.Tooltip("Movimiento:Q", title="Movimiento", format=",.2f"),
            alt.Tooltip(
                "Capital neto invertido:Q",
                title="Capital neto invertido",
                format=",.2f",
            ),
        ],
    ).properties(height=180, title="Movimiento diario")

    acumulado = serie_tiempo[
        ["Dia", "Capital neto invertido"]
    ].drop_duplicates().sort_values("Dia")

    linea = alt.Chart(acumulado).mark_line(
        color="#0f766e",
        strokeWidth=3,
        point=True,
    ).encode(
        x=alt.X("Dia:T", title="Fecha"),
        y=alt.Y("Capital neto invertido:Q", title="Capital neto invertido"),
        tooltip=[
            alt.Tooltip("Dia:T", title="Fecha"),
            alt.Tooltip(
                "Capital neto invertido:Q",
                title="Capital neto invertido",
                format=",.2f",
            ),
        ],
    ).properties(height=180, title="Capital neto invertido")

    regla_cero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        color="#6b7280",
        strokeDash=[4, 4],
    ).encode(
        y="y:Q",
    )

    return alt.vconcat(
        barras + regla_cero,
        linea,
    ).resolve_scale(x="shared")


def convertir_df_a_csv(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def obtener_x_secrets():
    bearer_env = os.environ.get("X_BEARER_TOKEN", "") or os.environ.get(
        "TWITTER_BEARER_TOKEN", ""
    )
    if bearer_env:
        return {"bearer_token": bearer_env, "source": ".env"}

    try:
        secrets = dict(st.secrets.get("x", {}))
        secrets["source"] = "st.secrets"
        return secrets
    except Exception:
        return {}


def leer_cuentas_x_monitoreadas():
    if not ARCHIVO_X_CUENTAS.exists():
        return pd.DataFrame(
            columns=[
                "username",
                "nombre",
                "tipo",
                "score_autoridad",
                "region",
                "temas",
                "palabras_clave",
                "activo",
            ]
        )
    cuentas = pd.read_csv(ARCHIVO_X_CUENTAS)
    if "activo" in cuentas:
        cuentas["activo"] = cuentas["activo"].astype(str).str.lower().isin(["true", "1", "si", "sí"])
    return cuentas


def construir_query_x_cuentas(cuentas):
    acciones = " OR ".join(ACCIONES_COLOMBIANAS)
    if cuentas.empty:
        return f"({acciones}) -is:retweet"
    activas = cuentas[cuentas["activo"]] if "activo" in cuentas else cuentas
    autores = [f"from:{usuario}" for usuario in activas["username"].dropna().astype(str)]
    if not autores:
        return f"({acciones}) -is:retweet"
    return f"(({acciones}) OR ({' OR '.join(autores)})) -is:retweet"


def leer_cache_x_posts():
    if not ARCHIVO_X_POSTS.exists():
        return pd.DataFrame()
    posts = pd.read_csv(ARCHIVO_X_POSTS)
    if "Fecha" in posts:
        posts["Fecha"] = pd.to_datetime(posts["Fecha"], errors="coerce", utc=True).dt.tz_convert(None)
    return posts


def guardar_cache_x_posts(posts):
    posts.to_csv(ARCHIVO_X_POSTS, index=False, encoding="utf-8-sig")


def x_api_get(bearer_token, endpoint, params=None):
    respuesta = requests.get(
        f"{X_BASE_URL}{endpoint}",
        params=params or {},
        headers={"Authorization": f"Bearer {bearer_token}"},
        timeout=20,
    )
    if not respuesta.ok:
        raise RuntimeError(f"X API {respuesta.status_code}: {respuesta.text}")
    return respuesta.json()


def buscar_posts_x(bearer_token, query, max_results):
    respuesta = x_api_get(
        bearer_token,
        "/tweets/search/recent",
        {
            "query": query,
            "max_results": int(max_results),
            "tweet.fields": "created_at,lang,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "name,username,verified,public_metrics",
        },
    )
    usuarios = {
        usuario["id"]: usuario for usuario in respuesta.get("includes", {}).get("users", [])
    }
    filas = []
    for post in respuesta.get("data", []):
        usuario = usuarios.get(post.get("author_id"), {})
        metricas = post.get("public_metrics", {})
        metricas_usuario = usuario.get("public_metrics", {})
        filas.append(
            {
                "Id": str(post.get("id", "")),
                "Fecha": pd.to_datetime(post.get("created_at"), utc=True).tz_convert(None),
                "Autor": usuario.get("username", ""),
                "Nombre": usuario.get("name", ""),
                "Verificado": bool(usuario.get("verified", False)),
                "Seguidores": metricas_usuario.get("followers_count", 0),
                "Texto": post.get("text", ""),
                "Idioma": post.get("lang", ""),
                "Likes": metricas.get("like_count", 0),
                "Respuestas": metricas.get("reply_count", 0),
                "Reposts": metricas.get("retweet_count", 0),
                "Citas": metricas.get("quote_count", 0),
            }
        )
    posts = pd.DataFrame(filas)
    if not posts.empty:
        posts["Engagement"] = posts[["Likes", "Respuestas", "Reposts", "Citas"]].sum(axis=1)
    return posts


def consultar_y_cachear_x_posts(bearer_token, query, max_results):
    nuevos = buscar_posts_x(bearer_token, query, max_results)
    cache = leer_cache_x_posts()
    if nuevos.empty:
        return cache, nuevos
    combinado = pd.concat([nuevos, cache], ignore_index=True)
    combinado = combinado.drop_duplicates(subset=["Id"]).sort_values("Fecha", ascending=False)
    guardar_cache_x_posts(combinado)
    return combinado, nuevos


def grafico_x_menciones(posts):
    base = posts.dropna(subset=["Fecha"]).copy()
    base["Dia"] = base["Fecha"].dt.date
    resumen = base.groupby("Dia", as_index=False).size()
    return (
        alt.Chart(resumen)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("Dia:T", title="Fecha"),
            y=alt.Y("size:Q", title="Posts"),
            tooltip=[alt.Tooltip("Dia:T", title="Fecha"), alt.Tooltip("size:Q", title="Posts")],
        )
        .properties(height=260)
    )


def grafico_x_posts_por_autor(posts):
    resumen = posts.groupby("Autor", as_index=False).size().sort_values("size", ascending=False)
    return (
        alt.Chart(resumen)
        .mark_bar(cornerRadiusTopRight=6)
        .encode(
            y=alt.Y("Autor:N", sort="-x", title=None),
            x=alt.X("size:Q", title="Posts"),
            tooltip=["Autor:N", alt.Tooltip("size:Q", title="Posts")],
        )
        .properties(height=260)
    )


def asociar_posts_con_acciones(posts):
    if posts.empty:
        return pd.DataFrame()

    filas = []
    for post in posts.to_dict("records"):
        texto = str(post.get("Texto", "")).upper()
        for accion in ACCIONES_COLOMBIANAS:
            if accion in texto:
                filas.append({**post, "Accion": accion})
    return pd.DataFrame(filas)


def construir_eventos_noticias_df(posts_acciones, historico_df):
    if posts_acciones.empty or historico_df.empty:
        return pd.DataFrame()

    eventos = []
    historico_ordenado = historico_df.copy()
    historico_ordenado["Fecha"] = pd.to_datetime(historico_ordenado["Fecha"])

    for post in posts_acciones.to_dict("records"):
        serie = historico_ordenado[
            historico_ordenado["Accion"] == post["Accion"]
        ].sort_values("Fecha")
        if serie.empty:
            continue

        fecha_post = pd.to_datetime(post["Fecha"])
        posteriores = serie[serie["Fecha"] >= fecha_post.normalize()]
        if posteriores.empty:
            continue

        fila_precio = posteriores.iloc[0]
        eventos.append(
            {
                **post,
                "Fecha evento": fila_precio["Fecha"],
                "Precio evento": float(fila_precio["Close"]),
            }
        )
    return pd.DataFrame(eventos)


def calcular_impacto_noticias(eventos_noticias, historico_df):
    if eventos_noticias.empty or historico_df.empty:
        return pd.DataFrame()

    filas = []
    historico = historico_df.copy()
    historico["Fecha"] = pd.to_datetime(historico["Fecha"])

    for evento in eventos_noticias.to_dict("records"):
        serie = historico[historico["Accion"] == evento["Accion"]].sort_values("Fecha")
        indice_evento = serie.index[serie["Fecha"] == evento["Fecha evento"]]
        if indice_evento.empty:
            continue
        posicion = serie.index.get_loc(indice_evento[0])
        fila = {
            "Accion": evento["Accion"],
            "Fecha post": evento["Fecha"],
            "Fecha evento": evento["Fecha evento"],
            "Autor": evento.get("Autor", ""),
            "Texto": evento.get("Texto", ""),
            "Precio evento": evento["Precio evento"],
        }
        for ventana in [1, 3, 5]:
            if posicion - ventana >= 0:
                precio_pasado = float(serie.iloc[posicion - ventana]["Close"])
                fila[f"Retorno previo {ventana} sesiones %"] = (
                    (evento["Precio evento"] / precio_pasado) - 1
                ) * 100
            else:
                fila[f"Retorno previo {ventana} sesiones %"] = None
            if posicion + ventana < len(serie):
                precio_futuro = float(serie.iloc[posicion + ventana]["Close"])
                fila[f"Retorno +{ventana} sesiones %"] = (
                    (precio_futuro / evento["Precio evento"]) - 1
                ) * 100
            else:
                fila[f"Retorno +{ventana} sesiones %"] = None
        filas.append(fila)
    return pd.DataFrame(filas)


def resumir_impacto_noticias(impacto_noticias):
    if impacto_noticias.empty:
        return pd.DataFrame()
    columnas_retorno = [col for col in impacto_noticias if col.startswith("Retorno +")]
    datos = impacto_noticias.copy()
    for ventana in [1, 3, 5]:
        columna = f"Retorno +{ventana} sesiones %"
        datos[f"Noticias positivas +{ventana} sesiones %"] = datos[columna].gt(0)
    return (
        datos.groupby("Accion", as_index=False)
        .agg(
            Noticias=("Accion", "size"),
            **{
                columna: (columna, "mean")
                for columna in columnas_retorno
            },
            **{
                f"Noticias positivas +{ventana} sesiones %": (
                    f"Noticias positivas +{ventana} sesiones %",
                    "mean",
                )
                for ventana in [1, 3, 5]
            },
        )
        .sort_values("Noticias", ascending=False)
    )


def grafico_historico_vs_noticias(historico_df, eventos_noticias):
    historico = historico_df.rename(columns={"Close": "Precio"}).copy()
    noticias = eventos_noticias.rename(
        columns={"Fecha evento": "Fecha", "Precio evento": "Precio"}
    ).copy()

    linea = (
        alt.Chart(historico)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("Fecha:T", title="Fecha"),
            y=alt.Y("Precio:Q", title="Precio cierre", scale=alt.Scale(zero=False)),
            color=alt.Color("Accion:N", legend=alt.Legend(title="Accion")),
            tooltip=[
                alt.Tooltip("Fecha:T", title="Fecha"),
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Precio:Q", title="Cierre", format=",.2f"),
            ],
        )
    )
    puntos = (
        alt.Chart(noticias)
        .mark_point(size=110, filled=True, shape="diamond", color="#7c2d12")
        .encode(
            x="Fecha:T",
            y="Precio:Q",
            tooltip=[
                alt.Tooltip("Fecha:T", title="Fecha bursatil"),
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Autor:N", title="Autor"),
                alt.Tooltip("Texto:N", title="Post"),
                alt.Tooltip("Precio:Q", title="Cierre", format=",.2f"),
            ],
        )
    )
    return (linea + puntos).properties(height=380)


def construir_impacto_largo(impacto_noticias):
    if impacto_noticias.empty:
        return pd.DataFrame()
    columnas = [f"Retorno +{ventana} sesiones %" for ventana in [1, 3, 5]]
    largo = impacto_noticias.melt(
        id_vars=["Accion", "Fecha post", "Autor"],
        value_vars=columnas,
        var_name="Ventana",
        value_name="Retorno %",
    ).dropna(subset=["Retorno %"])
    largo["Ventana"] = largo["Ventana"].str.replace("Retorno +", "", regex=False)
    return largo


def grafico_impacto_promedio(resumen_impacto):
    if resumen_impacto.empty:
        return alt.Chart(pd.DataFrame({"x": [], "y": []}))
    columnas = [f"Retorno +{ventana} sesiones %" for ventana in [1, 3, 5]]
    largo = resumen_impacto.melt(
        id_vars=["Accion"],
        value_vars=columnas,
        var_name="Ventana",
        value_name="Retorno promedio %",
    )
    largo["Ventana"] = largo["Ventana"].str.replace("Retorno +", "", regex=False)
    return (
        alt.Chart(largo)
        .mark_bar()
        .encode(
            x=alt.X("Ventana:N", title="Ventana posterior"),
            y=alt.Y("Retorno promedio %:Q", title="Retorno promedio %"),
            color=alt.Color("Accion:N", legend=alt.Legend(title="Accion")),
            column=alt.Column("Accion:N", title=None),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Ventana:N", title="Ventana"),
                alt.Tooltip("Retorno promedio %:Q", title="Retorno promedio", format=",.2f"),
            ],
        )
        .properties(height=260)
    )


def grafico_distribucion_impacto(impacto_noticias):
    largo = construir_impacto_largo(impacto_noticias)
    if largo.empty:
        return alt.Chart(pd.DataFrame({"x": [], "y": []}))
    return (
        alt.Chart(largo)
        .mark_circle(size=90, opacity=0.75)
        .encode(
            x=alt.X("Ventana:N", title="Ventana posterior"),
            y=alt.Y("Retorno %:Q", title="Retorno por noticia %"),
            color=alt.Color("Accion:N", legend=alt.Legend(title="Accion")),
            tooltip=[
                alt.Tooltip("Accion:N", title="Accion"),
                alt.Tooltip("Ventana:N", title="Ventana"),
                alt.Tooltip("Retorno %:Q", title="Retorno", format=",.2f"),
                alt.Tooltip("Fecha post:T", title="Fecha post"),
                alt.Tooltip("Autor:N", title="Autor"),
            ],
        )
        .properties(height=280)
    )


def construir_timeline_accion(historico_df, accion):
    serie = historico_df[historico_df["Accion"] == accion].sort_values("Fecha").copy()
    if serie.empty:
        return pd.DataFrame()
    serie["Variacion diaria %"] = serie["Close"].pct_change() * 100
    precio_inicial = float(serie.iloc[0]["Close"])
    serie["Variacion acumulada %"] = ((serie["Close"] / precio_inicial) - 1) * 100
    return serie


def preparar_eventos_timeline(eventos_noticias, accion, serie, metrica):
    if eventos_noticias.empty or serie.empty:
        return pd.DataFrame()
    eventos = eventos_noticias[eventos_noticias["Accion"] == accion].copy()
    if eventos.empty:
        return pd.DataFrame()
    valor_por_fecha = serie.set_index("Fecha")[metrica].to_dict()
    eventos["Valor"] = eventos["Fecha evento"].map(valor_por_fecha)
    return eventos.dropna(subset=["Valor"])


def grafico_timeline_con_noticias(serie, eventos, metrica):
    titulo_y = {
        "Close": "Precio de cierre",
        "Variacion acumulada %": "Variacion acumulada %",
        "Variacion diaria %": "Variacion diaria %",
    }[metrica]
    tooltip_linea = [
        alt.Tooltip("Fecha:T", title="Fecha"),
        alt.Tooltip("Close:Q", title="Cierre", format=",.2f"),
        alt.Tooltip("Variacion acumulada %:Q", title="Variacion acumulada", format=",.2f"),
        alt.Tooltip("Variacion diaria %:Q", title="Variacion diaria", format=",.2f"),
    ]
    base = alt.Chart(serie).encode(
        x=alt.X("Fecha:T", title="Fecha"),
        y=alt.Y(f"{metrica}:Q", title=titulo_y, scale=alt.Scale(zero=False)),
    )

    if metrica == "Variacion diaria %":
        linea = base.mark_bar(opacity=0.8, color="#0f766e").encode(
            tooltip=tooltip_linea,
            color=alt.condition(
                alt.datum["Variacion diaria %"] >= 0,
                alt.value("#0f766e"),
                alt.value("#b91c1c"),
            ),
        )
    else:
        linea = base.mark_line(strokeWidth=3, color="#0f766e").encode(
            tooltip=tooltip_linea
        )

    if eventos.empty:
        return linea.properties(height=360)

    noticias = (
        alt.Chart(eventos)
        .mark_point(size=130, filled=True, shape="diamond", color="#7c2d12")
        .encode(
            x=alt.X("Fecha evento:T"),
            y=alt.Y("Valor:Q"),
            tooltip=[
                alt.Tooltip("Fecha post:T", title="Fecha post"),
                alt.Tooltip("Fecha evento:T", title="Sesion asociada"),
                alt.Tooltip("Autor:N", title="Autor"),
                alt.Tooltip("Texto:N", title="Noticia"),
                alt.Tooltip("Valor:Q", title=titulo_y, format=",.2f"),
            ],
        )
    )
    return (linea + noticias).properties(height=360)


def main():
    st.set_page_config(
        page_title="Fondo de Acciones",
        page_icon=":bar_chart:",
        layout="wide",
    )
    cargar_env_local()
    aplicar_estilos()

    fuentes = ["Datos integrados"]
    if ARCHIVO_LOCAL.exists():
        fuentes.insert(0, "CSV local")
    fuentes.append("Archivo subido")

    with st.sidebar:
        st.header("Fuente de datos")
        origen = st.radio("Selecciona la fuente", options=fuentes, index=0)
        archivo_subido = None
        if origen == "Archivo subido":
            archivo_subido = st.file_uploader(
                "Sube un archivo",
                type=["csv", "xlsx"],
                help="Para archivos XLSX se necesita openpyxl en el entorno.",
            )

    try:
        fondo, descripcion = construir_fondo(origen, archivo_subido)
    except Exception as error:
        st.error(str(error))
        st.stop()

    df = construir_movimientos_df(fondo)
    if df.empty:
        st.warning("No hay movimientos para mostrar.")
        st.stop()

    acciones_disponibles = sorted(df["Accion"].unique().tolist())
    fecha_min = df["Fecha"].min().date()
    fecha_max_movimientos = df["Fecha"].max().date()
    fecha_actual = pd.Timestamp.today().date()
    fecha_max = fecha_actual

    with st.sidebar:
        st.divider()
        st.header("Filtros")
        acciones_seleccionadas = st.multiselect(
            "Acciones",
            options=acciones_disponibles,
            default=acciones_disponibles,
        )
        rango_fechas = st.date_input(
            "Rango de fechas",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max,
            key=f"rango_fechas_hasta_{fecha_actual.isoformat()}",
        )
        st.divider()
        st.header("Yahoo Finance")
        usar_yfinance = st.checkbox("Traer precios actuales", value=True)
        tickers_yfinance = {}
        with st.expander("Tickers"):
            for accion in acciones_disponibles:
                tickers_yfinance[accion] = st.text_input(
                    accion,
                    value=TICKERS_YFINANCE.get(accion, f"{accion}.CL"),
                    key=f"ticker_yfinance_{accion}",
                )
        st.divider()
        st.header("Noticias de X")
        usar_x_api = st.checkbox("Traer noticias de X", value=False)
        x_secrets = obtener_x_secrets()
        if x_secrets.get("source") == ".env":
            x_bearer_token = x_secrets.get("bearer_token", "")
            st.caption("Token de X cargado desde .env")
        else:
            x_bearer_token = st.text_input(
                "Bearer token",
                value=x_secrets.get("bearer_token", ""),
                type="password",
                key="x_bearer_token_manual",
            )
        cuentas_x = leer_cuentas_x_monitoreadas()
        x_query = st.text_area("Query X", value=construir_query_x_cuentas(cuentas_x), height=90)
        x_max_results = st.number_input("Max posts", min_value=10, max_value=100, value=20, step=10)


    if not isinstance(rango_fechas, tuple) or len(rango_fechas) != 2:
        rango_fechas = (fecha_min, fecha_max)

    df_filtrado = aplicar_filtros(df, acciones_seleccionadas, rango_fechas)
    if df_filtrado.empty:
        st.warning("No hay movimientos con los filtros seleccionados.")
        st.stop()

    resumen_general = construir_resumen_general(df_filtrado)
    indicadores, resumen_financiero = construir_resumen_financiero(
        fondo, df_filtrado, resumen_general
    )
    serie_tiempo = construir_serie_tiempo(df_filtrado)

    compras_aprobadas = df_filtrado[
        (df_filtrado["EstadoKey"] == "aprobada")
        & (df_filtrado["TipoKey"] == "compra")
    ].copy()
    ventas = df_filtrado[
        (df_filtrado["EstadoKey"] == "aprobada")
        & (df_filtrado["TipoKey"] == "venta")
    ].copy()
    dividendos = df_filtrado[
        (df_filtrado["EstadoKey"] == "aprobada")
        & (df_filtrado["TipoKey"] == "dividendo")
    ].copy()
    canceladas = df_filtrado[df_filtrado["EstadoKey"] == "cancelada"].copy()
    posiciones_vigentes = resumen_general[resumen_general["Acciones vigentes"] > 0]

    historico_yfinance = pd.DataFrame()
    precios_yfinance = pd.DataFrame()
    errores_yfinance = []
    balance_yfinance = pd.DataFrame()
    posts_x = leer_cache_x_posts()
    posts_x_nuevos = pd.DataFrame()
    error_x_api = None
    operaciones_precio = construir_operaciones_precio_df(
        df_filtrado,
        posiciones_vigentes["Accion"].tolist(),
    )
    posts_x_acciones = asociar_posts_con_acciones(posts_x)
    if usar_yfinance and not posiciones_vigentes.empty:
        acciones_vigentes = posiciones_vigentes["Accion"].tolist()
        tickers_posiciones = {
            accion: tickers_yfinance.get(accion, "")
            for accion in acciones_vigentes
        }
        fechas_inicio_yfinance = obtener_fechas_inicio_yfinance(df_filtrado)
        with st.spinner("Consultando Yahoo Finance..."):
            try:
                (
                    historico_yfinance,
                    precios_yfinance,
                    errores_yfinance,
                ) = descargar_historicos_yfinance(
                    tickers_posiciones,
                    fechas_inicio_yfinance,
                )
            except Exception as error:
                errores_yfinance = [str(error)]

    if not precios_yfinance.empty:
        precios_yfinance_map = precios_yfinance.set_index("Accion")[
            "Precio actual"
        ].to_dict()
        balance_yfinance = construir_balance_actual(
            resumen_general,
            precios_yfinance_map,
        )

    if usar_x_api:
        if not x_bearer_token:
            error_x_api = "Ingresa X_BEARER_TOKEN en .env o pega un bearer token en la barra lateral."
        else:
            with st.spinner("Consultando X API..."):
                try:
                    posts_x, posts_x_nuevos = consultar_y_cachear_x_posts(
                        x_bearer_token,
                        x_query,
                        x_max_results,
                    )
                except Exception as error:
                    error_x_api = str(error)

    posts_x_acciones = asociar_posts_con_acciones(posts_x)
    eventos_noticias = construir_eventos_noticias_df(posts_x_acciones, historico_yfinance)
    impacto_noticias = calcular_impacto_noticias(eventos_noticias, historico_yfinance)
    resumen_impacto_noticias = resumir_impacto_noticias(impacto_noticias)



    st.markdown(
        f"""
        <section class="hero">
            <div class="hero-kicker">Dashboard financiero</div>
            <h1>Fondo de Acciones</h1>
            <p>{descripcion} Vista filtrada entre {rango_fechas[0]} y {rango_fechas[1]} para {len(acciones_seleccionadas)} acciones. Ultimo movimiento registrado: {fecha_max_movimientos}.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    metrica_1, metrica_2, metrica_3, metrica_4 = st.columns(4)
    metrica_1.metric(
        "Costo portafolio actual",
        fondo._formatear_numero(indicadores["Costo portafolio actual"]),
    )
    metrica_2.metric(
        "Flujo neto invertido",
        fondo._formatear_numero(indicadores["Flujo neto invertido"]),
    )
    metrica_3.metric(
        "Disponible para invertir",
        fondo._formatear_numero(
            indicadores["Disponible para invertir (dinero a favor)"]
        ),
    )
    metrica_4.metric(
        "Resultado realizado",
        fondo._formatear_numero(indicadores["Resultado realizado"]),
    )

    metrica_5, metrica_6, metrica_7, metrica_8 = st.columns(4)
    metrica_5.metric(
        "Ventas netas",
        fondo._formatear_numero(indicadores["Ventas netas"]),
    )
    metrica_6.metric(
        "Comisiones acumuladas",
        fondo._formatear_numero(indicadores["Comisiones acumuladas"]),
    )
    metrica_7.metric(
        "Dividendos netos",
        fondo._formatear_numero(indicadores["Dividendos netos"]),
    )
    metrica_8.metric(
        "Acciones vigentes",
        fondo._formatear_numero(indicadores["Acciones vigentes"]),
    )

    if not balance_yfinance.empty:
        total_valor_yfinance = balance_yfinance["Valor actual"].sum()
        total_balance_yfinance = balance_yfinance["Balance"].sum()
        total_costo_yfinance = balance_yfinance["Costo portafolio actual"].sum()
        rentabilidad_yfinance = (
            (total_balance_yfinance / total_costo_yfinance) * 100
            if total_costo_yfinance > 0
            else 0.0
        )

        valor_col, balance_col, rentabilidad_col = st.columns(3)
        valor_col.metric(
            "Valor actual acciones",
            fondo._formatear_numero(total_valor_yfinance),
        )
        balance_col.metric(
            "Balance a precio actual",
            fondo._formatear_numero(total_balance_yfinance),
        )
        rentabilidad_col.metric(
            "Rentabilidad actual",
            f"{fondo._formatear_numero(rentabilidad_yfinance)}%",
        )

    resumen_col, descarga_col = st.columns([3, 1])
    with resumen_col:
        st.caption(descripcion)
    with descarga_col:
        st.download_button(
            "Descargar vista filtrada",
            data=convertir_df_a_csv(df_filtrado),
            file_name="movimientos_filtrados.csv",
            mime="text/csv",
            width="stretch",
        )

    col_izquierda, col_derecha = st.columns(2)
    with col_izquierda:
        st.subheader("Costo vs valor actual por accion")
        if balance_yfinance.empty:
            st.altair_chart(
                grafico_inversion_por_accion(resumen_general),
                width="stretch",
            )
        else:
            st.altair_chart(
                grafico_costo_vs_valor_actual(balance_yfinance),
                width="stretch",
            )

        st.subheader("Resultado realizado por ventas")
        acciones_con_ventas = resumen_general[
            resumen_general["Cantidad vendida"] > 0
        ]
        if acciones_con_ventas.empty:
            st.info("No hay ventas realizadas en el rango seleccionado.")
        else:
            st.caption(
                f"Solo {len(acciones_con_ventas)} accion(es) tienen ventas realizadas; las demas se mantienen vigentes."
            )
            st.altair_chart(
                grafico_ganancia_perdida(resumen_general),
                width="stretch",
            )

    with col_derecha:
        st.subheader("Cantidad de acciones vigentes")
        st.altair_chart(
            grafico_acciones_por_accion(resumen_general),
            width="stretch",
        )

        st.subheader("Diferencia actual por accion")
        if balance_yfinance.empty:
            st.info("Activa Yahoo Finance para graficar el valor actual.")
        else:
            st.altair_chart(
                grafico_valor_actual_por_accion(balance_yfinance),
                width="stretch",
            )

    st.subheader("Capital neto invertido")
    if serie_tiempo.empty:
        st.info("No hay suficientes movimientos aprobados para graficar el flujo.")
    else:
        st.caption(
            "Arriba ves el movimiento diario: las compras suman y las ventas/dividendos restan. Abajo ves el capital neto que sigue invertido despues de cada movimiento."
        )
        st.altair_chart(grafico_flujo(serie_tiempo), width="stretch")

    tablas = st.tabs(
        [
            "Compras aprobadas",
            "Ventas",
            "Dividendos",
            "Canceladas",
            "Resumen por accion",
            "Historico y precios",
            "Balance actual",
            "Noticias X",
            "Resumen financiero",
        ]
    )

    with tablas[0]:
        mostrar_tabla_movimientos("Compras aprobadas", compras_aprobadas, fondo)

    with tablas[1]:
        mostrar_tabla_movimientos("Ventas", ventas, fondo)

    with tablas[2]:
        mostrar_tabla_movimientos("Dividendos", dividendos, fondo)

    with tablas[3]:
        mostrar_tabla_movimientos("Canceladas", canceladas, fondo)

    with tablas[4]:
        st.subheader("Resumen general por accion")
        resumen_mostrable = formatear_tabla(
            resumen_general,
            fondo,
            [
                "Cantidad comprada",
                "Total comprado",
                "Cantidad vendida",
                "Ventas netas",
                "Dividendos netos",
                "Acciones vigentes",
                "Costo promedio compra",
                "Costo portafolio actual",
                "Resultado realizado",
                "Cantidad cancelada",
                "Total cancelado",
            ],
        )
        st.dataframe(resumen_mostrable, width="stretch", hide_index=True)

    with tablas[5]:
        st.subheader("Historico desde la primera compra")
        if not usar_yfinance:
            st.info("Activa Yahoo Finance en la barra lateral para consultar precios.")
        elif precios_yfinance.empty:
            st.warning("No se encontraron precios en Yahoo Finance para las posiciones vigentes.")
        else:
            acciones_grafico = st.multiselect(
                "Acciones para comparar",
                options=precios_yfinance["Accion"].tolist(),
                default=precios_yfinance["Accion"].tolist(),
                key="acciones_historico_vs_operaciones",
            )
            historico_comparado = historico_yfinance[
                historico_yfinance["Accion"].isin(acciones_grafico)
            ].copy()
            operaciones_comparadas = operaciones_precio[
                operaciones_precio["Accion"].isin(acciones_grafico)
            ].copy()

            precios_mostrables = precios_yfinance.copy()
            precios_mostrables["Fecha inicio"] = precios_mostrables[
                "Fecha inicio"
            ].dt.strftime("%Y-%m-%d")
            precios_mostrables["Ultima fecha"] = precios_mostrables[
                "Ultima fecha"
            ].dt.strftime("%Y-%m-%d")
            precios_mostrables = formatear_tabla(
                precios_mostrables,
                fondo,
                ["Precio actual"],
            )
            st.dataframe(precios_mostrables, width="stretch", hide_index=True)

            eventos_noticias_comparados = eventos_noticias[
                eventos_noticias["Accion"].isin(acciones_grafico)
            ].copy() if not eventos_noticias.empty else pd.DataFrame()

            if not historico_comparado.empty and not eventos_noticias_comparados.empty:
                st.caption(
                    "Los diamantes marcan noticias de X asociadas a la accion y se ubican en la primera sesion bursatil disponible posterior al post."
                )
                st.altair_chart(
                    grafico_historico_vs_noticias(
                        historico_comparado,
                        eventos_noticias_comparados,
                    ),
                    width="stretch",
                )
            elif not historico_comparado.empty and not operaciones_comparadas.empty:
                st.altair_chart(
                    grafico_historico_vs_operaciones(
                        historico_comparado,
                        operaciones_comparadas,
                    ),
                    width="stretch",
                )
            elif not historico_comparado.empty:
                st.altair_chart(
                    grafico_historico_precios(historico_comparado),
                    width="stretch",
                )
            if not balance_yfinance.empty:
                total_valor_yfinance = balance_yfinance["Valor actual"].sum()
                st.metric(
                    "Suma valor actual de acciones",
                    fondo._formatear_numero(total_valor_yfinance),
                )
                st.altair_chart(
                    grafico_valor_actual_por_accion(balance_yfinance),
                    width="stretch",
                )

            st.subheader("Linea de tiempo de noticias e impacto")
            accion_timeline = st.selectbox(
                "Accion para analizar",
                options=acciones_grafico,
                key="accion_timeline_noticias",
            )
            metrica_timeline = st.radio(
                "Metrica de la linea",
                options=["Variacion acumulada %", "Variacion diaria %", "Close"],
                format_func=lambda valor: {
                    "Variacion acumulada %": "Variacion acumulada",
                    "Variacion diaria %": "Variacion diaria",
                    "Close": "Precio de cierre",
                }[valor],
                horizontal=True,
                key="metrica_timeline_noticias",
            )
            serie_timeline = construir_timeline_accion(
                historico_comparado,
                accion_timeline,
            )
            eventos_timeline = preparar_eventos_timeline(
                eventos_noticias_comparados,
                accion_timeline,
                serie_timeline,
                metrica_timeline,
            )
            st.caption(
                "Los diamantes muestran noticias relacionadas con la accion seleccionada. Para comparar reacciones, la vista recomendada es 'Variacion acumulada'."
            )
            st.altair_chart(
                grafico_timeline_con_noticias(
                    serie_timeline,
                    eventos_timeline,
                    metrica_timeline,
                ),
                width="stretch",
            )

        for error in errores_yfinance:
            st.caption(error)

    with tablas[6]:
        st.subheader("Balance actual por accion")
        if posiciones_vigentes.empty:
            st.info("No hay acciones vigentes para calcular balance.")
        else:
            st.caption(
                "Los precios vienen de Yahoo Finance cuando estan disponibles. Puedes ajustarlos manualmente antes de calcular el balance."
            )

            precios_actuales = {}
            precios_yfinance_map = (
                precios_yfinance.set_index("Accion")["Precio actual"].to_dict()
                if not precios_yfinance.empty
                else {}
            )
            columnas_precios = st.columns(3)
            for indice, fila in enumerate(posiciones_vigentes.to_dict("records")):
                with columnas_precios[indice % 3]:
                    precio_base = precios_yfinance_map.get(
                        fila["Accion"],
                        fila["Costo promedio compra"],
                    )
                    precios_actuales[fila["Accion"]] = st.number_input(
                        f"Precio actual de {fila['Accion']}",
                        min_value=0.0,
                        value=float(precio_base),
                        step=1.0,
                        format="%.2f",
                        key=f"precio_actual_{fila['Accion']}",
                    )

            balance_actual = construir_balance_actual(resumen_general, precios_actuales)
            total_costo = balance_actual["Costo portafolio actual"].sum()
            total_valor = balance_actual["Valor actual"].sum()
            total_balance = balance_actual["Balance"].sum()

            balance_m1, balance_m2, balance_m3 = st.columns(3)
            balance_m1.metric("Costo base vigente", fondo._formatear_numero(total_costo))
            balance_m2.metric("Valor actual", fondo._formatear_numero(total_valor))
            balance_m3.metric("Balance", fondo._formatear_numero(total_balance))

            st.subheader("Precio promedio de compra vs precio actual")
            st.caption(
                "Comparacion por unidad: permite ver rapidamente si cada accion cotiza por encima o por debajo de tu costo promedio."
            )
            st.altair_chart(
                grafico_precio_promedio_vs_actual(balance_actual),
                width="stretch",
            )

            balance_mostrable = formatear_tabla(
                balance_actual,
                fondo,
                [
                    "Acciones vigentes",
                    "Costo promedio compra",
                    "Costo portafolio actual",
                    "Precio actual",
                    "Valor actual",
                    "Balance",
                ],
            )
            balance_mostrable["Rentabilidad %"] = balance_actual["Rentabilidad %"].map(
                lambda valor: f"{fondo._formatear_numero(valor)}%"
            )
            st.dataframe(balance_mostrable, width="stretch", hide_index=True)

    with tablas[7]:
        st.subheader("Noticias de X")
        st.caption(
            "La caché local se muestra aunque no haya token. Para refrescar noticias en vivo, usa tu propio token de X."
        )
        if error_x_api:
            st.error(error_x_api)
        elif posts_x.empty:
            st.info("Aun no hay noticias cacheadas. Activa 'Traer noticias de X' para descargar publicaciones recientes.")
        else:
            x1, x2, x3 = st.columns(3)
            x1.metric("Posts cacheados", fondo._formatear_numero(len(posts_x)))
            x2.metric("Nuevos descargados", fondo._formatear_numero(len(posts_x_nuevos)))
            x3.metric("Posts asociados a acciones", fondo._formatear_numero(len(posts_x_acciones)))
            st.altair_chart(grafico_x_menciones(posts_x), width="stretch")
            st.altair_chart(grafico_x_posts_por_autor(posts_x), width="stretch")
            st.subheader("Impacto posterior por accion")
            st.caption(
                "Lectura descriptiva: mide la variacion del cierre tras 1, 3 y 5 sesiones; no prueba causalidad por si sola."
            )
            if resumen_impacto_noticias.empty:
                st.info("Aun no hay noticias asociadas a acciones colombianas con suficiente historico para medir impacto.")
            else:
                resumen_impacto_mostrable = formatear_tabla(
                    resumen_impacto_noticias,
                    fondo,
                    [
                        "Noticias",
                        "Retorno +1 sesiones %",
                        "Retorno +3 sesiones %",
                        "Retorno +5 sesiones %",
                        "Noticias positivas +1 sesiones %",
                        "Noticias positivas +3 sesiones %",
                        "Noticias positivas +5 sesiones %",
                    ],
                )
                st.dataframe(resumen_impacto_mostrable, width="stretch", hide_index=True)
                st.altair_chart(
                    grafico_impacto_promedio(resumen_impacto_noticias),
                    width="stretch",
                )
            if not impacto_noticias.empty:
                st.subheader("Distribucion de retornos posteriores")
                st.altair_chart(
                    grafico_distribucion_impacto(impacto_noticias),
                    width="stretch",
                )
                st.subheader("Detalle por noticia")
                detalle_impacto = impacto_noticias.copy()
                detalle_impacto["Fecha post"] = detalle_impacto["Fecha post"].dt.strftime("%Y-%m-%d %H:%M")
                detalle_impacto["Fecha evento"] = detalle_impacto["Fecha evento"].dt.strftime("%Y-%m-%d")
                detalle_impacto = formatear_tabla(
                    detalle_impacto,
                    fondo,
                    [
                        "Precio evento",
                        "Retorno previo 1 sesiones %",
                        "Retorno previo 3 sesiones %",
                        "Retorno previo 5 sesiones %",
                        "Retorno +1 sesiones %",
                        "Retorno +3 sesiones %",
                        "Retorno +5 sesiones %",
                    ],
                )
                st.dataframe(detalle_impacto, width="stretch", hide_index=True)
            posts_mostrables = posts_x.copy()
            posts_mostrables["Fecha"] = posts_mostrables["Fecha"].dt.strftime("%Y-%m-%d %H:%M")
            posts_mostrables = formatear_tabla(
                posts_mostrables,
                fondo,
                ["Seguidores", "Likes", "Respuestas", "Reposts", "Citas", "Engagement"],
            )
            st.dataframe(posts_mostrables, width="stretch", hide_index=True)

    with tablas[8]:
        st.subheader("Resumen financiero")
        resumen_financiero_mostrable = formatear_tabla(
            resumen_financiero,
            fondo,
            ["Valor"],
        )
        st.dataframe(
            resumen_financiero_mostrable, width="stretch", hide_index=True
        )


if __name__ == "__main__":
    main()
