import logging

import pandas as pd
import requests
import streamlit as st

try:
    import yfinance as yf
except ImportError:
    yf = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("data_loader")

TICKER_CELSIA = "CELSIA.CL"
TICKER_TRM = "USDCOP=X"
XM_DAILY_URL = "https://servapibi.xm.com.co/daily"


@st.cache_data(ttl=1800, show_spinner=False)
def descargar_yfinance(inicio: str, fin: str, ticker: str, columna: str) -> pd.DataFrame:
    """Descarga cierre diario desde Yahoo Finance."""
    log.info("descargar_yfinance | ticker=%s inicio=%s fin=%s", ticker, inicio, fin)
    if yf is None:
        log.error("descargar_yfinance | yfinance no instalado")
        return pd.DataFrame()

    try:
        datos = yf.Ticker(ticker).history(start=inicio, end=fin, auto_adjust=False)
    except Exception as e:
        log.exception("descargar_yfinance | fallo ticker=%s: %s", ticker, e)
        return pd.DataFrame()

    if datos.empty or "Close" not in datos.columns:
        log.warning("descargar_yfinance | respuesta vacia ticker=%s", ticker)
        return pd.DataFrame()

    datos = datos.reset_index()
    fecha_col = "Date" if "Date" in datos.columns else datos.columns[0]
    fechas = pd.to_datetime(datos[fecha_col])
    if fechas.dt.tz is not None:
        fechas = fechas.dt.tz_convert(None)

    return (
        pd.DataFrame({"fecha": fechas.dt.normalize(), columna: datos["Close"].values})
        .dropna()
        .sort_values("fecha")
        .reset_index(drop=True)
    )


def descargar_celsia(inicio: str, fin: str) -> pd.DataFrame:
    """Precio de cierre diario de CELSIA en COP."""
    return descargar_yfinance(inicio, fin, TICKER_CELSIA, "precio_celsia")


def descargar_trm(inicio: str, fin: str) -> pd.DataFrame:
    """TRM aproximada USD/COP desde Yahoo Finance."""
    return descargar_yfinance(inicio, fin, TICKER_TRM, "trm_usd_cop")


def _xm_daily_post(payload: dict) -> dict:
    log.debug("_xm_daily_post | payload=%s", payload)
    respuesta = requests.post(XM_DAILY_URL, json=payload, timeout=60)
    log.debug("_xm_daily_post | status=%d", respuesta.status_code)
    if not respuesta.ok:
        raise RuntimeError(f"XM API {respuesta.status_code}: {respuesta.text[:200]}")
    return respuesta.json()


def _valor_diario_item(item: dict) -> float | None:
    entidades = item.get("DailyEntities", [])
    if not entidades:
        return None
    valor = entidades[0].get("Value")
    if valor in ("", None):
        return None
    return float(valor)


@st.cache_data(ttl=3600, show_spinner=False)
def descargar_xm_diario(inicio: str, fin: str, metric_id: str, columna: str) -> pd.DataFrame:
    """Descarga una metrica diaria por Sistema desde XM en ventanas de 30 dias."""
    log.info("descargar_xm_diario | metric=%s inicio=%s fin=%s", metric_id, inicio, fin)
    inicio_dt = pd.to_datetime(inicio).normalize()
    fin_dt = pd.to_datetime(fin).normalize()
    filas = []
    actual = inicio_dt

    while actual <= fin_dt:
        cierre = min(actual + pd.Timedelta(days=29), fin_dt)
        try:
            data = _xm_daily_post({
                "MetricId": metric_id,
                "StartDate": actual.date().isoformat(),
                "EndDate": cierre.date().isoformat(),
                "Entity": "Sistema",
            })
        except Exception as e:
            log.exception("descargar_xm_diario | fallo metric=%s ventana=%s: %s", metric_id, actual.date(), e)
            actual = cierre + pd.Timedelta(days=1)
            continue

        for item in data.get("Items", []):
            try:
                valor = _valor_diario_item(item)
                if valor is not None:
                    filas.append({"fecha": pd.to_datetime(item["Date"]), columna: valor})
            except Exception as e:
                log.warning("descargar_xm_diario | error item=%s metric=%s: %s", item.get("Date"), metric_id, e)

        actual = cierre + pd.Timedelta(days=1)

    if not filas:
        return pd.DataFrame()

    return pd.DataFrame(filas).dropna().sort_values("fecha").reset_index(drop=True)


def descargar_precio_bolsa_xm(inicio: str, fin: str) -> pd.DataFrame:
    """Precio de bolsa nacional ponderado diario (COP/kWh)."""
    return descargar_xm_diario(inicio, fin, "PPPrecBolsNaci", "precio_bolsa_energia")


def descargar_demanda_xm(inicio: str, fin: str) -> pd.DataFrame:
    """Demanda diaria de energia del SIN (kWh)."""
    return descargar_xm_diario(inicio, fin, "DemaSIN", "demanda_energia")


def descargar_embalses_xm(inicio: str, fin: str) -> pd.DataFrame:
    """Volumen util diario del SIN en porcentaje."""
    datos = descargar_xm_diario(inicio, fin, "PorcVoluUtilDiar", "embalse_util_pct")
    if not datos.empty:
        datos["embalse_util_pct"] = datos["embalse_util_pct"] * 100
    return datos


def descargar_aportes_xm(inicio: str, fin: str) -> pd.DataFrame:
    """Aportes hidricos diarios del SIN en porcentaje frente a la media."""
    datos = descargar_xm_diario(inicio, fin, "PorcApor", "aportes_pct")
    if not datos.empty:
        datos["aportes_pct"] = datos["aportes_pct"] * 100
    return datos


def construir_dataset(inicio: str, fin: str) -> pd.DataFrame:
    """Une series diarias reales para modelar el precio de Celsia."""
    log.info("construir_dataset | inicio=%s fin=%s", inicio, fin)

    series = [
        descargar_celsia(inicio, fin),
        descargar_precio_bolsa_xm(inicio, fin),
        descargar_demanda_xm(inicio, fin),
        descargar_embalses_xm(inicio, fin),
        descargar_aportes_xm(inicio, fin),
        descargar_trm(inicio, fin),
    ]

    nombres = ["celsia", "bolsa", "demanda", "embalses", "aportes", "trm"]
    for nombre, serie in zip(nombres, series):
        log.info("construir_dataset | %s filas=%d", nombre, len(serie))
        if serie.empty:
            log.error("construir_dataset | %s vacio", nombre)
            return pd.DataFrame()
        serie["fecha"] = pd.to_datetime(serie["fecha"]).dt.normalize()

    dataset = series[0]
    for serie in series[1:]:
        dataset = dataset.merge(serie, on="fecha", how="inner")

    return dataset.dropna().sort_values("fecha").reset_index(drop=True)
