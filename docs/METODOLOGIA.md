# Metodología

## Objetivo y unidad de análisis
El pipeline clasifica notas clínicas psiquiátricas del IPS, en español de Paraguay, entre `ansiedad` y `depresion`. La unidad principal de predicción y evaluación es la nota; los pacientes se separan entre conjuntos. No constituye diagnóstico clínico autónomo ni screening: no incluye controles ni una clase de comorbilidad.

Las ramas del ensamble producen probabilidades. TF-IDF + LinearSVC produce decisiones mediante un margen lineal, no probabilidades calibradas.

## Universo y EDA
La preparación conserva `3155 -> 3143 -> 1835` notas: corpus original, base limpia y universo denoised. Permanecen los 90 pacientes. `02` fija la partición por paciente antes del filtro de `03`.

| Conjunto denoised | Pacientes | Notas | Ansiedad | Depresión |
|---|---:|---:|---:|---:|
| Entrenamiento | 54 | 1107 | 358 | 749 |
| Validación | 18 | 343 | 100 | 243 |
| Prueba | 18 | 385 | 98 | 287 |
| Total | 90 | 1835 | 556 | 1279 |

El EDA completo reside en `01_datos_eda_limpieza.ipynb`, sin scripts externos de EDA: universo global, clases, notas por paciente, sexo y edad, longitudes, tokens, vocabulario, duplicados, retención y comparación por partición y clase. Genera tablas, figuras y reporte local. Su ejecución completa necesita las salidas de `02`/`03` y el tokenizer local; limpieza inicial y EDA completo tienen requisitos distintos. Véase [Guía de ejecución](GUIA_EJECUCION.md).

## Denoising y señal útil
`03` emplea el perfil `core`, spaCy, medspaCy y la política `utils_shared.keep_entity`. Excluye menciones históricas, hipotéticas o familiares; conserva las afirmadas y las negadas cuando la negación se atribuye al paciente. La negación de plantilla no se considera señal válida.

Una nota se retiene si contiene al menos una entidad aceptada. Puede ser sintomática, terapéutica o contextual: `has_clinical_signal` no demuestra por sí mismo capacidad diferencial ni equivale a validación clínica. Se excluyen 1308 de las 3143 notas (41.62%); el rendimiento corresponde al universo retenido, no a todas las consultas originales.

## Recursos clínico-léxicos y LLM
La dependencia clínica está versionada como submódulo. Se mantienen las capas y perfiles:

- `Concept_CO`: base histórica; perfil `co`.
- `Concept_Core`: núcleo depurado; perfil `core`.
- `Concept_PY`: adaptación paraguaya, sumada a Core en el perfil `py`.

Los diccionarios contienen patrones asociados a categorías clínicas, no etiquetas de diagnóstico. El LLM apoyó la revisión léxica y, en una operación distinta, normalizó menciones a una ontología cerrada. No clasifica ansiedad/depresión ni crea libremente categorías nuevas.

La extracción conservada mediante Google GenAI API cubre las 1835 notas, incluidas las de prueba, usando `row_id` y texto, sin suministrar la etiqueta ni el identificador del paciente como campos. Aplicar un extractor definido a prueba no equivale a entrenar con sus etiquetas. La trazabilidad no demuestra qué notas se consultaron al construir inicialmente el léxico ni liga inequívocamente toda la configuración a la ejecución efectiva. El modelo efectivo no debe inferirse solo de su valor predeterminado.

En `06`, la unión binaria de síntomas es `feat_X = max(rule_X, llm_X)`; las negaciones se representan de forma diferenciada y `rule_medication_*` permanece como evidencia terapéutica separada. Esta fusión de menciones no es el ensamble final de probabilidades.

## Modelos y selección
Todos los comparadores principales usan el mismo universo denoised:

1. `04a`: Dummy como referencia trivial.
2. `04b`: TF-IDF de caracteres + LinearSVC balanceado, ajustado solo con entrenamiento. Es una referencia para matrices dispersas de alta dimensionalidad, no el ganador de una búsqueda entre clasificadores léxicos.
3. `04c`: Transformers standalone ajustados para la tarea, comparados en `dev`.
4. `06`/`07`: integración temprana de variables clínico-léxicas, sentimiento y embeddings BETO, seguida de RF/XGBoost. El comparador completo 512 tiene 958 variables, distinto de la variante histórica reducida de 861.
5. Ensamble: integración tardía de probabilidades de tres modelos independientes, no de sus matrices de features.

La comparación controlada de backbone retuvo BETO en la variante de 861 variables (Macro-F1 en `dev`: 0.728894 frente a 0.724315 con RoBERTa clínico). No contradice la selección de RoBERTa como mejor standalone ni demuestra la misma diferencia en la matriz completa. `06` usa BETO por defecto; `FE_TEXT_BACKBONE=auto` adopta explícitamente la selección standalone.

`09b` conserva la selección multicriterio histórica del híbrido y su shortlist; `09` conserva el análisis de errores asociado. No eligieron los pesos vigentes. El recongelado del 6 de junio seleccionó por Macro-F1 en `dev` la mejor de 231 ternas de pesos, en pasos de 0.05:

- RoBERTa clínico ajustado, `max_length=512`: peso 0.65.
- Random Forest `py` (Core + PY), sin LLM: peso 0.15.
- Random Forest `core` con unión de síntomas de reglas y LLM: peso 0.20.

La decisión usa el máximo de las probabilidades combinadas, sin reajustar un umbral en prueba. El cierre anterior `0.80 / 0.10 / 0.10` es histórico: no se conservó el checkpoint exacto que lo reprodujera.

## Evaluación y alcance
`10_cierre_final_test_ensamble.ipynb` verifica reproducción contextual en `dev`, alineación por `row_id` y orden de clases, y ejecuta inferencia `predict-only` con modelos y pesos congelados. El cierre final del ensamble del 6 de junio no reentrenó ni reajustó. Las comparaciones posteriores son distintas de esa ejecución: TF-IDF se reprodujo ajustando solo en entrenamiento y el híbrido se evaluó cargando su modelo conservado.

Los [valores de referencia](REVALIDACION_RESULTADOS_REFERENCIA.md) reúnen resultados y procedencia. El ensamble fue el mejor en desarrollo (Macro-F1 0.757017), pero TF-IDF + LinearSVC obtuvo el mayor valor puntual en prueba (0.584478 frente a 0.555807). No se demuestra superioridad estadística ni aporte causal aislado del léxico paraguayo.

Se priorizan Macro-F1, balanced accuracy y F1 por clase. El bootstrap por paciente estima incertidumbre del rendimiento del ensamble, no de la diferencia entre modelos. Las métricas por paciente y SHAP de `09c` corresponden a configuraciones históricas en `dev`, no a explicabilidad del ensamble final.

El EDA y las auditorías posteriores no habilitan selección con prueba. La revisión clínica de retenidas/excluidas y la explicabilidad final siguen pendientes. Véanse [Limitaciones](LIMITACIONES.md) y [Estrategia de validación](ESTRATEGIA_VALIDACION.md).
