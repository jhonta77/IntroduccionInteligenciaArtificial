# Fondo de Acciones

Dashboard en Streamlit para analizar un portafolio a partir de transacciones ya registradas y consultar precios actuales con `yfinance`.

## Qué incluye

- Historial de movimientos desde `movimientos_acciones.csv`
- Resumen por acción, compras, ventas, dividendos y balance actual
- Consulta opcional de precios actuales e histórico desde Yahoo Finance mediante `yfinance`
- Noticias recientes desde X, con caché local y token propio opcional
- Carga alternativa de archivos CSV o XLSX con la misma estructura

## Qué no incluye

Esta versión pública no usa credenciales privadas ni integra Binance o Truth Social.  
La sección de X queda disponible, pero cada persona debe usar su propio token si quiere refrescar noticias en vivo.

## Estructura mínima

```text
.
├── fondo.py
├── movimientos_acciones.csv
├── streamlit_app.py
├── x_cuentas_monitoreadas.csv
├── requirements.txt
└── README.md
```

## Cómo ejecutarlo

1. Crear y activar un entorno virtual.
2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar la app:

   ```bash
   streamlit run streamlit_app.py
   ```

4. Opcionalmente, para refrescar noticias de X en vivo:

   ```bash
   copy .env.example .env
   ```

   Luego completa `X_BEARER_TOKEN` con tu propio token.

## Formato esperado del CSV

El archivo debe contener estas columnas:

```text
Accion,Tipo,Estado,Cantidad,Precio unidad,Inversion,Comision,Total,Fecha
```

## Nota sobre privacidad

Antes de publicar cualquier repositorio, revisa que no existan archivos `.env`, credenciales, tokens ni datos personales fuera de los archivos que realmente deseas compartir.
