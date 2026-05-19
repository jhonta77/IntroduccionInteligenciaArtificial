  requirements.txt

  streamlit>=1.35.0  yfinance>=0.2.40
  pandas>=2.0.0
  numpy>=1.26.0
  altair>=5.3.0
  requests>=2.31.0
  openpyxl>=3.1.0

  ---
  utils/data_loader.py

  import pandas as pd
  import requests
  import streamlit as st

  try:
      import yfinance as yf
  except ImportError:
      yf = None

  TICKER_CELSIA = "CELSIA.CL"
  TICKER_BRENT  = "BZ=F"
  XM_API_URL    = "https://servapibi.xm.com.co/hourly"


  @st.cache_data(ttl=1800, show_spinner=False)
  def descargar_celsia(inicio: str, fin: str) -> pd.DataFrame:
      """Precio de cierre diario de CELSIA en COP desde Yahoo Finance."""
      datos = yf.Ticker(TICKER_CELSIA).history(start=inicio, end=fin, auto_adjust=False)
      if datos.empty or "Close" not in datos.columns:
          return pd.DataFrame()
      datos = datos.reset_index()
      fechas = pd.to_datetime(datos["Date"])
      if fechas.dt.tz is not None:
          fechas = fechas.dt.tz_convert(None)
      return pd.DataFrame({
          "fecha": fechas.dt.normalize(),
          "precio_celsia": datos["Close"].values,
      }).dropna().sort_values("fecha").reset_index(drop=True)


  @st.cache_data(ttl=1800, show_spinner=False)
  def descargar_brent(inicio: str, fin: str) -> pd.DataFrame:
      """Precio spot del petróleo Brent en USD desde Yahoo Finance (ticker BZ=F)."""
      datos = yf.Ticker(TICKER_BRENT).history(start=inicio, end=fin, auto_adjust=False)
      if datos.empty or "Close" not in datos.columns:
          return pd.DataFrame()
      datos = datos.reset_index()
      fechas = pd.to_datetime(datos["Date"])
      if fechas.dt.tz is not None:
          fechas = fechas.dt.tz_convert(None)
      return pd.DataFrame({
          "fecha": fechas.dt.normalize(),
          "precio_brent": datos["Close"].values,
      }).dropna().sort_values("fecha").reset_index(drop=True)


  def _xm_post(payload: dict) -> dict:
      respuesta = requests.post(XM_API_URL, json=payload, timeout=60)
      if not respuesta.ok:
          raise RuntimeError(f"XM API {respuesta.status_code}: {respuesta.text}")
      return respuesta.json()


  @st.cache_data(ttl=3600, show_spinner=False)
  def descargar_precio_bolsa_xm(inicio: str, fin: str) -> pd.DataFrame:
      """
      Precio promedio diario de bolsa de energía (COP/MWh) desde API pública de XM.
      XM es el operador del mercado eléctrico colombiano.
      Métrica: PrecBolsNaci — precio de bolsa nacional.
      """
      inicio_dt = pd.to_datetime(inicio).normalize()
      fin_dt    = pd.to_datetime(fin).normalize()
      filas = []
      actual = inicio_dt

      # La API de XM acepta máximo 30 días por petición → iteramos en ventanas
      while actual <= fin_dt:
          cierre = min(actual + pd.Timedelta(days=29), fin_dt)
          data = _xm_post({
              "MetricId": "PrecBolsNaci",
              "StartDate": actual.date().isoformat(),
              "EndDate":   cierre.date().isoformat(),
              "Entity":    "Sistema",
          })
          for item in data.get("Items", []):
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
          actual = cierre + pd.Timedelta(days=1)

      if not filas:
          return pd.DataFrame()
      return pd.DataFrame(filas).sort_values("fecha").reset_index(drop=True)


  def construir_dataset(inicio: str, fin: str) -> pd.DataFrame:
      """
      Une las tres series por fecha (inner join).
      Solo quedan fechas donde existen los tres valores → días hábiles comunes.
      """
      celsia = descargar_celsia(inicio, fin)
      brent  = descargar_brent(inicio, fin)
      bolsa  = descargar_precio_bolsa_xm(inicio, fin)

      for df in [celsia, brent, bolsa]:
          if df.empty:
              return pd.DataFrame()

      celsia["fecha"] = pd.to_datetime(celsia["fecha"]).dt.normalize()
      brent["fecha"]  = pd.to_datetime(brent["fecha"]).dt.normalize()
      bolsa["fecha"]  = pd.to_datetime(bolsa["fecha"]).dt.normalize()

      return (
          celsia
          .merge(brent, on="fecha", how="inner")
          .merge(bolsa,  on="fecha", how="inner")
          .dropna()
          .sort_values("fecha")
          .reset_index(drop=True)
      )

  ---
  utils/stats.py

  import numpy as np
  import pandas as pd


  def regresion_simple(x: pd.Series, y: pd.Series) -> dict:
      """
      Regresión lineal simple: y = pendiente * x + intercepto
      Usa mínimos cuadrados ordinarios (OLS) con numpy.
      """
      x_arr = x.astype(float).to_numpy()
      y_arr = y.astype(float).to_numpy()

      # Correlación de Pearson
      r = float(x.astype(float).corr(y.astype(float)))

      # OLS: [intercepto, pendiente] = (XᵀX)⁻¹ Xᵀy
      X_design = np.column_stack([np.ones(len(x_arr)), x_arr])
      beta, *_ = np.linalg.lstsq(X_design, y_arr, rcond=None)
      intercepto, pendiente = float(beta[0]), float(beta[1])

      y_pred   = intercepto + pendiente * x_arr
      residuos = y_arr - y_pred
      mae  = float(np.abs(residuos).mean())
      rmse = float(np.sqrt((residuos ** 2).mean()))

      return {
          "pendiente":  pendiente,
          "intercepto": intercepto,
          "r":          r,
          "r2":         r ** 2,
          "mae":        mae,
          "rmse":       rmse,
          "n":          len(x_arr),
      }


  def regresion_multiple(df: pd.DataFrame, vars_x: list, var_y: str) -> dict:
      """
      Regresión lineal múltiple: y = b0 + b1*x1 + b2*x2
      """
      X = df[vars_x].astype(float).to_numpy()
      y = df[var_y].astype(float).to_numpy()
      X_design = np.column_stack([np.ones(len(X)), X])
      beta, *_ = np.linalg.lstsq(X_design, y, rcond=None)

      y_pred   = X_design @ beta
      residuos = y - y_pred
      ss_res   = (residuos ** 2).sum()
      ss_tot   = ((y - y.mean()) ** 2).sum()
      r2   = float(1 - ss_res / ss_tot) if ss_tot else 0.0
      mae  = float(np.abs(residuos).mean())
      rmse = float(np.sqrt((residuos ** 2).mean()))

      coeficientes = {"intercepto": float(beta[0])}
      for nombre, coef in zip(vars_x, beta[1:]):
          coeficientes[nombre] = float(coef)

      return {
          "coeficientes": coeficientes,
          "r2":    r2,
          "mae":   mae,
          "rmse":  rmse,
          "n":     len(y),
          "y_pred": y_pred,
      }


  def interpretar_correlacion(r: float) -> str:
      abs_r     = abs(r)
      direccion = "positiva" if r >= 0 else "negativa"
      if abs_r >= 0.8:   fuerza = "muy fuerte"
      elif abs_r >= 0.6: fuerza = "fuerte"
      elif abs_r >= 0.4: fuerza = "moderada"
      elif abs_r >= 0.2: fuerza = "débil"
      else:              fuerza = "muy débil o nula"
      return f"Correlación {direccion} {fuerza}  |  r = {r:.3f}"

  ---
  utils/plots.py

  import altair as alt
  import pandas as pd
  import numpy as np


  def grafico_serie_temporal(df, col_y, titulo, color="#0f766e"):
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
          "precio_celsia":       "Celsia (COP)",
          "precio_brent":        "Brent (USD)",
          "precio_bolsa_energia":"Bolsa Energía (COP/MWh)",
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

  ---
  app.py

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

  ---
  pages/analisis.py (EDA)

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

  ---
  pages/reportes.py (Regresión)

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

  ---
  Estructura final de carpetas

  analisis-bolsa-inversiones/
  ├── app.py                   ← Página de inicio
  ├── requirements.txt
  ├── .streamlit/
  │   └── config.toml          ← Tema visual
  ├── pages/
  │   ├── analisis.py          ← EDA (exploración de datos)
  │   └── reportes.py          ← Regresión lineal
  └── utils/
      ├── __init__.py
      ├── data_loader.py       ← Descarga datos (yfinance + XM)
      ├── stats.py             ← Cálculos estadísticos
      └── plots.py             ← Gráficos Altair

  Dónde consultar los datos

  ┌───────────────┬───────────────────────────────────┬──────────────────────────────────┐
  │    Fuente     │                URL                │             Para qué             │
  ├───────────────┼───────────────────────────────────┼──────────────────────────────────┤
  │ Yahoo Finance │ finance.yahoo.com/quote/CELSIA.CL │ Ver precio histórico manualmente │
  ├───────────────┼───────────────────────────────────┼──────────────────────────────────┤
  │ XM API docs   │ servapibi.xm.com.co               │ API precio bolsa energía         │
  ├───────────────┼───────────────────────────────────┼──────────────────────────────────┤
      ├── stats.py             ← Cálculos estadísticos
      └── plots.py             ← Gráficos Altair

  Dónde consultar los datos

  ┌───────────────┬───────────────────────────────────┬──────────────────────────────────┐
  │    Fuente     │                URL                │             Para qué             │
  ├───────────────┼───────────────────────────────────┼──────────────────────────────────┤
  │ Yahoo Finance │ finance.yahoo.com/quote/CELSIA.CL │ Ver precio histórico manualmente │
  ├───────────────┼───────────────────────────────────┼──────────────────────────────────┤
  │ XM API docs   │ servapibi.xm.com.co               │ API precio bolsa energía         │
  ├───────────────┼───────────────────────────────────┼──────────────────────────────────┤
  │ XM web        │ xm.com.co                         │ Contexto del mercado eléctrico   │
  ├───────────────┼───────────────────────────────────┼──────────────────────────────────┤
  │ yfinance docs │ pypi.org/project/yfinance         │ Documentación librería           │
  └───────────────┴───────────────────────────────────┴──────────────────────────────────┘

  ---
  ¿Quieres que cree los archivos ahora, o hay algo que cambiar primero?