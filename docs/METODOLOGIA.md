# Metodología

## Propósito del estudio
El objetivo es clasificar notas clínicas psiquiátricas entre dos etiquetas (`ansiedad`, `depresion`) con salida probabilística y un diseño que combine rendimiento y trazabilidad clínica.

## Restricciones metodológicas fijas
El estudio mantiene componentes congelados: `Concept_CO`, `Concept_PY`, `Concept_PY_Lexicon`, `patient-level split` y la regla de `late fusion` (`feat_X = max(rule_X, llm_X)`). Estas restricciones no son accesorias; permiten comparar decisiones sin reescribir la base clínica en cada iteración.

## Secuencia de trabajo
La lógica experimental sigue nueve etapas encadenadas: limpieza inicial, split por paciente, denoising clínico, líneas base, análisis de brecha léxica, ingeniería de features híbridas, entrenamiento, consolidación de resultados y análisis de errores. Esta secuencia evita mezclar decisiones de preprocesamiento con decisiones de modelado.

## Brecha léxica como problema central
La brecha entre `Concept_CO` y el uso real del español clínico paraguayo motivó la transición `Concept_CO -> Concept_PY -> Concept_PY_Lexicon`. El punto no fue solo agregar términos: primero se depuró la capa Core para reducir ruido y luego se extendió cobertura regional con criterios auditables.

## Rol del LLM
El LLM se usa en dos tareas delimitadas: normalización semántica de síntomas para `late fusion` y apoyo en auditoría léxica (coloquialismos, colombianismos, variantes paraguayas y equivalencias). No se usa como clasificador diagnóstico autónomo.

## Justificación de BETO en la cadena experimental
BETO se evalúa como baseline Transformer en 04c y luego se reutiliza en 07/08 como bloque contextual de embeddings. Esta continuidad evita introducir componentes sin evidencia interna previa.

## Salidas reproducibles
La reproducibilidad se apoya en artefactos versionados por corrida: features híbridas en `data/processed`, resultados de entrenamiento en `data/outputs/train_*`, consolidación en `data/outputs/results_*` y análisis de errores en `data/outputs/error_analysis_*`.

## Estado experimental de esta etapa
El cierre actual corresponde a fase de desarrollo en `dev`:
- comparación de líneas base,
- barridos y ablaciones,
- freeze léxico preliminar,
- selección formal de modelo.

La evaluación final en `test` queda explícitamente reservada para la fase siguiente y no forma parte de este cierre.
