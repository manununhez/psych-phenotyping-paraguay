# Datos locales del proyecto

Este directorio existe para trabajo local y **no forma parte del repositorio público**.

## Contenido esperado

Archivos típicos:

- `ips_raw.csv`: corpus clínico bruto local.
- `ips_clean.csv`: salida de limpieza inicial de `01_datos_eda_limpieza.ipynb`.
- `dataset_denoised.csv`: universo modelado tras `03_denoising_reglas_core.ipynb`.
- `splits/`: particiones `train/dev/test` por paciente.
- `processed/`: features, artefactos intermedios y salidas de LLM.
- `outputs/`: resultados, auditorías, cierres y reportes regenerables.

## Regla de manejo

- No versionar datos clínicos, identificadores, planillas ni artefactos con texto sensible.
- No usar este directorio para compartir material con terceros.
- Si se necesita un snapshot público, este directorio debe reemplazarse por:
  - un `README` descriptivo;
  - datos de juguete o sintéticos, si existieran;
  - instrucciones claras para montar datos autorizados de forma local.

## Uso con Docker

El `Dockerfile` del proyecto está pensado para montar los datos desde afuera, por ejemplo:

```bash
docker run --rm -it \
  -v "$PWD/data:/workspace/data" \
  psych-phenotyping-paraguay:dev
```

La imagen no debe empaquetar el corpus real.
