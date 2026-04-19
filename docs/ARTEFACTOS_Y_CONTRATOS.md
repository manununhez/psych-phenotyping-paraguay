# Artefactos Y Contratos Del Pipeline

## Propósito
Este documento define qué consume y qué produce cada etapa del proyecto, cuáles artefactos son la fuente de verdad de cada decisión y qué punteros deben preferirse para lectura automatizada o auditoría.

Su objetivo es evitar ambigüedades del tipo:

- qué archivo debe leer la etapa siguiente;
- qué carpeta timestamped es solo local y cuál representa una decisión canónica;
- qué resultados son regenerables y cuáles se usan como referencia de estado.

## Principio general
El repositorio separa dos planos:

- **documentación pública versionada**: vive en `README.md`, `docs/`, `notebooks/README.md` y `scripts/README.md`;
- **artefactos locales regenerables**: viven en `data/processed/` y `data/outputs/`.

Los notebooks y scripts deben trabajar, cuando exista, con punteros `latest` o con artefactos explícitamente resueltos por compatibilidad. No deben depender de recordar un timestamp manual.

## Regla de oro
Cuando exista un puntero `latest.json`, ese puntero tiene prioridad sobre inspeccionar carpetas timestamped a mano.

## Contrato por etapa

### 01. Limpieza inicial
Notebook:
- `notebooks/pipeline/01_datos_eda_limpieza.ipynb`

Entrada principal:
- `data/ips_raw.csv`

Salida principal:
- `data/ips_clean.csv`

Contrato:
- `02` no debería volver a consumir `ips_raw.csv` directamente.
- `ips_clean.csv` es la base documental limpia para el split.

### 02. Split por paciente
Notebook:
- `notebooks/pipeline/02_patient_level_split.ipynb`

Entradas:
- `data/ips_clean.csv`

Salidas:
- `data/splits/train_indices.csv`
- `data/splits/dev_indices.csv`
- `data/splits/test_indices.csv`
- `data/splits/dataset_base.csv`

Contrato:
- el split por paciente queda congelado aquí;
- toda comparación posterior debe respetar estos índices.

### 03. Denoising clínico
Notebook:
- `notebooks/pipeline/03_denoising_reglas_core.ipynb`

Entradas:
- `data/splits/dataset_base.csv`
- `data/splits/*_indices.csv`
- submódulo `Spanish_Psych_Phenotyping_PY/`

Salidas:
- `data/splits/train_denoised.csv`
- `data/splits/dev_denoised.csv`
- `data/splits/test_denoised.csv`
- `data/dataset_denoised.csv`
- `data/input_for_gemini.json`

Contrato:
- `04a`, `04b`, `04c`, `06` y el resto del pipeline principal operan sobre el universo `denoised`.
- `input_for_gemini.json` es el insumo formal para la extracción semántica acotada del LLM.

### 04a. Baseline Dummy
Salida principal:
- `data/dummy_eval.csv`
- `data/dummy_predicciones_dev.csv`

Contrato:
- sirve como piso trivial del problema;
- no alimenta ninguna decisión estructural del híbrido.

### 04b. Baseline TF-IDF
Salidas principales:
- `data/tfidf_eval.csv`
- `data/tfidf_classification_report.csv`
- `data/tfidf_predicciones_dev.csv`

Contrato:
- `TF-IDF` es baseline textual fuerte;
- no alimenta la matriz híbrida;
- sí entra como referencia en `08`, barrido y `09b`.

### 04c. Baselines Transformer standalone
Salidas principales:
- `data/beto_eval.csv`
- `data/roberta_clinical_eval.csv`
- `data/roberta_biomedical_eval.csv`
- `data/outputs/transformer_baseline_selection_<timestamp>.json`
- `data/outputs/transformer_baseline_selection_latest.json`

Fuente de verdad:
- `data/outputs/transformer_baseline_selection_latest.json`

Contrato:
- decide el mejor transformer standalone en `dev`;
- no decide por sí solo el backbone del híbrido.

### 05. Brecha léxica
Notebook:
- `notebooks/analysis/05_brecha_lexica_co_core_py.ipynb`

Rol:
- no produce el cierre del modelo;
- justifica el paso `Concept_CO -> Concept_Core -> Concept_PY` y la comparación `core` vs `py`.

Contrato:
- informa cómo leer el recurso clínico usado por `06` y el submódulo clínico.

### 06. Ingeniería de features híbridas
Notebook:
- `notebooks/pipeline/06_ingenieria_features_hibridas.ipynb`

