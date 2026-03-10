# Decisiones Metodológicas Resumidas

## Resumen ejecutivo

| Decisión | Alternativa descartada | Motivo principal | Impacto esperado |
|---|---|---|---|
| Split por paciente | Split aleatorio por nota | Evitar leakage longitudinal | Evaluación más realista |
| Denoising temprano | Modelar texto crudo completo | Reducir ruido administrativo | Señal clínica más limpia |
| Mantener `Concept_CO` como baseline histórico | Eliminar baseline histórico | Conservar trazabilidad de origen | Comparación auditada |
| Construir `Concept_PY (Core)` | Solo agregar términos locales | Robustecer reglas antes de expandir | Menos falsos positivos estructurales |
| Añadir `Concept_PY_Lexicon` | Quedarse solo con Core | Cubrir variación regional | Mejor cobertura clínica local |
| Incluir TF-IDF | Omitir baseline clásico | Referencia lexical estándar y económica | Punto de comparación sólido |
| Usar BETO como baseline Transformer principal | Tratar todos los Transformers por igual | Mejor equilibrio práctico en el proyecto | Reutilización coherente en híbrido |
| LLM acotado a normalización semántica | LLM como clasificador directo | Controlar opacidad y deriva | Mayor reproducibilidad |
| `late fusion` por síntoma | Expansión amplia del espacio LLM | Mantener ontología y auditabilidad | Menor complejidad espuria |
| Medicación en `rule_medication_*` separado | Fusión diagnóstica de medicación por LLM | Evitar inferencia indirecta no controlada | Interpretación clínica más clara |
| Negación de paciente preservada | Eliminar toda negación | Puede ser señal clínicamente útil | Mejor caracterización fenotípica |
| Negación de plantilla/médico filtrada | Preservarla completa | Reduce ruido no fenomenológico | Mayor especificidad |
| Clasificación con RandomForest/XGBoost | Un único clasificador fijo | Comparación de robustez en espacio mixto | Selección más defendible |
