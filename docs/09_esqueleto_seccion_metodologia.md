# Esqueleto de la Sección de Metodología

## 1. Contexto del problema y objetivo operacional
Qué explicar:
- tarea de fenotipado psiquiátrico en EHR paraguayo;
- clases objetivo (`ansiedad`, `depresion`);
- carácter probabilístico de la salida y manejo de casos ambiguos en zona de solapamiento clínico;
- criterio de diseño explicable y reproducible.

## 2. Datos y preparación inicial
Qué explicar:
- naturaleza del corpus clínico;
- limpieza y EDA;
- límites de calidad textual y su implicancia.

## 3. Estrategia de partición
Qué explicar:
- justificación de `patient-level split`;
- riesgo de leakage en datos longitudinales;
- impacto en validez de evaluación.

## 4. Denoising clínico con reglas
Qué explicar:
- motivo de filtrar ruido administrativo;
- criterios de retención de señal clínica;
- relación entre denoising y robustez posterior.

## 5. Líneas base
Qué explicar:
- objetivo de dummy como piso mínimo;
- papel de TF-IDF como baseline de texto;
- papel de BETO/Transformers como referencia contextual;
- cómo estas líneas base informan el diseño híbrido.

## 6. Brecha léxica y adaptación regional
Qué explicar:
- insuficiencia de `Concept_CO`;
- depuración de `Concept_PY (Core)`;
- construcción de `Concept_PY_Lexicon`;
- rol del LLM en verificación semántica léxica.

## 7. Ingeniería de features híbridas
Qué explicar:
- definición de bloques (`feat_*`, `feat_niega_*`, `rule_medication_*`, `sent_*`, `embeddings` BETO);
- criterio de integración por bloque;
- preservación de trazabilidad clínica.

## 8. LLM y `late fusion`
Qué explicar:
- alcance restringido del LLM;
- fórmula de fusión por síntoma;
- razón para no expandir espacio LLM sin control;
- manejo específico de medicaciones.

## 9. Entrenamiento y selección de modelos
Qué explicar:
- comparación `RandomForest` / `XGBoost`;
- lógica de tuning opcional;
- artefactos de salida para auditoría y reproducibilidad.

## 10. Consolidación de resultados y análisis de errores
Qué explicar:
- tablas y figuras de comparación;
- ablation core vs py;
- análisis por tipo de error y revisión cualitativa.

## 11. Consideraciones de validez y límites
Qué explicar:
- límites de generalización;
- límites de etiquetado clínico;
- riesgos de interpretación y control metodológico.
