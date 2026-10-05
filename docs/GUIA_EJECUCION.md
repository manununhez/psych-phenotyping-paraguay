# Guía de ejecución

Esta guía cubre la regeneración ordinaria del desarrollo. El cierre final del ensamble en `test` ya se ejecutó; es distinto de las comparaciones posteriores de TF-IDF y del híbrido, y no forma parte de una regeneración rutinaria.

No incluye:
- notebook final de xAI/explicabilidad (pendiente; fuera del cierre técnico actual).

El procedimiento predict-only está documentado en `notebooks/pipeline/10_cierre_final_test_ensamble.ipynb`. No debe reejecutarse para exploración ni selección. Una reproducción exacta necesita los artefactos congelados; regenerar entrenamientos no garantiza recuperar ese cierre.

## Requisitos de 01: limpieza y EDA
La implementación actual de `01` reúne dos fases con requisitos diferentes:

1. Secciones 1 a 5: carga, limpieza y exportación de `ips_clean.csv` desde `ips_raw.csv`.
2. Desde la sección 6: EDA completo del universo denoised; necesita `dataset_base.csv`, índices y CSV denoised por partición, `dataset_denoised.csv` y `dataset_with_clinical_signal_flag.csv`, producidos por `02`/`03`.

La longitud en tokens requiere además el tokenizer local en `data/checkpoints/roberta_clinical/checkpoint-210`. No sustituirlo silenciosamente por otro tokenizer al comparar cifras.

En un arranque con solo el corpus original, ejecutar interactivamente la limpieza hasta la sección 5, ejecutar `02` y `03`, disponer del tokenizer esperado y volver a ejecutar `01` completo. El orquestador actual no implementa automáticamente esas dos pasadas: ejecutar `01` completo al inicio sin los insumos posteriores falla. Este requisito no cambia el orden metodológico limpieza, partición y filtro.

Si `ips_clean.csv` existe y difiere de la limpieza reproducida, `01` no lo sobrescribe: deja un candidato en el área privada del EDA. Revisar esa discrepancia antes de encadenar etapas. El reporte, las tablas y las figuras se generan dentro de `01`, sin scripts de EDA, en `reports/eda_audit_20260619/`.

## Opción reproducible por contenedor

Si prefieres aislar dependencias del sistema host, puedes usar el contenedor del proyecto.

Scripts base:

```bash
bash scripts/docker_build.sh
bash scripts/docker_up.sh
CONTAINER_MODE=snapshot bash scripts/docker_up.sh
bash scripts/docker_smoke_test.sh
```

Si vas a usar Gemini desde el contenedor:

```bash
cp .env.docker.example .env.docker
```

Shell interactiva:

```bash
bash scripts/docker_shell.sh
```

Apagado:

```bash
bash scripts/docker_down.sh
```

Variables útiles:
- `CONTAINER_MODE=dev|snapshot`
- `CONTAINER_NAME=<nombre>`
- `IMAGE_NAME=<nombre>`
- `IMAGE_TAG=<tag>`

### Qué congela Docker y qué no

Docker congela:
- versión de Python de la imagen;
- dependencias Python declaradas;
- modelo spaCy base instalado en la imagen (`es_core_news_md`);
- utilidades del sistema necesarias para el pipeline.

Pero hay una diferencia operativa clave:
- `CONTAINER_MODE=dev` monta el repositorio local en `/workspace`, así que el código ejecutado es el de tu árbol actual;
- `CONTAINER_MODE=snapshot` usa el código copiado dentro de la imagen y solo monta `data/` si existe localmente.

Docker **no** congela por sí solo:
- datos clínicos reales;
- claves externas (`GEMINI_API_KEY`);
- artefactos locales de `data/outputs/` o `data/processed/`;
- caches remotas de Hugging Face descargadas después de construir la imagen.

### Inputs obligatorios

Para entender el contenedor correctamente:

1. **Siempre obligatorios**
   - código del repositorio;
   - submódulo `Spanish_Psych_Phenotyping_PY` inicializado.

