# Guía de Scripts

Scripts activos de soporte al pipeline.

## Estructura
```text
scripts/
  regenerar_pipeline_desarrollo.py
  run_regeneracion_desarrollo.sh
  ejecutar_barrido_hibrido.py
  comparar_backbones_hibrido.py
  cerrar_modelos_dev.py
  consolidar_insumos_tesis.py
  llm/
    run_gemini_constrained.py
  audit/
    audit_core.py
    cerrar_modelos_dev.py
    registrar_artefactos_backbone.py
    diff_meds_excel_repo.py
    generar_freeze_lexico.py
    freeze_core_from_excel.py
  export/
    export_project_chats_md.py
  devtools/
    split_batches.py
```

## Uso
```bash
python scripts/llm/run_gemini_constrained.py
python scripts/audit/audit_core.py --patterns_root Spanish_Psych_Phenotyping_PY/escribe/patterns --co Concept_CO --core Concept_PY --lexicon Concept_PY_Lexicon
python scripts/audit/diff_meds_excel_repo.py
python scripts/audit/generar_freeze_lexico.py
python scripts/audit/freeze_core_from_excel.py
python scripts/audit/registrar_artefactos_backbone.py
python scripts/export/export_project_chats_md.py <archivo.json> -o salidas_md
python scripts/devtools/split_batches.py --batch-size 10
python scripts/ejecutar_barrido_hibrido.py --eval-split dev --ref-train-run train_20260310_093418 --fases A,B,C --top-c 3
python scripts/comparar_backbones_hibrido.py --backbones beto,roberta_clinical --incluir-biomedical 0 --seed 42
python scripts/cerrar_modelos_dev.py
python scripts/consolidar_insumos_tesis.py --dry-run --verbose
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
```

## Regeneración del pipeline de desarrollo
- Script principal: `scripts/regenerar_pipeline_desarrollo.py`.
- Wrapper opcional: `scripts/run_regeneracion_desarrollo.sh`.
- Alcance: hasta cierre formal en `dev`, sin ejecutar `test` ni xAI.
- Flujo metodológico (resumen):
  1. datos, split y denoising (`01`-`03`);
  2. líneas base (`04a`, `04b`, `04c`);
  3. análisis léxico (`05`);
  4. features híbridas (`06`) con consumo de selección Transformer de `04c`;
  5. entrenamiento híbrido (`07`);
  6. comparación controlada de backbones (`scripts/comparar_backbones_hibrido.py`, opcional por flag);
  7. resultados comparativos (`08`);
  8. barrido/ablación en `dev` (`scripts/ejecutar_barrido_hibrido.py`);
  9. freeze léxico;
  10. manifiesto de artefactos de backbone;
  11. cierre formal en `09b` / `scripts/cerrar_modelos_dev.py`;
  12. análisis de errores.

Ejemplos:
```bash
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --desde 06_ingenieria_features_hibridas --hasta 09b_cierre_modelos_dev
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
python scripts/regenerar_pipeline_desarrollo.py --limpiar-outputs --confirmar-limpieza --dry-run
```

## Cierre formal de modelos en dev
- Script estable: `scripts/cerrar_modelos_dev.py`.
- Implementación operativa: `scripts/audit/cerrar_modelos_dev.py`.
- Uso:
```bash
python scripts/cerrar_modelos_dev.py
python scripts/cerrar_modelos_dev.py --barrido-dir data/outputs/barridos_hibridos/20260310_202656 --freeze-dir data/outputs/freeze_lexico_20260310_232420
```

Salidas del cierre de modelos:
- `data/outputs/cierre_modelos_dev_<timestamp>/ranking_modelos_dev.csv`
- `data/outputs/cierre_modelos_dev_<timestamp>/rubrica_seleccion_modelos.csv`
- `data/outputs/cierre_modelos_dev_<timestamp>/decision_modelo_final.md`
- `data/outputs/cierre_modelos_dev_<timestamp>/decision_modelo_final.json`
- `data/outputs/cierre_modelos_dev_<timestamp>/lista_modelos_para_test.json`
- `data/outputs/cierre_modelos_dev_<timestamp>/riesgos_y_limitaciones_dev.md`

Salidas de control de regeneración:
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.md`
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.json`

## Consolidación de insumos para tesis
- Script: `scripts/consolidar_insumos_tesis.py`.
- Rol: construir un paquete único y trazable de insumos de Metodología/Resultados sin hardcodear timestamps.
- No reentrena ni recalcula modelos; consolida artefactos ya generados.

Ejemplos:
```bash
python scripts/consolidar_insumos_tesis.py --dry-run --verbose
python scripts/consolidar_insumos_tesis.py --output-tag consolidacion_actual
```

