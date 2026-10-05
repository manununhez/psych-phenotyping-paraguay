# Guía de Notebooks

Esta guía describe los notebooks versionados del flujo oficial. Los archivos exploratorios locales no se convierten en etapas del pipeline por estar presentes en el árbol.

## Flujo experimental principal
1. `pipeline/01_datos_eda_limpieza.ipynb`
2. `pipeline/02_patient_level_split.ipynb`
3. `pipeline/03_denoising_reglas_core.ipynb`
4. `pipeline/04a_linea_base_dummy.ipynb`
5. `pipeline/04b_linea_base_tfidf.ipynb`
6. `pipeline/04c_linea_base_transformers.ipynb`
7. `analysis/05_brecha_lexica_co_core_py.ipynb`
8. `pipeline/06_ingenieria_features_hibridas.ipynb`
9. `pipeline/07_entrenamiento_modelos_hibridos.ipynb`
10. `../scripts/comparar_backbones_hibrido.py` (comparación controlada, no notebook).
11. `pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`
12. `pipeline/09b_cierre_modelos_dev.ipynb`
13. `analysis/09_analisis_errores_hibrido.ipynb`
14. `pipeline/10_cierre_final_test_ensamble.ipynb`

## Fases secundarias opcionales
- `analysis/09c_auditoria_validacion_secundaria_dev.ipynb`: controles sobre configuraciones históricas en desarrollo.
- `analysis/10_validacion_clinica_ips.ipynb`: preparación de materiales para revisión experta.

Estas fases consumen artefactos cerrados en `dev`; no redefinen selección. Generar materiales no acredita revisión clínica completada, y SHAP histórico del híbrido no explica el ensamble final.

## Limpieza y EDA en 01
El notebook `01` contiene todo el EDA, sin invocar scripts externos: análisis global y por partición/clase, consultas por paciente, demografía, histogramas e intervalos de edad, longitudes, tokens, truncamiento potencial, vocabulario, duplicados y retención.

Las secciones 1 a 5 preparan `ips_clean.csv`. Desde la sección 6 necesita los artefactos de `02`/`03`; el cálculo de tokens requiere el tokenizer local en `data/checkpoints/roberta_clinical/checkpoint-210`. En un arranque limpio ejecutar primero la limpieza, materializar los insumos y volver al EDA completo. El orquestador actual no implementa automáticamente esta ejecución en dos pasadas.

Si la limpieza difiere del archivo canónico existente, `01` conserva este último y exporta un candidato privado. Eso exige revisar la discrepancia antes de continuar; no sustituir silenciosamente el universo experimental.

## Análisis (científico)
1. `analysis/05_brecha_lexica_co_core_py.ipynb`
2. `analysis/09_analisis_errores_hibrido.ipynb`
3. `analysis/09c_auditoria_validacion_secundaria_dev.ipynb`
4. `analysis/10_validacion_clinica_ips.ipynb`

## Alcance de esta fase
- Este flujo llega al cierre histórico en `dev`, la verificación del recongelado y la inferencia final del ensamble en `test`.
- El notebook final de `test` es `pipeline/10_cierre_final_test_ensamble.ipynb`.
- Incluye auditoría secundaria en `dev` con SHAP mínimo; no incluye todavía xAI final posterior a `test`.
- `09b`/`09` conservan la selección multicriterio histórica y sus errores; no seleccionaron los pesos vigentes `0.65 / 0.15 / 0.20`.
- Las comparaciones posteriores de TF-IDF y del híbrido no son la ejecución final de `10` ni reabren selección con prueba. Véase [Resultados de referencia](../docs/REVALIDACION_RESULTADOS_REFERENCIA.md).
- `05` documenta cobertura `co/core/py` en desarrollo. Las métricas por rama de `10` en prueba describen desempeño, no contribución aislada de PY o LLM.

## Apéndice (solo soporte)
1. `appendix/A00_configuracion_entorno.ipynb`

## Convención obligatoria por notebook operativo
Cada notebook operativo declara al inicio:
- objetivo
- entradas
- salidas
- notebook anterior
- notebook siguiente
- técnicas, herramientas y librerías principales
- por qué esas herramientas son adecuadas en esta etapa y cuál sería la alternativa si no fueran la mejor opción

