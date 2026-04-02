# Guía de Scripts

Scripts públicos de soporte al experimento.

## Alcance
La superficie pública de scripts se centra en el flujo experimental principal `01–09`:
- regeneración del pipeline;
- extracción semántica acotada con LLM;
- auditoría léxica;
- comparación controlada de backbone;
- barrido y ablación del híbrido;
- freeze léxico;
- cierre formal en `dev`.

Los scripts de exportación clínica o de uso interno quedan fuera de esta guía principal.

## Estructura pública mínima
```text
scripts/
  regenerar_pipeline_desarrollo.py
  run_regeneracion_desarrollo.sh
  ejecutar_barrido_ablacion_hibrido.py
  ejecutar_barrido_hibrido.py
  comparar_backbones_hibrido.py
  cerrar_modelos_dev.py
  llm/
    run_gemini_constrained.py
  audit/
    audit_core.py
    cerrar_modelos_dev.py
    registrar_artefactos_backbone.py
    generar_freeze_lexico.py
  devtools/
    split_batches.py
```

## Convención léxica canónica
- capas:
  - `Concept_CO` = baseline histórico;
  - `Concept_Core` = núcleo clínico depurado;
  - `Concept_PY` = capa regional paraguaya.
- perfiles:
  - `co` = `Concept_CO`
  - `core` = `Concept_Core`
  - `py` = `Concept_Core` + `Concept_PY`

## Comandos principales
```bash
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
python scripts/llm/run_gemini_constrained.py
python scripts/audit/audit_core.py --patterns_root Spanish_Psych_Phenotyping_PY/escribe/patterns --co Concept_CO --core Concept_Core --lexicon Concept_PY
python scripts/comparar_backbones_hibrido.py --backbones beto,roberta_clinical --incluir-biomedical 0 --seed 42
python scripts/ejecutar_barrido_ablacion_hibrido.py --eval-split dev --ref-train-run train_YYYYMMDD_HHMMSS --fases A,B,C --top-c 3
python scripts/audit/generar_freeze_lexico.py
python scripts/cerrar_modelos_dev.py
```

## Regeneración del pipeline de desarrollo
- Script principal: `scripts/regenerar_pipeline_desarrollo.py`.
- Wrapper opcional: `scripts/run_regeneracion_desarrollo.sh`.
- Alcance: hasta cierre formal en `dev`, sin ejecutar `test` ni xAI.
- Flujo metodológico resumido:
  1. datos, split y denoising (`01`-`03`);
  2. líneas base (`04a`, `04b`, `04c`);
  3. análisis léxico (`05`);
  4. features híbridas (`06`) con `BETO` por defecto como backbone contextual del híbrido;
  5. entrenamiento híbrido (`07`);
  6. comparación controlada de backbone (`scripts/comparar_backbones_hibrido.py`);
  7. resultados comparativos (`08`);
  8. barrido y ablación en `dev` (`scripts/ejecutar_barrido_ablacion_hibrido.py`);
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

## Extracción semántica acotada con LLM
- Script: `scripts/llm/run_gemini_constrained.py`.
- Rol: generar `data/processed/gemini_extraction.json` para normalización semántica de síntomas y apoyo de auditoría léxica.
- Restricción metodológica: el LLM no se usa como clasificador clínico directo.

## Comparación controlada de backbones en híbrido
- Script: `scripts/comparar_backbones_hibrido.py`.
- Rol: comparar `BETO` y alternativas dentro del híbrido, manteniendo constante el resto de la configuración.
- Resultado esperado: artefactos en `data/outputs/comparacion_backbones_hibrido_<timestamp>/` y puntero `comparacion_backbones_hibrido_latest.json`.

## Barrido y ablación del híbrido
- Script canónico: `scripts/ejecutar_barrido_ablacion_hibrido.py`.
- Wrapper legacy compatible: `scripts/ejecutar_barrido_hibrido.py`.
- Fases:
  - `A`: barrido factorial principal.
  - `B`: ablaciones estructurales sobre candidatas.
  - `C`: estabilidad multi-seed.
- Salidas esperadas en `data/outputs/barridos_hibridos/<timestamp>/`:
  - `tabla_maestra_comparativa.csv`
  - `ranking_variantes.csv`
  - `resumen_barrido.json`
  - `resumen_interpretativo.md`
  - `predicciones_por_fila/`
  - `matrices_confusion/`
  - `importancia_features/`

## Freeze léxico
- Script: `scripts/audit/generar_freeze_lexico.py`.
- Objetivo: congelar la versión exacta de `Concept_CO`, `Concept_Core` y `Concept_PY` con snapshot, checksums y diff contra un freeze previo.
- No depende de una planilla externa; trabaja sobre el submódulo clínico y los artefactos del repositorio.

## Cierre formal de modelos en `dev`
- Script estable: `scripts/cerrar_modelos_dev.py`.
- Implementación operativa: `scripts/audit/cerrar_modelos_dev.py`.
- Uso:
```bash
python scripts/cerrar_modelos_dev.py
python scripts/cerrar_modelos_dev.py --barrido-dir data/outputs/barridos_hibridos/<timestamp> --freeze-dir data/outputs/freeze_lexico_<timestamp>
```

Salidas del cierre:
- `data/outputs/cierre_modelos_dev_<timestamp>/ranking_modelos_dev.csv`
- `data/outputs/cierre_modelos_dev_<timestamp>/rubrica_seleccion_modelos.csv`
- `data/outputs/cierre_modelos_dev_<timestamp>/decision_modelo_final.md`
- `data/outputs/cierre_modelos_dev_<timestamp>/decision_modelo_final.json`
- `data/outputs/cierre_modelos_dev_<timestamp>/lista_modelos_para_test.json`
- `data/outputs/cierre_modelos_dev_<timestamp>/riesgos_y_limitaciones_dev.md`

## Manifiesto de artefactos de backbone
- Script: `scripts/audit/registrar_artefactos_backbone.py`.
- Objetivo: marcar artefactos válidos e incompletos sin borrar salidas previas y publicar punteros confiables.

Salidas en `data/outputs/`:
- `backbone_artifacts_manifest_<timestamp>.json`
- `backbone_artifacts_manifest_latest.json`
- `backbone_artifacts_manifest_latest.md`
- `comparacion_backbones_hibrido_latest.json`

## Nota metodológica sobre `06`
- `04c` decide el mejor transformer standalone.
- `06` usa `BETO` por defecto para el híbrido porque la comparación controlada de backbone retuvo `BETO` dentro de la arquitectura híbrida.
- Si se quiere heredar explícitamente la selección standalone de `04c`, debe indicarse `FE_TEXT_BACKBONE=auto`.
- `04b` no interviene en esta decisión: `TF-IDF` es un baseline textual fuerte, pero no alimenta el bloque contextual `ctx_<backbone>_*`.
