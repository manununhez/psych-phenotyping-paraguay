# Índice General de Documentos Metodológicos

## Propósito del compendio
Este conjunto de documentos está pensado para acompañar la escritura de tesis y la preparación de manuscritos. El foco no es repetir el contenido de los notebooks, sino ordenar la lógica metodológica detrás de las decisiones técnicas.

## Cómo usar este índice
La lectura recomendada sigue la misma secuencia del trabajo experimental:

1. Planteo de preguntas científicas.
2. Justificación de decisiones de diseño (split, denoising, líneas base, reglas, LLM, modelo híbrido).
3. Síntesis de decisiones y estructura de capítulo metodológico.
4. Cierre con aportes, limitaciones y trabajo futuro.

## Relación con el flujo experimental
Estos documentos se corresponden con el flujo activo de trabajo:

1. `01_datos_eda_limpieza`
2. `02_split_por_paciente` (o equivalente vigente en el repositorio)
3. `03_denoising_reglas_core`
4. `04a_linea_base_dummy`
5. `04b_linea_base_tfidf`
6. `04c_linea_base_transformers`
7. `06_brecha_lexica_co_core_py`
8. `07_ingenieria_features_hibridas`
9. `08_entrenamiento_modelos_hibridos`
10. `09_resultados_hibrido_vs_lineas_base`
11. `10_analisis_errores_hibrido`

## Mapa de documentos
- `01_preguntas_clave_tesis.md`: define qué preguntas debe responder la tesis.
- `02_narrativa_brecha_lexica.md`: describe el problema léxico central y su resolución.
- `03_justificacion_lineas_base.md`: explica por qué se incluyeron dummy, TF-IDF y baselines Transformer.
- `04_justificacion_split_y_denoising.md`: defiende split por paciente y denoising clínico.
- `05_justificacion_reglas_negacion_y_medicacion.md`: fija criterios de reglas, negación y medicación.
- `06_justificacion_llm_y_late_fusion.md`: delimita el rol del LLM y la lógica de late fusion.
- `07_justificacion_modelo_hibrido.md`: integra racionalmente todos los bloques del sistema.
- `08_decisiones_metodologicas_resumidas.md`: resumen ejecutivo de decisiones.
- `09_esqueleto_seccion_metodologia.md`: esquema de capítulo metodológico.
- `10_aportes_limitaciones_y_trabajo_futuro.md`: cierre crítico del trabajo.
- `compendio_notebooklm.md`: versión consolidada para ingesta rápida en NotebookLM.

## Sugerencia práctica para NotebookLM
Primero cargar `compendio_notebooklm.md` para dar contexto general. Después sumar, en este orden, `02`, `03`, `06` y `07` para reforzar la lógica de diseño y los trade-offs metodológicos.
