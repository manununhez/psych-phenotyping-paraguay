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
- mejor híbrido tabular alineado a 512: `py XGB`;
- mejor modelo global actual en `dev`: ensamble weighted soft `ROBERTA_CLINICAL 512 + simbólico py RF + simbólico core RF late fusion LLM`;
- cierre híbrido tabular previo: conservado como referencia histórica/comparativa;
- `max_length=512` es la condición principal del cierre actual; `max_length=256` queda como sensibilidad no adoptada;
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
- estado de `test`: reservado metodológicamente; auditoría formal `auditoria_test_*.md` pendiente;
- estado de xAI: fuera del cierre técnico actual; integración formal final pendiente;
- frente formal de validación clínica: `ACTIVO`;
- estado de la fase: `CIERRE_DEV_ENSAMBLE_512_RECOMENDADO`.

## Validación secundaria incorporada en `dev`
- la evaluación principal sigue siendo a nivel nota, pero se reportan lecturas secundarias `patient-weighted` y `patient-aggregated`;
- en el híbrido final, `macro_f1` pasa de `0.728894` a nivel nota a `0.692788` en lectura `patient-weighted`;
- TF-IDF conserva el mejor comportamiento bruto entre las referencias evaluadas, incluyendo `patient-weighted`, `patient-aggregated` y AP para `ansiedad`;
- la sensibilidad de entrenamiento con `sample_weight = 1 / n_notas_paciente_train` fue negativa en `dev`, por lo que no se adopta como nuevo cierre;
- la auditoría SHAP mínima muestra predominio global de `ctx_beto_*` sobre `rule_*`; las reglas quedan como señal auditable, no como explicación dominante del XGB final.

## Alcance y límites
- el grupo de control explícito queda fuera del alcance actual;
- las notas administrativas o de reposición conservan sentido asistencial, pero pueden filtrarse cuando no aportan señal clínica útil para esta tarea diferencial;
- el corpus combina estilos estructurados y narrativos, con abreviaturas, comillas, marcas de duda y convenciones locales que deben considerarse en la lectura clínica;
- la narrativa final debe evitar sobreafirmar al híbrido como mejor modelo absoluto, porque los mejores resultados agregados en `dev` siguen en líneas base textuales fuertes.

## Fuentes canónicas
- cierre formal vigente: `data/outputs/cierre_dev_ensamble_512_20260512_155606/manifest.json`
- reporte de cierre vigente: `data/outputs/cierre_dev_ensamble_512_20260512_155606/reporte_cierre_dev_ensamble.md`
- cierre histórico tabular: `notebooks/pipeline/09b_cierre_modelos_dev.ipynb` o `scripts/cerrar_modelos_dev.py`
- comparación backbone válida: `data/outputs/comparacion_backbones_hibrido_latest.json`
- selección transformer vigente: `data/outputs/transformer_baseline_selection_latest.json`
- auditoría de `test`: `data/outputs/auditoria_test_*.md`
- dossier IPS curado vigente: `data/outputs/dossier_ips_curado_latest.json`
