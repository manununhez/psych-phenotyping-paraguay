#!/usr/bin/env python3
"""
Consolida la fase de revisión clínica externa con un paquete final reusable.

No reentrena el pipeline principal, no abre `test` y no modifica la selección
formal del modelo. Construye una capa final de auditoría del dataset,
justificación metodológica, contraste con baseline crudo y material para
revisión clínica externa y futura etapa de xAI.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import shutil
import sys
import textwrap
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils_shared import keep_entity

DATA_DIR = ROOT / "data"
OUTPUTS_DIR = DATA_DIR / "outputs"
DOCS_DIR = ROOT / "docs"

SPANISH_STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "se", "del", "las", "un", "por", "con", "no", "una",
    "su", "para", "es", "al", "lo", "como", "mas", "pero", "sus", "le", "ya", "o", "fue", "este", "ha",
    "si", "sin", "sobre", "tambien", "hasta", "son", "mi", "tu", "mc", "dx", "imp", "plan", "sic",
    "paciente", "refiere", "acude", "control", "encuentra", "bien", "estable", "hace", "años", "año",
    "pcte", "esta", "está", "tiene", "desde", "siente", "sentirse", "general", "buena", "mejor", "buen",
    "algunos", "mismo", "misma", "tratante", "consulta", "tratamiento", "medicacion", "medicación",
}

ADMIN_PATTERNS = [
    ("reposicion_retiro_medicacion", re.compile(r"\b(?:reposicion|reposición|retira|retirar|retira medicamentos|acude a retirar medicacion|retira medicación)\b", re.I)),
    ("misma_indicacion_control", re.compile(r"\b(?:misma medicacion|misma medicación|misma indicacion|misma indicación|control con tratante|segun indicaciones de tratante)\b", re.I)),
    ("estudios_auxiliares", re.compile(r"\b(?:laboratorio|lab de rutina|eeg|encefalo|encéfalo|rmn|estudios|audiometria|timpanometria|logoaudiometria|consulta con orl)\b", re.I)),
    ("plantilla_administrativa", re.compile(r"\b(?:examen fisico|examen físico|diagnostico presuntivo|tratamiento clinico|carimbo|assinatura)\b", re.I)),
]


def now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_latest_source_dir(pattern: str, manifest_name: str, exclude_prueba: bool = False) -> Path:
    candidates = []
    for p in OUTPUTS_DIR.glob(pattern):
        if not p.is_dir():
            continue
        if exclude_prueba and "prueba" in p.name.lower():
            continue
        if (p / manifest_name).exists():
            candidates.append(p)
    if not candidates:
        raise FileNotFoundError(f"No se encontró un directorio `{pattern}` con `{manifest_name}`.")
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def resolve_latest_dossier_dir() -> Path:
    latest_ptr = OUTPUTS_DIR / "dossier_ips_curado_latest.json"
    if latest_ptr.exists():
        payload = read_json(latest_ptr)
        out = Path(payload["output_dir"])
        if out.exists():
            return out
    return resolve_latest_source_dir("dossier_ips_curado_*", "dossier_ips_curado_manifest.json")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def token_count(text: str) -> int:
    return len(re.findall(r"[a-záéíóúñ0-9]+", str(text).lower()))


def top_words(texts: list[str], top_k: int = 40) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for text in texts:
        tokens = re.findall(r"[a-záéíóúñ0-9]+", str(text).lower())
        for token in tokens:
            if len(token) <= 2:
                continue
            if token in SPANISH_STOPWORDS:
                continue
            if token.isdigit():
                continue
            counter[token] += 1
    return counter.most_common(top_k)


def render_useful_signal_md() -> str:
    keep_entity_doc = inspect.getdoc(keep_entity) or ""
    keep_entity_excerpt = textwrap.shorten(
        " ".join(keep_entity_doc.split()),
        width=320,
        placeholder="...",
    )
    return (
        "# Qué se considera señal clínica útil\n\n"
        "## Fuente operativa\n"
        "- Pipeline clínico construido con el fork `Spanish_Psych_Phenotyping_PY`, montado sobre `spaCy` y componentes de `medSpaCy`.\n"
        "- Las entidades candidatas provienen del matcher de reglas clínicas del pipeline (`TargetMatcher` dentro del fork).\n"
        "- Los atributos de contexto (`is_historical`, `is_hypothetical`, `is_family`, `is_negated`) provienen de la capa de contexto clínico de `medSpaCy`.\n"
        "- Definición centralizada en `utils_shared.keep_entity`.\n"
        f"- Resumen del docstring vigente: {keep_entity_excerpt}\n\n"
        "## Regla práctica usada por el pipeline\n"
        "Una mención se considera **señal clínica útil** si pasa el filtro de aseveración clínica de `keep_entity`.\n\n"
        "### Se conserva como señal útil cuando\n"
        "- la mención no está en contexto histórico, hipotético ni familiar;\n"
        "- la mención no está negada;\n"
        "- o está negada, pero la negación es atribuible al paciente.\n\n"
        "### No se conserva como señal útil cuando\n"
        "- la mención pertenece a antecedentes, hipótesis clínicas o historia familiar;\n"
        "- la negación proviene del médico, de una plantilla o de una fórmula administrativa tipo `sin síntomas`.\n\n"
        "## Traducción metodológica\n"
        "- `has_clinical_signal = 1` significa que la nota contiene al menos una entidad que pasa ese filtro.\n"
        "- `has_clinical_signal = 0` significa que, aun si el texto contiene palabras clínicas, no quedó evidencia válida bajo esa política.\n"
        "- La negación del paciente se conserva porque puede aportar fenomenología relevante, por ejemplo estado subjetivo, defensas o insight.\n"
        "- La negación de plantilla o del médico se descarta porque suele diluir la señal diagnóstica útil.\n\n"
        "## Alcance\n"
        "- Esto es una decisión de limpieza y normalización del EHR, no una decisión diagnóstica final.\n"
        "- Su objetivo es evitar que el modelo aprenda ruido documental como si fuera evidencia clínica.\n"
    )


def dataset_state_tables(raw_df: pd.DataFrame, clean_df: pd.DataFrame, flag_df: pd.DataFrame, deno_df: pd.DataFrame,
                         train_df: pd.DataFrame, dev_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    raw_n = len(raw_df)
    raw_patients = raw_df["Prontuario"].nunique()
    clean_n = len(clean_df)
    clean_patients = clean_df["patient_id"].nunique()
    duplicates_removed = raw_n - clean_n
    template_blocks = int(clean_df["feat_had_template_block"].sum())
    no_signal_removed = int((~flag_df["has_clinical_signal"]).sum())
    final_n = len(deno_df)
    final_patients = deno_df["patient_id"].nunique()

    rows.extend([
        {"bloque": "conteos", "metrica": "registros_originales", "valor": raw_n, "detalle": "ips_raw.csv"},
        {"bloque": "conteos", "metrica": "pacientes_originales", "valor": raw_patients, "detalle": "ips_raw.csv"},
        {"bloque": "conteos", "metrica": "registros_post_deduplicacion", "valor": clean_n, "detalle": "dataset_base / ips_clean"},
        {"bloque": "conteos", "metrica": "pacientes_post_deduplicacion", "valor": clean_patients, "detalle": "dataset_base / ips_clean"},
        {"bloque": "eliminacion", "metrica": "duplicados_eliminados", "valor": duplicates_removed, "detalle": "raw -> clean"},
        {"bloque": "eliminacion", "metrica": "plantillas_administrativas_eliminadas_directamente", "valor": 0, "detalle": "se detectan y limpian intra-nota, no por eliminación aislada"},
        {"bloque": "eliminacion", "metrica": "notas_con_bloque_plantilla_detectado", "valor": template_blocks, "detalle": "feat_had_template_block = 1"},
        {"bloque": "eliminacion", "metrica": "notas_sin_senal_clinica_util_eliminadas", "valor": no_signal_removed, "detalle": "has_clinical_signal = 0"},
        {"bloque": "conteos", "metrica": "registros_finales_modelados", "valor": final_n, "detalle": "dataset_denoised.csv"},
        {"bloque": "conteos", "metrica": "pacientes_finales_modelados", "valor": final_patients, "detalle": "dataset_denoised.csv"},
    ])

    for split_name, df in [("global_pre_denoising", clean_df), ("global_final", deno_df), ("train", train_df), ("dev", dev_df), ("test", test_df)]:
        dist = df["etiqueta"].value_counts().to_dict()
        rows.append({"bloque": "distribucion", "metrica": f"{split_name}_n_total", "valor": len(df), "detalle": ""})
        rows.append({"bloque": "distribucion", "metrica": f"{split_name}_n_pacientes", "valor": df["patient_id"].nunique(), "detalle": ""})
        rows.append({"bloque": "distribucion", "metrica": f"{split_name}_ansiedad", "valor": int(dist.get("ansiedad", 0)), "detalle": ""})
        rows.append({"bloque": "distribucion", "metrica": f"{split_name}_depresion", "valor": int(dist.get("depresion", 0)), "detalle": ""})

        lengths_chars = df["texto"].astype(str).str.len()
        lengths_tokens = df["texto"].astype(str).apply(token_count)
        rows.append({"bloque": "longitud", "metrica": f"{split_name}_longitud_media_chars", "valor": round(lengths_chars.mean(), 2), "detalle": ""})
        rows.append({"bloque": "longitud", "metrica": f"{split_name}_longitud_mediana_chars", "valor": float(lengths_chars.median()), "detalle": ""})
        rows.append({"bloque": "longitud", "metrica": f"{split_name}_longitud_media_tokens", "valor": round(lengths_tokens.mean(), 2), "detalle": ""})
        rows.append({"bloque": "longitud", "metrica": f"{split_name}_longitud_mediana_tokens", "valor": float(lengths_tokens.median()), "detalle": ""})

    out_df = pd.DataFrame(rows)

    md = [
        "# Estado actual del dataset",
        "",
        "## Resumen de conteos",
        f"- Registros originales: {raw_n}",
        f"- Pacientes originales: {raw_patients}",
        f"- Duplicados eliminados: {duplicates_removed}",
        "- Eliminación directa por plantilla administrativa: 0",
        f"- Registros con bloque de plantilla detectado: {template_blocks}",
        f"- Notas eliminadas por ausencia de señal clínica útil: {no_signal_removed}",
        f"- Registros finales modelados: {final_n}",
        f"- Pacientes finales modelados: {final_patients}",
        "",
        "## Distribución por clase",
        f"- Antes del denoising clínico fuerte (`dataset_base`): ansiedad={clean_df['etiqueta'].value_counts().get('ansiedad', 0)}, depresion={clean_df['etiqueta'].value_counts().get('depresion', 0)}",
        f"- Después del denoising (`dataset_denoised`): ansiedad={deno_df['etiqueta'].value_counts().get('ansiedad', 0)}, depresion={deno_df['etiqueta'].value_counts().get('depresion', 0)}",
        "",
        "## Splits",
        f"- Train: {len(train_df)} registros, {train_df['patient_id'].nunique()} pacientes",
        f"- Dev: {len(dev_df)} registros, {dev_df['patient_id'].nunique()} pacientes",
        f"- Test: {len(test_df)} registros, {test_df['patient_id'].nunique()} pacientes",
        "",
        "## Longitud de notas",
        f"- Longitud media final: {round(deno_df['texto'].astype(str).str.len().mean(), 2)} caracteres",
        f"- Longitud mediana final: {float(deno_df['texto'].astype(str).str.len().median())} caracteres",
        f"- Longitud media final: {round(deno_df['texto'].astype(str).apply(token_count).mean(), 2)} tokens",
        f"- Longitud mediana final: {float(deno_df['texto'].astype(str).apply(token_count).median())} tokens",
        "",
        "## Nota metodológica",
        "- Las plantillas administrativas se detectaron y limpiaron dentro del texto, pero no se eliminaron automáticamente por ese solo criterio.",
        "- El filtro que verdaderamente reduce el universo modelado es la ausencia de señal clínica útil (`has_clinical_signal = 0`).",
        "",
        "## Qué entendemos aquí por señal clínica útil",
        "- La definición operativa viene de `utils_shared.keep_entity`.",
        "- Se conserva una mención si no está en contexto histórico, hipotético o familiar.",
        "- Si la mención está negada, solo se conserva cuando la negación proviene del paciente.",
        "- Las negaciones de plantilla o del médico se descartan como ruido documental.",
        "- Por eso una nota puede contener vocabulario clínico y aun así quedar fuera si no aporta evidencia clínica válida bajo esa política.",
    ]
    return out_df, "\n".join(md) + "\n"


def categorize_removed_noise(flag_df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, list[str]]]]:
    removed = flag_df[~flag_df["has_clinical_signal"]].copy()
    removed["texto_clean"] = removed["texto"].astype(str).apply(clean_text)
    rows = []
    examples: list[tuple[str, list[str]]] = []
    assigned = pd.Series(False, index=removed.index)
    for label, pattern in ADMIN_PATTERNS:
        mask = removed["texto_clean"].str.contains(pattern)
        subset = removed[mask]
        rows.append({"categoria": label, "n_registros": int(len(subset))})
        sample = subset["texto_clean"].drop_duplicates().head(3).tolist()
        if sample:
            examples.append((label, sample))
        assigned = assigned | mask
    other = removed[~assigned]
    rows.append({"categoria": "otros_seguimientos_breves", "n_registros": int(len(other))})
    if not other.empty:
        examples.append(("otros_seguimientos_breves", other["texto_clean"].drop_duplicates().head(3).tolist()))
    return pd.DataFrame(rows).sort_values("n_registros", ascending=False), examples


def duplicate_examples(raw_df: pd.DataFrame, top_k: int = 3) -> list[tuple[str, int]]:
    texts = raw_df["Motivo Consulta"].fillna("").astype(str).apply(clean_text)
    texts = texts[texts.astype(str).str.strip().ne("")]
    counts = texts.value_counts()
    duplicates = counts[counts > 1]
    return [(textwrap.shorten(text, width=160, placeholder="..."), int(count)) for text, count in duplicates.head(top_k).items()]


def render_noise_examples_md(noise_counts: pd.DataFrame, examples: list[tuple[str, list[str]]], duplicate_samples: list[tuple[str, int]]) -> str:
    lines = [
        "# Ejemplos de ruido administrativo y notas poco diagnósticas",
        "",
        "## Categorías frecuentes entre notas removidas por falta de señal clínica útil",
        noise_counts.to_markdown(index=False),
        "",
        "## Ejemplos por categoría",
    ]
    for label, sample_list in examples:
        lines.append(f"### {label}")
        for sample in sample_list:
            lines.append(f"- `{textwrap.shorten(sample, width=220, placeholder='...')}`")
        lines.append("")

    lines.append("## Ejemplos de duplicación o repetición textual en el origen")
    for sample, count in duplicate_samples:
        lines.append(f"- Repetido {count} veces: `{sample}`")

    lines.extend([
        "",
        "## Interpretación",
        "- Estos ejemplos no prueban por sí solos que toda nota breve sea inútil, pero sí muestran por qué el universo crudo mezcla seguimiento, reposición, trámite y fenomenología clínica.",
        "- El objetivo del filtrado no fue mejorar números de forma artificial, sino acotar el problema a consultas con mínima carga diagnóstica útil.",
    ])
    return "\n".join(lines) + "\n"


def build_top_words_tables(base_df: pd.DataFrame, deno_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    specs = [
        ("antes_filtrado", base_df),
        ("despues_filtrado", deno_df),
        ("ansiedad_final", deno_df[deno_df["etiqueta"] == "ansiedad"]),
        ("depresion_final", deno_df[deno_df["etiqueta"] == "depresion"]),
    ]
    rows = []
    for corpus, df in specs:
        for term, count in top_words(df["texto"].astype(str).tolist(), top_k=40):
            rows.append({"corpus": corpus, "palabra": term, "conteo": count})
    out_df = pd.DataFrame(rows)
    md = [
        "# Palabras más frecuentes del dataset",
        "",
        "## Lectura rápida",
        "- `antes_filtrado` muestra con claridad el peso de seguimiento, reposición y lenguaje administrativo.",
        "- `despues_filtrado` sigue siendo descriptivo, pero ya refleja mejor la fenomenología clínica del universo modelado.",
        "- Las visualizaciones deben usarse como apoyo descriptivo, no como evidencia clínica fuerte por sí sola.",
        "",
        "## Top palabras por corpus",
    ]
    for corpus, group in out_df.groupby("corpus"):
        joined = ", ".join(f"{row.palabra} ({row.conteo})" for row in group.head(15).itertuples())
        md.append(f"- `{corpus}`: {joined}")
    return out_df, "\n".join(md) + "\n"


def generate_wordclouds(output_dir: Path, deno_df: pd.DataFrame) -> list[str]:
    os.environ.setdefault("MPLCONFIGDIR", str(OUTPUTS_DIR / ".mplconfig"))
    os.environ.setdefault("XDG_CACHE_HOME", str(OUTPUTS_DIR / ".cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from wordcloud import WordCloud

    generated = []

    def build_wc(texts: list[str], filename: str) -> None:
        joined = " ".join(texts)
        wc = WordCloud(
            width=1600,
            height=900,
            background_color="white",
            stopwords=SPANISH_STOPWORDS,
            collocations=False,
        ).generate(joined if joined.strip() else "sin datos")
        fig = plt.figure(figsize=(16, 9))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off")
        path = output_dir / filename
        fig.savefig(path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        generated.append(filename)

    build_wc(deno_df["texto"].astype(str).tolist(), "wordcloud_global.png")
    for label in ["ansiedad", "depresion"]:
        subset = deno_df[deno_df["etiqueta"] == label]
        build_wc(subset["texto"].astype(str).tolist(), f"wordcloud_{label}.png")
    return generated


def classify_balance(dist: dict[str, int]) -> str:
    total = sum(dist.values())
    major = max(dist.values()) / total
    if major < 0.60:
        return "balanceado"
    if major < 0.67:
        return "moderadamente_desbalanceado"
    return "claramente_desbalanceado"


def build_imbalance_table(base_df: pd.DataFrame, deno_df: pd.DataFrame, train_df: pd.DataFrame, dev_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    universe_rows = []
    for name, df in [("base_pre_denoising", base_df), ("final_denoised", deno_df), ("train", train_df), ("dev", dev_df), ("test", test_df)]:
        dist = df["etiqueta"].value_counts().to_dict()
        total = len(df)
        universe_rows.append({
            "tipo_fila": "universo",
            "modelo": name,
            "n_total": total,
            "n_ansiedad": int(dist.get("ansiedad", 0)),
            "n_depresion": int(dist.get("depresion", 0)),
            "prop_ansiedad": round(dist.get("ansiedad", 0) / total, 4),
            "prop_depresion": round(dist.get("depresion", 0) / total, 4),
            "balance": classify_balance(dist),
            "class_weight": "",
            "sampling": "",
            "metricas_priorizadas": "",
            "comentario": "",
        })

    model_rows = [
        {
            "tipo_fila": "modelo", "modelo": "Dummy", "n_total": "", "n_ansiedad": "", "n_depresion": "",
            "prop_ansiedad": "", "prop_depresion": "", "balance": "",
            "class_weight": "no", "sampling": "no", "metricas_priorizadas": "macro_f1, balanced_accuracy, F1 por clase",
            "comentario": "Sirve como piso metodológico."
        },
        {
            "tipo_fila": "modelo", "modelo": "TF-IDF", "class_weight": "si (`LinearSVC`, balanced)", "sampling": "no",
            "metricas_priorizadas": "macro_f1, balanced_accuracy, F1 por clase",
            "comentario": "La línea base textual fuerte se ajusta al desbalance por ponderación de clase, no por resampling."
        },
        {
            "tipo_fila": "modelo", "modelo": "Transformers standalone", "class_weight": "no explícito", "sampling": "no explícito",
            "metricas_priorizadas": "macro_f1, balanced_accuracy, F1 por clase",
            "comentario": "No se documentó resampling explícito en la versión vigente."
        },
        {
            "tipo_fila": "modelo", "modelo": "RandomForest", "class_weight": "si (`balanced`)", "sampling": "no",
            "metricas_priorizadas": "macro_f1, balanced_accuracy, F1 por clase",
            "comentario": "Se compensa el desbalance por ponderación interna."
        },
        {
            "tipo_fila": "modelo", "modelo": "XGBoost", "class_weight": "no explícito", "sampling": "no",
            "metricas_priorizadas": "macro_f1, balanced_accuracy, F1 por clase",
            "comentario": "El híbrido final usa este esquema; por eso el análisis por clase es obligatorio."
        },
    ]

    out_df = pd.DataFrame(universe_rows + model_rows).fillna("")
    md = [
        "# Manejo del desbalance en dataset y modelos",
        "",
        f"- El dataset final quedó **{classify_balance(deno_df['etiqueta'].value_counts().to_dict())}**.",
        "- La clase `depresion` sigue siendo mayoritaria en todos los splits.",
        "- Por eso se privilegiaron `macro_f1`, `balanced_accuracy` y F1 por clase, en vez de precisión global simple.",
        "",
        "## Universos",
        out_df[out_df["tipo_fila"] == "universo"].to_markdown(index=False),
        "",
        "## Decisiones por modelo",
        out_df[out_df["tipo_fila"] == "modelo"].to_markdown(index=False),
        "",
        "## Lectura metodológica",
        "- El desbalance no invalida la tarea, pero obliga a leer cualquier mejora con cuidado por clase.",
        "- El híbrido final, por ejemplo, acumula más aciertos totales en `depresion`, pero eso no basta para declararlo superior.",
    ]
    return out_df, "\n".join(md) + "\n"


def controlled_tfidf_metrics(train_df: pd.DataFrame, eval_df: pd.DataFrame) -> dict[str, Any]:
    vec = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=2,
        max_features=50000,
        sublinear_tf=True,
    )
    Xtr = vec.fit_transform(train_df["texto"].astype(str))
    clf = LinearSVC(class_weight="balanced", random_state=42)
    clf.fit(Xtr, train_df["etiqueta"])
    pred = clf.predict(vec.transform(eval_df["texto"].astype(str)))
    y = eval_df["etiqueta"]
    return {
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "f1_ansiedad": float(f1_score(y == "ansiedad", pred == "ansiedad")),
        "f1_depresion": float(f1_score(y == "depresion", pred == "depresion")),
        "n_eval": int(len(eval_df)),
        "n_train": int(len(train_df)),
    }


def build_baseline_raw_vs_filtered(base_df: pd.DataFrame, train_idx: pd.Series, dev_idx: pd.Series,
                                   train_deno_df: pd.DataFrame, dev_deno_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    train_base = base_df[base_df["row_id"].isin(set(train_idx))].copy()
    dev_base = base_df[base_df["row_id"].isin(set(dev_idx))].copy()

    rows = []
    for train_name, train_df in [("train_base", train_base), ("train_denoised", train_deno_df)]:
        for eval_name, eval_df in [("dev_base", dev_base), ("dev_denoised", dev_deno_df)]:
            m = controlled_tfidf_metrics(train_df, eval_df)
            rows.append({
                "configuracion": f"{train_name}→{eval_name}",
                "train_universo": train_name,
                "eval_universo": eval_name,
                **m,
            })
    out_df = pd.DataFrame(rows).sort_values(["train_universo", "eval_universo"]).reset_index(drop=True)
    md = [
        "# Baseline crudo vs filtrado",
        "",
        "## Objetivo",
        "Este contraste no reemplaza la línea base oficial del experimento. Su función es mostrar qué pasa cuando se entrena y evalúa una configuración textual simple sobre universos con distinto nivel de ruido.",
        "",
        "## Tabla comparativa",
        out_df.to_markdown(index=False),
        "",
        "## Lectura metodológica",
        "- `train_base→dev_base` muestra el costo de trabajar sobre un universo todavía lleno de seguimiento, reposición y ruido administrativo.",
        "- `train_base→dev_denoised` sirve como control de qué pasa cuando el modelo ve más volumen de texto pero se lo evalúa en un universo clínicamente más coherente.",
        "- `train_denoised→dev_denoised` es el contraste filtrado equivalente con la misma configuración simple.",
        "- Si el crudo no se desploma sobre `dev_denoised`, eso no invalida el denoising: lo que muestra es que el problema principal no es solo rendimiento, sino coherencia metodológica del universo evaluado.",
        "",
        "## Conclusión práctica",
        "- El filtrado sigue siendo necesario para que la tarea diferencial tenga sentido clínico.",
        "- El contraste crudo ayuda a mostrar que limpiar el dataset no fue una operación cosmética, sino una forma de separar notas diagnósticas de notas de trámite o seguimiento.",
    ]
    return out_df, "\n".join(md) + "\n"


def render_dataset_problems_md() -> str:
    return (
        "# Problemas del dataset y decisiones tomadas\n\n"
        "## Problemas principales\n"
        "- desbalance entre `ansiedad` y `depresion`;\n"
        "- sospecha de que parte de la etiqueta responde a trayectoria del paciente y no solo a la consulta puntual;\n"
        "- presencia de notas administrativas, reposiciones y seguimientos con baja carga fenomenológica;\n"
        "- duplicados o repeticiones textuales en el origen;\n"
        "- consultas donde sueño, medicación o clínica médica se superponen con la lectura psiquiátrica;\n"
        "- ausencia de grupo de control explícito en la versión actual.\n\n"
        "## Cómo se mitigaron\n"
        "- deduplicación inicial del corpus;\n"
        "- detección y limpieza de bloques de plantilla administrativa dentro del texto;\n"
        "- eliminación de notas sin señal clínica útil (`has_clinical_signal = 0`), definida según `utils_shared.keep_entity`;\n"
        "- conservación de negación atribuida al paciente y descarte de negación de plantilla/médico;\n"
        "- `patient-level split` para evitar leakage entre desarrollo y evaluación;\n"
        "- uso de `macro_f1`, `balanced_accuracy` y F1 por clase;\n"
        "- comparación entre baselines e híbrido en `dev` sobre el mismo universo final comparable;\n"
        "- análisis de errores alineado al modelo final congelado;\n"
        "- validación clínica pendiente con IPS antes de `test`.\n\n"
        "## Qué no se resolvió todavía\n"
        "- la duda sobre etiqueta a nivel paciente vs consulta;\n"
        "- la necesidad eventual de un grupo de control para otra formulación del problema;\n"
        "- la validación experta final del freeze léxico y de los patrones clínicos.\n"
    )


def render_glossary_md() -> str:
    entries = [
        ("TF-IDF", "Forma simple de representar texto según qué palabras aparecen y cuán específicas son dentro del corpus."),
        ("transformer", "Modelo neuronal que representa el texto usando contexto, no solo presencia de palabras aisladas."),
        ("mejor transformer standalone", "Transformer baseline que resultó más fuerte sobre `dev` en la comparación vigente."),
        ("backbone contextual del híbrido", "Modelo contextual en español usado como componente denso del híbrido vigente."),
        ("backbone contextual", "Componente que aporta representación textual densa al modelo híbrido."),
        ("híbrido", "Modelo que combina reglas clínicas, backbone contextual y otras familias de features en un clasificador tabular."),
        ("baseline", "Modelo de referencia usado para comparar si una propuesta realmente aporta algo."),
        ("macro_f1", "Promedio del F1 por clase; obliga a mirar el rendimiento de ambas clases, no solo la mayoritaria."),
        ("balanced_accuracy", "Promedio de recall por clase; útil cuando hay desbalance."),
        ("precisión", "De los casos que el modelo predijo como una clase, cuántos eran correctos."),
        ("recall", "De los casos reales de una clase, cuántos logró recuperar el modelo."),
        ("F1", "Media armónica entre precisión y recall."),
        ("desbalance de clases", "Situación donde una clase tiene muchos más ejemplos que la otra."),
        ("split por paciente", "Separación train/dev/test evitando que notas del mismo paciente caigan en universos distintos."),
        ("leakage", "Contaminación entre train y evaluación que hace parecer mejor al modelo de lo que realmente es."),
        ("denoising", "Proceso de limpiar ruido para quedarse con notas más útiles para la tarea."),
        ("señal clínica útil", "Mención que pasa el filtro `keep_entity` de `utils_shared`: no es histórica/hipotética/familiar y, si está negada, la negación debe venir del paciente."),
        ("ablación", "Prueba donde se apaga un componente para ver cuánto aporta."),
        ("explicabilidad / xAI", "Técnicas para entender qué señales está usando el modelo y cómo decide en casos concretos."),
        ("label noise", "Ruido de etiqueta: la etiqueta disponible no representa con precisión lo que el texto muestra."),
        ("grupo de control", "Conjunto de casos sin el fenómeno principal o fuera de la población objetivo, útil para otras formulaciones del problema."),
        ("freeze léxico", "Congelamiento formal de reglas y léxico antes de evaluación final."),
        ("freeze del modelo", "Decisión formal de qué configuración exacta pasa a evaluación final sin seguir ajustándose."),
    ]
    lines = ["# Glosario breve del proyecto", ""]
    for term, definition in entries:
        lines.append(f"## {term}")
        lines.append(definition)
        lines.append("")
    return "\n".join(lines)


def render_puntos_clave_metodologicos_md() -> str:
    return (
        "# Puntos clave para revisión metodológica\n\n"
        "## Qué conviene explicar con claridad\n"
        "- por qué la tarea actual es `ansiedad` vs `depresion` y no incluye `comorbilidad` ni grupo de control;\n"
        "- por qué fue necesario el denoising del dataset;\n"
        "- cómo se evitó leakage con `patient-level split`;\n"
        "- por qué se eligieron `macro_f1`, `balanced_accuracy` y F1 por clase;\n"
        "- por qué el mejor transformer standalone y el backbone contextual del híbrido cumplen roles metodológicos distintos;\n"
        "- por qué el híbrido no debe venderse como ganador absoluto si no lo es.\n\n"
        "## Errores de concepto a evitar\n"
        "- confundir mejor transformer standalone con mejor backbone del híbrido;\n"
        "- presentar notas administrativas como si fueran evidencia clínica fuerte;\n"
        "- usar cantidad total de aciertos como si fuera suficiente en un problema desbalanceado;\n"
        "- insinuar que `test` ya fue usado o que la validación clínica ya quedó cerrada.\n\n"
        "## Respuestas breves sugeridas\n"
        "- **¿Por qué limpiaron tanto el dataset?** Porque el universo original mezclaba consultas diagnósticas con reposición, seguimiento y trámites; sin esa limpieza la tarea deja de ser clínicamente interpretable.\n"
        "- **¿Por qué no usar solo el mejor transformer?** Porque el proyecto no busca solo una métrica más alta; también necesita trazabilidad clínica y control explícito de señales.\n"
        "- **¿Por qué el híbrido si no gana siempre?** Porque aporta auditabilidad clínica y permite discutir señales y errores con especialistas de forma más defendible.\n"
        "- **¿Qué sigue pendiente?** Freeze oficial con IPS, evaluación final en `test` y etapa de xAI.\n"
    )


def render_summary_md(output_dir_name: str) -> str:
    return (
        "# Resumen de cierre de fase IPS\n\n"
        "## Qué quedó listo en esta fase\n"
        "- auditoría estadística del dataset con conteos exactos y motivos de eliminación;\n"
        "- definición explícita de qué se considera señal clínica útil en el pipeline;\n"
        "- ejemplos concretos de ruido administrativo y seguimiento poco diagnóstico;\n"
        "- contraste controlado entre baseline crudo y filtrado;\n"
        "- dossier clínico actualizado para mostrar patrones, errores y preguntas a IPS;\n"
        "- glosario y puntos clave para lectura metodológica.\n\n"
        "## Qué quedó listo para documentación técnica\n"
        "- justificación metodológica del tratamiento del dataset;\n"
        "- explicación del desbalance y de las métricas elegidas;\n"
        "- lectura más clara de lo que aporta cada modelo;\n"
        "- material reusable para discusión de errores y futuras figuras de xAI.\n\n"
        "## Qué sigue pendiente para fases posteriores\n"
        "- freeze oficial con IPS;\n"
        "- evaluación final en `test`;\n"
        "- etapa final de xAI;\n"
        "- eventual discusión sobre grupo de control fuera del pipeline actual.\n\n"
        "## Qué depende de validación experta\n"
        "- qué notas de seguimiento deberían quedar fuera de la tarea;\n"
        "- si parte de la etiqueta disponible opera a nivel paciente y no consulta;\n"
        "- qué señales clínicas y dialectales conviene congelar en la versión final.\n\n"
        "## Qué depende de grupo de control\n"
        "- cualquier extensión que deje de ser diferencial entre dos diagnósticos y busque separar clínica psiquiátrica de no psiquiátrica.\n\n"
        f"## Carpeta de salida\n- `data/outputs/{output_dir_name}/`\n"
    )


def copy_dossier_files(dossier_dir: Path, output_dir: Path) -> list[str]:
    copied = []
    for name in [
        "dossier_ips_patrones_ansiedad.md",
        "dossier_ips_patrones_depresion.md",
        "dossier_ips_errores_curados.md",
        "dossier_ips_errores_curados.csv",
        "dossier_ips_comparacion_modelos.md",
        "dossier_ips_preguntas_finales.md",
        "patrones_clinicos_ansiedad_ampliado.md",
        "patrones_clinicos_depresion_ampliado.md",
        "analisis_comparativo_modelos_ampliado.md",
        "casos_clinicos_reutilizables_xai.csv",
        "preguntas_bibliografia_validacion_clinica_v2.md",
    ]:
        src = dossier_dir / name
        if src.exists():
            shutil.copy2(src, output_dir / name)
            copied.append(name)
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Consolida la fase de revisión clínica externa con auditoría de dataset, contraste metodológico y dossier final.")
    parser.add_argument("--output-tag", type=str, default=None, help="Tag opcional para reemplazar el timestamp de salida.")
    parser.add_argument("--verbose", action="store_true", help="Imprime rutas y decisiones de resolución.")
    args = parser.parse_args()

    suffix = args.output_tag or now_ts()
    output_dir = ensure_dir(OUTPUTS_DIR / f"ips_cierre_final_{suffix}")
    summary_path = OUTPUTS_DIR / f"resumen_cierre_fase_ips_{suffix}.md"

    material_dir = resolve_latest_source_dir("material_validacion_ips_*", "material_validacion_ips_manifest.json", exclude_prueba=True)
    dossier_dir = resolve_latest_dossier_dir()

    if args.verbose:
        print(f"Material IPS base: {material_dir}")
        print(f"Dossier curado: {dossier_dir}")
        print(f"Salida final: {output_dir}")

    raw_df = pd.read_csv(DATA_DIR / "ips_raw.csv")
    clean_df = pd.read_csv(DATA_DIR / "ips_clean.csv")
    flag_df = pd.read_csv(DATA_DIR / "dataset_with_clinical_signal_flag.csv")
    deno_df = pd.read_csv(DATA_DIR / "dataset_denoised.csv")
    base_df = pd.read_csv(DATA_DIR / "splits" / "dataset_base.csv")
    train_df = pd.read_csv(DATA_DIR / "splits" / "train_denoised.csv")
    dev_df = pd.read_csv(DATA_DIR / "splits" / "dev_denoised.csv")
    test_df = pd.read_csv(DATA_DIR / "splits" / "test_denoised.csv")
    train_idx = pd.read_csv(DATA_DIR / "splits" / "train_indices.csv")["row_id"]
    dev_idx = pd.read_csv(DATA_DIR / "splits" / "dev_indices.csv")["row_id"]

    state_csv, state_md = dataset_state_tables(raw_df, clean_df, flag_df, deno_df, train_df, dev_df, test_df)
    state_csv.to_csv(output_dir / "dataset_estado_actual_resumen.csv", index=False)
    (output_dir / "dataset_estado_actual_resumen.md").write_text(state_md, encoding="utf-8")
    (output_dir / "senal_clinica_util.md").write_text(render_useful_signal_md(), encoding="utf-8")

    noise_counts, noise_examples = categorize_removed_noise(flag_df)
    dup_examples = duplicate_examples(raw_df)
    (output_dir / "dataset_ejemplos_ruido_administrativo.md").write_text(
        render_noise_examples_md(noise_counts, noise_examples, dup_examples),
        encoding="utf-8",
    )

    top_words_csv, top_words_md = build_top_words_tables(base_df, deno_df)
    top_words_csv.to_csv(output_dir / "dataset_top_palabras.csv", index=False)
    (output_dir / "dataset_top_palabras.md").write_text(top_words_md, encoding="utf-8")

    generated_wordclouds = generate_wordclouds(output_dir, deno_df)

    (output_dir / "problemas_dataset_y_mitigaciones.md").write_text(render_dataset_problems_md(), encoding="utf-8")

    imbalance_csv, imbalance_md = build_imbalance_table(base_df, deno_df, train_df, dev_df, test_df)
    imbalance_csv.to_csv(output_dir / "manejo_desbalance_modelos.csv", index=False)
    (output_dir / "manejo_desbalance_modelos.md").write_text(imbalance_md, encoding="utf-8")

    raw_vs_filtered_csv, raw_vs_filtered_md = build_baseline_raw_vs_filtered(base_df, train_idx, dev_idx, train_df, dev_df)
    raw_vs_filtered_csv.to_csv(output_dir / "baseline_crudo_vs_filtrado.csv", index=False)
    (output_dir / "baseline_crudo_vs_filtrado.md").write_text(raw_vs_filtered_md, encoding="utf-8")

    copied_dossier = copy_dossier_files(dossier_dir, output_dir)

    glossary = render_glossary_md()
    methodological_points = render_puntos_clave_metodologicos_md()
    (output_dir / "glosario_proyecto.md").write_text(glossary, encoding="utf-8")
    (output_dir / "puntos_clave_revision_metodologica.md").write_text(methodological_points, encoding="utf-8")

    summary = render_summary_md(output_dir.name)
    summary_path.write_text(summary, encoding="utf-8")

    manifest = {
        "material_dir": str(material_dir),
        "dossier_dir": str(dossier_dir),
        "output_dir": str(output_dir),
        "generated_wordclouds": generated_wordclouds,
        "copied_dossier_files": copied_dossier,
        "baseline_crudo_viable": True,
        "test_estado": "pendiente",
        "xai_estado": "pendiente",
    }
    write_json(output_dir / "ips_cierre_final_manifest.json", manifest)
    write_json(OUTPUTS_DIR / "ips_cierre_final_latest.json", manifest)

    print(f"Paquete final IPS generado en: {output_dir}")
    print(f"Resumen final: {summary_path}")


if __name__ == "__main__":
    main()
