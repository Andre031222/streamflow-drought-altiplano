# Inventario de fuentes de datos

Procedencia, URL y licencia de todos los datos del benchmark (actualizado 2026-09-30).
Todas las descargas son reproducibles con `03-codigo/extract_stations.py` y `03-codigo/fetch_data.py`.

## Fuentes usadas

| Fuente | Variable | Dominio | Acceso | Licencia | Archivos |
| --- | --- | --- | --- | --- | --- |
| Andean-GC (Aguayo et al. 2026), Zenodo [10.5281/zenodo.18035801](https://doi.org/10.5281/zenodo.18035801) | Caudal diario QC (m³/s), metadatos y polígonos de cuenca | 19 aforos con ≥5000 días QC: 13 Perú (SENAMHI) + 6 Altiplano chileno (DGA; Lauca/Caquena) | Descarga directa Zenodo | CC BY 4.0 | `crudos/andean-gc/` (metadatos; el CSV QC completo y el `.gpkg` están en `.gitignore`), `crudos/stations/*.csv`, `crudos/stations/benchmark_stations.csv` |
| ERA5 (Hersbach et al. 2020) vía Open-Meteo Historical Weather API (`models=era5`) | Precipitación diaria (mm), temperatura media 2 m (°C) | Centroide de cada cuenca | https://archive-api.open-meteo.com/v1/archive | Copernicus (C3S) / Open-Meteo CC BY 4.0 | `crudos/clima/era5/<gauge_id>.csv` |
| NASA POWER (MERRA-2, `PRECTOTCORR` corregido con GPCP; `T2M`) | Precipitación y temperatura diarias | Centroide de cuenca, desde 1981 | https://power.larc.nasa.gov/api/temporal/daily/point | Datos públicos NASA | `crudos/clima/merra2_power/<gauge_id>.csv` |
| GloFAS v4 reanálisis vía Open-Meteo Flood API | Caudal simulado diario (m³/s) | Vecindario 3×3 (0,05°) alrededor del aforo, desde 1984 | https://flood-api.open-meteo.com/v1/flood | Copernicus EMS / CC BY 4.0 | `crudos/clima/glofas/<gauge_id>.csv` |
| Copernicus DEM GLO-90, Natural Earth | Relieve y cartografía base (solo mapa fig00) | Andes centrales | AWS Open Data / naciscdn.org | Copernicus DEM licence / dominio público | `crudos/dem/`, `crudos/naturalearth/` (en `.gitignore`) |

**Nota importante (ERA5 vs. ERA5-Land):** el endpoint `era5_land` de Open-Meteo devuelve la precipitación vacía, por eso la precipitación y la temperatura se toman de ERA5 (0,25°). La versión anterior del manuscrito atribuía la precipitación a ERA5-Land; eso era incorrecto y se corrigió.

## Alternativas evaluadas y no usadas

| Fuente | Resultado |
| --- | --- |
| HydroShare `Peru_Hydrological_Data` | HTTP 404 en la descarga |
| PISCO v2.1 (SENAMHI) vía IRI Data Library | Sin respuesta del servidor el 2026-09-30 |
| CHIRPS 2.0 diario | Disponible, pero solo en NetCDF globales anuales (~1 GB/año); no se usó por tiempo |
| GRDC | Requiere solicitud por correo |
| ANA SNIRH | Sin API abierta estable |
