# Phone Geolocator CLI

CLI en Python para obtener una ubicacion aproximada de un numero telefonico usando solo metadatos publicos del numero y geocodificacion de region o ciudad. No realiza rastreo GPS ni seguimiento en tiempo real.
Tambien puede ejecutar dorking en fuentes abiertas y generar un reporte HTML mas completo tipo expediente.

## Requisitos

```bash
pip install -r requirements.txt
```

## Configuracion

Crea un archivo `.env` en la raiz:

```env
OPENCAGE_API_KEY=tu_api_key_aqui
DEFAULT_LANG=es
MAP_ZOOM=9
ENABLE_CIRCLE=true
CIRCLE_RADIUS_KM=50
```

## Uso

```bash
python phone_osint.py --number +573001234567
python phone_osint.py +573001234567
python phone_osint.py --number +573001234567 --lang es
python phone_osint.py --number +573001234567 --no-map
python phone_osint.py --number +573001234567 --output output/mi_reporte.html
python phone_osint.py --number +573001234567 --pro
python phone_osint.py --number +573001234567 --pro --report-output output/expediente.html
python phone_osint.py --batch numeros.txt
python phone_osint.py --batch numeros.txt --csv output/mis_resultados.csv
```

## Salidas

- Mapa HTML: `output/map_<numero>.html`
- Reporte HTML: `output/report_<numero>.html`
- CSV batch: `output/batch_results.csv`
- Log: `output/phone_geolocator.log`

## Alcance tecnico

- Validacion y parsing con `phonenumbers`
- Carrier, pais, region y zonas horarias desde metadata offline
- Geocodificacion aproximada con OpenCage
- Reverse geocoding para direccion aproximada
- Mapa interactivo con Folium
- Dorking automatizado y enlaces manuales de investigacion
- Reporte ejecutivo HTML con mapa, cobertura abierta y hallazgos
- Modo batch con CSV y barra de progreso

## Aviso legal y etico

Este proyecto usa unicamente metadatos publicos del numero telefonico y servicios de geocodificacion de ciudad o region.

- No realiza rastreo GPS en tiempo real.
- La ubicacion es aproximada y puede tener un margen amplio de error.
- Debe usarse solo con consentimiento del titular o con una base legal valida.
- En Colombia aplica la Ley 1581 de 2012.
- En la Union Europea aplica GDPR.