Entradas:
- `data/dataset_denoised.csv`
- `data/processed/gemini_extraction.json` si existe y se habilita
- submódulo `Spanish_Psych_Phenotyping_PY/`
- `data/outputs/transformer_baseline_selection_latest.json` solo si `FE_TEXT_BACKBONE=auto`

Salidas por corrida:
- `data/processed/fe_<run_id>_core/features_core.parquet`
- `data/processed/fe_<run_id>_py/features_py.parquet`
- `data/processed/fe_<run_id>_core/feature_summary.csv`
- `data/processed/fe_<run_id>_py/feature_summary.csv`
- `data/processed/fe_<run_id>_config.json`

Fuente de verdad:
- `fe_<run_id>_config.json`

Contrato:
- `07` debe consumir un par coherente `fe_<run_id>_core` + `fe_<run_id>_py`;
- no debe mezclar corridas de features de distintos `run_id`.

### 07. Entrenamiento híbrido
Notebook:
- `notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb`

Entradas:
- una corrida completa de `06`
- split congelado por paciente

Salidas por corrida:
- `data/outputs/train_<run_id>/comparacion_modelos_<split>.csv`
- `data/outputs/train_<run_id>/predicciones_<profile>_<model>_<split>.csv`
- `data/outputs/train_<run_id>/modelo_<profile>_<model>.joblib`
- `data/outputs/train_<run_id>/<profile>_X_cols.json`
- `data/outputs/train_<run_id>/resumen_entrenamiento.json`
- `data/outputs/train_<run_id>/resumen_ablacion.json`
- `data/outputs/train_<run_id>/detalle_columnas_ablacion.json`

Fuentes de verdad:
- `resumen_entrenamiento.json`
- `comparacion_modelos_dev.csv`

Contrato:
- `08` consume una corrida base canónica de `train_*`;
- barrido y cierre usan también esta metadata para reconstruir bloques activos y backbone.

### Comparación controlada de backbone
Script:
- `scripts/comparar_backbones_hibrido.py`

Salidas:
- `data/outputs/comparacion_backbones_hibrido_<timestamp>/comparacion_backbones_hibrido.csv`
- `data/outputs/comparacion_backbones_hibrido_<timestamp>/comparacion_backbones_hibrido.json`
- `data/outputs/comparacion_backbones_hibrido_<timestamp>/resumen_backbones_hibrido.md`
- `data/outputs/comparacion_backbones_hibrido_latest.json`

Fuente de verdad:
- `data/outputs/comparacion_backbones_hibrido_latest.json`

Contrato:
- resuelve el backbone contextual del híbrido con el resto fijo;
- `06` usa `BETO` por defecto siguiendo esta decisión, no la de `04c`.

### 08. Consolidación de resultados comparativos
Notebook:
- `notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`

Entradas:
- artefactos de `04a/04b/04c`
- corrida base válida de `07`

Salidas:
- `data/outputs/results_<timestamp>/tabla_comparativa_modelos.csv`
- figuras y resúmenes comparativos

Contrato:
- compara familias de modelos;
- no congela todavía el mejor híbrido final.

### Barrido y ablación del híbrido
Script:
- `scripts/ejecutar_barrido_ablacion_hibrido.py`

Entradas:
- `feature_run_base`
- `ref_train_run`
- artefactos base de líneas base textuales

Salidas:
- `data/outputs/barridos_hibridos/<timestamp>/tabla_maestra_comparativa.csv`
- `ranking_variantes.csv`
- `estabilidad_variantes.csv`
- `analisis_dependencia_beto.csv`
- `resumen_barrido.json`
- `resumen_interpretativo.md`

Fuentes de verdad:
- `tabla_maestra_comparativa.csv`
- `ranking_variantes.csv`

Contrato:
- `09b` consume estas dos salidas para armar el pool final de candidatos.

### Freeze léxico
Script:
- `scripts/audit/generar_freeze_lexico.py`

Salidas:
- `data/outputs/freeze_lexico_<timestamp>/freeze_lexico_resumen.json`
- `freeze_lexico_resumen.md`
- `checksums_sha256.csv`
- `snapshot/`

Fuente de verdad:
- `freeze_lexico_resumen.json`

Contrato:
- `09b` exige un freeze válido para registrar el estado del recurso clínico usado en el cierre.

### Manifiesto de artefactos de backbone
Script:
- `scripts/audit/registrar_artefactos_backbone.py`

Salidas:
- `data/outputs/backbone_artifacts_manifest_<timestamp>.json`
- `data/outputs/backbone_artifacts_manifest_latest.json`
- `data/outputs/backbone_artifacts_manifest_latest.md`

Fuente de verdad:
- `backbone_artifacts_manifest_latest.json`

