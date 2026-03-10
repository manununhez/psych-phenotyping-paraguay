# Justificación de LLM y Late Fusion

## Rol acotado del LLM
El LLM se usa en dos frentes específicos:

1. normalización semántica de síntomas para apoyar `feat_*`;
2. auditoría léxica (coloquialismos, colombianismos, variantes paraguayas, equivalencias).

No se usa como clasificador final ni como motor principal de decisión clínica.

## Por qué elegir `late fusion`
La estrategia `feat_X = max(rule_X, llm_X)` se eligió para mantener control del espacio de features y de la ontología congelada. Frente a expandir masivamente el espacio con señales LLM crudas, `late fusion` ofrece tres ventajas:

- mantiene interpretabilidad por síntoma;
- reduce dimensionalidad redundante;
- facilita auditoría de discrepancias regla vs. LLM.

## Trade-off explícito
Se resigna parte de granularidad potencial del LLM para ganar estabilidad metodológica. En el contexto de tesis, ese trade-off es razonable: privilegia reproducibilidad y defensa técnica por encima de maximizar complejidad.

## Medicaciones detectadas por LLM
Las detecciones de medicación del LLM no se fusionan en el bloque diagnóstico. Se usan como apoyo de revisión y enriquecimiento léxico, manteniendo `rule_medication_*` como fuente terapéutica separada.

## Resultado metodológico
Esta decisión permite aprovechar utilidad semántica del LLM sin convertir el sistema en una caja negra difícil de validar clínicamente.
