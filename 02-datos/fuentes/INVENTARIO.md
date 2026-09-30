# Inventario de fuentes de datos

Documento de procedencia, URL y licencia para el estudio ICICCDS 2027
(caudal / sequia hidrologica, Altiplano peruano + benchmark multi-estacion Peru).
Actualizado tras el experimento multi-estacion (13 estaciones, 2026-09-30).

## Fuentes usadas en el experimento

| Fuente | Variable | Estacion / dominio | URL | Licencia | Estado | Notas |
| --- | --- | --- | --- | --- | --- | --- |
| Andean Glacierized Catchment (Andean-GC) v1.1 | Caudal diario QC (m3/s) | 13 estaciones SENAMHI Peru con `days_w_data_qc >= 5000` (incluye foco Altiplano `P00000055` Puente Isla Cabanillas) | https://zenodo.org/records/18035801 | CC BY 4.0 | Descargado | Archivos: `AndeanGC_data_1950_2024_qc.csv`, `AndeanGC_metadata.csv`. Extracciones en `02-datos/crudos/stations/`. DOI: 10.5281/zenodo.18035801 |
| Open-Meteo Historical Weather API (ERA5-Land reanalisis) | Precipitacion diaria (mm) | Punto en lat/lon de cada aforo del benchmark | https://open-meteo.com/en/docs/historical-weather-api | Datos ERA5/ECMWF sujetos a terminos Copernicus; API Open-Meteo segun su ToS | Descargado | Cache: `02-datos/crudos/openmeteo/precip_P*_*.csv` (13 archivos) |

### Estaciones del benchmark (Andean-GC Peru, QC days >= 5000)

| gauge_id | name | days_w_data_qc | notes |
| --- | --- | ---: | --- |
| P00000031 | La Capilla | 18420 | |
| P00000008 | Condorcerro | 17517 | |
| P00000041 | Salamanca | 15352 | southern Peru |
| P00000047 | Egemsa Km 105 | 14308 | |
| P00000027 | Cahua | 9131 | |
| P00000022 | Recreta | 7481 | historical Cordillera Blanca era |
| P00000021 | Quitaracsa | 6928 | historical |
| P00000005 | Colcas | 6796 | historical |
| P00000003 | Chancos | 6739 | historical |
| P00000016 | Pachacoto | 6701 | historical |
| P00000055 | Puente Isla Cabanillas | 6572 | **Altiplano focus** (Titicaca / Coata-Cabanillas) |
| P00000011 | Llanganuco | 6398 | historical |
| P00000040 | Ocona | 5701 | southern Peru |

## Fuentes secundarias (extraidas, no usadas en el modelo principal)

| Fuente | Variable | Estacion | URL | Licencia | Estado |
| --- | --- | --- | --- | --- | --- |
| Andean-GC | Caudal diario QC | SENAMHI `P00000051` Salcca (n=1548, serie corta <5000) | https://zenodo.org/records/18035801 | CC BY 4.0 | Extraido a `salcca_daily_qc.csv`; no incluida en el benchmark (>=5000) |

## Alternativas intentadas (bloqueos o no usables a tiempo)

| Fuente | URL intentada | Resultado |
| --- | --- | --- |
| HydroShare `Peru_Hydrological_Data` | https://www.hydroshare.org/resource/b7efdb43bf59470fb5baa4426931d8fe/ | HTTP 404 en descarga |
| PISCO-ARNOVIC v1.1 | HydroShare THREDDS | Disponible (simulado); no usado como verdad de terreno |
| ANA SNIRH / portales oficiales | portales institucionales | Sin API abierta estable; se uso espejo Andean-GC |
| GRDC Data Portal | https://grdc.bafg.de/data/data_portal/ | Requiere solicitud por email |

## Citacion sugerida de datos

- Aguayo, R., et al. (2026). Andean Glacierized Catchment (Andean-GC) dataset. Zenodo. https://doi.org/10.5281/zenodo.18035801
- Zippenfenig, P. / Open-Meteo: Historical Weather API documentation. https://open-meteo.com/en/docs/historical-weather-api
- Hersbach et al., ERA5 / Munoz-Sabater et al., ERA5-Land (Copernicus Climate Change Service) via Open-Meteo.

## Archivos locales

```
02-datos/crudos/andean-gc/AndeanGC_metadata.csv
02-datos/crudos/andean-gc/AndeanGC_data_1950_2024_qc.csv
02-datos/crudos/stations/peru_benchmark_stations.csv
02-datos/crudos/stations/P*_daily_qc.csv
02-datos/crudos/openmeteo/precip_P*_daily.csv
02-datos/crudos/openmeteo/precip_cabanillas_daily.csv
02-datos/crudos/puente_isla_cabanillas_daily_qc.csv
02-datos/crudos/salcca_daily_qc.csv
02-datos/procesados/cabanillas_q_precip_daily.csv
02-datos/procesados/cabanillas_ssi30.csv
02-datos/procesados/predictions_P00000055_h{1,7}.csv
04-resultados/tablas/metrics_by_station.csv
04-resultados/tablas/metrics_walkforward_cabanillas.csv
04-resultados/tablas/metrics_summary.md
```
