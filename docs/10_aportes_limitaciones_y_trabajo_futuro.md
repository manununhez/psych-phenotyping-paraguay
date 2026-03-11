# Aportes, Limitaciones y Trabajo Futuro

## Aportes metodológicos del trabajo
1. Formalización de una ruta de adaptación léxica clínica (`Concept_CO -> Concept_PY -> Concept_PY_Lexicon`) con trazabilidad.
2. Integración híbrida defendible entre reglas, normalización semántica por LLM, `embeddings` BETO y señal de sentimiento.
3. Delimitación explícita del rol del LLM para evitar dependencia diagnóstica opaca.
4. Tratamiento diferenciado de negación clínica: preservación de negación del paciente y filtrado de negación de plantilla/médico.
5. Conservación de medicación como evidencia terapéutica separada (`rule_medication_*`), evitando fusión diagnóstica incontrolada.
6. Flujo reproducible con artefactos exportables para reporte metodológico y auditoría.

## Limitaciones
1. Dependencia de cobertura lexical y calidad de redacción clínica local.
2. Riesgo de que expresiones regionales nuevas queden fuera de ontología si no hay auditoría continua.
3. Sensibilidad a decisiones de etiquetado cuando existe superposición fenotípica.
4. Condicionamiento del rendimiento de bloques contextuales por disponibilidad de cómputo y librerías.
5. Necesidad de validación externa para afirmar transferibilidad fuera del entorno institucional original.

## Trabajo futuro razonable
1. Validación multicéntrica en otros servicios y regiones.
2. Protocolo periódico de auditoría léxica para variantes emergentes.
3. Evaluación controlada de estrategias de calibración y estabilidad temporal del modelo.
4. Profundización de análisis de error por subtipo clínico y por contexto documental.
5. Estudio prospectivo de impacto operativo, manteniendo trazabilidad de decisiones.
