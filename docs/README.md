# Documentación activa

Esta carpeta concentra la documentación pública y versionada del proyecto. La meta es que un tercero pueda entender el estado metodológico del repositorio sin depender de `data/outputs/` ni de cronologías internas.

## Núcleo canónico
1. `../README.md`: entrada general del repositorio.
2. `DECISIONES_METODOLOGICAS_CLAVE.md`: decisiones experimentales ya cerradas.
3. `GUIA_EJECUCION.md`: guía operativa del pipeline.
4. `METODOLOGIA.md`: resumen ejecutivo de la metodología vigente.
5. `METODOLOGIA_PIPELINE_COMPLETA.md`: descripción integral del pipeline, sus decisiones y la conexión entre notebooks y scripts.
6. `METODOLOGIA_HIBRIDO_ABLACION_Y_CIERRE.md`: detalle completo de la matriz híbrida, la comparación `RF/XGB`, la ablación, la parsimonia y el cierre formal en `dev`.
7. `ARTEFACTOS_Y_CONTRATOS.md`: contrato entre etapas, artefactos canónicos y fuentes de verdad del pipeline.
8. `SPANISH_PSYCH_PHENOTYPING_PY.md`: explicación del submódulo clínico, sus capas y su esquema fenotípico curado.
9. `UTILS_SHARED.md`: contrato y alcance de `notebooks/utils_shared.py`.
10. `LIMITACIONES.md`: límites actuales del experimento.
11. `ESTRATEGIA_VALIDACION.md`: alcance de la validación clínica externa.
12. `REVALIDACION_RESULTADOS_REFERENCIA.md`: resultados de referencia para reruns.

## Documentos de apoyo
- No hay documentación de apoyo pública adicional fuera de los archivos anteriores.
- El material interno, legacy o de trabajo personal queda fuera del frente público y se conserva localmente en `docs/legacy/`.

## Material excluido del frente público
- `docs/legacy/` queda ignorado por Git.
- Allí se preserva material interno, histórico o circunstancial que no aporta reproducibilidad directa al repositorio público.

## Notas de alcance
- La fase final de evaluación en `test` todavía no está integrada como notebook operativo en esta etapa.
- La fase final de xAI/explicabilidad también queda pendiente para integración manual posterior.
- Los artefactos de `data/outputs/` no forman parte del repositorio público; son salidas locales regenerables.
- La síntesis pública estable debe quedar reflejada solo en estos `.md`.
- Cuando existan artefactos locales relevantes, usar punteros `latest` antes que carpetas con timestamp fijo.
- La revisión clínica externa se documenta aquí como parte del método, no como bitácora operativa.
