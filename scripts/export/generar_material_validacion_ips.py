#!/usr/bin/env python3
"""
Genera material clínico reutilizable para revisión clínica externa.

Usa únicamente artefactos ya existentes del proyecto en desarrollo.
No reentrena modelos ni toca `test`.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer


STOP_WORDS = [
    "de", "la", "que", "el", "en", "y", "a", "los", "se", "del", "las", "un", "por", "con", "no", "una",
    "su", "para", "es", "al", "lo", "como", "mas", "pero", "sus", "le", "ya", "o", "fue", "este", "ha",
    "me", "si", "sin", "sobre", "tambien", "hasta", "son", "mi", "tu", "mc", "dx", "imp", "plan", "sic",
]

FOLLOW_UP_RE = re.compile(
    r"\b(control|seguimiento|reposicion|reposición|misma medicacion|misma medicación|sin cambios|control posterior|ambulatorio)\b",
    flags=re.IGNORECASE,
)
MEDICAL_OVERLAP_RE = re.compile(
    r"\b(colitis|corticoides|prednisona|hta|cardio|laboratorio|ecg|renal|hepat|neurolog|cefalea|vertig|orl|urol|ginec|edema|hormona|litio|dolor)\b",
    flags=re.IGNORECASE,
)

ANXIETY_HINTS = [
    "ansiedad", "angustia", "miedo", "temor", "panico", "pánico", "inquiet", "crisis", "catastrof",
    "taquipsiqu", "compulsion", "obsesi",
]
DEPRESSION_HINTS = [
    "animo", "ánimo", "anhedonia", "abulia", "apata", "apatía", "bajaener", "fatiga", "culpa",
    "desesperanza", "triste", "llanto", "autoles", "suic", "bajaconcentr",
]


@dataclass
class ContextoProyecto:
    repo_root: Path
    data_dir: Path
    outputs_dir: Path
    processed_dir: Path
    cierre_dir: Path
    decision: dict[str, Any]
    ranking_df: pd.DataFrame
    final_row: pd.Series
    error_dir: Path
    error_payload: dict[str, Any]
    transformer_payload: dict[str, Any]
    backbone_payload: dict[str, Any]


def now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_label(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def safe_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_dirs(base: Path, pattern: str) -> list[Path]:
    return sorted([p for p in base.glob(pattern) if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)


def latest_files(base: Path, pattern: str) -> list[Path]:
    return sorted([p for p in base.glob(pattern) if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find_latest_cierre(outputs_dir: Path) -> tuple[Path, dict[str, Any]]:
    for d in latest_dirs(outputs_dir, "cierre_modelos_dev_*"):
        decision_path = d / "decision_modelo_final.json"
        ranking_path = d / "ranking_modelos_dev.csv"
        if decision_path.exists() and ranking_path.exists():
            payload = safe_json(decision_path)
            if str(payload.get("split_decision", "")).lower() == "dev":
                return d, payload
    raise FileNotFoundError("No se encontró un cierre formal vigente en dev.")


def _find_error_dir(outputs_dir: Path, train_run_id: str) -> tuple[Path, dict[str, Any]]:
    for d in latest_dirs(outputs_dir, "error_analysis_*"):
        p = d / "resumen_error_analysis.json"
        if not p.exists():
            continue
        payload = safe_json(p)
        if payload.get("train_run_id_origen") == train_run_id:
            return d, payload
    raise FileNotFoundError(f"No se encontró error_analysis alineado con train_run_id={train_run_id}.")


def resolver_contexto(repo_root: Path) -> ContextoProyecto:
    data_dir = repo_root / "data"
    outputs_dir = data_dir / "outputs"
    processed_dir = data_dir / "processed"

    cierre_dir, decision = _find_latest_cierre(outputs_dir)
    ranking_df = pd.read_csv(cierre_dir / "ranking_modelos_dev.csv")
    final_variant = decision["modelo_hibrido_final"]["modelo_variante"]
    final_rows = ranking_df[ranking_df["modelo_variante"].astype(str) == str(final_variant)].copy()
    if final_rows.empty:
        raise ValueError("No se encontró la fila del modelo final dentro del ranking vigente.")
    final_row = final_rows.iloc[0]

    train_run_id = str(final_row["run_id_train_referencia"])
    error_dir, error_payload = _find_error_dir(outputs_dir, train_run_id)

    transformer_path = outputs_dir / "transformer_baseline_selection_latest.json"
    backbone_path = outputs_dir / "comparacion_backbones_hibrido_latest.json"
    if not transformer_path.exists():
        raise FileNotFoundError("No existe transformer_baseline_selection_latest.json.")
    if not backbone_path.exists():
        raise FileNotFoundError("No existe comparacion_backbones_hibrido_latest.json.")

    return ContextoProyecto(
        repo_root=repo_root,
        data_dir=data_dir,
        outputs_dir=outputs_dir,
        processed_dir=processed_dir,
        cierre_dir=cierre_dir,
        decision=decision,
        ranking_df=ranking_df,
        final_row=final_row,
        error_dir=error_dir,
        error_payload=error_payload,
        transformer_payload=safe_json(transformer_path),
        backbone_payload=safe_json(backbone_path),
    )


def top_terms(texts: list[str], top_k: int = 12) -> list[tuple[str, int]]:
    texts = [str(t) for t in texts if isinstance(t, str) and str(t).strip()]
    if not texts:
        return []
    vec = CountVectorizer(ngram_range=(1, 1), stop_words=STOP_WORDS, min_df=1)
    bag = vec.fit_transform(texts)
    freqs = bag.sum(axis=0).A1
    terms = vec.get_feature_names_out()
    order = freqs.argsort()[::-1]
    return [(str(terms[i]), int(freqs[i])) for i in order[:top_k] if freqs[i] > 0]


def humanize_signal(name: str) -> str:
    text = str(name)
    text = re.sub(r"^(rule_|niega_)", "", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ").strip()
    replacements = {
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
    return replacements.get(text, text)


def classify_balance(dist: dict[str, int]) -> str:
    total = sum(dist.values())
    if not total:
        return "sin_datos"
    major = max(dist.values()) / total
    if major < 0.60:
        return "balanceado"
    if major < 0.67:
        return "moderadamente_desbalanceado"
    return "claramente_desbalanceado"


def load_predictions(path: Path, alias: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    keep = [c for c in ["row_id", "y_true", "y_pred", "prob_ansiedad", "prob_depresion"] if c in df.columns]
    out = df[keep].copy()
    out["row_id"] = out["row_id"].astype(int)
    out["modelo"] = alias
    return out


def _baseline_prediction_path(data_dir: Path, model_variant: str) -> Path:
    slug = str(model_variant).strip().lower()
    return data_dir / f"{slug}_predicciones_dev.csv"


def _hybrid_prediction_path(outputs_dir: Path, train_run: str, final_row: pd.Series) -> Path:
    profile = str(final_row["perfil"]).strip().lower()
    model = str(final_row["modelo"]).strip().lower()
    return outputs_dir / train_run / f"predicciones_{profile}_{model}_dev.csv"


def _feature_table_path(processed_dir: Path, feature_run: str) -> Path:
    run_id = str(feature_run).strip()
    if run_id.endswith("_core"):
        suffix = "core"
    elif run_id.endswith("_py"):
        suffix = "py"
    else:
        suffix = "py"
    return processed_dir / run_id / f"features_{suffix}.csv"


def _xcols_path(outputs_dir: Path, train_run: str, final_row: pd.Series) -> Path:
    profile = str(final_row["perfil"]).strip().lower()
    return outputs_dir / train_run / f"{profile}_X_cols.json"


def summarize_signal_sets(signals: list[str]) -> tuple[bool, bool]:
    low = " | ".join(signals).lower()
    has_anxiety = any(k in low for k in ANXIETY_HINTS)
    has_depression = any(k in low for k in DEPRESSION_HINTS)
    return has_anxiety, has_depression


def build_hypothesis(tags: list[str], y_true: str, y_pred: str) -> str:
    if "seguimiento_administrativo" in tags:
        return "La nota parece de control/seguimiento con baja fenomenología activa; conviene revisar si la etiqueta representa el episodio actual o el antecedente global."
    if "solapamiento_medico" in tags:
        return "La fenomenología psiquiátrica aparece mezclada con clínica médica o efectos de tratamiento, lo que reduce especificidad diagnóstica."
    if "frontera_ambigua" in tags and "solapamiento_sintomatico" in tags:
        return "La consulta mezcla señales compatibles con ambos polos y el modelo quedó cerca de la frontera de decisión."
    if "frontera_ambigua" in tags:
        return "La predicción quedó cerca del umbral; el error puede reflejar baja separabilidad diagnóstica en la consulta."
    if y_true == "ansiedad" and y_pred == "depresion":
        return "El modelo priorizó señales depresivas o de enlentecimiento sobre un cuadro rotulado como ansiedad."
    if y_true == "depresion" and y_pred == "ansiedad":
        return "El modelo priorizó activación ansiosa, somatización o preocupación sobre un cuadro rotulado como depresión."
    return "Caso que requiere revisión clínica específica."


def build_question(tags: list[str], y_true: str, y_pred: str) -> str:
    if "seguimiento_administrativo" in tags:
        return "¿Esta nota debería considerarse diagnóstica o corresponde más bien a seguimiento/gestión del tratamiento?"
    if "solapamiento_medico" in tags:
        return "¿La fenomenología principal aquí es psiquiátrica o está dominada por enfermedad médica/medicación?"
    if "solapamiento_sintomatico" in tags:
        return "¿La consulta expresa ansiedad, depresión o un solapamiento clínico difícil de separar con esta nota sola?"
    if "frontera_ambigua" in tags:
        return "¿La etiqueta de esta consulta es suficientemente específica o debería marcarse como caso de baja separabilidad clínica?"
    if y_true == "ansiedad" and y_pred == "depresion":
        return "¿Qué señal clínica justificaría sostener ansiedad como etiqueta principal en esta nota?"
    if y_true == "depresion" and y_pred == "ansiedad":
        return "¿Qué señal clínica justificaría sostener depresión como etiqueta principal en esta nota?"
    return "¿Qué parte de esta consulta conviene revisar con mayor detalle?"


def write_markdown(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def export_markdown_table(path: Path, title: str, intro: str, df: pd.DataFrame) -> None:
    lines = [f"# {title}", "", intro, "", df.to_markdown(index=False)]
    write_markdown(path, lines)


def generar_material(output_dir: Path, verbose: bool = False) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    ctx = resolver_contexto(repo_root)
    ensure_dir(output_dir)

    raw = pd.read_csv(ctx.data_dir / "ips_raw.csv")
    raw["etiqueta_norm"] = raw["Tipo"].map(normalize_label)
    base = pd.read_csv(ctx.data_dir / "dataset_with_clinical_signal_flag.csv")
    base["etiqueta"] = base["etiqueta"].map(normalize_label)
    dataset_base = pd.read_csv(ctx.data_dir / "splits" / "dataset_base.csv")
    dataset_denoised = pd.read_csv(ctx.data_dir / "dataset_denoised.csv")
    train = pd.read_csv(ctx.data_dir / "splits" / "train_denoised.csv")
    dev = pd.read_csv(ctx.data_dir / "splits" / "dev_denoised.csv")
    test = pd.read_csv(ctx.data_dir / "splits" / "test_denoised.csv")
    clean = pd.read_csv(ctx.data_dir / "ips_clean.csv")

    # Resumen de preprocesamiento
    raw_dist = raw["etiqueta_norm"].value_counts().to_dict()
    final_dist = dataset_denoised["etiqueta"].value_counts().to_dict()
    template_n = int(dataset_base["feat_had_template_block"].sum())
    no_signal_n = int((~base["has_clinical_signal"].astype(bool)).sum())
    resumen_pre = pd.DataFrame([
        {
            "etapa": "original_crudo",
            "n_registros": int(len(raw)),
            "n_pacientes": int(raw["Prontuario"].nunique()),
            "delta_registros": 0,
            "observacion": "Carga inicial previa a deduplicación y limpieza de plantilla.",
        },
        {
            "etapa": "post_deduplicacion_base",
            "n_registros": int(len(dataset_base)),
            "n_pacientes": int(dataset_base["patient_id"].nunique()),
            "delta_registros": int(len(dataset_base) - len(raw)),
            "observacion": "Se eliminaron duplicados completos; la plantilla administrativa se depuró dentro de la nota.",
        },
        {
            "etapa": "notas_con_plantilla_administrativa",
            "n_registros": template_n,
            "n_pacientes": int(dataset_base.loc[dataset_base["feat_had_template_block"] == 1, "patient_id"].nunique()),
            "delta_registros": 0,
            "observacion": "No son notas eliminadas por sí mismas; la plantilla se limpia y luego se evalúa si queda señal clínica.",
        },
        {
            "etapa": "eliminadas_sin_senal_clinica_util",
            "n_registros": no_signal_n,
            "n_pacientes": int(base.loc[~base["has_clinical_signal"].astype(bool), "patient_id"].nunique()),
            "delta_registros": -no_signal_n,
            "observacion": "Descarte posterior a denoising y lógica de aseveración clínica.",
        },
        {
            "etapa": "dataset_final_post_filtrado",
            "n_registros": int(len(dataset_denoised)),
            "n_pacientes": int(dataset_denoised["patient_id"].nunique()),
            "delta_registros": int(len(dataset_denoised) - len(raw)),
            "observacion": "Universo final modelado en train/dev/test denoised.",
        },
    ])
    resumen_pre_path = output_dir / "material_ips_preprocesamiento_resumen.csv"
    resumen_pre.to_csv(resumen_pre_path, index=False)

    example_clean = dataset_base.loc[dataset_base["feat_had_template_block"] == 1].iloc[0]
    patient_id = int(example_clean["patient_id"])
    cleaned_text = str(example_clean["texto"])
    raw_match = raw[raw["Prontuario"] == patient_id].copy()
    raw_match["contains_clean"] = raw_match["Motivo Consulta"].astype(str).str.contains(re.escape(cleaned_text[:25]), regex=True, na=False)
    if raw_match["contains_clean"].any():
        raw_example = raw_match[raw_match["contains_clean"]].iloc[0]
    else:
        raw_example = raw_match.iloc[0]
    removed_example = base.loc[~base["has_clinical_signal"].astype(bool)].iloc[0]

    md_lines = [
        "# Resumen de preprocesamiento para IPS",
        "",
        "## Conteos principales",
        "",
        resumen_pre.to_markdown(index=False),
        "",
        "## Distribución por clase",
        f"- Antes del filtrado (crudo): {raw_dist}",
        f"- Después del filtrado clínico: {final_dist}",
        "",
        "## Aclaración metodológica",
        "- La plantilla administrativa no dispara por sí sola la eliminación de la nota.",
        "- Primero se limpia el bloque plantilla dentro del texto.",
        "- El descarte ocurre cuando, después de la limpieza y del denoising con reglas de aseveración, no queda señal clínica útil.",
        "",
        "## Ejemplos",
        "### Texto crudo",
        str(raw_example["Motivo Consulta"])[:1200],
        "",
        "### Texto limpiado",
        cleaned_text[:1200],
        "",
        "### Texto eliminado y motivo",
        str(removed_example["texto"])[:800],
        "",
        "- Motivo de exclusión sugerido: consulta de reposición/seguimiento sin señal clínica suficiente tras depuración.",
    ]
    write_markdown(output_dir / "material_ips_preprocesamiento_resumen.md", md_lines)

    # Balance / desbalance
    split_rows = []
    for split_name, df in [("global_base", dataset_base), ("global_post_filtrado", dataset_denoised), ("train", train), ("dev", dev), ("test", test)]:
        dist = df["etiqueta"].value_counts().to_dict()
        total = int(len(df))
        split_rows.append(
            {
                "split": split_name,
                "n_total": total,
                "ansiedad_n": int(dist.get("ansiedad", 0)),
                "depresion_n": int(dist.get("depresion", 0)),
                "ansiedad_prop": round(dist.get("ansiedad", 0) / total, 4) if total else 0.0,
                "depresion_prop": round(dist.get("depresion", 0) / total, 4) if total else 0.0,
                "clasificacion_balance": classify_balance(dist),
            }
        )
    balance_df = pd.DataFrame(split_rows)
    balance_df.to_csv(output_dir / "material_ips_balance_dataset.csv", index=False)
    balance_md = [
        "# Balance y desbalance del dataset",
        "",
        balance_df.to_markdown(index=False),
        "",
        "## Lectura metodológica",
        f"- En el corte actual el problema queda `{classify_balance(final_dist)}` en el dataset final modelado.",
        "- La clase mayoritaria es `depresion`; la menor, `ansiedad`.",
        "- Por esta razón se priorizan `macro_f1`, `balanced_accuracy` y F1 por clase en lugar de depender solo de accuracy.",
        "",
        "## Cómo se trató el desbalance",
        "- `TF-IDF` usa `class_weight='balanced'` en `LinearSVC`.",
        "- `RandomForest` usa `class_weight='balanced'`.",
        "- `XGBoost` no muestra reponderación explícita de clases ni sampling adicional en el notebook vigente.",
        "- No se detectó resampling/oversampling en el pipeline de desarrollo.",
        "- Los transformers baseline se comparan sobre el mismo `dev_denoised`; no se documenta sampling explícito en 04c.",
    ]
    write_markdown(output_dir / "material_ips_balance_dataset.md", balance_md)

    # Hecho vs pendiente
    hecho_vs_pendiente = [
        "# Qué se hizo y qué no se hizo todavía",
        "",
        "## Se hizo",
        "- limpieza de duplicados",
        "- filtrado de plantillas administrativas dentro de la nota",
        "- remoción de notas sin señal clínica útil",
        "- split por paciente",
        "- comparación entre baselines e híbridos",
        f"- selección del mejor transformer standalone (`{ctx.transformer_payload['mejor_transformer_baseline']['modelo']}`)",
        f"- selección del backbone del híbrido (`{ctx.backbone_payload.get('backbone_ganador', 'beto')}`)",
        "- cierre formal del mejor modelo en `dev`",
        "- análisis de errores alineado al modelo final",
        "",
        "## No se hizo todavía",
        "- validación clínica final con IPS",
        "- reetiquetado experto consulta por consulta",
        "- incorporación de grupo de control",
        "- evaluación final en `test`",
        "- xAI final",
    ]
    write_markdown(output_dir / "material_ips_hecho_vs_pendiente.md", hecho_vs_pendiente)

    # Predicciones y patrones
    final_train_run = str(ctx.final_row["run_id_train_referencia"])
    transformer_label = str(ctx.decision["mejor_transformer_baseline_dev"]["modelo_variante"]).strip()
    pred_paths = {
        "TF-IDF": ctx.data_dir / "tfidf_predicciones_dev.csv",
        transformer_label: _baseline_prediction_path(ctx.data_dir, transformer_label),
        "HIBRIDO_FINAL": _hybrid_prediction_path(ctx.outputs_dir, final_train_run, ctx.final_row),
    }
    preds = {name: load_predictions(path, name) for name, path in pred_paths.items()}
    dev_text = dev[["row_id", "patient_id", "etiqueta", "texto"]].copy()
    dev_text["row_id"] = dev_text["row_id"].astype(int)

    feature_run = str(ctx.final_row["run_id_features"])
    feat_path = _feature_table_path(ctx.processed_dir, feature_run)
    features_df = pd.read_csv(feat_path)
    xcols_path = _xcols_path(ctx.outputs_dir, final_train_run, ctx.final_row)
    selected_cols = json.loads(xcols_path.read_text(encoding="utf-8"))
    signal_cols = [c for c in selected_cols if c.startswith("rule_") or c.startswith("niega_")]

    pattern_rows = []
    for model_name, pred_df in preds.items():
        merged = pred_df.merge(dev_text, on="row_id", how="left")
        for clase in ["ansiedad", "depresion"]:
            tp = merged[(merged["y_true"] == clase) & (merged["y_pred"] == clase)].copy()
            for term, count in top_terms(tp["texto"].tolist(), top_k=12):
                pattern_rows.append(
                    {
                        "modelo": model_name,
                        "clase": clase,
                        "fuente_patron": "texto_tp",
                        "patron": term,
                        "conteo": count,
                    }
                )

    # Señales del híbrido final a partir de reglas/negaciones activas
    hybrid_tp = preds["HIBRIDO_FINAL"].merge(features_df[["row_id"] + signal_cols], on="row_id", how="left")
    for clase in ["ansiedad", "depresion"]:
        tp = hybrid_tp[(hybrid_tp["y_true"] == clase) & (hybrid_tp["y_pred"] == clase)].copy()
        if tp.empty:
            continue
        means = tp[signal_cols].fillna(0).mean().sort_values(ascending=False)
        top_signals = means[means > 0].head(12)
        for sig, val in top_signals.items():
            pattern_rows.append(
                {
                    "modelo": "HIBRIDO_FINAL",
                    "clase": clase,
                    "fuente_patron": "senial_regla_tp",
                    "patron": humanize_signal(sig),
                    "conteo": round(float(val), 4),
                }
            )

    patterns_df = pd.DataFrame(pattern_rows)
    for clase in ["ansiedad", "depresion"]:
        dfc = patterns_df[patterns_df["clase"] == clase].copy()
        csv_path = output_dir / f"material_ips_patrones_{clase}.csv"
        md_path = output_dir / f"material_ips_patrones_{clase}.md"
        dfc.to_csv(csv_path, index=False)
        lines = [
            f"# Patrones asociados a {clase}",
            "",
            f"Resumen por modelo sobre verdaderos positivos en `dev` para `{clase}`.",
            "",
        ]
        for model_name in ["TF-IDF", transformer_label, "HIBRIDO_FINAL"]:
            sub = dfc[dfc["modelo"] == model_name]
            if sub.empty:
                continue
            lines.append(f"## {model_name}")
            for fuente in ["texto_tp", "senial_regla_tp"]:
                src = sub[sub["fuente_patron"] == fuente]
                if src.empty:
                    continue
                etiqueta = "Términos recurrentes" if fuente == "texto_tp" else "Señales clínicas/reglas activas"
                vals = ", ".join(src["patron"].astype(str).head(10).tolist())
                lines.append(f"- {etiqueta}: {vals}")
            lines.append("")
        write_markdown(md_path, lines)

    # Comparación de aportes entre modelos
    joined = None
    for model_name, pred_df in preds.items():
        base_cols = pred_df[["row_id", "y_true", "y_pred"]].copy()
        base_cols = base_cols.rename(columns={"y_pred": f"y_pred_{model_name}"})
        base_cols[f"correcto_{model_name}"] = (pred_df["y_true"].astype(str) == pred_df["y_pred"].astype(str)).astype(int)
        joined = base_cols if joined is None else joined.merge(base_cols, on=["row_id", "y_true"], how="inner")

    comp_rows = []
    correct_sets = {}
    for model_name in preds:
        mask = joined[f"correcto_{model_name}"] == 1
        correct_sets[model_name] = set(joined.loc[mask, "row_id"].astype(int).tolist())
        comp_rows.append({"tipo": "correctos_total", "modelo_a": model_name, "modelo_b": "", "clase": "todas", "n_casos": int(mask.sum()), "detalle": ""})
        for clase in ["ansiedad", "depresion"]:
            m = mask & (joined["y_true"] == clase)
            comp_rows.append({"tipo": "correctos_por_clase", "modelo_a": model_name, "modelo_b": "", "clase": clase, "n_casos": int(m.sum()), "detalle": ""})

    for a, b in combinations(preds.keys(), 2):
        inter = correct_sets[a] & correct_sets[b]
        comp_rows.append({"tipo": "interseccion_correctos", "modelo_a": a, "modelo_b": b, "clase": "todas", "n_casos": len(inter), "detalle": ""})
        for clase in ["ansiedad", "depresion"]:
            sub = joined[joined["y_true"] == clase]
            ca = set(sub.loc[sub[f"correcto_{a}"] == 1, "row_id"].astype(int).tolist())
            cb = set(sub.loc[sub[f"correcto_{b}"] == 1, "row_id"].astype(int).tolist())
            comp_rows.append({"tipo": "interseccion_correctos", "modelo_a": a, "modelo_b": b, "clase": clase, "n_casos": len(ca & cb), "detalle": ""})

    all_three = set.intersection(*correct_sets.values())
    comp_rows.append({"tipo": "interseccion_correctos", "modelo_a": "TF-IDF", "modelo_b": f"{transformer_label}|HIBRIDO_FINAL", "clase": "todas", "n_casos": len(all_three), "detalle": "Casos que aciertan los tres modelos."})

    dev_join = dev_text[["row_id", "texto", "etiqueta"]].copy()
    for model_name in preds:
        other_sets = set().union(*[correct_sets[m] for m in preds if m != model_name])
        unique_ids = sorted(correct_sets[model_name] - other_sets)
        comp_rows.append({"tipo": "solo_modelo", "modelo_a": model_name, "modelo_b": "", "clase": "todas", "n_casos": len(unique_ids), "detalle": ""})
        unique_df = dev_join[dev_join["row_id"].isin(unique_ids)]
        for clase in ["ansiedad", "depresion"]:
            unique_cls = unique_df[unique_df["etiqueta"] == clase]
            terms = top_terms(unique_cls["texto"].tolist(), top_k=6)
            detail = ", ".join([t for t, _ in terms]) if terms else ""
            comp_rows.append({"tipo": "solo_modelo", "modelo_a": model_name, "modelo_b": "", "clase": clase, "n_casos": int(len(unique_cls)), "detalle": detail})

    comp_df = pd.DataFrame(comp_rows)
    comp_df.to_csv(output_dir / "comparacion_aportes_modelos.csv", index=False)
    comp_md = [
        "# Comparación de aportes entre modelos",
        "",
        f"Modelos comparados: `TF-IDF`, `{transformer_label}` y `HIBRIDO_FINAL` sobre el mismo `dev_denoised`.",
        "",
        "## Lectura rápida",
        f"- Mejor baseline simple fuerte: `TF-IDF` ({float(ctx.ranking_df.loc[ctx.ranking_df['modelo_variante'] == 'TF-IDF', 'macro_f1_mean'].iloc[0]):.4f}).",
        f"- Mejor transformer standalone: `{ctx.decision['mejor_transformer_baseline_dev']['modelo_variante']}`.",
        f"- Híbrido final congelado en dev: `{ctx.decision['modelo_hibrido_final']['modelo_variante']}`.",
        "",
        comp_df.to_markdown(index=False),
        "",
        "## Interpretación mínima",
        "- Si dos modelos comparten muchos aciertos, probablemente están captando un núcleo sintomático parecido.",
        "- Si un modelo conserva casos correctos exclusivos, aporta complementariedad clínica o textual.",
        "- El híbrido final debe leerse aquí no solo por métrica, sino por trazabilidad y señal clínica reutilizable.",
    ]
    write_markdown(output_dir / "comparacion_aportes_modelos.md", comp_md)

    # Material de errores para IPS
    pred_final = preds["HIBRIDO_FINAL"].copy()
    pred_final["margen_prob"] = (
        pred_final.get("prob_ansiedad", pd.Series([None] * len(pred_final))).fillna(0).astype(float)
        - pred_final.get("prob_depresion", pd.Series([None] * len(pred_final))).fillna(0).astype(float)
    ).abs()
    err = pred_final[pred_final["y_true"] != pred_final["y_pred"]].copy()
    err = err.merge(dev_text, on="row_id", how="left")
    err = err.merge(features_df[["row_id"] + signal_cols], on="row_id", how="left")
    err["split"] = "dev"

    rows_err = []
    for _, row in err.iterrows():
        active = []
        for col in signal_cols:
            try:
                val = float(row.get(col, 0) or 0)
            except Exception:
                val = 0.0
            if val > 0:
                active.append(humanize_signal(col))
        active = active[:8]
        tags = [f"{row['y_true']}→{row['y_pred']}"]
        if float(row.get("margen_prob", 1.0)) < 0.20:
            tags.append("frontera_ambigua")
        if FOLLOW_UP_RE.search(str(row.get("texto", ""))):
            tags.append("seguimiento_administrativo")
        if MEDICAL_OVERLAP_RE.search(str(row.get("texto", ""))):
            tags.append("solapamiento_medico")
        has_anx, has_dep = summarize_signal_sets(active)
        if has_anx and has_dep:
            tags.append("solapamiento_sintomatico")
        if len(str(row.get("texto", "")).split()) < 20:
            tags.append("nota_breve")

        rows_err.append(
            {
                "row_id": int(row["row_id"]),
                "etiqueta_original": str(row["y_true"]),
                "prediccion_modelo": str(row["y_pred"]),
                "split": "dev",
                "señales_detectadas": " | ".join(active),
                "tipo_de_error": "; ".join(tags),
                "hipotesis_clinica": build_hypothesis(tags, str(row["y_true"]), str(row["y_pred"])),
                "pregunta_para_IPS": build_question(tags, str(row["y_true"]), str(row["y_pred"])),
                "margen_prob": round(float(row.get("margen_prob", 0.0)), 4),
                "patient_id": int(row["patient_id"]) if pd.notna(row["patient_id"]) else None,
                "texto": str(row["texto"]),
            }
        )

    err_df = pd.DataFrame(rows_err)
    err_df.to_csv(output_dir / "material_ips_errores_modelo.csv", index=False)
    # Selección curada
    curado = pd.concat(
        [
            err_df[err_df["tipo_de_error"].str.contains("seguimiento_administrativo", na=False)].head(5),
            err_df[err_df["tipo_de_error"].str.contains("frontera_ambigua", na=False)].head(5),
            err_df[err_df["tipo_de_error"].str.contains("solapamiento_medico|solapamiento_sintomatico", na=False)].head(5),
        ],
        ignore_index=True,
    ).drop_duplicates(subset=["row_id"]).head(15)
    err_md = [
        "# Errores del modelo final para discusión con IPS",
        "",
        "La tabla completa está en `material_ips_errores_modelo.csv`.",
        "",
        f"- Total de errores analizados: {len(err_df)}",
        f"- Error global en dev: {float(ctx.error_payload['tasa_error_global']):.4f}",
        "",
        "## Casos curados para revisión clínica",
        curado[[
            "row_id",
            "etiqueta_original",
            "prediccion_modelo",
            "tipo_de_error",
            "señales_detectadas",
            "hipotesis_clinica",
            "pregunta_para_IPS",
        ]].to_markdown(index=False),
    ]
    write_markdown(output_dir / "material_ips_errores_modelo.md", err_md)

    # Preguntas para revisión clínica
    preguntas_ips = [
        "# Preguntas sugeridas para revisión clínica externa",
        "",
        "## Sobre señales clínicas",
        "- ¿Los patrones más recurrentes asociados a ansiedad y depresión tienen sentido clínico en estas notas de Paraguay?",
        "- ¿Hay señales locales, coloquialismos o abreviaturas clínicas que todavía estemos subcapturando?",
        "",
        "## Sobre errores y etiquetas",
        "- ¿Los errores ansiedad→depresion y depresión→ansiedad corresponden a error real del modelo o a consultas clínicamente ambiguas?",
        "- ¿Hay consultas de seguimiento donde la etiqueta global del paciente no coincide con la fenomenología de esa consulta puntual?",
        "- ¿Qué tipo de notas deberían considerarse poco diagnósticas o no apropiadas para esta tarea diferencial?",
        "",
        "## Sobre filtrado",
        "- ¿Los casos removidos como reposición/control sin señal clínica útil están bien excluidos o conviene rescatar alguno?",
        "- ¿La distinción entre negación del paciente y negación de plantilla/médico coincide con la práctica clínica?",
        "",
        "## Sobre futuros datos",
        "- ¿Sería viable obtener un grupo de control o más consultas con baja carga psiquiátrica para una fase posterior?",
        "- ¿Qué subconjunto de casos convendría reetiquetar primero si se decide una validación experta consulta por consulta?",
    ]
    write_markdown(output_dir / "preguntas_sugeridas_ips.md", preguntas_ips)

    # Justificación breve y preguntas bibliográficas
    justif = [
        "# Justificación metodológica y clínica",
        "",
        "- Mostrar el preprocesamiento y el filtrado importa porque el rendimiento depende del universo de notas realmente modelado, no solo del clasificador.",
        "- En un problema diferencial entre ansiedad y depresión, el desbalance afecta la lectura de las métricas; por eso conviene priorizar `macro_f1`, `balanced_accuracy` y F1 por clase.",
        "- Validar errores con psiquiatras importa porque parte del desacuerdo modelo-etiqueta puede reflejar baja separabilidad clínica de la consulta y no solo una falla algorítmica.",
        "- En esta fase sigue siendo razonable trabajar sin grupo de control porque la tarea actual es diferencial dentro de una población ya clínica; eso no elimina el valor de un grupo de control como extensión futura.",
        "- La validación clínica antes de abrir `test` ayuda a cerrar supuestos sobre señales relevantes, notas poco diagnósticas y posibles límites del etiquetado actual.",
    ]
    write_markdown(output_dir / "justificacion_metodologica_y_clinica.md", justif)

    preguntas_biblio = [
        "# Preguntas bibliográficas sugeridas sobre validación clínica",
        "",
        "- ¿Qué literatura clínica o de cNLP justifica revisar errores de clasificación con expertos antes de una evaluación final en hold-out?",
        "- ¿Qué evidencia existe sobre label noise o baja especificidad diagnóstica en notas de seguimiento dentro de EHR psiquiátricos?",
        "- ¿Cómo se discute en la literatura la diferencia entre etiqueta a nivel paciente y etiqueta a nivel consulta en tareas de fenotipado clínico?",
        "- ¿Qué argumentos metodológicos sostienen usar `macro_f1` y `balanced_accuracy` en tareas binarias desbalanceadas en salud mental?",
        "- ¿Qué se reporta sobre la utilidad y los límites de trabajar sin grupo de control en tareas diferenciales acotadas dentro de población clínica?",
        "- ¿Qué enfoques se usan para validar con expertos señales clínicas detectadas por modelos híbridos o reglas en EHR?",
        "- ¿Qué trabajos discuten cómo presentar ejemplos de error, ambigüedad clínica y consultas poco diagnósticas en reportes de cNLP clínico?",
    ]
    write_markdown(output_dir / "preguntas_bibliografia_validacion_clinica.md", preguntas_biblio)

    manifest = {
        "output_dir": str(output_dir),
        "cierre_dir": str(ctx.cierre_dir),
        "error_dir": str(ctx.error_dir),
        "train_run_referencia": final_train_run,
        "feature_run_referencia": feature_run,
        "transformer_standalone": transformer_label,
        "transformer_pred_relpath": str(pred_paths[transformer_label].relative_to(repo_root)),
        "hybrid_pred_relpath": str(pred_paths["HIBRIDO_FINAL"].relative_to(repo_root)),
        "feature_table_relpath": str(feat_path.relative_to(repo_root)),
        "hybrid_profile": str(ctx.final_row["perfil"]).strip().lower(),
        "hybrid_model": str(ctx.final_row["modelo"]).strip().lower(),
        "backbone_hibrido": (
            ctx.backbone_payload.get("backbone_ganador")
            or (ctx.backbone_payload.get("latest_valid_backbone_comparison") or {}).get("best_backbone")
        ),
        "modelo_hibrido_final": ctx.decision["modelo_hibrido_final"]["modelo_variante"],
        "test_estado": "pendiente",
        "xai_estado": "pendiente",
    }
    (output_dir / "material_validacion_ips_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (ctx.outputs_dir / "material_validacion_ips_latest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if verbose:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))

    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera material reutilizable para revisión clínica externa.")
    parser.add_argument("--output-tag", default="", help="Tag estable opcional para la carpeta de salida.")
    parser.add_argument("--verbose", action="store_true", help="Muestra un resumen de fuentes y salidas.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    outputs_dir = repo_root / "data" / "outputs"
    tag = args.output_tag.strip() or now_ts()
    out_dir = outputs_dir / f"material_validacion_ips_{tag}"
    manifest = generar_material(out_dir, verbose=args.verbose)
    print(json.dumps({"status": "ok", **manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
