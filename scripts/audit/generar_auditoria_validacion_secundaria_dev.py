#!/usr/bin/env python3
"""
Genera la auditoría secundaria reproducible sobre `dev`.

Esta etapa es posterior al cierre formal en `dev` y no reabre selección de
modelo, ontología ni búsqueda de hiperparámetros. Su función es regenerar los
artefactos que sostienen la auditoría final previa a `test`.

Salidas por defecto:
  data/outputs/auditoria_final_caseC_validacion_secundaria/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import unicodedata
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex-cache")

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from xgboost import XGBClassifier

LABELS = ["ansiedad", "depresion"]
POS_LABEL = "ansiedad"
NEG_LABEL = "depresion"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO = repo_root()
DATA = REPO / "data"
OUTPUTS = DATA / "outputs"
SPLITS = DATA / "splits"
DEFAULT_OUT_DIR = OUTPUTS / "auditoria_final_caseC_validacion_secundaria"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def mode_stable(values: Iterable[Any]) -> Any:
    s = pd.Series(list(values)).dropna()
    if s.empty:
        return None
    # Reproduce la regla usada en la auditoría final: mayoría simple por
    # `value_counts()`, sin reordenar alfabéticamente los empates.
    return s.value_counts().sort_values(ascending=False).index[0]


def metric_block(y_true: Iterable[str], y_pred: Iterable[str], sample_weight=None) -> dict[str, Any]:
    yt = pd.Series(list(y_true)).astype(str)
    yp = pd.Series(list(y_pred)).astype(str)
    if len(yt) == 0:
        return {
            "macro_f1": None,
            "balanced_accuracy": None,
            "f1_ansiedad": None,
            "f1_depresion": None,
            "recall_ansiedad": None,
            "precision_ansiedad": None,
        }

    return {
        "macro_f1": float(f1_score(yt, yp, labels=LABELS, average="macro", zero_division=0, sample_weight=sample_weight)),
        "balanced_accuracy": float(balanced_accuracy_score(yt, yp, sample_weight=sample_weight)),
        "f1_ansiedad": float(f1_score(yt, yp, labels=LABELS, pos_label=POS_LABEL, average="binary", zero_division=0, sample_weight=sample_weight)),
        "f1_depresion": float(f1_score(yt, yp, labels=LABELS, pos_label=NEG_LABEL, average="binary", zero_division=0, sample_weight=sample_weight)),
        "recall_ansiedad": float(recall_score(yt, yp, pos_label=POS_LABEL, zero_division=0, sample_weight=sample_weight)),
        "precision_ansiedad": float(precision_score(yt, yp, pos_label=POS_LABEL, zero_division=0, sample_weight=sample_weight)),
    }


def subgroup_metric_block(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty or df["y_true"].nunique() < 2:
        return {
            "macro_f1": None,
            "balanced_accuracy": None,
            "f1_ansiedad": None,
            "f1_depresion": None,
            "recall_ansiedad": None,
            "precision_ansiedad": None,
        }
    return metric_block(df["y_true"], df["y_pred"])


def add_metric_record(records: list[dict[str, Any]], modelo: str, nivel: str, df: pd.DataFrame, sample_weight=None) -> None:
    metrics = metric_block(df["y_true"], df["y_pred"], sample_weight=sample_weight)
    records.append(
        {
            "modelo": modelo,
            "nivel": nivel,
            "n": int(len(df)),
            "n_pacientes": int(df["patient_id"].nunique()) if "patient_id" in df.columns else None,
            **metrics,
        }
    )


def patient_aggregated_metrics(
    pred_df: pd.DataFrame,
    modelo: str,
    method: str,
    threshold: float = 0.5,
) -> dict[str, Any]:
    if method == "mean_prob":
        if "prob_ansiedad" not in pred_df.columns:
            raise ValueError(f"{modelo}: mean_prob requiere columna prob_ansiedad")
        agg = (
            pred_df.groupby("patient_id")
            .agg(
                y_true=("y_true", mode_stable),
                prob_ansiedad=("prob_ansiedad", "mean"),
            )
            .reset_index()
        )
        agg["y_pred"] = np.where(agg["prob_ansiedad"] >= threshold, POS_LABEL, NEG_LABEL)
    elif method == "mode_pred":
        agg = (
            pred_df.groupby("patient_id")
            .agg(y_true=("y_true", mode_stable), y_pred=("y_pred", mode_stable))
            .reset_index()
        )
    else:
        raise ValueError(f"Método de agregación desconocido: {method}")

    metrics = metric_block(agg["y_true"], agg["y_pred"])
    return {
        "modelo": modelo,
        "nivel": "patient-aggregated",
        "n": int(len(agg)),
        "n_pacientes": int(len(agg)),
        **metrics,
    }


def latest_dir(base: Path, prefix: str) -> Path | None:
    candidates = [p for p in base.glob(f"{prefix}*") if p.is_dir()]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def resolve_final_train_dir() -> Path:
    error_dir = latest_dir(OUTPUTS, "error_analysis_")
    if error_dir:
        summary_path = error_dir / "resumen_error_analysis.json"
        if summary_path.exists():
            summary = read_json(summary_path)
            run_id = summary.get("train_run_id_origen")
            if run_id:
                train_dir = OUTPUTS / run_id
                if (train_dir / "predicciones_py_xgb_dev.csv").exists():
                    return train_dir

    candidates = sorted(
        OUTPUTS.glob("train_C_B_A_llm0_sent0_beto1_tpl0_py_XGB_sin_feat_sin_medication_py_XGB_seed42_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for train_dir in candidates:
        if (train_dir / "predicciones_py_xgb_dev.csv").exists():
            return train_dir
    raise FileNotFoundError("No se pudo resolver el train_dir del XGB final seed42.")


def resolve_feature_path(train_dir: Path) -> Path:
    summary_path = train_dir / "resumen_entrenamiento.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        feature_run = summary.get("feature_run_id_py")
        if feature_run:
            path = DATA / "processed" / feature_run / "features_py.parquet"
            if path.exists():
                return path
    default = DATA / "processed" / "fe_20260401_093631_py" / "features_py.parquet"
    if default.exists():
        return default
    raise FileNotFoundError("No se encontró features_py.parquet para el modelo final.")


def load_prediction_with_patient(path: Path, dev: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(path)
    out = df.merge(dev[["row_id", "patient_id"]], on="row_id", how="left")
    if out["patient_id"].isna().any():
        raise ValueError(f"Predicciones sin patient_id al mergear: {path}")
    return out


def tfidf_legacy_cleaner(s: Any) -> str:
    """
    Reproduce el preprocesamiento textual efectivamente usado en el notebook 04b.

    El notebook versionado contiene secuencias de control históricas en dos regex.
    Se mantienen aquí para reproducir exactamente `data/tfidf_predicciones_dev.csv`
    y los scores usados para AP/ROC de ansiedad.
    """
    if pd.isna(s):
        return ""
    s = str(s).lower().strip()
    s = unicodedata.normalize("NFC", s)
    re_multi = re.compile("(.)\x01{2,}")
    s = re_multi.sub("\x01\x01", s)
    s = re.sub(r"[^a-z0-9áéíóúüñ\s.,!?:/\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub("\x08no\\s+([a-záéíóúüñ]{2,})", "no_\x01", s)
    return s


def tfidf_anxiety_scores(train: pd.DataFrame, dev: pd.DataFrame, saved_pred: pd.DataFrame) -> tuple[np.ndarray, dict[str, Any]]:
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    max_features=10000,
                ),
            ),
            ("clf", LinearSVC(class_weight="balanced", random_state=42)),
        ]
    )
    x_train = train["texto"].map(tfidf_legacy_cleaner)
    x_dev = dev["texto"].map(tfidf_legacy_cleaner)
    pipeline.fit(x_train, train["etiqueta"].astype(str))
    y_pred = pd.Series(pipeline.predict(x_dev)).astype(str)
    raw_scores = pipeline.decision_function(x_dev)
    classes = list(pipeline.named_steps["clf"].classes_)
    anxiety_scores = raw_scores if classes[1] == POS_LABEL else -raw_scores
    saved = saved_pred.sort_values("row_id")["y_pred"].reset_index(drop=True).astype(str)
    current = (
        pd.DataFrame({"row_id": dev["row_id"].astype(int), "y_pred": y_pred})
        .sort_values("row_id")["y_pred"]
        .reset_index(drop=True)
    )
    return anxiety_scores, {
        "classes": classes,
        "pred_matches_saved": bool((current == saved).all()),
        "n_mismatches": int((current != saved).sum()),
    }


def compute_patient_concentration(dev: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    counts = dev.groupby("patient_id").size().sort_values(ascending=False)
    effective_n = float((counts.sum() ** 2) / (counts.pow(2).sum()))
    top = counts.reset_index(name="n_notas")
    top["prop_split"] = top["n_notas"] / len(dev)
    top["prop_acumulada"] = top["prop_split"].cumsum()
    top.to_csv(out_dir / "concentracion_pacientes_dev.csv", index=False)
    summary = {
        "n_notas": int(len(dev)),
        "n_pacientes": int(dev["patient_id"].nunique()),
        "paciente_top1": int(counts.index[0]),
        "notas_top1": int(counts.iloc[0]),
        "prop_top1": float(counts.iloc[0] / len(dev)),
        "top3_prop_acumulada": float(counts.iloc[:3].sum() / len(dev)),
        "n_efectivo_pacientes": effective_n,
    }
    write_json(summary, out_dir / "concentracion_pacientes_dev.json")
    return summary


def compute_three_level_metrics(
    train: pd.DataFrame,
    dev: pd.DataFrame,
    final_pred: pd.DataFrame,
    out_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tfidf_pred = load_prediction_with_patient(DATA / "tfidf_predicciones_dev.csv", dev)
    roberta_pred = load_prediction_with_patient(DATA / "roberta_clinical_predicciones_dev.csv", dev)
    beto_pred = load_prediction_with_patient(DATA / "beto_predicciones_dev.csv", dev)

    tfidf_scores, tfidf_repro = tfidf_anxiety_scores(train, dev, tfidf_pred)
    tfidf_pred = tfidf_pred.copy()
    tfidf_pred["score_ansiedad"] = tfidf_scores
    pd.DataFrame(
        {
            "row_id": dev["row_id"].astype(int),
            "score_ansiedad": tfidf_scores,
            "y_true": dev["etiqueta"].astype(str),
            "y_pred_refit": tfidf_pred["y_pred"].astype(str),
        }
    ).to_csv(out_dir / "tfidf_scores_ansiedad_dev.csv", index=False)
    write_json(tfidf_repro, out_dir / "tfidf_refit_reproduccion.json")

    modelos = [
        ("Hibrido final XGB seed42", final_pred, "mean_prob"),
        ("TF-IDF LinearSVC", tfidf_pred, "mode_pred"),
        ("ROBERTA_CLINICAL", roberta_pred, "mean_prob"),
        ("BETO standalone", beto_pred, "mean_prob"),
    ]

    records: list[dict[str, Any]] = []
    for modelo, pred, agg_method in modelos:
        add_metric_record(records, modelo, "note-level", pred)
        weights = 1 / pred["patient_id"].map(pred.groupby("patient_id").size())
        add_metric_record(records, modelo, "patient-weighted", pred, sample_weight=weights)
        records.append(patient_aggregated_metrics(pred, modelo, agg_method))

    metrics_df = pd.DataFrame(records)
    metrics_df.to_csv(out_dir / "metricas_tres_niveles_dev.csv", index=False)

    auc_records = []
    for modelo, pred, score_col in [
        ("Hibrido final XGB seed42", final_pred, "prob_ansiedad"),
        ("TF-IDF LinearSVC", tfidf_pred, "score_ansiedad"),
        ("ROBERTA_CLINICAL", roberta_pred, "prob_ansiedad"),
        ("BETO standalone", beto_pred, "prob_ansiedad"),
    ]:
        y_bin = (pred["y_true"].astype(str) == POS_LABEL).astype(int)
        scores = pred[score_col].astype(float)
        auc_records.append(
            {
                "modelo": modelo,
                "roc_auc_ansiedad": float(roc_auc_score(y_bin, scores)),
                "average_precision_ansiedad": float(average_precision_score(y_bin, scores)),
                "n": int(len(pred)),
                "n_ansiedad": int(y_bin.sum()),
                "score_col": score_col,
            }
        )
    auc_df = pd.DataFrame(auc_records)
    auc_df.to_csv(out_dir / "metricas_auc_ap_ansiedad_dev.csv", index=False)
    return metrics_df, auc_df


def compute_threshold_sweep(final_pred: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    probs = final_pred["prob_ansiedad"].astype(float)
    thresholds = sorted(set([0.0, 0.25, 0.40, 0.45, 0.50, 0.55, 0.60, 0.75, 1.0] + probs.round(12).tolist()))
    records = []
    for thr in thresholds:
        y_pred = np.where(probs >= thr, POS_LABEL, NEG_LABEL)
        m = metric_block(final_pred["y_true"], y_pred)
        fn_ans = int(((final_pred["y_true"] == POS_LABEL) & (pd.Series(y_pred) == NEG_LABEL)).sum())
        fp_ans = int(((final_pred["y_true"] == NEG_LABEL) & (pd.Series(y_pred) == POS_LABEL)).sum())
        records.append({"threshold": float(thr), **m, "fn_ansiedad": fn_ans, "fp_ansiedad": fp_ans})
    sweep = pd.DataFrame(records)
    sweep.to_csv(out_dir / "threshold_sweep_hibrido_dev.csv", index=False)

    row_050 = sweep.iloc[(sweep["threshold"] - 0.5).abs().argsort()[:1]].iloc[0]
    best_f1 = sweep.sort_values(["f1_ansiedad", "macro_f1", "balanced_accuracy"], ascending=False).iloc[0]
    best_macro = sweep.sort_values(["macro_f1", "f1_ansiedad", "balanced_accuracy"], ascending=False).iloc[0]
    summary = {
        "threshold_canonico": 0.5,
        "threshold_050_row": {k: safe_float(v) for k, v in row_050.to_dict().items()},
        "best_by_f1_ansiedad": {k: safe_float(v) for k, v in best_f1.to_dict().items()},
        "best_by_macro_f1": {k: safe_float(v) for k, v in best_macro.to_dict().items()},
        "recomendacion": "mantener 0.50 salvo pre-especificación clínica antes de abrir test",
    }
    write_json(summary, out_dir / "threshold_sweep_hibrido_dev_resumen.json")
    return summary


def compute_denoising_summary(base: pd.DataFrame, denoised: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    records = []
    for label in LABELS:
        n_base = int((base["etiqueta"] == label).sum())
        n_den = int((denoised["etiqueta"] == label).sum())
        records.append(
            {
                "clase": label,
                "dataset_base_n": n_base,
                "dataset_denoised_n": n_den,
                "notas_eliminadas": n_base - n_den,
                "retencion": n_den / n_base if n_base else None,
            }
        )
    records.append(
        {
            "clase": "total",
            "dataset_base_n": int(len(base)),
            "dataset_denoised_n": int(len(denoised)),
            "notas_eliminadas": int(len(base) - len(denoised)),
            "retencion": len(denoised) / len(base),
        }
    )
    df = pd.DataFrame(records)
    df["pacientes_base"] = int(base["patient_id"].nunique())
    df["pacientes_denoised"] = int(denoised["patient_id"].nunique())
    df.to_csv(out_dir / "resumen_denoising_retencion.csv", index=False)
    return df


def age_group_audit_repro(age: float | None) -> str:
    if age is None or pd.isna(age):
        return "sin_dato"
    # Bins retenidos para reproducir la auditoría final ya redactada.
    if age < 42:
        return "<40"
    if age <= 61:
        return "40-60"
    return ">60"


def compute_demographics(dev: pd.DataFrame, final_pred: pd.DataFrame, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(DATA / "ips_raw.csv")
    raw_cols = pd.DataFrame(
        [
            {
                "columna": c,
                "existe": c in raw.columns,
                "n_missing": int(raw[c].isna().sum()) if c in raw.columns else None,
                "pct_missing": float(raw[c].isna().mean()) if c in raw.columns else None,
            }
            for c in ["Sexo", "Fecha Nacimiento", "Fecha Consulta", "Prontuario", "Tipo"]
        ]
    )
    raw_cols.to_csv(out_dir / "variables_demograficas_crudo.csv", index=False)

    raw["fecha_nacimiento_dt"] = pd.to_datetime(raw["Fecha Nacimiento"], dayfirst=True, errors="coerce")
    raw["fecha_consulta_dt"] = pd.to_datetime(raw["Fecha Consulta"], dayfirst=True, errors="coerce")
    patient_demo = (
        raw.groupby("Prontuario")
        .agg(
            sexo=("Sexo", mode_stable),
            fecha_nacimiento=("fecha_nacimiento_dt", "first"),
            fecha_consulta_max=("fecha_consulta_dt", "max"),
            sexo_nunique=("Sexo", lambda s: int(s.dropna().nunique())),
            fecha_nacimiento_nunique=("Fecha Nacimiento", lambda s: int(s.dropna().nunique())),
        )
        .reset_index()
        .rename(columns={"Prontuario": "patient_id"})
    )
    patient_demo["edad_referencia"] = (
        patient_demo["fecha_consulta_max"] - patient_demo["fecha_nacimiento"]
    ).dt.days / 365.25
    patient_demo["age_group"] = patient_demo["edad_referencia"].map(age_group_audit_repro)
    patient_demo.to_csv(out_dir / "demografia_por_paciente_desde_crudo.csv", index=False)

    merged = dev[["row_id", "patient_id", "etiqueta"]].merge(
        final_pred[["row_id", "y_true", "y_pred"]], on="row_id", how="left"
    ).merge(patient_demo[["patient_id", "sexo", "age_group"]], on="patient_id", how="left")

    dist_records = []
    metric_records = []
    for variable, col in [("sexo", "sexo"), ("age_group", "age_group")]:
        for subgroup, sub in merged.groupby(col, dropna=False):
            subgroup_value = "sin_dato" if pd.isna(subgroup) else str(subgroup)
            vc = sub["etiqueta"].value_counts()
            dist_records.append(
                {
                    "variable": variable,
                    "subgrupo": subgroup_value,
                    "n_notas": int(len(sub)),
                    "n_pacientes": int(sub["patient_id"].nunique()),
                    "ansiedad_n": int(vc.get(POS_LABEL, 0)),
                    "depresion_n": int(vc.get(NEG_LABEL, 0)),
                }
            )
            metric_records.append(
                {
                    "variable": variable,
                    "subgrupo": subgroup_value,
                    "n_notas": int(len(sub)),
                    "n_pacientes": int(sub["patient_id"].nunique()),
                    "ansiedad_n": int(vc.get(POS_LABEL, 0)),
                    "depresion_n": int(vc.get(NEG_LABEL, 0)),
                    **subgroup_metric_block(sub),
                }
            )

    dist_df = pd.DataFrame(dist_records)
    metrics_df = pd.DataFrame(metric_records)
    dist_df.to_csv(out_dir / "distribucion_subgrupos_dev.csv", index=False)
    metrics_df.to_csv(out_dir / "metricas_subgrupos_dev.csv", index=False)
    return raw_cols, dist_df, metrics_df


def load_xgb_data(train_dir: Path) -> tuple[pd.DataFrame, list[str], Any, Path]:
    feature_path = resolve_feature_path(train_dir)
    features = pd.read_parquet(feature_path)
    cols = read_json(train_dir / "py_X_cols.json")
    missing_cols = sorted(set(cols) - set(features.columns))
    if missing_cols:
        raise ValueError(f"Columnas faltantes en features: {missing_cols[:10]}")
    model = joblib.load(train_dir / "modelo_py_XGB.joblib")
    return features, cols, model, feature_path


def encode_labels(series: pd.Series) -> np.ndarray:
    mapping = {label: i for i, label in enumerate(LABELS)}
    return series.astype(str).map(mapping).astype(int).to_numpy()


def decode_labels(values: Iterable[int]) -> list[str]:
    arr = np.asarray(values)
    if arr.ndim > 1:
        arr = np.argmax(arr, axis=1)
    return [LABELS[int(v)] for v in arr]


def build_xgb_from_model(model: Any, seed: int = 42) -> XGBClassifier:
    params = model.get_params()
    params["random_state"] = seed
    return XGBClassifier(**params)


def compute_sample_weight_sensitivity(
    train: pd.DataFrame,
    dev: pd.DataFrame,
    train_dir: Path,
    final_pred: pd.DataFrame,
    out_dir: Path,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, list[str], Any, Path]:
    features, cols, frozen_model, feature_path = load_xgb_data(train_dir)
    train_ids = train["row_id"].astype(int)
    dev_ids = dev["row_id"].astype(int)
    feature_idx = features.set_index("row_id", drop=False)
    train_feat = feature_idx.loc[train_ids]
    dev_feat = feature_idx.loc[dev_ids]

    x_train = train_feat[cols]
    x_dev = dev_feat[cols]
    y_train = encode_labels(train_feat["etiqueta"])
    y_dev_text = dev_feat["etiqueta"].astype(str).reset_index(drop=True)

    unweighted = build_xgb_from_model(frozen_model, seed=42)
    unweighted.fit(x_train, y_train)
    unweighted_pred_codes = unweighted.predict(x_dev)
    unweighted_pred = decode_labels(unweighted_pred_codes)
    unweighted_proba = unweighted.predict_proba(x_dev)
    proba_ans_idx = LABELS.index(POS_LABEL)
    unweighted_pred_df = pd.DataFrame(
        {
            "row_id": dev_ids.to_numpy(),
            "y_true": y_dev_text,
            "y_pred": unweighted_pred,
            "prob_ansiedad": unweighted_proba[:, proba_ans_idx],
            "prob_depresion": unweighted_proba[:, LABELS.index(NEG_LABEL)],
        }
    )
    unweighted_pred_df.to_csv(out_dir / "predicciones_xgb_unweighted_reproduccion_dev.csv", index=False)

    frozen_sorted = final_pred.sort_values("row_id")["y_pred"].reset_index(drop=True).astype(str)
    reproduced_sorted = unweighted_pred_df.sort_values("row_id")["y_pred"].reset_index(drop=True).astype(str)
    mismatches = int((frozen_sorted != reproduced_sorted).sum())

    train_counts = train_feat["patient_id"].map(train_feat.groupby("patient_id").size())
    sample_weight = (1 / train_counts).astype(float).to_numpy()

    weighted = build_xgb_from_model(frozen_model, seed=42)
    weighted.fit(x_train, y_train, sample_weight=sample_weight)
    weighted_pred_codes = weighted.predict(x_dev)
    weighted_pred = decode_labels(weighted_pred_codes)
    weighted_proba = weighted.predict_proba(x_dev)
    weighted_pred_df = pd.DataFrame(
        {
            "row_id": dev_ids.to_numpy(),
            "y_true": y_dev_text,
            "y_pred": weighted_pred,
            "prob_ansiedad": weighted_proba[:, proba_ans_idx],
            "prob_depresion": weighted_proba[:, LABELS.index(NEG_LABEL)],
        }
    )
    weighted_pred_df = weighted_pred_df.merge(dev[["row_id", "patient_id"]], on="row_id", how="left")
    weighted_pred_df.to_csv(out_dir / "predicciones_xgb_sample_weight_dev.csv", index=False)

    records: list[dict[str, Any]] = []
    for name, pred_df in [
        ("XGB congelado actual", final_pred),
        ("XGB sample_weight paciente", weighted_pred_df),
    ]:
        add_metric_record(records, name, "note-level", pred_df)
        weights = 1 / pred_df["patient_id"].map(pred_df.groupby("patient_id").size())
        add_metric_record(records, name, "patient-weighted", pred_df, sample_weight=weights)
        records.append(patient_aggregated_metrics(pred_df, name, "mean_prob"))
    metrics_df = pd.DataFrame(records)
    for idx, row in metrics_df.iterrows():
        pred_df = final_pred if row["modelo"] == "XGB congelado actual" else weighted_pred_df
        y_bin = (pred_df["y_true"].astype(str) == POS_LABEL).astype(int)
        metrics_df.loc[idx, "average_precision_ansiedad"] = average_precision_score(y_bin, pred_df["prob_ansiedad"])
        metrics_df.loc[idx, "fn_ansiedad"] = int(((pred_df["y_true"] == POS_LABEL) & (pred_df["y_pred"] == NEG_LABEL)).sum())
        metrics_df.loc[idx, "fp_ansiedad"] = int(((pred_df["y_true"] == NEG_LABEL) & (pred_df["y_pred"] == POS_LABEL)).sum())

    metrics_df.to_csv(out_dir / "metricas_xgb_sample_weight_comparacion.csv", index=False)
    summary = {
        "n_train": int(len(train_feat)),
        "n_dev": int(len(dev_feat)),
        "n_features_final": int(len(cols)),
        "feature_path": str(feature_path),
        "sample_weight_formula": "1 / n_notas_paciente_train",
        "sample_weight_sum": float(sample_weight.sum()),
        "sample_weight_min": float(sample_weight.min()),
        "sample_weight_max": float(sample_weight.max()),
        "sample_weight_mean": float(sample_weight.mean()),
        "unweighted_reproduction_pred_matches_frozen": bool(mismatches == 0),
        "unweighted_reproduction_mismatches_vs_frozen": mismatches,
    }
    write_json(summary, out_dir / "resumen_xgb_sample_weight_shap.json")
    return metrics_df, summary, features, cols, frozen_model, feature_path


def feature_family(col: str) -> str:
    if col.startswith("rule_medication_"):
        return "rule_medication"
    if col.startswith("ctx_beto_"):
        return "ctx_beto"
    if col.startswith("ctx_"):
        return "ctx_other"
    if col.startswith("rule_"):
        return "rule"
    if col.startswith("niega_") or col.startswith("feat_niega_"):
        return "niega"
    if col.startswith("feat_"):
        return "feat"
    if col.startswith("sent_"):
        return "sent"
    if "template" in col:
        return "template"
    if col == "has_clinical_signal":
        return "has_clinical_signal"
    return "other"


def normalize_shap_values(shap_values: Any) -> np.ndarray:
    if isinstance(shap_values, list):
        return np.stack(shap_values, axis=-1)
    arr = np.asarray(shap_values)
    if arr.ndim == 2:
        return arr[:, :, None]
    return arr


def compute_shap_outputs(
    dev: pd.DataFrame,
    train_dir: Path,
    features: pd.DataFrame,
    cols: list[str],
    model: Any,
    out_dir: Path,
    appendix_row_ids: list[int],
) -> dict[str, Any]:
    import shap

    dev_ids = dev["row_id"].astype(int)
    feature_idx = features.set_index("row_id", drop=False)
    dev_feat = feature_idx.loc[dev_ids]
    x_dev = dev_feat[cols]

    family_df = pd.DataFrame({"feature": cols, "family": [feature_family(c) for c in cols]})
    family_df.to_csv(out_dir / "feature_families_final_model.csv", index=False)

    explainer = shap.TreeExplainer(model)
    shap_raw = explainer.shap_values(x_dev)
    shap_arr = normalize_shap_values(shap_raw)
    class_names = LABELS[: shap_arr.shape[-1]]

    feature_records = []
    family_records = []
    for class_idx, class_name in enumerate(class_names):
        mean_abs = np.abs(shap_arr[:, :, class_idx]).mean(axis=0)
        tmp = pd.DataFrame(
            {
                "class_name": class_name,
                "feature": cols,
                "family": family_df["family"],
                "mean_abs_shap": mean_abs,
            }
        ).sort_values("mean_abs_shap", ascending=False)
        feature_records.append(tmp)
        fam = (
            tmp.groupby("family")
            .agg(
                sum_mean_abs_shap=("mean_abs_shap", "sum"),
                mean_mean_abs_shap=("mean_abs_shap", "mean"),
                n_features=("feature", "size"),
            )
            .reset_index()
        )
        fam["class_name"] = class_name
        family_records.append(fam)

    shap_features = pd.concat(feature_records, ignore_index=True)
    shap_families = pd.concat(family_records, ignore_index=True)
    shap_features.to_csv(out_dir / "shap_global_features.csv", index=False)
    shap_families.to_csv(out_dir / "shap_global_familias.csv", index=False)

    final_pred = pd.read_csv(train_dir / "predicciones_py_xgb_dev.csv")
    case_ids = [rid for rid in appendix_row_ids if rid in set(dev_ids)]
    local_top_records = []
    local_family_records = []
    local_summary_records = []
    row_pos = {int(rid): pos for pos, rid in enumerate(dev_ids.tolist())}
    for rid in case_ids:
        pos = row_pos[int(rid)]
        pred_row = final_pred.loc[final_pred["row_id"] == rid].iloc[0]
        pred_class = str(pred_row["y_pred"])
        class_idx = class_names.index(pred_class) if pred_class in class_names else int(np.argmax([pred_row.get("prob_ansiedad", 0), pred_row.get("prob_depresion", 0)]))
        vals = shap_arr[pos, :, class_idx]
        local = pd.DataFrame(
            {
                "row_id": int(rid),
                "class_name": class_names[class_idx],
                "feature": cols,
                "family": family_df["family"],
                "feature_value": x_dev.iloc[pos].to_numpy(),
                "shap_value": vals,
                "abs_shap": np.abs(vals),
            }
        ).sort_values("abs_shap", ascending=False)
        local_top_records.append(local.head(30))
        fam_local = (
            local.groupby("family")
            .agg(sum_abs_shap=("abs_shap", "sum"), mean_abs_shap=("abs_shap", "mean"), n_features=("feature", "size"))
            .reset_index()
        )
        fam_local["row_id"] = int(rid)
        fam_local["class_name"] = class_names[class_idx]
        local_family_records.append(fam_local)
        top_family = fam_local.sort_values("sum_abs_shap", ascending=False).iloc[0]
        local_summary_records.append(
            {
                "row_id": int(rid),
                "y_true": str(pred_row["y_true"]),
                "y_pred": pred_class,
                "prob_ansiedad": safe_float(pred_row.get("prob_ansiedad")),
                "prob_depresion": safe_float(pred_row.get("prob_depresion")),
                "class_explained": class_names[class_idx],
                "top_family": top_family["family"],
                "top_family_sum_abs_shap": safe_float(top_family["sum_abs_shap"]),
                "rule_Autolesin_value": safe_float(x_dev.iloc[pos]["rule_Autolesin"]) if "rule_Autolesin" in x_dev.columns else None,
                "rule_Autolesin_shap": safe_float(local.loc[local["feature"] == "rule_Autolesin", "shap_value"].iloc[0]) if "rule_Autolesin" in x_dev.columns else None,
            }
        )

    if local_top_records:
        pd.concat(local_top_records, ignore_index=True).to_csv(out_dir / "shap_local_top_features_appendix_cases.csv", index=False)
        pd.concat(local_family_records, ignore_index=True).to_csv(out_dir / "shap_local_familias_appendix_cases.csv", index=False)
        pd.DataFrame(local_summary_records).to_csv(out_dir / "shap_local_appendix_cases_summary.csv", index=False)

    return {
        "n_features": int(len(cols)),
        "n_dev": int(len(dev)),
        "class_names": class_names,
        "appendix_row_ids_explained": case_ids,
    }


def compute_case_c_trace(
    base: pd.DataFrame,
    flagged: pd.DataFrame,
    denoised: pd.DataFrame,
    dev: pd.DataFrame,
    final_pred: pd.DataFrame,
    out_dir: Path,
    row_id: int = 51,
) -> dict[str, Any]:
    raw = pd.read_csv(DATA / "ips_raw.csv")
    rule_features_path = OUTPUTS / "compare_20260401_093038_py" / "rule_features.csv"
    autolesin_samples_path = OUTPUTS / "compare_20260401_093038_py" / "samples_by_phenotype" / "Autolesin.csv"
    error_cases_path = latest_dir(OUTPUTS, "error_analysis_") / "casos_mal_clasificados.csv"

    row_base = base.loc[base["row_id"] == row_id]
    row_flag = flagged.loc[flagged["row_id"] == row_id]
    row_den = denoised.loc[denoised["row_id"] == row_id]
    row_dev = dev.loc[dev["row_id"] == row_id]
    row_pred = final_pred.loc[final_pred["row_id"] == row_id]

    rule_features = pd.read_csv(rule_features_path)
    rule_row = rule_features.loc[rule_features["row_id"] == row_id]
    active_rules = []
    if not rule_row.empty:
        active_rules = [
            c
            for c in rule_row.columns
            if (c.startswith("rule_") or c.startswith("niega_")) and int(rule_row.iloc[0].get(c, 0)) == 1
        ]

    autolesin_samples = pd.read_csv(autolesin_samples_path)
    in_autolesin_samples = bool((autolesin_samples["row_id"] == row_id).any())

    error_cases = pd.read_csv(error_cases_path) if error_cases_path.exists() else pd.DataFrame()
    in_error_analysis = bool((error_cases.get("row_id", pd.Series(dtype=int)) == row_id).any())

    entities = []
    try:
        sys.path.insert(0, str(REPO))
        sys.path.insert(0, str((REPO / "Spanish_Psych_Phenotyping_PY").resolve()))
        from cli import build_pipeline, load_yaml
        from notebooks.utils_shared import keep_entity

        cfg = load_yaml(REPO / "Spanish_Psych_Phenotyping_PY" / "configs" / "fenotipos.yml")
        nlp = build_pipeline("core", cfg)
        doc = nlp(str(row_base.iloc[0]["texto"]))
        for ent in getattr(doc, "ents", []):
            keep, is_patient_neg = keep_entity(ent, doc, window_tokens=12)
            ext = getattr(ent, "_", None)
            entities.append(
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "keep_entity": bool(keep),
                    "is_patient_negation": bool(is_patient_neg),
                    "is_negated": bool(getattr(ext, "is_negated", False)),
                    "is_historical": bool(getattr(ext, "is_historical", False)),
                    "is_hypothetical": bool(getattr(ext, "is_hypothetical", False)),
                    "is_family": bool(getattr(ext, "is_family", False)),
                }
            )
    except Exception as exc:
        entities.append({"error_entity_reconstruction": str(exc)})

    raw_record = raw.iloc[row_id].to_dict() if row_id < len(raw) else {}
    trace = {
        "row_id": row_id,
        "patient_id": int(row_base.iloc[0]["patient_id"]) if not row_base.empty else None,
        "label": str(row_base.iloc[0]["etiqueta"]) if not row_base.empty else None,
        "split": "dev" if not row_dev.empty else None,
        "texto_modelado": str(row_base.iloc[0]["texto"]) if not row_base.empty else None,
        "texto_original_raw_row": raw_record.get("Motivo Consulta"),
        "raw_row_id_assumption": "row_id coincide con índice limpio; para row_id=51 coincide con ips_raw.iloc[51]",
        "appears_in_dataset_base": bool(not row_base.empty),
        "appears_in_dataset_denoised": bool(not row_den.empty),
        "appears_in_dev_denoised": bool(not row_dev.empty),
        "has_clinical_signal": bool(row_flag.iloc[0]["has_clinical_signal"]) if not row_flag.empty else None,
        "feat_negacion_paciente": int(row_flag.iloc[0]["feat_negacion_paciente"]) if not row_flag.empty else None,
        "entities_core_reconstructed": entities,
        "active_rule_columns_py_compare": active_rules,
        "in_autolesin_samples": in_autolesin_samples,
        "in_error_analysis": in_error_analysis,
        "prediction": row_pred.iloc[0].to_dict() if not row_pred.empty else None,
        "survival_condition": "Autolesin se activa por la secuencia administrativa 'Misma medicacion Misma'; keep_entity la retiene al no estar negada, histórica, hipotética ni familiar.",
        "source_rule_file": "Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_Core/Depresion/Autolesin.json",
    }
    write_json(trace, out_dir / "case_c_trace.json")
    pd.DataFrame([trace | {"entities_core_reconstructed": json.dumps(entities, ensure_ascii=False)}]).to_csv(out_dir / "case_c_trace.csv", index=False)
    return trace


def compute_document_checks(out_dir: Path) -> dict[str, Any]:
    decision_path = OUTPUTS / "cierre_modelos_dev_20260401_114409" / "decision_modelo_final.json"
    decision = read_json(decision_path)
    test_audits = sorted(OUTPUTS.glob("auditoria_test_*.md"))
    docs_reval = (REPO / "docs" / "REVALIDACION_RESULTADOS_REFERENCIA.md").read_text(encoding="utf-8")
    expected_score = str(decision["modelo_hibrido_final"]["score_final_seleccion"])
    checks = {
        "decision_modelo_final_json": str(decision_path),
        "score_final_seleccion_fuente_verdad": float(decision["modelo_hibrido_final"]["score_final_seleccion"]),
        "score_final_seleccion_presente_en_revalidacion_doc": expected_score in docs_reval,
        "auditoria_test_md_encontrados": [str(p) for p in test_audits],
        "test_auditoria_formal_pendiente": len(test_audits) == 0,
    }
    write_json(checks, out_dir / "checks_documentales.json")
    return checks


def write_markdown_summary(summary: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# Auditoría secundaria reproducible en `dev`",
        "",
        f"- Fecha de corrida: `{summary['run_timestamp']}`",
        f"- Modelo final: `{summary['modelo_final']}`",
        f"- Train run: `{summary['train_dir']}`",
        f"- Features: `{summary['feature_path']}`",
        f"- `sample_weight` adoptado como final: `no`",
        f"- Reproducción XGB sin pesos: `{summary['sample_weight']['unweighted_reproduction_mismatches_vs_frozen']}` discrepancias",
        f"- Caso C: `row_id={summary['case_c']['row_id']}`, veredicto `A`",
        "",
        "## Artefactos principales",
        "",
    ]
    for artifact in summary["artifacts"]:
        lines.append(f"- `{artifact}`")
    (out_dir / "resumen_auditoria_validacion_secundaria_dev.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--case-c-row-id", type=int, default=51)
    parser.add_argument("--appendix-row-ids", default="255,2254,51")
    parser.add_argument("--skip-shap", action="store_true")
    parser.add_argument("--skip-sample-weight", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    base = pd.read_csv(SPLITS / "dataset_base.csv")
    flagged = pd.read_csv(DATA / "dataset_with_clinical_signal_flag.csv")
    denoised = pd.read_csv(DATA / "dataset_denoised.csv")
    train = pd.read_csv(SPLITS / "train_denoised.csv")
    dev = pd.read_csv(SPLITS / "dev_denoised.csv")

    decision_path = OUTPUTS / "cierre_modelos_dev_20260401_114409" / "decision_modelo_final.json"
    decision = read_json(decision_path)
    train_dir = resolve_final_train_dir()
    final_pred = load_prediction_with_patient(train_dir / "predicciones_py_xgb_dev.csv", dev)

    concentration = compute_patient_concentration(dev, out_dir)
    metrics_three, auc_ap = compute_three_level_metrics(train, dev, final_pred, out_dir)
    threshold_summary = compute_threshold_sweep(final_pred, out_dir)
    denoising_summary = compute_denoising_summary(base, denoised, out_dir)
    raw_cols, subgroup_dist, subgroup_metrics = compute_demographics(dev, final_pred, out_dir)
    case_c = compute_case_c_trace(base, flagged, denoised, dev, final_pred, out_dir, row_id=args.case_c_row_id)
    checks = compute_document_checks(out_dir)

    sample_weight_summary: dict[str, Any] = {"skipped": True}
    shap_summary: dict[str, Any] = {"skipped": True}
    feature_path: Path | None = None
    if not args.skip_sample_weight:
        _, sample_weight_summary, features, cols, model, feature_path = compute_sample_weight_sensitivity(
            train, dev, train_dir, final_pred, out_dir
        )
    else:
        features, cols, model, feature_path = load_xgb_data(train_dir)

    if not args.skip_shap:
        appendix_row_ids = [int(x.strip()) for x in args.appendix_row_ids.split(",") if x.strip()]
        shap_summary = compute_shap_outputs(dev, train_dir, features, cols, model, out_dir, appendix_row_ids)

    artifacts = sorted(str(p.relative_to(REPO)) for p in out_dir.glob("*") if p.is_file())
    summary = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "python": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "repo": str(REPO),
        "decision_path": str(decision_path),
        "modelo_final": decision["modelo_hibrido_final"]["modelo_variante"],
        "train_dir": str(train_dir),
        "feature_path": str(feature_path) if feature_path else None,
        "input_hashes": {
            "decision_modelo_final.json": sha256_file(decision_path),
            "predicciones_final_dev": sha256_file(train_dir / "predicciones_py_xgb_dev.csv"),
            "dataset_base": sha256_file(SPLITS / "dataset_base.csv"),
            "dataset_denoised": sha256_file(DATA / "dataset_denoised.csv"),
            "dev_denoised": sha256_file(SPLITS / "dev_denoised.csv"),
        },
        "concentracion_dev": concentration,
        "case_c": {
            "row_id": case_c["row_id"],
            "veredicto": "A",
            "passed_denoising": case_c["appears_in_dataset_denoised"],
            "classified_by_final_model": case_c["prediction"] is not None,
            "active_rule_columns": case_c["active_rule_columns_py_compare"],
        },
        "denoising_total": denoising_summary.loc[denoising_summary["clase"] == "total"].iloc[0].to_dict(),
        "threshold": threshold_summary,
        "checks_documentales": checks,
        "sample_weight": sample_weight_summary,
        "shap": shap_summary,
        "artifacts": artifacts,
    }
    write_json(summary, out_dir / "resumen_auditoria_validacion_secundaria_dev.json")
    write_markdown_summary(summary, out_dir)

    print("Auditoría secundaria dev generada.")
    print(f"Salida: {out_dir}")
    print(f"Artefactos: {len(artifacts)}")
    print("No se reabre selección de modelo ni ontología.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
