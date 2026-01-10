# WeatherLink Dashboard 🌤️

Dashboard meteorológico para monitorear múltiples estaciones WeatherLink con gráficos interactivos y exportación a Excel.

## ✨ Características

- 📊 **Gráficos interactivos** de temperatura, humedad, viento, precipitación, radiación solar y DPV
- 🏢 **Múltiples estaciones** - Soporta 3 estaciones simultáneamente
- 📅 **Filtros de tiempo** - 1 día, 7 días, 15 días, 30 días o rango personalizado
- 📈 **Gráfico de lluvia inteligente** - Solo muestra días con precipitación
- 📥 **Exportar a Excel** - Descarga todos los datos con el filtro aplicado
- 🚀 **Caché inteligente** - Reduce llamadas a la API
- 🐳 **Dockerizado** - Fácil despliegue en cualquier servidor
- 📅 **Filtros Flexibles**: Por días rápidos o por rango de fechas personalizado

## Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Configurar el archivo `.env` con tus credenciales de WeatherLink API

3. Ejecutar la aplicación:
```bash
python app.py
```

4. Abrir en el navegador: `http://localhost:5000`

## Estructura del Proyecto

```
.
├── app.py                    # Aplicación Flask principal
├── weatherlink_client.py     # Cliente para API de WeatherLink
├── requirements.txt          # Dependencias
├── .env                      # Credenciales de API
└── templates/
    ├── index.html           # Dashboard principal
    ├── station_detail.html  # Detalle de estación con gráficos
    └── compare.html         # Comparación de estaciones
```

## Uso

### Dashboard Principal
- Muestra las condiciones actuales de las 3 estaciones
- Actualización automática cada 5 minutos

### Vista de Detalle
- Selecciona rango rápido (1, 7, 15, 30 días)
- O selecciona fechas personalizadas
- Visualiza 6 gráficos diferentes por estación

### Comparación
- Compara las 3 estaciones simultáneamente
- Filtro por período de días
- 5 gráficos comparativos

## Tecnologías

- **Backend**: Flask, Python
- **Frontend**: Bootstrap 5, Chart.js
- **API**: WeatherLink API v2
