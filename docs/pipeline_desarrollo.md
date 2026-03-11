# Pipeline de desarrollo (estado actual)

## Alcance
Este documento define el pipeline reproducible hasta el cierre actual en `dev`.

No incluye:
- notebook final de evaluación en `test` (pendiente);
- notebook final de xAI/explicabilidad (pendiente).

## Nota de numeración
En la estructura vigente:
- `07` entrena modelos híbridos.
- `08` compara resultados híbrido vs líneas base.
- `09b` realiza la decisión/freeze formal en `dev`.

## Etapas y orden operativo

### 1) Limpieza y EDA
- Notebook: `notebooks/pipeline/01_datos_eda_limpieza.ipynb`
- Entradas: datos crudos del proyecto.
- Salidas: dataset limpio base para split.

### 2) Split por paciente
- Notebook: `notebooks/pipeline/02_patient_level_split.ipynb`
- Entradas: dataset limpio.
- Salidas: particiones por paciente (`train/dev/test`).

### 3) Denoising clínico
- Notebook: `notebooks/pipeline/03_denoising_reglas_core.ipynb`
- Entradas: split por paciente + reglas clínicas.
- Salidas: versiones denoised para modelado.

### 4) Baseline dummy
- Notebook: `notebooks/pipeline/04a_linea_base_dummy.ipynb`
- Entradas: split denoised.
- Salidas: métricas de control.

### 5) Baseline TF-IDF
- Notebook: `notebooks/pipeline/04b_linea_base_tfidf.ipynb`
- Entradas: split denoised.
- Salidas: métricas y predicciones baseline lexical-estadístico.

### 6) Baselines Transformers
- Notebook: `notebooks/pipeline/04c_linea_base_transformers.ipynb`
- Entradas: split denoised.
- Salidas:
  - métricas y predicciones contextuales (`BETO`, `ROBERTA_CLINICAL`, `ROBERTA_BIOMEDICAL`);
  - artefacto de selección de baseline Transformer en `dev`:
    - `data/outputs/transformer_baseline_selection_<timestamp>.json`
    - `data/outputs/transformer_baseline_selection_latest.json`.

### 7) Análisis de brecha léxica
- Notebook: `notebooks/analysis/05_brecha_lexica_co_core_py.ipynb`
- Entradas: recursos `Concept_CO`, `Concept_PY`, `Concept_PY_Lexicon`.
- Salidas: evidencia de cobertura y justificación de adaptación regional.

### 8) Ingeniería de features híbridas
- Notebook: `notebooks/pipeline/06_ingenieria_features_hibridas.ipynb`
- Entradas: denoised + reglas + (LLM opcional) + sentimiento + backbone contextual configurable.
- Salidas:
  - `data/processed/fe_<run_id>_core/features_core.parquet`
  - `data/processed/fe_<run_id>_py/features_py.parquet`
- Nota de método:
  - `FE_TEXT_BACKBONE=auto` consume la selección de `04c`;
  - también admite override explícito (`beto`, `roberta_clinical`, `roberta_biomedical`).

### 9) Entrenamiento híbrido
- Notebook: `notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb`
- Entradas: features de etapa 8.
- Salidas:
  - `data/outputs/train_<run_id>/comparacion_modelos_dev.csv`
  - reportes, predicciones, modelos y artefactos de ablación.

### 10) Comparación controlada de backbones en el híbrido
- Script: `scripts/comparar_backbones_hibrido.py`
- Entradas: notebooks 06/07 + split `dev` + selección Transformer de `04c`.
- Salidas:
  - `data/outputs/comparacion_backbones_hibrido_<timestamp>/comparacion_backbones_hibrido.csv`
  - `comparacion_backbones_hibrido.json`
  - `resumen_backbones_hibrido.md`.

### 11) Consolidación de resultados
- Notebook: `notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`
- Entradas: salidas de líneas base + salidas de entrenamiento híbrido.
- Salidas:
  - `data/outputs/results_<run_id>/tabla_comparativa_modelos.csv`
  - matrices y gráficos comparativos.

### 12) Barrido híbrido en dev
- Script: `scripts/ejecutar_barrido_hibrido.py`
- Entradas: features híbridas + referencia de entrenamiento en dev.
- Salidas:
  - `data/outputs/barridos_hibridos/<timestamp>/tabla_maestra_comparativa.csv`
  - `ranking_variantes.csv`
  - `resumen_barrido.json`
  - `analisis_dependencia_beto.csv`.

## Artefactos documentales de cierre en dev

### 13) Freeze léxico preliminar
- Script: `scripts/audit/generar_freeze_lexico.py`
- Salida: `data/outputs/freeze_lexico_<timestamp>/`.

### 14) Manifiesto de artefactos de backbone
- Script: `scripts/audit/registrar_artefactos_backbone.py`
- Salida:
  - `data/outputs/backbone_artifacts_manifest_<timestamp>.json`
  - `data/outputs/backbone_artifacts_manifest_latest.json`
  - `data/outputs/backbone_artifacts_manifest_latest.md`.

### 15) Cierre formal de selección en dev
- Notebook: `notebooks/pipeline/09b_cierre_modelos_dev.ipynb`
- Script reutilizable invocado: `scripts/cerrar_modelos_dev.py`
- Salida: `data/outputs/cierre_modelos_dev_<timestamp>/`.
- Nota de método:
  - `09b` consume explícitamente selección Transformer (`04c`) y comparación controlada de backbones cuando hay artefactos válidos;
  - no asume BETO de forma implícita.

### 16) Análisis de errores
- Notebook: `notebooks/analysis/09_analisis_errores_hibrido.ipynb`
- Entradas: predicciones y métricas consolidadas.
- Salidas:
  - `data/outputs/error_analysis_<run_id>/`.

## Orquestación reproducible
- Script principal: `scripts/regenerar_pipeline_desarrollo.py`
- Wrapper opcional: `scripts/run_regeneracion_desarrollo.sh`

## Pendientes para fase final
1. Notebook final de evaluación en `test` (ejecución única post-freeze).
2. Notebook final de xAI/explicabilidad.
3. Acta final post-test (no incluida en esta fase).