Contrato:
- ayuda a distinguir artefactos de backbone válidos de corridas incompletas.

### 09b. Cierre formal en `dev`
Notebook:
- `notebooks/pipeline/09b_cierre_modelos_dev.ipynb`

Script operativo:
- `scripts/cerrar_modelos_dev.py`
- `scripts/audit/cerrar_modelos_dev.py`

Entradas:
- barrido compatible
- freeze léxico válido
- selección standalone de `04c`
- comparación controlada de backbone

Salidas:
- `data/outputs/cierre_modelos_dev_<timestamp>/ranking_modelos_dev.csv`
- `rubrica_seleccion_modelos.csv`
- `decision_modelo_final.json`
- `decision_modelo_final.md`
- `lista_modelos_para_test.json`
- `riesgos_y_limitaciones_dev.md`

Fuentes de verdad:
- `decision_modelo_final.json`
- `ranking_modelos_dev.csv`
- `rubrica_seleccion_modelos.csv`

Contrato:
- `decision_modelo_final.json` es la fuente de verdad del modelo final congelado en `dev`.
- `09` debe analizar ese modelo, no el mejor por una heurística propia.

### 09. Análisis de errores
Notebook:
- `notebooks/analysis/09_analisis_errores_hibrido.ipynb`

Entrada:
- `decision_modelo_final.json`
- predicciones del modelo final congelado

Salidas:
- `data/outputs/error_analysis_<timestamp>/...`

Fuente de verdad:
- el artefacto de cierre de `09b` manda sobre qué modelo debe analizarse.

### 09c. Auditoría y validación secundaria en `dev`
Notebook:
- `notebooks/analysis/09c_auditoria_validacion_secundaria_dev.ipynb`

Script:
- `scripts/audit/generar_auditoria_validacion_secundaria_dev.py`

Entrada:
- `decision_modelo_final.json`
- predicciones del modelo final congelado
- baselines de `dev`
- `dataset_base`, `dataset_denoised` y splits denoised
- `ips_raw.csv` solo para auditoría demográfica descriptiva

Salidas:
- `data/outputs/auditoria_final_caseC_validacion_secundaria/resumen_auditoria_validacion_secundaria_dev.json`
- `metricas_tres_niveles_dev.csv`
- `metricas_auc_ap_ansiedad_dev.csv`
- `threshold_sweep_hibrido_dev.csv`
- `metricas_xgb_sample_weight_comparacion.csv`
- `case_c_trace.json`
- `shap_global_familias.csv`

Contrato:
- consume artefactos ya congelados en `dev`;
- no reabre selección de modelo, ontología ni tarea binaria;
- documenta robustez secundaria antes de abrir `test`.

### 10. Revisión clínica externa
Notebook:
- `notebooks/analysis/10_validacion_clinica_ips.ipynb`

Scripts:
- `scripts/export/generar_material_validacion_ips.py`
- `scripts/export/curar_dossier_ips.py`
- `scripts/export/cerrar_fase_ips.py`

Contrato:
- consume artefactos ya cerrados en `dev`;
- no redefine la shortlist;
- no reabre entrenamiento ni cierre.

## Punteros `latest` relevantes
Cuando existan, priorizar:

- `data/outputs/transformer_baseline_selection_latest.json`
- `data/outputs/comparacion_backbones_hibrido_latest.json`
- `data/outputs/backbone_artifacts_manifest_latest.json`
- `data/outputs/reporte_estado_actual_latest.json`

## Qué artefactos son canónicos y cuáles no

### Canónicos de decisión
- `transformer_baseline_selection_latest.json`
- `comparacion_backbones_hibrido_latest.json`
- `decision_modelo_final.json`
- `rubrica_seleccion_modelos.csv`

### Regenerables locales
- carpetas `train_<timestamp>/`
- carpetas `results_<timestamp>/`
- carpetas `error_analysis_<timestamp>/`
- carpetas `regeneracion_desarrollo_<timestamp>/`

### Secundarios o de apoyo
- auditoría secundaria en `dev` (`09c`)
- material de revisión clínica externa (`10`)
- `BASELINE_CRUDO_VS_FILTRADO.md`

## Regla práctica para lectores y scripts
Si una pregunta es de:

- **qué modelo quedó congelado**: leer `decision_modelo_final.json`.
- **qué backbone ganó dentro del híbrido**: leer `comparacion_backbones_hibrido_latest.json`.
- **qué transformer standalone quedó primero**: leer `transformer_baseline_selection_latest.json`.
- **qué artefactos actuales son consistentes entre sí**: leer `reporte_estado_actual_latest.json`.
