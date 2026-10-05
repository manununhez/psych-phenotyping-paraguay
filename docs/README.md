# Documentación activa

Esta carpeta concentra la documentación pública y versionada del proyecto. La meta es que un tercero pueda entender el estado metodológico del repositorio sin depender de `data/outputs/` ni de cronologías internas.

## Núcleo canónico
1. `../README.md`: entrada general del repositorio.
2. `DECISIONES_METODOLOGICAS_CLAVE.md`: decisiones experimentales ya cerradas.
3. `GUIA_EJECUCION.md`: guía operativa del pipeline.
4. `METODOLOGIA.md`: resumen ejecutivo de la metodología vigente.
5. `METODOLOGIA_PIPELINE_COMPLETA.md`: descripción integral del pipeline, sus decisiones y la conexión entre notebooks y scripts.
6. `METODOLOGIA_HIBRIDO_ABLACION_Y_CIERRE.md`: detalle de la matriz híbrida y del cierre histórico reducido; no sustituye el cierre vigente del ensamble.
7. `ARTEFACTOS_Y_CONTRATOS.md`: contrato entre etapas, artefactos canónicos y fuentes de verdad del pipeline.
8. `SPANISH_PSYCH_PHENOTYPING_PY.md`: explicación del submódulo clínico, sus capas y su esquema fenotípico curado.
9. `UTILS_SHARED.md`: contrato y alcance de `notebooks/utils_shared.py`.
10. `LIMITACIONES.md`: límites actuales del experimento.
11. `ESTRATEGIA_VALIDACION.md`: alcance de la validación clínica externa.
12. `REVALIDACION_RESULTADOS_REFERENCIA.md`: cifras vigentes, procedencia de comparadores y diferencia entre reproducción congelada y nuevos entrenamientos.
13. `GLOSARIO.md`: definiciones estables del vocabulario metodológico y técnico del proyecto.

## Documentos de apoyo
- `BASELINE_CRUDO_VS_FILTRADO.md`: contraste metodológico auxiliar entre universo base y universo filtrado.
- El material interno, legacy o de trabajo personal queda fuera del frente público y se conserva localmente en `docs/legacy/` o como archivos locales no canónicos.
- Si existen documentos locales de presentación o checklist en `docs/`, deben leerse como insumos de trabajo y no como fuente de verdad metodológica por encima del núcleo canónico.

## Material excluido del frente público
- `docs/legacy/` queda ignorado por Git.
- Allí se preserva material interno, histórico o circunstancial que no aporta reproducibilidad directa al repositorio público.

## Notas de alcance
- El cierre final del ensamble en `test` está integrado en `notebooks/pipeline/10_cierre_final_test_ensamble.ipynb`. Su ejecución predict-only del 6 de junio es distinta de las comparaciones posteriores de TF-IDF y del híbrido.
- La fase final de xAI/explicabilidad queda pendiente para integración posterior y se interpreta como análisis pos-hoc, no como reajuste del modelo.
- `data/` y `reports/` no forman parte del repositorio público. Conservar los artefactos originales para reproducción exacta: no todos pueden recuperarse con código y seeds.
- La síntesis pública estable debe quedar reflejada solo en estos `.md`.
- Usar `latest` para operación corriente y manifiestos/rutas explícitas para reproducir una referencia congelada.
- La revisión clínica externa tiene materiales preparados; no se presenta como validación clínica completada.
- Todo el EDA global y por partición se genera en `01`, sin scripts externos de EDA; la fase completa necesita artefactos de `02`/`03` y el tokenizer local.

## Cierre vigente
- Modelo seleccionado en `dev`: ensamble weighted soft recongelado con `ROBERTA_CLINICAL max_length=512` + ramas simbólicas `RF`.
- Pesos vigentes: `0.65 / 0.15 / 0.20`.
- Carpeta local de cierre `dev`: `data/outputs/cierre_dev_recongelado_roberta_512_20260606_160946/`.
- Carpeta local de cierre `test`: `data/outputs/cierre_final_test_ensamble_512_20260606_1640/`.
- `max_length=512` es la configuración principal; `256` queda como sensibilidad no adoptada.
- El ensamble fue el mejor resultado en desarrollo; TF-IDF + LinearSVC obtuvo el mayor Macro-F1 puntual en prueba. La tabla completa y la procedencia se reúnen en [Revalidación](REVALIDACION_RESULTADOS_REFERENCIA.md).
