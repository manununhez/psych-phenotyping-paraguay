# Justificación de Reglas, Negación y Medicación

## Por qué sostener reglas en un sistema híbrido
Las reglas siguen siendo útiles por dos razones concretas:

- permiten trazabilidad clínica de la extracción;
- ofrecen un punto de control estable cuando el resto de componentes es más flexible.

En un estudio con foco aplicado, esa trazabilidad pesa tanto como la métrica final.

## Negación del paciente como señal
Frases de negación del paciente no se interpretan automáticamente como “ausencia clínica”. En psiquiatría, pueden codificar falta de insight, minimización o conflicto entre relato y observación. Por eso se preservan como features (`feat_niega_*`) y se modelan como información, no como descarte.

## Negación de plantilla/médico como ruido
En cambio, negaciones estructurales de plantilla o formulación clínica general suelen operar como contexto documental y no como fenotipo del caso. Mantenerlas sin filtro aumenta falsos positivos y deteriora especificidad. Por eso se filtran en denoising/reglas.

## Medicación como evidencia terapéutica separada
Las señales de medicación se conservan en `rule_medication_*` por diseño. Esa separación evita mezclar dos planos distintos:

- plano sintomático (base del objetivo diagnóstico);
- plano terapéutico (contexto clínico relevante, pero no equivalente al diagnóstico textual puntual).

## LLM y medicación
Aunque el LLM puede detectar menciones de fármacos, esas detecciones no se fusionan para inferencia diagnóstica directa. Se usan para auditoría, apoyo léxico y verificación semántica. Este límite metodológico reduce el riesgo de inferencias indirectas difíciles de justificar.