Opciones:
- `--dry-run`: valida selección/consistencia sin escribir archivos.
- `--verbose`: imprime detalle de resolución de artefactos.
- `--output-tag`: reemplaza timestamp por tag estable en la carpeta de salida.

Criterio de selección de artefactos:
- Prioridad 1: punteros estables (`*_latest.json`, manifiestos vigentes, aliases).
- Prioridad 2: fallback por patrón + timestamp cuando falta puntero latest.
- Prioridad 3: validación de compatibilidad entre componentes (cierre dev, freeze, backbone, error analysis); si hay ambigüedad, se reporta explícitamente.

Salida:
- `data/outputs/insumos_tesis_metodologia_resultados_<timestamp_o_tag>/`
- Incluye: `dataset_resumen.csv`, `dataset_resumen.md`, `arquitectura_lexica_resumen.csv`, `arquitectura_lexica_resumen.md`, `baselines_dev_resumen.csv`, `transformers_baseline_resumen.csv`, `backbones_hibrido_resumen.csv`, `transformer_vs_backbone_decision.csv`, `hibridos_dev_resumen.csv`, `modelo_final_dev_resumen.json`, `auditoria_test_resumen.json`, `error_analysis_modelo_final_resumen.csv`, `error_analysis_modelo_final_resumen.md`, `tabla_maestra_insumos_tesis.csv`, `tabla_decisiones_metodologicas_clave.csv`, `tabla_decisiones_metodologicas_clave.md`, `reporte_consolidacion_insumos.md`, `reporte_consolidacion_insumos.json`.

## Comparación controlada de backbones en híbrido
- Script: `scripts/comparar_backbones_hibrido.py`.
- Rol en el pipeline: evaluación controlada de backbone contextual dentro del híbrido (mismo split `dev`, misma configuración de ablación).
- No reemplaza por sí solo el cierre formal: sus resultados deben quedar trazados y consumidos por `09b`.

Salidas en `data/outputs/comparacion_backbones_hibrido_<timestamp>/`:
- `comparacion_backbones_hibrido.csv`
- `comparacion_backbones_hibrido.json`
- `resumen_backbones_hibrido.md`
- `predicciones_por_fila/`
- `metadatos_backbone/`

## Barrido híbrido: contrato mínimo recomendado
- Ejecutar con el entorno del proyecto: `.venv/bin/python scripts/ejecutar_barrido_hibrido.py ...`.
- Definir `--feature-run-base` para fijar el universo de features.
- Definir `--eval-split` (`dev` o `test`) y mantenerlo constante durante la comparación.
- Fases:
  - `A`: barrido factorial principal.
  - `B`: ablaciones estructurales sobre candidatas top.
  - `C`: estabilidad multi-seed.

Salidas esperadas en `data/outputs/barridos_hibridos/<timestamp>/`:
- `tabla_maestra_comparativa.csv`
- `ranking_variantes.csv`
- `resumen_barrido.json`
- `resumen_interpretativo.md`
- `analisis_dependencia_beto.csv`
- `predicciones_por_fila/`, `matrices_confusion/`, `importancia_features/`

Estos scripts no modifican la arquitectura científica congelada; solo apoyan extracción, auditoría, ablación y trazabilidad.

## Freeze lexico (cierre antes de test)
- Script: `scripts/audit/generar_freeze_lexico.py`
- Objetivo: congelar version exacta de `Concept_CO`, `Concept_PY` y `Concept_PY_Lexicon` con snapshot, checksums y diff contra freeze previo.

Ejemplos:
```bash
python scripts/audit/generar_freeze_lexico.py
python scripts/audit/generar_freeze_lexico.py --comparar-con data/outputs/freeze_lexico_20260310_231534
python scripts/audit/generar_freeze_lexico.py --freeze-id freeze_lexico_20260311_101500 --ips-excel data/IPS_validacion.xlsx
```

Salidas en `data/outputs/freeze_lexico_<timestamp>/`:
- `freeze_lexico_resumen.md`
- `freeze_lexico_resumen.json`
- `freeze_lexico_tabla.csv`
- `checksums_sha256.csv`
- `freeze_lexico_diff_resumen.csv`
- `freeze_lexico_diff_terminos.csv`
- `snapshot/`

## Manifiesto de artefactos de backbone
- Script: `scripts/audit/registrar_artefactos_backbone.py`
- Objetivo: marcar artefactos válidos/incompletos sin borrar salidas previas y publicar punteros confiables.

Salidas en `data/outputs/`:
- `backbone_artifacts_manifest_<timestamp>.json`
- `backbone_artifacts_manifest_latest.json`
- `backbone_artifacts_manifest_latest.md`
- `comparacion_backbones_hibrido_latest.json`

Uso recomendado antes de `09b`:
```bash
python scripts/audit/registrar_artefactos_backbone.py
python scripts/cerrar_modelos_dev.py
```
