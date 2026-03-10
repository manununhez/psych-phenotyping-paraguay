# Preguntas Clave de la Tesis

## Pregunta 1
¿La brecha léxica entre español clínico colombiano y paraguayo afecta de forma sustantiva la detección de fenotipos psiquiátricos?

Por qué importa: si la respuesta es sí, el problema principal no es solo de modelo, sino de cobertura lingüística. Eso cambia la estrategia: primero hay que corregir representación clínica local, luego optimizar clasificación.

## Pregunta 2
¿`Concept_CO` puede sostener desempeño clínicamente razonable en EHR paraguayos sin adaptación?

Por qué importa: esta pregunta justifica tratar `Concept_CO` como baseline histórico, no como solución final.

## Pregunta 3
¿La transición `Concept_CO -> Concept_PY -> Concept_PY_Lexicon` mejora la robustez semántica sin romper trazabilidad de reglas?

Por qué importa: permite defender que la adaptación no fue una edición ad hoc, sino una progresión auditada.

## Pregunta 4
¿Un baseline de texto convencional (TF-IDF) captura señal útil aun cuando la variación regional siga siendo un problema?

Por qué importa: si TF-IDF funciona razonablemente, aporta una referencia fuerte y económica; también muestra qué parte del problema es resoluble con estadística lexical y qué parte no.

## Pregunta 5
¿BETO ofrece el mejor compromiso entre contexto semántico y estabilidad para este proyecto?

Por qué importa: si BETO es el baseline Transformer más sólido, su reutilización en el modelo híbrido deja de ser una decisión estética y pasa a ser una decisión técnica.

## Pregunta 6
¿El `patient-level split` es indispensable en este escenario longitudinal?

Por qué importa: sin separar por paciente, el modelo puede aprender rastros idiosincráticos y sobredimensionar desempeño por fuga de información.

## Pregunta 7
¿El denoising clínico previo mejora la validez del entrenamiento y del análisis de errores?

Por qué importa: entrenar sobre ruido administrativo distorsiona señales y dificulta interpretar fallas reales del sistema.

## Pregunta 8
¿La negación del paciente aporta señal clínica y la negación de plantilla/médico aporta ruido?

Por qué importa: esta decisión impacta directamente el diseño de `feat_niega_*` y la interpretación del fenotipo.

## Pregunta 9
¿El LLM debe limitarse a normalización semántica y verificación léxica, en lugar de inferencia diagnóstica directa?

Por qué importa: delimita riesgo metodológico y protege reproducibilidad en un proyecto con reglas congeladas.

## Pregunta 10
¿La combinación final (reglas + late fusion + embeddings BETO + sentimiento + RandomForest/XGBoost) es defendible como arquitectura híbrida explicable?

Por qué importa: esta es la pregunta de cierre. Si no se responde con claridad, la tesis queda como una suma de piezas en lugar de un diseño metodológico coherente.
