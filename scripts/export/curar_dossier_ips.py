#!/usr/bin/env python3
"""
Curación clínica y documental del paquete de revisión clínica externa.

Toma como entrada el paquete vigente `material_validacion_ips_*` y genera un
dossier más utilizable para revisión clínica externa y futura etapa de xAI.
No reentrena modelos, no abre `test` y no modifica decisiones metodológicas.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = DATA_DIR / "outputs"

GENERIC_STOP_TERMS = {
    "refiere", "acude", "control", "paciente", "bien", "encuentra", "estable", "años", "año", "hace",
    "pcte", "aea", "noche", "medicacion", "medicación", "tratamiento", "dias", "vez", "semana", "sigue",
    "esta", "está", "tiene", "desde", "siente", "sentirse", "general", "buena", "mejor", "buen",
    "algunos", "mamá", "hija", "consulta", "plan", "mc", "dx", "imp", "sic", "mg", "comprimido",
    "clonazepam", "zolpidem", "amitriptilina", "paroxetina", "fluoxetina", "litio", "vigil", "vn",
    "qtp", "f31", "100", "20", "10", "26", "50", "olz10", "flx", "fxt", "cnz", "dr", "dra",
    "misma", "tratante", "indicaciones", "fecha", "muy", "cada", "tuvo", "recibe", "sola", "marido",
    "hijo", "casa",
}

KEYWORD_GROUPS = {
    "ansiedad": [
        ("Crisis y activación ansiosa", ["crisis", "ansiedad", "panico", "pánico", "intranquilidad", "desesperacion", "desesperación"]),
        ("Sueño e hiperactivación", ["sueño", "sueno", "duerme", "insomnio", "alprazolam"]),
        ("Somatización y tensión corporal", ["sensacion", "sensación", "parestesias", "mareos", "fatiga", "cansancio", "bochornos"]),
        ("Afecto mixto y retraimiento", ["animo", "ánimo", "niega", "ideas", "aislamiento", "retraimiento", "duelo"]),
    ],
    "depresion": [
        ("Riesgo autolesivo e ideas de muerte", ["autolesion", "autolesión", "suicida", "ideacion", "ideación", "muerte", "ideas"]),
        ("Ánimo depresivo y retraimiento", ["animo", "ánimo", "triste", "llanto", "aislamiento", "retraimiento", "abulia", "anhedonia", "bajon", "bajón"]),
        ("Sueño, energía y enlentecimiento", ["duerme", "sueño", "sueno", "insomnio", "fatiga", "astenia", "cansancio"]),
        ("Contexto longitudinal y terapéutico", ["consulta", "medicación", "medicacion", "indicaciones", "litio", "vigil", "cnz", "qtp"]),
    ],
}

RULE_CATEGORY_MAP = {
    "Autolesion": "Riesgo autolesivo e ideas de muerte",
    "Ideacinsuicida": "Riesgo autolesivo e ideas de muerte",
    "Intentosuicida": "Riesgo autolesivo e ideas de muerte",
    "Ideas de muerte": "Riesgo autolesivo e ideas de muerte",
    "Animo deprimido": "Ánimo depresivo y retraimiento",
    "Retraimiento social / aislamiento": "Ánimo depresivo y retraimiento",
    "Llantofcil": "Ánimo depresivo y retraimiento",
    "Anhedonia": "Ánimo depresivo y retraimiento",
    "Abulia": "Ánimo depresivo y retraimiento",
    "Sntomasdepresivosgenerales": "Ánimo depresivo y retraimiento",
    "Ansiedad": "Crisis y activación ansiosa",
    "Sintomas ansiosos generales": "Crisis y activación ansiosa",
    "Angustia Miedo Temor": "Crisis y activación ansiosa",
    "Pnico": "Crisis y activación ansiosa",
    "Agitacinpsicomotora": "Crisis y activación ansiosa",
    "Sueno / insomnio": "Sueño e hiperactivación",
    "Sueno alterado": "Sueño e hiperactivación",
    "Sueo Despertartemprano": "Sueño e hiperactivación",
    "Sintomas somaticos": "Somatización y tensión corporal",
    "Fatiga": "Somatización y tensión corporal",
    "Baja energia": "Somatización y tensión corporal",
    "Irritabilidad": "Afecto mixto y retraimiento",
    "Labilidademocional": "Afecto mixto y retraimiento",
    "Contexto": "Contexto longitudinal y terapéutico",
}

RULE_RENAMES = {
    "Sntomassomticos Ejemplos": "Sintomas somaticos",
    "Sntomasansiososgenerales": "Sintomas ansiosos generales",
    "Sueo Alterado": "Sueno alterado",
    "Sueo Insomnio": "Sueno / insomnio",
    "Bajaconcentracin": "Baja concentracion",
    "Bajaenerga": "Baja energia",
    "Animodeprimido": "Animo deprimido",
    "Retraimientosocial Aislamiento": "Retraimiento social / aislamiento",
    "Ideasdemuerte": "Ideas de muerte",
    "Autolesin": "Autolesion",
    "Apetitoaumentode": "Apetito aumentado",
}

ERROR_SELECTION_SPECS = [
    ("ansiedad→depresion | seguimiento breve", lambda df: dir_filter(df, "ansiedad", "depresion") & text_or_type(df, ["nota_breve", "misma medicacion", "misma indicacion", "seguimiento_administrativo"])),
    ("ansiedad→depresion | solapamiento médico", lambda df: dir_filter(df, "ansiedad", "depresion") & text_or_type(df, ["solapamiento_medico", "prednisona", "corticoides", "colitis", "orl", "gineco", "perimenopausia", "eeg", "encefalo"])),
    ("ansiedad→depresion | ansiedad explícita en consulta de control", lambda df: dir_filter(df, "ansiedad", "depresion") & text_or_type(df, ["crisis de ansiedad", "crisis de panico", "sintomas ansiosos generales", "pnico", "panico", "desesperacion"])),
    ("ansiedad→depresion | frontera ambigua", lambda df: dir_filter(df, "ansiedad", "depresion") & df["tipo_de_error"].fillna("").str.contains("frontera_ambigua", case=False)),
    ("ansiedad→depresion | posible etiqueta a nivel paciente", lambda df: dir_filter(df, "ansiedad", "depresion") & (df["patient_error_count"] >= 5)),
    ("ansiedad→depresion | mezcla afectiva", lambda df: dir_filter(df, "ansiedad", "depresion") & text_or_type(df, ["animo deprimido", "llantofcil", "ideas de muerte", "autolesion"])),
    ("depresion→ansiedad | seguimiento breve", lambda df: dir_filter(df, "depresion", "ansiedad") & text_or_type(df, ["seguimiento_administrativo", "control con tratante", "misma medicacion", "misma indicacion"])),
    ("depresion→ansiedad | riesgo autolesivo", lambda df: dir_filter(df, "depresion", "ansiedad") & text_or_type(df, ["autolesion", "ideacinsuicida", "ideas de muerte", "intentosuicida", "suicida"])),
    ("depresion→ansiedad | frontera ambigua", lambda df: dir_filter(df, "depresion", "ansiedad") & df["tipo_de_error"].fillna("").str.contains("frontera_ambigua", case=False)),
    ("depresion→ansiedad | posible etiqueta a nivel paciente", lambda df: dir_filter(df, "depresion", "ansiedad") & (df["patient_error_count"] >= 5)),
    ("depresion→ansiedad | solapamiento sintomático", lambda df: dir_filter(df, "depresion", "ansiedad") & text_or_type(df, ["solapamiento_sintomatico", "ansiedad |", "irritabilidad", "sueno / insomnio"])),
    ("depresion→ansiedad | depresión con alto ruido contextual", lambda df: dir_filter(df, "depresion", "ansiedad") & text_or_type(df, ["sntomasdepresivosgenerales", "animo deprimido", "vigil", "litio", "cnz"])),
]


@dataclass
class ContextoCuracion:
    source_dir: Path
    output_dir: Path
    manifest: dict[str, Any]
    source_manifest_path: Path
    summary_path: Path
    preproc_csv: pd.DataFrame
    balance_csv: pd.DataFrame
    errors_df: pd.DataFrame
    comparison_df: pd.DataFrame
    dev_df: pd.DataFrame
    transformer_label: str
    tfidf_pred: pd.DataFrame
    transformer_pred: pd.DataFrame
    hybrid_pred: pd.DataFrame
    features_df: pd.DataFrame


def now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_latest_source_dir() -> Path:
    candidates = sorted(
        [
            p for p in OUTPUTS_DIR.glob("material_validacion_ips_*")
            if p.is_dir()
            and "prueba" not in p.name.lower()
            and (p / "material_validacion_ips_manifest.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No se encontró un paquete `material_validacion_ips_*` con manifiesto.")
    return candidates[0]


def resolve_output_dir(tag: str | None) -> tuple[Path, str]:
    suffix = tag or now_ts()
    return ensure_dir(OUTPUTS_DIR / f"dossier_ips_curado_{suffix}"), suffix


def load_prediction(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    rename_map = {}
    if "etiqueta" in df.columns and "y_true" not in df.columns:
        rename_map["etiqueta"] = "y_true"
    for cand in ["pred_label", "pred", "y_pred_label"]:
        if cand in df.columns and "y_pred" not in df.columns:
            rename_map[cand] = "y_pred"
            break
    if rename_map:
        df = df.rename(columns=rename_map)
    keep = [c for c in ["row_id", "y_true", "y_pred", "prob_ansiedad", "prob_depresion"] if c in df.columns]
    out = df[keep].copy()
    out["row_id"] = out["row_id"].astype(int)
    return out


def dir_filter(df: pd.DataFrame, y_true: str, y_pred: str) -> pd.Series:
    return (df["etiqueta_original"] == y_true) & (df["prediccion_modelo"] == y_pred)


def text_or_type(df: pd.DataFrame, patterns: list[str]) -> pd.Series:
    pat = "|".join(re.escape(p) for p in patterns)
    return (
        df["tipo_de_error"].fillna("").str.contains(pat, case=False, regex=True)
        | df["texto"].fillna("").str.contains(pat, case=False, regex=True)
        | df["señales_detectadas"].fillna("").str.contains(pat, case=False, regex=True)
    )


def humanize_rule(name: str) -> str:
    text = re.sub(r"^rule_", "", str(name))
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ").strip()
    return RULE_RENAMES.get(text, text)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[\.;:])\s+", text)
    seen: set[str] = set()
    unique_parts = []
    for part in parts:
        normalized = re.sub(r"[^a-z0-9áéíóúñ]+", " ", part.lower()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_parts.append(part.strip())
        if len(unique_parts) >= 3:
            break
    return " ".join(unique_parts).strip()


def short_summary(row: pd.Series) -> str:
    text = clean_text(row.get("texto", ""))
    low = text.lower()
    signals_raw = row.get("señales_detectadas", "")
    signals = "" if pd.isna(signals_raw) else str(signals_raw)
    tipo = row.get("tipo_de_error", "") or ""

    if "misma medicacion" in low or "misma indicacion" in low or "control con tratante" in low:
        return "Nota muy breve de seguimiento con continuidad terapéutica y sin fenomenología suficientemente detallada."
    if "seguimiento_administrativo" in tipo:
        return "Consulta de control o seguimiento con baja fenomenología activa y predominio del contexto longitudinal."
    if any(k in low for k in ["prednisona", "corticoides", "colitis", "orl", "gineco", "perimenopausia", "encefalo", "eeg", "laboratorio", "tiroideo"]):
        return "Consulta con superposición relevante de clínica médica o efectos de tratamiento, lo que baja la especificidad diagnóstica."
    if any(k in low for k in ["crisis de panico", "crisis de ansiedad", "desesperacion", "intranquilidad", "parestesias", "tensionada"]):
        return "Consulta con activación ansiosa explícita y componente somático marcado."
    if any(k in low for k in ["duerme", "sueño", "insomnio", "sueño no reparador"]) or "Sueno / insomnio" in signals:
        return "Consulta donde el problema del sueño domina la fenomenología registrada."
    if any(k in low for k in ["bajoneada", "triste", "llanto", "ánimo", "animo"]) or any(k in signals for k in ["Animo deprimido", "Llantofcil"]):
        return "Consulta con mezcla de afecto depresivo y seguimiento longitudinal del cuadro."
    if any(k in signals for k in ["Autolesion", "Ideacinsuicida", "Ideas de muerte", "Intentosuicida"]):
        return "Consulta con señal de riesgo autolesivo que conviene discutir en relación con la etiqueta asignada."
    return "Consulta con información clínica parcial o mixta, difícil de asignar con seguridad a una sola etiqueta diferencial."


def patient_label_suspicion(row: pd.Series) -> str:
    tipo = row.get("tipo_de_error", "") or ""
    text = str(row.get("texto", "")).lower()
    if row.get("patient_error_count", 0) >= 5:
        return "alta"
    if "seguimiento_administrativo" in tipo or "control con tratante" in text or "misma medicacion" in text or "misma indicacion" in text:
        return "media"
    if "frontera_ambigua" in tipo or "solapamiento" in tipo:
        return "media"
    return "baja"


def split_signals(value: Any) -> list[str]:
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split("|") if part.strip()]


def compute_model_metrics(df: pd.DataFrame) -> dict[str, Any]:
    y_true = df["y_true"]
    y_pred = df["y_pred"]
    return {
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1_ansiedad": float(f1_score(y_true == "ansiedad", y_pred == "ansiedad")),
        "f1_depresion": float(f1_score(y_true == "depresion", y_pred == "depresion")),
        "correctos_total": int((y_true == y_pred).sum()),
        "correctos_ansiedad": int(((y_true == "ansiedad") & (y_pred == "ansiedad")).sum()),
        "correctos_depresion": int(((y_true == "depresion") & (y_pred == "depresion")).sum()),
        "n_eval": int(len(df)),
    }


def top_filtered_terms(df: pd.DataFrame, y_true: str, y_pred: str, top_k: int = 12) -> list[tuple[str, int]]:
    subset = df[(df["y_true"] == y_true) & (df["y_pred"] == y_pred)]
    counter: Counter[str] = Counter()
    for text in subset["texto"].astype(str):
        tokens = re.findall(r"[a-záéíóúñ0-9]+", text.lower())
        for token in tokens:
            if len(token) <= 2:
                continue
            if token in GENERIC_STOP_TERMS:
                continue
            if token.isdigit():
                continue
            counter[token] += 1
    return counter.most_common(top_k)


def build_rule_counts(features_df: pd.DataFrame, pred_df: pd.DataFrame, dev_df: pd.DataFrame, y_true: str) -> list[tuple[str, int]]:
    merged = pred_df.merge(dev_df[["row_id", "etiqueta"]], on="row_id", how="left")
    merged = merged.merge(features_df, on="row_id", how="left", suffixes=("", "_feat"))
    rule_cols = [c for c in features_df.columns if c.startswith("rule_") and not c.startswith("rule_medication_")]
    subset = merged[(merged["y_true"] == y_true) & (merged["y_pred"] == y_true)]
    if subset.empty:
        return []
    counts = subset[rule_cols].sum().sort_values(ascending=False)
    counts = counts[counts > 0].head(12)
    return [(humanize_rule(col), int(value)) for col, value in counts.items()]


def summarize_categories(class_name: str, term_sources: dict[str, list[tuple[str, int]]], rule_counts: list[tuple[str, int]]) -> list[dict[str, Any]]:
    categories = []
    for title, keywords in KEYWORD_GROUPS[class_name]:
        evid_text = []
        for model_name, terms in term_sources.items():
            hits = [(term, count) for term, count in terms if any(key in term for key in keywords)]
            if hits:
                evid_text.append((model_name, hits[:3]))
        evid_rules = [(name, count) for name, count in rule_counts if RULE_CATEGORY_MAP.get(name) == title]
        if evid_text or evid_rules:
            categories.append({
                "titulo": title,
                "texto": evid_text,
                "reglas": evid_rules,
            })
    return categories


def render_pattern_doc_brief(class_name: str, categories: list[dict[str, Any]], transformer_label: str) -> str:
    class_title = "ansiedad" if class_name == "ansiedad" else "depresion"
    other = "depresión" if class_name == "ansiedad" else "ansiedad"
    lines = [
        f"# Dossier IPS: patrones clínicos asociados a {class_title}",
        "",
        "## Lectura breve",
        f"- Este resumen integra lo que captan `TF-IDF`, `{transformer_label}` y el híbrido final sobre verdaderos positivos de `{class_name}` en `dev`.",
        f"- Debe leerse como material preparatorio para validación clínica, no como verdad diagnóstica cerrada.",
        f"- El híbrido final no domina la tarea completa, pero sí aporta trazabilidad clínica sobre un subconjunto relevante de notas.",
        "",
        "## Núcleo clínico observable",
    ]
    for item in categories:
        bullet = f"- **{item['titulo']}**"
        detail_parts = []
        if item["texto"]:
            text_bits = []
            for model_name, hits in item["texto"]:
                joined = ", ".join(f"{term} ({count})" for term, count in hits)
                text_bits.append(f"{model_name}: {joined}")
            detail_parts.append("texto: " + " | ".join(text_bits))
        if item["reglas"]:
            joined = ", ".join(f"{signal} ({count})" for signal, count in item["reglas"][:5])
            detail_parts.append("reglas del híbrido: " + joined)
        if detail_parts:
            bullet += ". " + "; ".join(detail_parts)
        lines.append(bullet)

    lines.extend([
        "",
        "## Lectura por enfoque",
        f"- `TF-IDF`: funciona bien cuando la nota deja marcas textuales relativamente directas del cuadro de {class_title}.",
        f"- `{transformer_label}`: conserva ese núcleo y agrega algo más de contexto longitudinal, aunque sigue dependiendo del lenguaje explícito de la nota.",
        f"- Híbrido final: cuando acierta, suele hacerlo con señales clínicas más auditables; cuando falla, puede desplazarse hacia {other} si la consulta es breve, mixta o de seguimiento.",
        "",
        "## Observación clínica adicional",
    ])
    if class_name == "ansiedad":
        lines.extend([
            "- En ansiedad conviene discutir especialmente cuánto pesan las consultas de seguimiento, la somatización y el sueño en la decisión final.",
            "- También aparece un subconjunto de notas con señales de riesgo o afecto depresivo mezclado, lo que puede reflejar ambigüedad clínica real o etiqueta longitudinal.",
        ])
    else:
        lines.extend([
            "- En depresión los modelos textuales no solo captan síntomas afectivos; también parecen apoyarse en contexto longitudinal, seguimiento terapéutico y lenguaje de manejo clínico.",
            "- El híbrido vuelve más visible la capa de riesgo autolesivo, retraimiento y ánimo deprimido, pero sigue necesitando validación experta para separar cuadro actual de trayectoria previa.",
        ])
    lines.extend([
        "",
        "## Advertencias para revisión clínica",
        f"- Parte de las notas etiquetadas como `{class_name}` contienen fenomenología mixta o longitudinal; esto puede reflejar solapamiento clínico real o ruido de etiqueta a nivel paciente/consulta.",
        f"- Los patrones aquí resumidos deben contrastarse con psiquiatría antes de reutilizarse como señal clínica consolidada en documentación pública o futuras fases de xAI.",
    ])
    return "\n".join(lines) + "\n"


def render_pattern_doc_ampliado(class_name: str, categories: list[dict[str, Any]], rule_counts: list[tuple[str, int]], term_sources: dict[str, list[tuple[str, int]]], transformer_label: str) -> str:
    lines = [
        f"# Patrones clínicos asociados a {class_name} para revisión ampliada",
        "",
        "## Alcance",
        f"- Clase analizada: `{class_name}`.",
        "- Split analizado: `dev`.",
        f"- Modelos comparados: `TF-IDF`, `{transformer_label}`, híbrido final congelado en `dev`.",
        "",
        "## Lectura metodológica",
        f"- `TF-IDF` y `{transformer_label}` ayudan a ver qué retiene el texto por sí solo.",
        "- El híbrido final agrega reglas clínicas explícitas y un backbone contextual, lo que vuelve más auditable parte de la señal.",
        "",
        "## Categorías clínicas resumidas",
    ]
    for item in categories:
        lines.append(f"### {item['titulo']}")
        if item["texto"]:
            lines.append("- Evidencia en modelos textuales:")
            for model_name, hits in item["texto"]:
                joined = ", ".join(f"{term} ({count})" for term, count in hits)
                lines.append(f"  - `{model_name}`: {joined}")
        if item["reglas"]:
            joined = ", ".join(f"{signal} ({count})" for signal, count in item["reglas"])
            lines.append(f"- Evidencia en reglas del híbrido: {joined}")
        lines.append("")

    lines.extend([
        "## Señales de reglas más frecuentes en el híbrido",
        "| señal | conteo |",
        "|---|---:|",
    ])
    for signal, count in rule_counts:
        lines.append(f"| {signal} | {count} |")

    lines.extend([
        "",
        "## Términos filtrados más recurrentes en verdaderos positivos",
    ])
    for model_name, terms in term_sources.items():
        joined = ", ".join(f"{term} ({count})" for term, count in terms[:12])
        lines.append(f"- `{model_name}`: {joined}")

    lines.extend([
        "",
        "## Observación metodológica adicional",
    ])
    if class_name == "ansiedad":
        lines.extend([
            "- La clase `ansiedad` sigue siendo la más sensible a seguimiento, sueño y somatización; esto debe explicitarse en la discusión metodológica.",
            "- La presencia de señales depresivas o de riesgo dentro de verdaderos positivos de ansiedad sugiere que parte de la fenomenología observada es mixta o longitudinal.",
        ])
    else:
        lines.extend([
            "- En `depresion`, los modelos textuales retienen también un componente longitudinal y terapéutico; no todo lo que aciertan es sintomatología pura.",
            "- El híbrido aporta una lectura más auditable del riesgo y del retraimiento, pero no reemplaza la necesidad de validar externamente si la etiqueta responde a la consulta o al paciente.",
        ])
    lines.extend([
        "",
        "## Interpretación",
        "- Este material no debe leerse como lista cerrada de síntomas, sino como patrón observable en notas que el modelo clasificó correctamente.",
        "- La revisión clínica externa debe distinguir qué parte de esta señal es verdaderamente diagnóstica y qué parte corresponde a seguimiento, medicación o contexto longitudinal.",
    ])
    return "\n".join(lines) + "\n"


def build_error_frame(errors_df: pd.DataFrame) -> pd.DataFrame:
    df = errors_df.copy()
    df["patient_error_count"] = df.groupby("patient_id")["row_id"].transform("count")
    df["direccion_error"] = df["etiqueta_original"] + "→" + df["prediccion_modelo"]
    df["resumen_clinico_corto"] = df.apply(short_summary, axis=1)
    df["sospecha_etiquetado"] = df.apply(patient_label_suspicion, axis=1)
    return df


def select_curated_errors(df: pd.DataFrame) -> pd.DataFrame:
    selected_rows = []
    used_row_ids: set[int] = set()
    selected_per_patient: Counter[int] = Counter()
    for label, spec in ERROR_SELECTION_SPECS:
        candidates = df[spec(df)].copy()
        if candidates.empty:
            continue
        candidates["selected_per_patient"] = candidates["patient_id"].map(lambda x: selected_per_patient.get(int(x), 0))
        preferred = candidates[candidates["selected_per_patient"] < 2].copy()
        if not preferred.empty:
            candidates = preferred
        candidates = candidates.sort_values(
            by=["selected_per_patient", "patient_error_count", "margen_prob", "row_id"],
            ascending=[True, False, False, True],
        )
        chosen = candidates.loc[~candidates["row_id"].isin(used_row_ids)].head(1)
        if chosen.empty:
            continue
        row = chosen.iloc[0].copy()
        row["grupo_curacion"] = label
        selected_rows.append(row)
        used_row_ids.add(int(row["row_id"]))
        selected_per_patient[int(row["patient_id"])] += 1

    if not selected_rows:
        return df.head(0).copy()

    curated = pd.DataFrame(selected_rows)
    curated["tipo_caso"] = curated["grupo_curacion"].map(tipo_caso_from_group)
    curated["hipotesis_clinica_curada"] = curated.apply(curate_hypothesis, axis=1)
    curated["pregunta_para_IPS_curada"] = curated.apply(curate_question, axis=1)
    curated["relevante_para_ips"] = "si"
    curated["relevante_para_xai"] = curated["tipo_caso"].isin(
        {"frontera_ambigua", "sospecha_etiquetado_paciente_consulta", "solapamiento_medico", "riesgo_autolesivo"}
    ).map({True: "si", False: "si"})
    curated["relevante_para_reporte"] = "si"
    curated["comentario"] = curated.apply(build_comment, axis=1)
    keep_cols = [
        "row_id", "patient_id", "etiqueta_original", "prediccion_modelo", "direccion_error", "grupo_curacion",
        "tipo_caso", "tipo_de_error", "sospecha_etiquetado", "señales_detectadas", "resumen_clinico_corto",
        "hipotesis_clinica_curada", "pregunta_para_IPS_curada", "margen_prob", "relevante_para_ips",
        "relevante_para_xai", "relevante_para_reporte", "comentario",
    ]
    curated = curated[keep_cols].sort_values(by=["direccion_error", "row_id"]).reset_index(drop=True)
    return curated


def tipo_caso_from_group(group: str) -> str:
    if "seguimiento breve" in group:
        return "seguimiento_poco_fenomenologico"
    if "solapamiento médico" in group:
        return "solapamiento_medico"
    if "frontera ambigua" in group:
        return "frontera_ambigua"
    if "posible etiqueta a nivel paciente" in group:
        return "sospecha_etiquetado_paciente_consulta"
    if "riesgo autolesivo" in group:
        return "riesgo_autolesivo"
    if "mezcla afectiva" in group or "solapamiento sintomático" in group:
        return "solapamiento_sintomatico"
    return "error_clinico_relevante"


def curate_hypothesis(row: pd.Series) -> str:
    tipo_caso = row["tipo_caso"]
    if tipo_caso == "seguimiento_poco_fenomenologico":
        return "La nota concentra control terapéutico o continuidad de medicación, con fenomenología activa insuficiente para una lectura diferencial robusta."
    if tipo_caso == "solapamiento_medico":
        return "La consulta mezcla síntomas psiquiátricos con clínica médica o efectos de tratamiento, lo que puede sesgar la etiqueta diferencial."
    if tipo_caso == "frontera_ambigua":
        return "La fenomenología registrada admite una lectura ambigua entre ansiedad y depresión, sin predominio clínico limpio en el texto."
    if tipo_caso == "sospecha_etiquetado_paciente_consulta":
        return "La serie de errores del mismo paciente sugiere revisar si la etiqueta fue asignada por trayectoria global y no por fenomenología de la consulta puntual."
    if tipo_caso == "riesgo_autolesivo":
        return "La presencia de señales de riesgo requiere discusión clínica porque puede coexistir con ansiedad, depresión o longitudinalidad del caso."
    if tipo_caso == "solapamiento_sintomatico":
        return "El error parece surgir de síntomas compartidos entre cuadros afectivos, especialmente sueño, irritabilidad o ansiedad concomitante."
    return "La nota contiene señal clínica parcial o mixta y conviene discutir qué etiqueta diferencial representa mejor la consulta."


def curate_question(row: pd.Series) -> str:
    tipo_caso = row["tipo_caso"]
    if tipo_caso == "seguimiento_poco_fenomenologico":
        return "¿Esta consulta debería entrar en la tarea diferencial o conviene tratarla como seguimiento no diagnóstico?"
    if tipo_caso == "solapamiento_medico":
        return "¿La fenomenología principal aquí es psiquiátrica o está dominada por enfermedad médica, perimenopausia o efectos de medicación?"
    if tipo_caso == "frontera_ambigua":
        return "¿Qué rasgo clínico sostendría aquí una etiqueta principal por encima de la otra?"
    if tipo_caso == "sospecha_etiquetado_paciente_consulta":
        return "¿La etiqueta disponible representa mejor al paciente global que a esta consulta específica?"
    if tipo_caso == "riesgo_autolesivo":
        return "¿Cómo debería leerse esta señal de riesgo dentro de una tarea binaria ansiedad vs depresión?"
    if tipo_caso == "solapamiento_sintomatico":
        return "¿Estos síntomas compartidos deberían considerarse suficientes para sostener la etiqueta original?"
    return "¿Qué haría clínicamente más defendible la etiqueta de esta consulta?"


def build_comment(row: pd.Series) -> str:
    return (
        f"{row['grupo_curacion']}. "
        f"Resumen: {row['resumen_clinico_corto']} "
        f"Sospecha de etiqueta paciente/consulta: {row['sospecha_etiquetado']}."
    )


def render_curated_errors_md(curated: pd.DataFrame) -> str:
    lines = [
        "# Dossier IPS: errores curados del modelo final",
        "",
        "- Modelo auditado: híbrido final congelado en `dev`.",
        "- Objetivo: llevar a IPS una muestra reducida, diversa y clínicamente discutible.",
        "- Criterios de selección: seguimiento poco fenomenológico, frontera ambigua, solapamiento médico, riesgo autolesivo y sospecha de etiqueta paciente/consulta.",
        "",
        "## Casos seleccionados",
        "| row_id | dirección | tipo de caso | señales detectadas | resumen clínico corto | hipótesis clínica | pregunta para IPS |",
        "|---:|---|---|---|---|---|---|",
    ]
    for _, row in curated.iterrows():
        signals = row["señales_detectadas"] if pd.notna(row["señales_detectadas"]) else "sin señal explícita"
        lines.append(
            f"| {int(row['row_id'])} | {row['direccion_error']} | {row['tipo_caso']} | "
            f"{signals} | {row['resumen_clinico_corto']} | "
            f"{row['hipotesis_clinica_curada']} | {row['pregunta_para_IPS_curada']} |"
        )
    lines.extend([
        "",
        "## Lectura de conjunto",
        "- La mayoría de los errores no parecen simples fallas mecánicas del modelo; se concentran en consultas breves, longitudinales, mixtas o con fuerte superposición médica.",
        "- La asimetría más importante sigue siendo clínica: el modelo final favorece `depresion` sobre `ansiedad`, por lo que ansiedad queda más expuesta a seguimiento, sueño y somatización.",
        "- Los pacientes con series largas de errores merecen revisión explícita porque pueden reflejar una etiqueta heredada por trayectoria clínica y no por consulta puntual.",
    ])
    return "\n".join(lines) + "\n"


def render_questions_md() -> str:
    lines = [
        "# Dossier IPS: preguntas clínicas finales",
        "",
        "## A. Validez clínica de señales",
        "- ¿Los patrones resumidos para ansiedad y depresión tienen sentido clínico en estas notas del IPS?",
        "- ¿Qué señales del híbrido considerarían realmente diagnósticas y cuáles leerían más como contexto longitudinal o terapéutico?",
        "- ¿Hay abreviaturas, localismos o modos de narrar síntomas que sigan quedando subcapturados?",
        "",
        "## B. Errores y ambigüedad",
        "- ¿Los errores `ansiedad→depresion` y `depresion→ansiedad` seleccionados son errores clínicos reales o consultas intrínsecamente ambiguas?",
        "- ¿Qué combinación de síntomas volvería clínicamente razonable aceptar una zona de solapamiento entre ambas etiquetas?",
        "",
        "## C. Etiquetado paciente vs consulta",
        "- ¿La etiqueta disponible parece describir al paciente global o a la fenomenología de cada consulta?",
        "- En pacientes con muchas consultas, ¿qué criterios usarían para decidir si una nota puntual sostiene o no la etiqueta histórica?",
        "",
        "## D. Notas administrativas y de seguimiento",
        "- ¿Qué tipo de notas deberían considerarse poco diagnósticas para esta tarea diferencial?",
        "- ¿Las consultas de reposición, control breve o ajuste farmacológico deberían excluirse sistemáticamente o solo en ciertos casos?",
        "",
        "## E. Patrones locales y dialectales",
        "- ¿Hay expresiones paraguayas, institucionales o coloquiales que convenga incorporar al freeze léxico final?",
        "- ¿Existen pistas clínicas frecuentes en IPS que no aparezcan bien capturadas por reglas o modelos textuales?",
        "",
        "## F. Grupo de control y ampliación futura",
        "- ¿Sería clínicamente útil incorporar un grupo de control o notas con baja carga psiquiátrica en una fase posterior?",
        "- Si hubiera que priorizar una validación experta manual, ¿qué subconjunto revisarían primero: errores ambiguos, series por paciente o patrones léxicos locales?",
    ]
    return "\n".join(lines) + "\n"


def render_preguntas_bibliografia_v2() -> str:
    lines = [
        "# Preguntas bibliográficas sobre validación clínica y estado del arte",
        "",
        "## Revisión de errores con expertos",
        "- ¿Qué literatura clínica o de cNLP justifica revisar errores con expertos antes de abrir un hold-out final?",
        "- ¿Qué beneficios y límites se reportan al usar revisión experta como paso intermedio entre desarrollo y evaluación final?",
        "",
        "## Label noise y nivel de etiqueta",
        "- ¿Qué evidencia existe sobre ruido de etiqueta en EHR psiquiátricos cuando la etiqueta se asigna al paciente pero se modela a nivel consulta?",
        "- ¿Cómo se ha discutido en la literatura la diferencia entre diagnóstico longitudinal y fenomenología puntual de una consulta?",
        "",
        "## Métricas en tareas desbalanceadas",
        "- ¿Qué argumentos metodológicos sostienen priorizar `macro_f1`, `balanced_accuracy` y F1 por clase en tareas binarias desbalanceadas de salud mental?",
        "- ¿Cómo conviene explicar que un modelo tenga más aciertos totales pero peor `macro_f1`?",
        "",
        "## Grupo de control",
        "- ¿Qué trabajos justifican empezar por una tarea diferencial clínica sin grupo de control explícito?",
        "- ¿En qué escenarios sí conviene incorporar grupo de control y cómo cambia la interpretación del problema?",
        "",
        "## Patrones clínicos y validación experta",
        "- ¿Cómo se presenta en cNLP clínico la validación de patrones detectados por modelos con especialistas humanos?",
        "- ¿Qué buenas prácticas existen para mostrar patrones clínicos sin sobreinterpretar correlaciones textuales o contextuales?",
        "",
        "## Interpretabilidad clínica y xAI",
        "- ¿Qué enfoques de explicabilidad son más útiles cuando el objetivo es contrastar señales con expertos clínicos y no solo optimizar desempeño?",
        "- ¿Cómo se integran explicaciones locales de casos ambiguos o mal clasificados en la discusión metodológica de un reporte clínico computacional?",
    ]
    return "\n".join(lines) + "\n"


def render_curacion_summary(ctx: ContextoCuracion, output_dir: Path, curated_errors: pd.DataFrame) -> str:
    return (
        "# Curación del dossier IPS\n\n"
        "## Qué se curó\n"
        f"- Fuente de entrada: `{ctx.source_dir.relative_to(ROOT)}`.\n"
        f"- Salida curada: `{output_dir.relative_to(ROOT)}`.\n"
        "- Patrones por clase reescritos en lenguaje clínico y separados en versión breve para revisión externa y versión ampliada para análisis metodológico.\n"
        "- Errores del modelo reducidos a una muestra diversa y clínicamente discutible.\n"
        f"- Comparación entre `TF-IDF`, `{ctx.transformer_label}` e híbrido final reescrita para revisión clínica, documentación técnica y futura etapa de xAI.\n"
        "- Preguntas para revisión clínica y preguntas bibliográficas reordenadas por problema metodológico.\n\n"
        "## Qué mejora respecto al paquete anterior\n"
        "- El paquete original era correcto para trazabilidad, pero todavía muy cercano al artefacto técnico.\n"
        "- La nueva capa evita listas léxicas superficiales y prioriza señales clínicamente interpretables.\n"
        "- Los errores ahora están agrupados por tipología útil para discusión clínica: seguimiento, frontera ambigua, solapamiento médico y sospecha de etiqueta paciente/consulta.\n\n"
        "## Qué sirve para IPS\n"
        "- `dossier_ips_patrones_ansiedad.md`\n"
        "- `dossier_ips_patrones_depresion.md`\n"
        "- `dossier_ips_errores_curados.md`\n"
        "- `dossier_ips_comparacion_modelos.md`\n"
        "- `dossier_ips_preguntas_finales.md`\n\n"
        "## Qué sirve para análisis ampliado\n"
        "- `patrones_clinicos_ansiedad_ampliado.md`\n"
        "- `patrones_clinicos_depresion_ampliado.md`\n"
        "- `analisis_comparativo_modelos_ampliado.md`\n"
        "- `casos_clinicos_reutilizables_xai.csv`\n\n"
        "## Qué queda como base para xAI y documentación técnica\n"
        "- tabla de casos reutilizables con relevancia explícita para xAI y reporte técnico;\n"
        "- puente documental entre validación clínica y análisis futuro por familias de features;\n"
        "- preguntas bibliográficas refinadas para ampliar el estado del arte.\n\n"
        "## Vacíos que siguen dependiendo de validación experta\n"
        "- confirmar si los errores repetidos por paciente reflejan etiqueta longitudinal más que error del modelo;\n"
        "- decidir qué notas de seguimiento deberían quedar fuera de la tarea diferencial;\n"
        "- validar si los patrones locales y clínicos resumidos son clínicamente defendibles en IPS.\n\n"
        f"## Casos curados seleccionados\n- Total: {len(curated_errors)} casos.\n"
    )


def build_metrics_table(tfidf_df: pd.DataFrame, transformer_df: pd.DataFrame, hybrid_df: pd.DataFrame, transformer_label: str) -> pd.DataFrame:
    rows = []
    for model_name, df in [("TF-IDF", tfidf_df), (transformer_label, transformer_df), ("HIBRIDO_FINAL", hybrid_df)]:
        metrics = compute_model_metrics(df)
        rows.append({"modelo": model_name, **metrics})
    return pd.DataFrame(rows)


def render_model_comparison_ips(metrics_df: pd.DataFrame, comparison_df: pd.DataFrame, transformer_label: str, backbone_label: str) -> str:
    lines = [
        "# Dossier IPS: comparación de modelos",
        "",
        "## Lectura breve",
        "- `TF-IDF` sigue siendo una línea base simple y fuerte.",
        f"- `{transformer_label}` es el mejor transformer standalone vigente en `dev`.",
        f"- El híbrido final congelado en `dev` usa `{backbone_label}` como backbone contextual y prioriza trazabilidad clínica.",
        "",
        "## Métricas principales en `dev`",
        "| modelo | macro_f1 | balanced_accuracy | correctos totales | correctos ansiedad | correctos depresion |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['modelo']} | {row['macro_f1']:.4f} | {row['balanced_accuracy']:.4f} | "
            f"{int(row['correctos_total'])} | {int(row['correctos_ansiedad'])} | {int(row['correctos_depresion'])} |"
        )
    lines.extend([
        "",
        "## Interpretación para clínica",
        "- `TF-IDF` funciona bien cuando la nota explicita el cuadro con lenguaje relativamente directo.",
        f"- `{transformer_label}` conserva ese núcleo y lo contextualiza mejor en algunos casos, por eso queda como mejor transformer standalone.",
        "- El híbrido final acierta más casos totales, sobre todo en `depresion`, pero no domina `macro_f1` porque pierde sensibilidad relativa en `ansiedad`.",
        "- Esto no invalida al híbrido; indica que su aporte es más clínico-auditable y menos homogéneo entre clases.",
        "",
        "## Superposición útil entre enfoques",
    ])
    subset = comparison_df[comparison_df["tipo"].isin(["interseccion_correctos", "solo_modelo"])].copy()
    for _, row in subset.iterrows():
        if row["tipo"] == "interseccion_correctos" and str(row["clase"]) == "todas":
            lines.append(f"- {row['modelo_a']} y {row.get('modelo_b', '')}: {int(row['n_casos'])} casos correctos compartidos en `dev`.")
        if row["tipo"] == "solo_modelo" and str(row["clase"]) == "todas":
            lines.append(f"- {row['modelo_a']}: {int(row['n_casos'])} casos correctos exclusivos.")
    lines.extend([
        "",
        "## Cómo usar esta comparación en revisión clínica",
        "- No presentar al híbrido como ganador absoluto por métrica.",
        "- Sí usarlo para discutir qué señales clínicas vuelven más auditable un acierto y qué errores parecen venir de la propia estructura del dataset.",
    ])
    return "\n".join(lines) + "\n"


def render_model_comparison_ampliado(metrics_df: pd.DataFrame, comparison_df: pd.DataFrame, transformer_label: str) -> str:
    lines = [
        "# Análisis comparativo ampliado de modelos",
        "",
        "## Marco de lectura",
        "- `TF-IDF` se mantiene como baseline fuerte simple.",
        f"- `{transformer_label}` es el mejor transformer standalone vigente.",
        "- El híbrido final congelado en `dev` no maximiza la métrica agregada, pero ofrece mayor trazabilidad sobre parte de la señal clínica.",
        "",
        "## Métricas comparables en `dev`",
        metrics_df.to_markdown(index=False),
        "",
        "## Qué aporta cada enfoque",
        "### TF-IDF",
        "- Recupera bien casos donde la nota usa marcas textuales explícitas del cuadro.",
        "- Su fortaleza metodológica es la simplicidad: sirve como baseline fuerte y difícil de ignorar.",
        "",
        f"### {transformer_label}",
        "- Es el mejor transformer standalone sobre `dev`.",
        "- Añade contexto semántico sobre el texto, pero sigue dependiendo de lo que la consulta explicita verbalmente.",
        "",
        "### Híbrido final",
        "- Articula reglas clínicas auditables con backbone contextual y selección de señales menos problemáticas.",
        "- En el estado actual capta especialmente más casos de `depresion`, pero con menor equilibrio interclase que las mejores líneas base textuales.",
        "",
        "## Por qué el híbrido puede acertar más casos totales y no ganar en macro_f1",
        "- El `dev` está desbalanceado a favor de `depresion`.",
        "- El híbrido final concentra más aciertos en `depresion` y menos en `ansiedad`.",
        "- `macro_f1` penaliza ese desequilibrio entre clases, por eso sigue siendo una métrica más defendible que el conteo bruto de aciertos.",
        "",
        "## Lectura metodológica final",
        f"- La comparación final razonable no es entre dos Transformers, sino entre un baseline simple fuerte (`TF-IDF`), el mejor transformer standalone (`{transformer_label}`) y el mejor híbrido final congelado en `dev`.",
    ]
    return "\n".join(lines) + "\n"


def build_reusable_cases(curated_errors: pd.DataFrame) -> pd.DataFrame:
    out = curated_errors.copy()
    out = out.rename(columns={"prediccion_modelo": "prediccion_modelo_final"})
    keep = [
        "row_id", "etiqueta_original", "prediccion_modelo_final", "tipo_caso", "tipo_de_error",
        "sospecha_etiquetado", "relevante_para_ips", "relevante_para_xai", "relevante_para_reporte", "comentario",
    ]
    return out[keep].sort_values(by=["tipo_caso", "row_id"]).reset_index(drop=True)


def build_context(source_dir: Path, output_dir: Path, summary_path: Path) -> ContextoCuracion:
    manifest_path = source_dir / "material_validacion_ips_manifest.json"
    manifest = read_json(manifest_path)

    preproc_csv = pd.read_csv(source_dir / "material_ips_preprocesamiento_resumen.csv")
    balance_csv = pd.read_csv(source_dir / "material_ips_balance_dataset.csv")
    errors_df = pd.read_csv(source_dir / "material_ips_errores_modelo.csv")
    comparison_df = pd.read_csv(source_dir / "comparacion_aportes_modelos.csv")
    dev_df = pd.read_csv(DATA_DIR / "splits" / "dev_denoised.csv")
    transformer_label = str(manifest["transformer_standalone"]).strip()
    tfidf_pred = load_prediction(DATA_DIR / "tfidf_predicciones_dev.csv").merge(dev_df[["row_id", "texto"]], on="row_id", how="left")
    transformer_pred = load_prediction(ROOT / manifest["transformer_pred_relpath"]).merge(dev_df[["row_id", "texto"]], on="row_id", how="left")
    hybrid_pred = load_prediction(ROOT / manifest["hybrid_pred_relpath"]).merge(dev_df[["row_id", "texto"]], on="row_id", how="left")
    features_df = pd.read_csv(ROOT / manifest["feature_table_relpath"])

    return ContextoCuracion(
        source_dir=source_dir,
        output_dir=output_dir,
        manifest=manifest,
        source_manifest_path=manifest_path,
        summary_path=summary_path,
        preproc_csv=preproc_csv,
        balance_csv=balance_csv,
        errors_df=errors_df,
        comparison_df=comparison_df,
        dev_df=dev_df,
        transformer_label=transformer_label,
        tfidf_pred=tfidf_pred,
        transformer_pred=transformer_pred,
        hybrid_pred=hybrid_pred,
        features_df=features_df,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Curar un dossier clínico reutilizable a partir del paquete vigente de revisión externa.")
    parser.add_argument("--source-dir", type=Path, default=None, help="Paquete fuente `material_validacion_ips_*`. Si no se define, usa el más reciente.")
    parser.add_argument("--output-tag", type=str, default=None, help="Tag opcional para reemplazar el timestamp en la carpeta de salida.")
    parser.add_argument("--verbose", action="store_true", help="Imprime detalles de resolución.")
    args = parser.parse_args()

    source_dir = args.source_dir.resolve() if args.source_dir else resolve_latest_source_dir()
    output_dir, suffix = resolve_output_dir(args.output_tag)
    summary_path = OUTPUTS_DIR / f"curacion_dossier_ips_{suffix}.md"

    ctx = build_context(source_dir, output_dir, summary_path)
    if args.verbose:
        print(f"Paquete fuente: {ctx.source_dir}")
        print(f"Salida curada: {ctx.output_dir}")

    metrics_df = build_metrics_table(ctx.tfidf_pred, ctx.transformer_pred, ctx.hybrid_pred, ctx.transformer_label)

    anxiety_terms = {
        "TF-IDF": top_filtered_terms(ctx.tfidf_pred, "ansiedad", "ansiedad"),
        ctx.transformer_label: top_filtered_terms(ctx.transformer_pred, "ansiedad", "ansiedad"),
        "HIBRIDO_FINAL": top_filtered_terms(ctx.hybrid_pred, "ansiedad", "ansiedad"),
    }
    depression_terms = {
        "TF-IDF": top_filtered_terms(ctx.tfidf_pred, "depresion", "depresion"),
        ctx.transformer_label: top_filtered_terms(ctx.transformer_pred, "depresion", "depresion"),
        "HIBRIDO_FINAL": top_filtered_terms(ctx.hybrid_pred, "depresion", "depresion"),
    }
    anxiety_rules = build_rule_counts(ctx.features_df, ctx.hybrid_pred, ctx.dev_df, "ansiedad")
    depression_rules = build_rule_counts(ctx.features_df, ctx.hybrid_pred, ctx.dev_df, "depresion")
    anxiety_categories = summarize_categories("ansiedad", anxiety_terms, anxiety_rules)
    depression_categories = summarize_categories("depresion", depression_terms, depression_rules)

    curated_errors = select_curated_errors(build_error_frame(ctx.errors_df))
    reusable_cases = build_reusable_cases(curated_errors)

    files_to_write = {
        "dossier_ips_patrones_ansiedad.md": render_pattern_doc_brief("ansiedad", anxiety_categories, ctx.transformer_label),
        "dossier_ips_patrones_depresion.md": render_pattern_doc_brief("depresion", depression_categories, ctx.transformer_label),
        "patrones_clinicos_ansiedad_ampliado.md": render_pattern_doc_ampliado("ansiedad", anxiety_categories, anxiety_rules, anxiety_terms, ctx.transformer_label),
        "patrones_clinicos_depresion_ampliado.md": render_pattern_doc_ampliado("depresion", depression_categories, depression_rules, depression_terms, ctx.transformer_label),
        "dossier_ips_comparacion_modelos.md": render_model_comparison_ips(metrics_df, ctx.comparison_df, ctx.transformer_label, ctx.manifest["backbone_hibrido"]),
        "analisis_comparativo_modelos_ampliado.md": render_model_comparison_ampliado(metrics_df, ctx.comparison_df, ctx.transformer_label),
        "dossier_ips_errores_curados.md": render_curated_errors_md(curated_errors),
        "dossier_ips_preguntas_finales.md": render_questions_md(),
        "preguntas_bibliografia_validacion_clinica_v2.md": render_preguntas_bibliografia_v2(),
    }
    for name, content in files_to_write.items():
        (output_dir / name).write_text(content, encoding="utf-8")

    curated_errors.to_csv(output_dir / "dossier_ips_errores_curados.csv", index=False)
    reusable_cases.to_csv(output_dir / "casos_clinicos_reutilizables_xai.csv", index=False)

    dossier_manifest = {
        "source_dir": str(ctx.source_dir),
        "output_dir": str(output_dir),
        "source_manifest": str(ctx.source_manifest_path),
        "cierre_dir": ctx.manifest["cierre_dir"],
        "error_dir": ctx.manifest["error_dir"],
        "train_run_referencia": ctx.manifest["train_run_referencia"],
        "feature_run_referencia": ctx.manifest["feature_run_referencia"],
        "transformer_standalone": ctx.manifest["transformer_standalone"],
        "backbone_hibrido": ctx.manifest["backbone_hibrido"],
        "modelo_hibrido_final": ctx.manifest["modelo_hibrido_final"],
        "test_estado": ctx.manifest["test_estado"],
        "xai_estado": ctx.manifest["xai_estado"],
        "n_casos_curados": int(len(curated_errors)),
    }
    write_json(output_dir / "dossier_ips_curado_manifest.json", dossier_manifest)
    write_json(OUTPUTS_DIR / "dossier_ips_curado_latest.json", dossier_manifest)

    summary_text = render_curacion_summary(ctx, output_dir, curated_errors)
    summary_path.write_text(summary_text, encoding="utf-8")

    print(f"Paquete curado generado en: {output_dir}")
    print(f"Resumen de curación: {summary_path}")


if __name__ == "__main__":
    main()
