# Analisis Bolsa Inversiones

Dashboard en Streamlit para analizar el precio diario de la accion de Celsia con variables del mercado electrico colombiano.

## Variables del modelo diario

- Precio de Celsia (`CELSIA.CL`) desde Yahoo Finance.
- Precio de bolsa de energia (`PPPrecBolsNaci`) desde XM.
- Demanda diaria del SIN (`DemaSIN`) desde XM.
- Volumen util de embalses (`PorcVoluUtilDiar`) desde XM.
- Aportes hidricos (`PorcApor`) desde XM.
- TRM USD/COP (`USDCOP=X`) desde Yahoo Finance.

## Ejecutar

Desde la raiz del repositorio:

```powershell
cd analisis-bolsa-inversiones
..\venv\Scripts\python.exe -m streamlit run app.py
```

## Paginas

- `analisis`: exploracion de datos, series temporales y correlaciones.
- `reportes`: regresion simple, modelo multiple diario y rezagos temporales.

## Nota metodologica

El modelo usa variables diarias reales. No convierte indicadores financieros trimestrales a datos diarios, porque eso puede introducir informacion artificial o futura en el modelo.
