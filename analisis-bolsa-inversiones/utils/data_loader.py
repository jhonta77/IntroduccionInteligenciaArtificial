import logging
import pandas as pd
import requests
import streamlit as st

try:
    import yfinance as yf
except ImportError:
    yf = None

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("data_loader")

TICKER_CELSIA = "CELSIA.CL"
TICKER_BRENT  = "BZ=F"
XM_API_URL    = "https://servapibi.xm.com.co/hourly"


@st.cache_data(ttl=1800, show_spinner=False)
def descargar_celsia(inicio: str, fin: str) -> pd.DataFrame:
    """Precio de cierre diario de CELSIA en COP desde Yahoo Finance."""
    log.info("descargar_celsia | inicio=%s fin=%s", inicio, fin)
    if yf is None:
        log.error("descargar_celsia | yfinance no instalado")
        return pd.DataFrame()
    try:
        datos = yf.Ticker(TICKER_CELSIA).history(start=inicio, end=fin, auto_adjust=False)
        log.debug("descargar_celsia | filas crudas=%d columnas=%s", len(datos), list(datos.columns))
    except Exception as e:
        log.exception("descargar_celsia | fallo al llamar yfinance: %s", e)
        return pd.DataFrame()

    if datos.empty or "Close" not in datos.columns:
        log.warning("descargar_celsia | respuesta vacía o sin columna Close")
        return pd.DataFrame()

    datos = datos.reset_index()
    fechas = pd.to_datetime(datos["Date"])
    if fechas.dt.tz is not None:
        fechas = fechas.dt.tz_convert(None)

    resultado = pd.DataFrame({
        "fecha":         fechas.dt.normalize(),
        "precio_celsia": datos["Close"].values,
    }).dropna().sort_values("fecha").reset_index(drop=True)

    log.info("descargar_celsia | registros limpios=%d", len(resultado))
    return resultado


@st.cache_data(ttl=1800, show_spinner=False)
def descargar_brent(inicio: str, fin: str) -> pd.DataFrame:
    """Precio spot del petróleo Brent en USD desde Yahoo Finance (BZ=F)."""
    log.info("descargar_brent | inicio=%s fin=%s", inicio, fin)
    if yf is None:
        log.error("descargar_brent | yfinance no instalado")
        return pd.DataFrame()
    try:
        datos = yf.Ticker(TICKER_BRENT).history(start=inicio, end=fin, auto_adjust=False)
        log.debug("descargar_brent | filas crudas=%d columnas=%s", len(datos), list(datos.columns))
    except Exception as e:
        log.exception("descargar_brent | fallo al llamar yfinance: %s", e)
        return pd.DataFrame()

    if datos.empty or "Close" not in datos.columns:
        log.warning("descargar_brent | respuesta vacía o sin columna Close")
        return pd.DataFrame()

    datos = datos.reset_index()
    fechas = pd.to_datetime(datos["Date"])
    if fechas.dt.tz is not None:
        fechas = fechas.dt.tz_convert(None)

    resultado = pd.DataFrame({
        "fecha":        fechas.dt.normalize(),
        "precio_brent": datos["Close"].values,
    }).dropna().sort_values("fecha").reset_index(drop=True)

    log.info("descargar_brent | registros limpios=%d", len(resultado))
    return resultado


def _xm_post(payload: dict) -> dict:
    log.debug("_xm_post | payload=%s", payload)
    respuesta = requests.post(XM_API_URL, json=payload, timeout=60)
    log.debug("_xm_post | status=%d", respuesta.status_code)
    if not respuesta.ok:
        raise RuntimeError(f"XM API {respuesta.status_code}: {respuesta.text[:200]}")
    return respuesta.json()


@st.cache_data(ttl=3600, show_spinner=False)
def descargar_precio_bolsa_xm(inicio: str, fin: str) -> pd.DataFrame:
    """Precio promedio diario de bolsa de energía (COP/MWh) desde API pública de XM."""
    log.info("descargar_precio_bolsa_xm | inicio=%s fin=%s", inicio, fin)
    inicio_dt = pd.to_datetime(inicio).normalize()
    fin_dt    = pd.to_datetime(fin).normalize()
    filas = []
    actual = inicio_dt

    while actual <= fin_dt:
        cierre = min(actual + pd.Timedelta(days=29), fin_dt)
        log.debug("descargar_precio_bolsa_xm | ventana %s → %s", actual.date(), cierre.date())
        try:
            data = _xm_post({
                "MetricId": "PrecBolsNaci",
                "StartDate": actual.date().isoformat(),
                "EndDate":   cierre.date().isoformat(),
                "Entity":    "Sistema",
            })
        except Exception as e:
            log.exception("descargar_precio_bolsa_xm | fallo en ventana %s: %s", actual.date(), e)
            actual = cierre + pd.Timedelta(days=1)
            continue

        items = data.get("Items", [])
        log.debug("descargar_precio_bolsa_xm | items recibidos=%d", len(items))
        for item in items:
            try:
                valores = item["HourlyEntities"][0]["Values"]
                horas = [
                    float(v)
                    for k, v in valores.items()
                    if k.startswith("Hour") and v not in ("", None)
                ]
                if horas:
                    filas.append({
                        "fecha": pd.to_datetime(item["Date"]),
                        "precio_bolsa_energia": sum(horas) / len(horas),
                    })
            except Exception as e:
                log.warning("descargar_precio_bolsa_xm | error en item %s: %s", item.get("Date"), e)

        actual = cierre + pd.Timedelta(days=1)

    if not filas:
        log.warning("descargar_precio_bolsa_xm | sin filas — devuelve DataFrame vacío")
        return pd.DataFrame()

    resultado = pd.DataFrame(filas).dropna().sort_values("fecha").reset_index(drop=True)
    log.info("descargar_precio_bolsa_xm | registros limpios=%d", len(resultado))
    return resultado


def construir_dataset(inicio: str, fin: str) -> pd.DataFrame:
    """Une las tres series por fecha (inner join). Solo fechas con los tres valores."""
    log.info("construir_dataset | inicio=%s fin=%s", inicio, fin)

    celsia = descargar_celsia(inicio, fin)
    brent  = descargar_brent(inicio, fin)
    bolsa  = descargar_precio_bolsa_xm(inicio, fin)

    log.info(
        "construir_dataset | filas: celsia=%d brent=%d bolsa=%d",
        len(celsia), len(brent), len(bolsa),
    )

    if celsia.empty:
        log.error("construir_dataset | celsia vacío → no se puede armar dataset")
        return pd.DataFrame()
    if brent.empty:
        log.error("construir_dataset | brent vacío → no se puede armar dataset")
        return pd.DataFrame()
    if bolsa.empty:
        log.error("construir_dataset | bolsa_xm vacío → no se puede armar dataset")
        return pd.DataFrame()

    celsia["fecha"] = pd.to_datetime(celsia["fecha"]).dt.normalize()
    brent["fecha"]  = pd.to_datetime(brent["fecha"]).dt.normalize()
    bolsa["fecha"]  = pd.to_datetime(bolsa["fecha"]).dt.normalize()

    dataset = (
        celsia
        .merge(brent, on="fecha", how="inner")
        .merge(bolsa,  on="fecha", how="inner")
        .dropna()
        .sort_values("fecha")
        .reset_index(drop=True)
    )

    log.info("construir_dataset | dataset final filas=%d columnas=%s", len(dataset), list(dataset.columns))
    return dataset
