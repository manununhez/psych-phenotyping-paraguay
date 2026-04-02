# Decisiones Metodológicas Clave

## Decisiones ya cerradas
- tarea actual: clasificación probabilística entre `ansiedad` y `depresion`;
- `comorbilidad` no se modela como tercera clase ni como salida multilabel en esta versión;
- la interpretación vigente del etiquetado es a nivel `texto/consulta`;
- `dev` se usa para desarrollo, comparación y selección;
- `test` sigue reservado para evaluación final;
- baseline fuerte simple: `TF-IDF`;
- mejor transformer standalone actual: `ROBERTA_CLINICAL`;
- mejor backbone contextual del híbrido actual: `BETO`;
- mejor híbrido final actual en `dev`: `B_A_llm0_sent0_beto1_tpl0_py_XGB_sin_feat_sin_medication|py|XGB`;
- `mejor transformer standalone` y `mejor backbone del híbrido` no coinciden y no deben mezclarse conceptualmente.

## Convención léxica vigente
- capas:
  - `Concept_CO` = baseline histórico;
  - `Concept_Core` = núcleo clínico depurado;
  - `Concept_PY` = capa regional paraguaya;
- perfiles:
  - `co` = `Concept_CO`
  - `core` = `Concept_Core`
  - `py` = `Concept_Core` + `Concept_PY`

## Estado operativo
- estado de `test`: `TEST_VIRGEN`;
- estado de xAI: `PENDIENTE`;
- frente formal de validación clínica: `ACTIVO`;
- estado de la fase: `CASI_LISTO_PARA_FREEZE_OFICIAL_Y_TEST`.

## Alcance y límites
- el grupo de control explícito queda fuera del alcance actual;
- las notas administrativas o de reposición conservan sentido asistencial, pero pueden filtrarse cuando no aportan señal clínica útil para esta tarea diferencial;
- el corpus combina estilos estructurados y narrativos, con abreviaturas, comillas, marcas de duda y convenciones locales que deben considerarse en la lectura clínica;
- la narrativa final debe evitar sobreafirmar al híbrido como mejor modelo absoluto, porque los mejores resultados agregados en `dev` siguen en líneas base textuales fuertes.

## Fuentes canónicas
- cierre formal: `notebooks/pipeline/09b_cierre_modelos_dev.ipynb` o `scripts/cerrar_modelos_dev.py`
- comparación backbone válida: `data/outputs/comparacion_backbones_hibrido_latest.json`
- selección transformer vigente: `data/outputs/transformer_baseline_selection_latest.json`
- auditoría de `test`: `data/outputs/auditoria_test_*.md`
- dossier IPS curado vigente: `data/outputs/dossier_ips_curado_latest.json`