2. **Obligatorios solo si se corre el pipeline desde 01**
   - `data/ips_raw.csv` disponible en el volumen local montado.
   - para ejecutar `01` completo, los artefactos y tokenizer descritos arriba.

3. **Obligatorios solo si se ejecuta extracción LLM**
   - `.env.docker` con `GEMINI_API_KEY`, o variable equivalente pasada al contenedor.
   - Puedes partir de `.env.docker.example`.

4. **Obligatorios solo para reusar cierres previos**
   - artefactos locales ya generados en `data/processed/` y `data/outputs/`.

### Cuándo usar cada modo

- `CONTAINER_MODE=dev`
  - uso diario;
  - iteración local con código y notebooks vivos;
  - no congela el árbol fuente, solo el entorno.

- `CONTAINER_MODE=snapshot`
  - validación más cercana a un futuro repo público;
  - el código proviene de la imagen ya construida;
  - mantiene fuera de la imagen los datos clínicos y la caché de Hugging Face.

### Nota sobre BETO y otros modelos externos

El contenedor no empaqueta los pesos de `BETO`, `ROBERTA_CLINICAL` ni `ROBERTA_BIOMEDICAL`.

Eso significa:
- la lógica metodológica y los identificadores del backbone sí quedan congelados en código y notebooks;
- los pesos se descargarán desde Hugging Face cuando una corrida los necesite;
- la caché queda persistida localmente en `.docker_cache/huggingface/` para no descargar todo cada vez.

En otras palabras: Docker congela el **entorno de ejecución**, no los datos clínicos ni todos los artefactos pesados externos por defecto.

## Orquestador de desarrollo (con insumos disponibles)

```bash
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
python scripts/audit/generar_auditoria_validacion_secundaria_dev.py
```

Wrapper bash opcional:

```bash
bash scripts/run_regeneracion_desarrollo.sh --dry-run
bash scripts/run_regeneracion_desarrollo.sh
```

## Ejecución parcial

```bash
python scripts/regenerar_pipeline_desarrollo.py --desde 06_ingenieria_features_hibridas --hasta 09b_cierre_modelos_dev
```

## Limpieza controlada de outputs

```bash
python scripts/regenerar_pipeline_desarrollo.py \
  --limpiar-outputs \
  --confirmar-limpieza \
  --dry-run
```

Para ejecutar limpieza real, quitar `--dry-run`.

Antes de limpiar, respaldar modelos, checkpoints, extracción LLM, reglas e índices de referencia. No todos pueden recuperarse únicamente desde `ips_raw.csv`; una llamada remota nueva o un entrenamiento nuevo no reproduce necesariamente el experimento original.

## Salidas de la regeneración
Cada corrida deja:
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.md`
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.json`
- logs por paso en `data/outputs/regeneracion_desarrollo_<timestamp>/logs/`.

## Orden operativo cubierto por la regeneración
1. `01_datos_eda_limpieza`
2. `02_patient_level_split`
3. `03_denoising_reglas_core`
4. `04a_linea_base_dummy`
5. `04b_linea_base_tfidf`
6. `04c_linea_base_transformers`
7. `05_brecha_lexica_co_core_py`
8. `06_ingenieria_features_hibridas`
9. `07_entrenamiento_modelos_hibridos`
10. `comparacion_backbones_hibrido` (si se activa `--incluir-comparacion-backbones`)
11. `08_resultados_hibrido_vs_lineas_base`
12. `barrido_hibrido_dev`
13. `freeze_lexico_preliminar`
14. `manifiesto_artefactos_backbone`
15. `09b_cierre_modelos_dev`
16. `09_analisis_errores_hibrido`

## Cierre dev histórico con ensamble 512
El cierre de mayo se preserva como histórico; sus tablas y predicciones pueden consultarse, pero no se encontró el checkpoint contextual exacto que lo reproduzca. No reejecutar usando su identificador para sobrescribir la evidencia original.

