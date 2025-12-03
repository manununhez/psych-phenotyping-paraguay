# Análisis de Resultados

## 1. Resumen Ejecutivo
El estudio evaluó tres enfoques de clasificación (Baseline Trivial, Machine Learning Tradicional, Deep Learning) para la detección de Ansiedad y Depresión.

**Hallazgos Principales:**
1.  **TF-IDF + LinearSVC** fue el modelo con mejor desempeño global (**F1-Macro: 0.850**), superando significativamente a los baselines triviales y siendo estadísticamente equivalente a modelos más complejos como BETO.
2.  **BETO (Transformer)** mostró un rendimiento competitivo (**F1-Macro: 0.821**) pero no superior a TF-IDF, sugiriendo que la tarea es resoluble con características léxicas superficiales (n-grams).
3.  **Rule-Based** tuvo un desempeño deficiente (**F1-Macro: 0.511**), revelando una brecha crítica de vocabulario entre el español colombiano (origen del sistema) y el paraguayo, especialmente en la clase Ansiedad.

## 2. Rendimiento Comparativo (Validación Cruzada 5-Fold)

| Modelo | F1-Macro (Media ± DE) | IC95% | Mejora vs Baseline |
|--------|-----------------------|-------|-------------------|
| **TF-IDF char(3,5)** | **0.850 ± 0.031** | **[0.789, 0.910]** | **+73.2%** |
| BETO (Fine-tuned) | 0.821 ± 0.035 | [0.753, 0.890] | +67.4% |
| Rule-Based (Concept_PY) | 0.511 ± 0.053 | [0.407, 0.615] | +4.1% (n.s.) |
| Dummy Stratified | 0.491 ± 0.006 | [0.478, 0.503] | - |

*Nota: n.s. = no significativo (p > 0.05).*

### Análisis de Significancia
*   **TF-IDF y BETO** superan significativamente al baseline aleatorio (IC95% no solapados).
*   **TF-IDF vs BETO:** Sus intervalos de confianza se solapan, indicando que **no hay diferencia estadísticamente significativa** entre ellos. Se prefiere TF-IDF por su eficiencia y menor costo computacional.

## 3. Análisis por Clase

### 3.1 Depresión (Clase Mayoritaria)
Todos los modelos mostraron buen desempeño, con F1-scores > 0.80. Incluso el sistema Rule-Based funcionó bien aquí (F1: 0.806), indicando que el vocabulario de depresión es compartido entre Colombia y Paraguay.

### 3.2 Ansiedad (Clase Minoritaria)
Se observó una caída dramática en el sistema Rule-Based:
*   **TF-IDF:** F1 0.811
*   **Rule-Based:** F1 0.216

**Causa:** El análisis de errores reveló que el 75% de los términos clave de ansiedad usados en Paraguay (e.g., "preocupación constante", "no logra relajarse") no estaban presentes en el vocabulario colombiano original.

## 4. Estabilidad y Generalización
*   **Consistencia:** Los resultados en el conjunto de desarrollo (single-split) cayeron dentro de los intervalos de confianza de la validación cruzada para todos los modelos, validando la representatividad de la partición.
*   **Varianza:** TF-IDF mostró la menor varianza (CV: 3.6%), indicando robustez ante la heterogeneidad de los pacientes.

## 5. Conclusión Técnica
Para este dataset y tarea, los modelos basados en **n-gramas de caracteres (TF-IDF)** ofrecen la mejor relación costo-beneficio: capturan eficazmente las variaciones morfológicas y errores ortográficos comunes en notas clínicas sin la necesidad de recursos computacionales masivos requeridos por Transformers.
