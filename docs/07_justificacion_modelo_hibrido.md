# Justificación del Modelo Híbrido

## Racional general
Ningún bloque, por sí solo, resolvía todo el problema:

- reglas: trazables, pero sensibles a cobertura lexical;
- LLM: fuerte en equivalencia semántica, pero menos determinista;
- embeddings BETO: contexto útil, pero no necesariamente suficiente como única fuente;
- sentimiento: señal complementaria, no diagnóstica en aislamiento.

El modelo híbrido surge como integración de fortalezas, no como acumulación indiscriminada.

## Función de cada componente
- Reglas (`rule_*`, `feat_*`, `feat_niega_*`): anclaje clínico interpretable.
- `late fusion` con LLM: recuperación semántica cuando la forma textual varía.
- `embeddings` BETO: contexto distribuido para patrones no explícitos en reglas.
- Features de sentimiento: modulación de tono afectivo que puede aportar separabilidad.
- `RandomForest` / `XGBoost`: clasificadores robustos para espacios heterogéneos y no lineales.

## Por qué no un único modelo end-to-end
Un enfoque único, más opaco, puede dificultar auditoría de errores clínicos y justificar menos claramente qué parte del sistema aporta cada señal. La arquitectura híbrida permite analizar contribuciones por bloque y sostener discusiones metodológicas más finas.

## Defendibilidad de la propuesta
La propuesta es defendible porque mantiene un equilibrio entre:

- explicabilidad clínica,
- flexibilidad semántica,
- reutilización coherente de resultados de líneas base,
- reproducibilidad experimental.