Artefactos principales:
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/manifest.json`
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/reporte_cierre_dev_ensamble.md`
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/tabla_experimentos_dev_cierre.csv`

Este cierre usa `max_length=512`, pero queda como histórico porque luego se recongeló `ROBERTA_CLINICAL 512` con checkpoint reproducible.

## Cierre dev recongelado y cierre final test

El cierre vigente se apoya en:

- cierre `dev` recongelado:
  - `data/outputs/cierre_dev_recongelado_roberta_512_20260606_160946/`;
- dry-run dev del notebook final:
  - `data/outputs/cierre_final_pretest_dev_reprocheck_refreeze_20260606_1620/`;
- cierre final en `test`:
  - `data/outputs/cierre_final_test_ensamble_512_20260606_1640/`.

Para validar en `dev` sin abrir `test`:

```bash
CIERRE_FINAL_RUN_ID=verificacion_dev_20261005 \
FINAL_EVAL_SPLIT=dev \
FINAL_BOOTSTRAP_N=0 \
jupyter nbconvert --to notebook --execute \
  --output-dir=/tmp --output=verificacion_cierre_dev.ipynb \
  notebooks/pipeline/10_cierre_final_test_ensamble.ipynb
```

Usar un `CIERRE_FINAL_RUN_ID` nuevo en cada comprobación, conservar el entorno compatible con los modelos serializados y comparar contra la referencia explícita, no contra un `latest` posterior. El ejemplo no sobrescribe el notebook versionado ni los directorios originales.

La ejecución final de prueba quedó en `cierre_final_test_ensamble_512_20260606_1640`. El notebook protege ese modo mediante `FINAL_PERMITIR_TEST` y `FINAL_DEV_REPRO_OK`; estas variables son confirmaciones operativas, no sustituyen la evidencia de reproducción. No repetirlo para reajustar modelos, pesos ni reglas. Las corridas `max_length=256` son sensibilidad no adoptada.

## Control secundario histórico en desarrollo
La auditoría secundaria consume el cierre histórico y su análisis de errores:

```bash
python scripts/audit/generar_auditoria_validacion_secundaria_dev.py
```

Este paso corresponde al notebook `notebooks/analysis/09c_auditoria_validacion_secundaria_dev.ipynb`. Consume artefactos congelados en `dev` y no reabre selección de modelo.

## Nota específica sobre backbone
- `04c` define y exporta la selección del baseline Transformer.
- `06` usa BETO por defecto para el híbrido, de acuerdo con la comparación controlada de backbone.
- Si se quiere probar una herencia explícita desde `04c`, debe indicarse `FE_TEXT_BACKBONE=auto`.
- `09b` utiliza la selección de `04c` y la comparación controlada de backbones (si existe artefacto válido) para fundamentar la decisión final en `dev`.

Cadena operativa recomendada:
`04c` -> `06` -> `07` -> `scripts/comparar_backbones_hibrido.py` -> `scripts/audit/registrar_artefactos_backbone.py` -> `09b`.

## Resolución automática en notebooks
- `07` resuelve por defecto la última corrida completa de features (`fe_*`) por mtime real y no por orden alfabético.
- `08` resuelve por defecto la última corrida base canónica `train_YYYYMMDD_HHMMSS`.
- `09b` busca un barrido compatible con la corrida base actual y, si no existe, puede preparar automáticamente:
  - `scripts/ejecutar_barrido_ablacion_hibrido.py`
  - `scripts/audit/generar_freeze_lexico.py`

Esto deja el flujo notebook-only alineado con la regeneración reproducible del proyecto.

La resolución automática permite trabajar con nuevas corridas; no convierte los resultados de `09b` en el recongelado actual ni recupera los pesos vigentes del ensamble. Para eso consultar [Revalidación y procedencia](REVALIDACION_RESULTADOS_REFERENCIA.md).

## Nota metodológica
La regeneración reconstruye el flujo de desarrollo sin mezclar decisiones de la fase final. Reusar la extracción LLM conservada permite mantener sus variables; llamar de nuevo a la API requiere autorización/resguardo y crea otra evidencia. `data/` y `reports/` son material local excluido de publicación.