## Artefactos esperados por etapa
- 01: `reports/eda_audit_20260619/reporte_auditoria_eda.md`, `tables/`, `figures/` y `execution_manifest.json`, además de la limpieza inicial. Son salidas locales, no documentos públicos a versionar.
- 04c: `data/outputs/transformer_baseline_selection_<timestamp>.json` y `data/outputs/transformer_baseline_selection_latest.json`.
- 06: `data/processed/fe_<run_id>_{core,py}/features_{core,py}.parquet`.
- 07: `data/outputs/train_<run_id>/` con métricas, predicciones, figuras y modelos.
- 08: `data/outputs/results_<run_id>/` con tablas y figuras de comparación.
- 09b: `data/outputs/cierre_modelos_dev_<timestamp>/` con ranking, decisión y shortlist histórica. Si no existe un barrido compatible, puede prepararlo y regenerar el freeze; una nueva ejecución no reproduce por sí sola el recongelado vigente.
- 09 análisis: `data/outputs/error_analysis_<run_id>/` con resumen de errores y casos.
- 09c auditoría secundaria: `data/outputs/auditoria_final_caseC_validacion_secundaria/` con Caso C, métricas por paciente, AP/PR-AUC, sensibilidad `sample_weight`, demografía descriptiva y SHAP por familias.
- 10 cierre final test: `data/outputs/cierre_final_test_ensamble_512_20260606_1640/` con métricas, matriz de confusión, predicciones por rama, errores, resumen por paciente y bootstrap agrupado por paciente.
- 10 validación IPS: `data/outputs/material_validacion_ips_<timestamp>/` con preprocesamiento, balance, patrones por clase, comparación entre modelos, errores curados y preguntas para revisión clínica externa.
- Curación posterior al 10: `scripts/export/curar_dossier_ips.py` genera `data/outputs/dossier_ips_curado_<timestamp>/` como dossier reusable para revisión clínica externa y xAI.
- `analysis/10_validacion_clinica_ips.ipynb` funciona como capa legible y reutiliza scripts backend para generación reproducible de artefactos clínicos (`generar_material_validacion_ips.py`, `curar_dossier_ips.py`, `cerrar_fase_ips.py`).

## Flags clave para ablación
- 06 (`pipeline/06_ingenieria_features_hibridas.ipynb`):
  - `FE_USE_LLM = auto | 1 | 0`
  - `FE_COMPUTE_SENTIMENT = 1 | 0`
  - `FE_COMPUTE_CONTEXT = 1 | 0` (alias legacy: `FE_COMPUTE_BETO`)
  - `FE_TEXT_BACKBONE = auto | beto | roberta_clinical | roberta_biomedical`
  - `FE_RUN_ID`, `FE_CACHE_KEY`
- 07 (`pipeline/07_entrenamiento_modelos_hibridos.ipynb`):
  - `TRAIN_MODELS`, `TRAIN_PROFILES`, `TRAIN_SEED`, `TRAIN_EVAL_ON`
  - `TRAIN_FEATURE_RUN_BASE`, `TRAIN_FEATURE_RUN_ID_CORE`, `TRAIN_FEATURE_RUN_ID_PY`
  - `TRAIN_USE_LLM`, `TRAIN_USE_CONTEXT` (alias legacy: `TRAIN_USE_BETO`), `TRAIN_USE_TEMPLATE`
  - `TRAIN_USE_FEAT`, `TRAIN_USE_RULES`, `TRAIN_USE_MEDICATION`, `TRAIN_USE_SENTIMENT`
  - `TRAIN_DROP_COLUMNS`, `TRAIN_DROP_PREFIXES`, `TRAIN_KEEP_PREFIXES`

## Resolución por defecto de artefactos
- La resolución automática sirve para nuevas corridas. Para reproducir el cierre vigente conservar manifiestos, hashes e identificadores explícitos; no asumir que `latest` sigue apuntando a la referencia original.
- 07 resuelve la última corrida completa de features (`fe_*`) por mtime real, no por orden alfabético del nombre.
- 08 resuelve por defecto la última corrida base canónica `train_YYYYMMDD_HHMMSS`, evitando confundirse con corridas hijas del barrido.
- 09b busca un barrido compatible con la corrida base actual (`train_*` + `fe_*`) y, si no existe, puede generarlo automáticamente antes del cierre formal.

## Nota metodológica de backbone
- `04c` es la etapa explícita de selección del baseline Transformer en `dev`.
- `06` usa BETO por defecto para el híbrido, de acuerdo con la comparación controlada de backbone. Si se quiere heredar explícitamente la selección de `04c`, debe indicarse `FE_TEXT_BACKBONE=auto`.
- `04b` no interviene en esta decisión: `TF-IDF` es un baseline textual fuerte, pero no alimenta el bloque contextual `ctx_<backbone>_*`.

## Convención léxica canónica
- Capas:
  - `Concept_CO` = baseline histórico colombiano.
  - `Concept_Core` = núcleo clínico depurado.
  - `Concept_PY` = capa regional paraguaya.
- Perfiles:
  - `co` = `Concept_CO`
  - `core` = `Concept_Core`
  - `py` = `Concept_Core` + `Concept_PY`
