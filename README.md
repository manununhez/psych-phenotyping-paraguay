# Fenotipado Psiquiátrico Paraguay

Repositorio de investigación para clasificación probabilística de notas clínicas psiquiátricas del IPS (Paraguay).

## Objetivo actual
- Tarea supervisada binaria: `ansiedad` vs `depresion`.
- En esta fase no existe clase explícita de `comorbilidad`.
- Arquitectura híbrida congelada: reglas clínicas + normalización semántica acotada con LLM + `embeddings` contextuales (`ctx_<backbone>_*`) + sentimiento + `RandomForest`/`XGBoost`.

## Selección de backbone contextual
- `04c_linea_base_transformers.ipynb` define explícitamente la comparación de baselines Transformer en `dev` y exporta:
  - `data/outputs/transformer_baseline_selection_<timestamp>.json`
  - `data/outputs/transformer_baseline_selection_latest.json`
- `06+` consume ese artefacto para definir el backbone contextual por defecto (`FE_TEXT_BACKBONE=auto`), con posibilidad de override explícito.
- El backbone del híbrido no debe asumirse por defecto; debe justificarse con evidencia experimental (`04c` + comparación controlada de backbones).

Cadena de trazabilidad (sin saltos):
`04c (selección baseline Transformer)` -> `06 (features con backbone configurable)` -> `07 (entrenamiento con metadata de backbone)` -> `scripts/comparar_backbones_hibrido.py` -> `scripts/audit/registrar_artefactos_backbone.py` -> `09b (cierre formal en dev)`.

## Estado metodológico actual
- Selección y ablación cerradas en `dev`.
- `test` reservado para evaluación final (no ejecutado en esta fase).
- Freeze léxico preliminar generado.
- Cierre formal de selección de modelo en `dev` generado.
- Pendientes de fase final (manual):
  - notebook final de evaluación en `test`;
  - notebook final de xAI/explicabilidad.

## Reglas de control experimental
- Split obligatorio: `patient-level split`.
- Regla de `late fusion` congelada: `feat_X = max(rule_X, llm_X)`.
- Recursos léxicos congelados para trazabilidad:
  - `Concept_CO` (baseline histórico),
  - `Concept_PY` (Core),
  - `Concept_PY_Lexicon` (adaptación regional).

## Flujo activo del pipeline de desarrollo
1. `notebooks/pipeline/01_datos_eda_limpieza.ipynb`
2. `notebooks/pipeline/02_patient_level_split.ipynb`
3. `notebooks/pipeline/03_denoising_reglas_core.ipynb`
4. `notebooks/pipeline/04a_linea_base_dummy.ipynb`
5. `notebooks/pipeline/04b_linea_base_tfidf.ipynb`
6. `notebooks/pipeline/04c_linea_base_transformers.ipynb`
7. `notebooks/analysis/05_brecha_lexica_co_core_py.ipynb`
8. `notebooks/pipeline/06_ingenieria_features_hibridas.ipynb`
9. `notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb`
10. `scripts/comparar_backbones_hibrido.py` (comparación controlada en `dev`)
11. `notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`
12. `notebooks/pipeline/09b_cierre_modelos_dev.ipynb`
13. `notebooks/analysis/09_analisis_errores_hibrido.ipynb`

## Diferencia entre `dev` y `test`
- `dev`: comparación de líneas base, barridos, ablaciones y selección del modelo final.
- `test`: evaluación final única de la lista corta congelada.
- En el estado actual del repositorio, la fase `test` y la fase final de xAI todavía no están integradas al flujo automático.

## Reproducción limpia del desarrollo (hasta estado actual)
Script principal:
- `python scripts/regenerar_pipeline_desarrollo.py --dry-run`
- `python scripts/regenerar_pipeline_desarrollo.py`
- `python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones`

Con esto se reproduce el flujo de desarrollo y los artefactos de cierre en `dev`, sin ejecutar `test`.
La decisión formal del modelo final queda en `notebooks/pipeline/09b_cierre_modelos_dev.ipynb` y también es invocable por `scripts/cerrar_modelos_dev.py`.

## Salidas clave
- Features híbridas: `data/processed/fe_<run_id>_{core,py}/`.
- Entrenamiento: `data/outputs/train_<run_id>/`.
- Comparación controlada de backbones: `data/outputs/comparacion_backbones_hibrido_<timestamp>/`.
- Manifiesto de artefactos de backbone: `data/outputs/backbone_artifacts_manifest_latest.json`.
- Resultados comparativos: `data/outputs/results_<run_id>/`.
- Error analysis: `data/outputs/error_analysis_<run_id>/`.
- Freeze léxico: `data/outputs/freeze_lexico_<timestamp>/`.
- Cierre de modelos en `dev`: `data/outputs/cierre_modelos_dev_<timestamp>/`.
- Regeneración: `data/outputs/regeneracion_desarrollo_<timestamp>/`.

## Documentación recomendada
- `docs/pipeline_desarrollo.md`
- `docs/metodologia_experimental.md`
- `docs/estado_actual_proyecto.md`
- `docs/GUIA_EJECUCION.md`
- `scripts/README.md`
