# Fenotipado Psiquiátrico en Notas Clínicas (Paraguay)

Este repositorio contiene el código, datos y documentación para el proyecto de tesis sobre **Extracción Automática de Fenotipos Psiquiátricos en Notas Clínicas del Español Paraguayo**.

El proyecto implementa y compara modelos de Procesamiento de Lenguaje Natural (NLP) para clasificar notas clínicas en dos categorías diagnósticas: **Ansiedad** y **Depresión**.

## 🚀 Resumen de Resultados

El mejor modelo (**TF-IDF + LinearSVC**) alcanzó un **F1-Macro de 0.850**, demostrando que es posible detectar patologías psiquiátricas con alta precisión utilizando características léxicas, incluso en un corpus de tamaño limitado.

| Modelo | F1-Macro | Descripción |
|--------|----------|-------------|
| **TF-IDF + LinearSVC** | **0.850** | **Recomendado.** Eficiente, interpretable y robusto. |
| BETO (Transformer) | 0.821 | Competitivo, pero mayor costo computacional. |
| Rule-Based | 0.511 | Limitado por brecha de vocabulario dialectal. |

## 📂 Estructura del Repositorio

```
.
├── data/                   # Datos (splits, figuras, resultados)
├── docs/                   # Documentación del proyecto
│   ├── METHODOLOGY.md      # Detalles del dataset y modelos
│   ├── RESULTS_ANALYSIS.md # Análisis detallado de rendimiento
│   ├── VALIDATION_STRATEGY.md # Protocolo de validación clínica
│   └── LIMITATIONS.md      # Limitaciones y trabajo futuro
├── notebooks/              # Notebooks de análisis (Jupyter)
│   ├── 00_setup.ipynb      # Configuración inicial
│   ├── 01_eda.ipynb        # Análisis Exploratorio de Datos
│   ├── 02_create_splits.ipynb # Partición Train/Dev/Test
│   ├── 03_rule_based_denoising.ipynb # Limpieza y Denoising
│   ├── 03_preparacion_validacion_psiquiatras.ipynb # Validación Clínica
│   ├── 04_baseline_dummy.ipynb # Baselines Triviales
│   ├── 04_baseline_tfidf.ipynb # Modelo TF-IDF
│   ├── 04_baseline_transformers.ipynb # Modelos BETO/RoBERTa
│   └── 05_comparacion_resultados.ipynb # Comparativa Final
└── Spanish_Psych_Phenotyping_PY/ # Fork del sistema base (reglas)
```

## 🛠️ Instalación y Uso

1.  **Clonar el repositorio:**
    ```bash
    git clone <url-repo>
    cd psych-phenotyping-paraguay
    ```

2.  **Configurar entorno:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Ejecutar pipeline:**
    Siga el orden numérico de los notebooks en `notebooks/`. Consulte `docs/EXECUTION_GUIDE.md` para más detalles.

## 📄 Documentación Clave

*   **[Metodología](docs/METHODOLOGY.md):** Descripción del corpus, preprocesamiento y modelos.
*   **[Análisis de Resultados](docs/RESULTS_ANALYSIS.md):** Comparación estadística y análisis de errores.
*   **[Estrategia de Validación](docs/VALIDATION_STRATEGY.md):** Protocolo para validación con expertos clínicos.
*   **[Limitaciones](docs/LIMITATIONS.md):** Restricciones del estudio y sesgos identificados.

## 👥 Créditos

Proyecto desarrollado como parte de tesis de grado. Basado en el trabajo *Spanish Psych Phenotyping* (Colombia).
Datos provistos por el Instituto de Previsión Social (IPS), Paraguay.
