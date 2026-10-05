# Decisiones metodológicas clave

## Decisiones cerradas
- Clasificación por nota entre `ansiedad` y `depresion`, sin controles ni comorbilidad como tercera clase.
- Partición por paciente anterior al denoising; universo comparativo principal de 1835 notas retenidas.
- `dev` para comparación y selección; `test` para evaluación de configuraciones definidas, sin reajuste posterior.
- TF-IDF + LinearSVC como referencia léxica, no como clasificador elegido mediante búsqueda exhaustiva.
- RoBERTa clínico como mejor Transformer standalone del cierre 512.
- BETO como backbone del híbrido, retenido por comparación controlada en una variante de 861 variables.
- Híbrido completo PY XGBoost 512 (958 variables) como comparador de integración temprana, distinto del histórico reducido.
- Ensamble de integración tardía seleccionado en desarrollo: contextual RoBERTa clínico + RF `py` sin LLM + RF `core` con LLM.
- Pesos vigentes `0.65 / 0.15 / 0.20`, seleccionados por Macro-F1 entre 231 ternas en `dev`.
- `max_length=512` como condición principal; `256` es sensibilidad no adoptada.
- Pesos históricos `0.80 / 0.10 / 0.10` no vigentes: checkpoint contextual exacto no recuperado.

## Convención léxica y fusión
- `co = Concept_CO`: baseline histórico.
- `core = Concept_Core`: núcleo clínico depurado.
- `py = Concept_Core + Concept_PY`: núcleo más adaptación paraguaya.
- `feat_X = max(rule_X, llm_X)`: unión binaria de síntomas, no combinación de predicciones diagnósticas.
- `rule_medication_*`: evidencia terapéutica separada.
- LLM limitado a revisión léxica y normalización dentro de la ontología; no clasificación clínica directa.

La extracción conservada se aplica a entrenamiento, desarrollo y prueba sin suministrar etiquetas. No se demuestra procedencia individual completa de cada término local ni independencia inicial de su construcción respecto del texto posteriormente asignado a prueba.

## Cierres que no deben confundirse
`09b` conserva el cierre multicriterio histórico y su shortlist; `09` interpreta sus errores. La rúbrica histórica no seleccionó los pesos vigentes del ensamble.

El recongelado reproducible del 6 de junio precedió al cierre final `predict-only` de `10`. Las comparaciones posteriores de TF-IDF y del híbrido no forman parte de esa ejecución: se reprodujo TF-IDF con entrenamiento solo en train y se hizo inferencia del híbrido conservado.

El ensamble fue el mejor Macro-F1 en desarrollo, pero TF-IDF obtuvo el mayor valor puntual en prueba. No presentar al ensamble ni al híbrido como ganador de la evaluación final ni afirmar superioridad estadística sin una comparación pareada.

## Análisis secundarios y pendientes
- `01` contiene todo el EDA global y por partición, sin scripts de EDA; su fase completa requiere artefactos posteriores.
- `05` documenta cobertura `co/core/py` en desarrollo, no una auditoría equivalente de cobertura en prueba.
- `09c` conserva métricas por paciente, sensibilidad de entrenamiento y SHAP de configuraciones históricas; no reabre selección.
- Las métricas aisladas de las ramas en prueba no son una ablación causal de PY o LLM.
- Preparar materiales clínicos no acredita revisión experta completada; la correctitud del denoising sigue pendiente de validación.
- La explicabilidad del ensamble final sigue pendiente; SHAP del XGBoost histórico no la reemplaza.

## Referencias congeladas
- Desarrollo: `data/outputs/cierre_dev_recongelado_roberta_512_20260606_160946/`.
- Prueba: `data/outputs/cierre_final_test_ensamble_512_20260606_1640/`.
- Mayo histórico: `data/outputs/cierre_dev_ensamble_512_20260512_155606/`.

Consultar [Revalidación](REVALIDACION_RESULTADOS_REFERENCIA.md) para cifras y procedencia. Los manifiestos e identificadores explícitos definen el cierre; los punteros `latest` pueden cambiar y no sustituyen esa identidad. No publicar artefactos clínicos ni documentación interna con el código.
