#!/usr/bin/env python3
"""Orquestador de barridos de ablación para el pipeline híbrido.

Diseñado para:
- ejecutar fases A/B/C con el mismo universo de evaluación,
- tolerar fallas parciales,
- consolidar resultados comparables para análisis metodológico.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
NB06 = REPO_ROOT / "notebooks" / "pipeline" / "06_ingenieria_features_hibridas.ipynb"
NB07 = REPO_ROOT / "notebooks" / "pipeline" / "07_entrenamiento_modelos_hibridos.ipynb"
DATA_PATH = REPO_ROOT / "data"
OUTPUTS_PATH = DATA_PATH / "outputs"
SPLITS_PATH = DATA_PATH / "splits"
PROCESSED_PATH = DATA_PATH / "processed"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PYTHON_EXEC = os.getenv("BARRIDO_PYTHON") or (str(VENV_PY) if VENV_PY.exists() else sys.executable)


@dataclass
class Ejecucion:
    fase: str
    variante: str
    ok: bool
    duracion_seg: float
    run_id_features: str | None = None
    run_id_train: str | None = None
    mensaje: str = ""
    log_path: str | None = None


class BarridoError(Exception):
    pass


def ts_now() -> str:
    return pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")


def sanitize_name(s: str, max_len: int = 120) -> str:
    s = re.sub(r"[^a-zA-Z0-9_\-\.]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] if len(s) > max_len else s


def run_cmd(cmd: list[str], env: dict[str, str], log_path: Path) -> tuple[bool, float, str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write("$ " + " ".join(cmd) + "\n\n")
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            env=env,
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
        )
    dur = time.time() - start
    ok = proc.returncode == 0
    msg = f"exit={proc.returncode}"
    return ok, dur, msg


def convertir_notebooks(tmp_dir: Path) -> tuple[Path, Path]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    conv = [
        ["jupyter", "nbconvert", "--to", "script", str(NB06), "--output-dir", str(tmp_dir)],
        ["jupyter", "nbconvert", "--to", "script", str(NB07), "--output-dir", str(tmp_dir)],
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    for cmd in conv:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            raise BarridoError(
                "No se pudieron convertir notebooks a script.\n"
                f"CMD: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

    py06 = tmp_dir / "06_ingenieria_features_hibridas.py"
    py07 = tmp_dir / "07_entrenamiento_modelos_hibridos.py"
    if not py06.exists() or not py07.exists():
        raise BarridoError("No se generaron scripts de 06/07 tras nbconvert.")
    return py06, py07


def leer_csv_si_existe(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def extraer_importancias(train_dir: Path, profile: str, model: str, out_dir: Path, nombre_variante: str) -> None:
    try:
        import joblib
    except Exception:
        return

    model_key = model.upper()
    model_path = train_dir / f"modelo_{profile}_{model_key}.joblib"
    cols_path = train_dir / f"{profile}_X_cols.json"
    if not model_path.exists() or not cols_path.exists():
        return

    try:
        mdl = joblib.load(model_path)
        with open(cols_path, "r", encoding="utf-8") as f:
            cols = json.load(f)
    except Exception:
        return

    if not hasattr(mdl, "feature_importances_"):
        return

    imp = np.asarray(getattr(mdl, "feature_importances_"), dtype=float)
    if imp.ndim != 1 or len(imp) == 0:
        return

    n = min(len(cols), len(imp))
    dfi = pd.DataFrame({
        "feature": cols[:n],
        "importance": imp[:n],
    }).sort_values("importance", ascending=False)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sanitize_name(nombre_variante)}_importancias.csv"
    dfi.to_csv(out_path, index=False)


def copiar_si_existe(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def normalizar_fila_hibrida(
    row: dict[str, Any],
    run_id_train: str,
    source: str,
) -> dict[str, Any]:
    model_raw = str(row.get("model", "")).upper()
    profile = str(row.get("profile", "")).lower()
    nombre_variante = str(row.get("variant_name", f"{source}_{profile}_{model_raw}")).strip() or f"{source}_{profile}_{model_raw}"

    run_id_features = row.get("run_id_features_py") if profile == "py" else row.get("run_id_features_core")

    out = {
        "source": source,
        "nombre_variante": f"{nombre_variante}|{profile}|{model_raw}",
        "run_id_features": run_id_features,
        "run_id_features_core": row.get("run_id_features_core"),
        "run_id_features_py": row.get("run_id_features_py"),
        "run_id_train": run_id_train,
        "perfil": profile,
        "modelo": model_raw,
        "llm_activo": row.get("llm_activo", np.nan),
        "sentimiento_activo": row.get("sentimiento_activo", np.nan),
        "beto_activo": row.get("beto_activo", np.nan),
        "contexto_activo": row.get("contexto_activo", row.get("beto_activo", np.nan)),
        "text_backbone": row.get("text_backbone", np.nan),
        "context_prefixes": row.get("context_prefixes", np.nan),
        "template_activo": row.get("template_activo", np.nan),
        "feat_activo": row.get("feat_activo", np.nan),
        "reglas_activas": row.get("reglas_activas", np.nan),
        "medicacion_activa": row.get("medicacion_activa", np.nan),
        "seed": row.get("seed", np.nan),
        "n_features": row.get("n_features", np.nan),
        "n_train": row.get("n_train", np.nan),
        "n_eval": row.get("n_eval", np.nan),
        "macro_f1": row.get("macro_f1", np.nan),
        "balanced_accuracy": row.get("balanced_acc", np.nan),
        "precision_macro": row.get("precision_macro", np.nan),
        "recall_macro": row.get("recall_macro", np.nan),
        "f1_ansiedad": row.get("f1_ansiedad", np.nan),
        "f1_depresion": row.get("f1_depresion", np.nan),
        "soporte_ansiedad": row.get("soporte_ansiedad", np.nan),
        "soporte_depresion": row.get("soporte_depresion", np.nan),
        "eval_split": row.get("eval_split", np.nan),
        "fase": row.get("fase", np.nan),
        "cv_macro_f1": row.get("cv_macro_f1", np.nan),
    }
    return out


def ejecutar_06(
    py06: Path,
    logs_dir: Path,
    run_id: str,
    llm_flag: int,
    cache_key: str,
) -> Ejecucion:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    cache_home = REPO_ROOT / ".cache"
    mpl_cache = cache_home / "matplotlib"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    env["XDG_CACHE_HOME"] = str(cache_home)
    env["MPLCONFIGDIR"] = str(mpl_cache)
    env["MPLBACKEND"] = "Agg"
    env["FE_RUN_ID"] = run_id
    env["FE_CACHE_KEY"] = cache_key
    env["FE_USE_LLM"] = str(llm_flag)
    env["FE_COMPUTE_SENTIMENT"] = "1"
    env["FE_COMPUTE_BETO"] = "1"

    log_path = logs_dir / f"06_{sanitize_name(run_id)}.log"
    ok, dur, msg = run_cmd([PYTHON_EXEC, str(py06)], env, log_path)
    return Ejecucion(
        fase="A",
        variante=f"features_llm{llm_flag}",
        ok=ok,
        duracion_seg=dur,
        run_id_features=run_id,
        mensaje=msg,
        log_path=str(log_path),
    )


def ejecutar_07(
    py07: Path,
    logs_dir: Path,
    run_id_train: str,
    variant_name: str,
    feature_run_id: str,
    profile: str | None,
    model: str | None,
    seed: int,
    flags: dict[str, int],
    eval_on: str = "dev",
) -> tuple[Ejecucion, pd.DataFrame]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    cache_home = REPO_ROOT / ".cache"
    mpl_cache = cache_home / "matplotlib"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    env["XDG_CACHE_HOME"] = str(cache_home)
    env["MPLCONFIGDIR"] = str(mpl_cache)
    env["MPLBACKEND"] = "Agg"

    env["TRAIN_RUN_ID"] = run_id_train
    env["TRAIN_VARIANT_NAME"] = variant_name
    env["TRAIN_EVAL_ON"] = eval_on
    env["TRAIN_FEATURE_RUN_ID_CORE"] = f"{feature_run_id}_core"
    env["TRAIN_FEATURE_RUN_ID_PY"] = f"{feature_run_id}_py"

    env["TRAIN_USE_RANDOM_SEARCH"] = "0"
    env["TRAIN_SEED"] = str(seed)
    env["TRAIN_USE_XGB"] = "1"

    env["TRAIN_MODELS"] = model if model else "xgb,rf"
    env["TRAIN_PROFILES"] = profile if profile else "core,py"

    env["TRAIN_USE_BETO"] = str(flags.get("beto", 1))
    env["TRAIN_USE_LLM"] = str(flags.get("llm", 1))
    env["TRAIN_USE_TEMPLATE"] = str(flags.get("template", 1))
    env["TRAIN_USE_FEAT"] = str(flags.get("feat", 1))
    env["TRAIN_USE_RULES"] = str(flags.get("rules", 1))
    env["TRAIN_USE_MEDICATION"] = str(flags.get("medication", 1))
    env["TRAIN_USE_SENTIMENT"] = str(flags.get("sentiment", 1))

    if "drop_columns" in flags:
        env["TRAIN_DROP_COLUMNS"] = str(flags["drop_columns"])
    if "drop_prefixes" in flags:
        env["TRAIN_DROP_PREFIXES"] = str(flags["drop_prefixes"])
    if "keep_prefixes" in flags:
        env["TRAIN_KEEP_PREFIXES"] = str(flags["keep_prefixes"])

    log_path = logs_dir / f"07_{sanitize_name(run_id_train)}.log"
    ok, dur, msg = run_cmd([PYTHON_EXEC, str(py07)], env, log_path)

    exec_info = Ejecucion(
        fase="?",
        variante=variant_name,
        ok=ok,
        duracion_seg=dur,
        run_id_features=feature_run_id,
        run_id_train=run_id_train,
        mensaje=msg,
        log_path=str(log_path),
    )

    comp_path = OUTPUTS_PATH / run_id_train / f"comparacion_modelos_{eval_on}.csv"
    if not ok or not comp_path.exists():
        return exec_info, pd.DataFrame()

    df = pd.read_csv(comp_path)
    return exec_info, df


def filas_baselines() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_defs = {
        "DUMMY": DATA_PATH / "dummy_eval.csv",
        "TF-IDF": DATA_PATH / "tfidf_eval.csv",
        "BETO": DATA_PATH / "beto_eval.csv",
        "ROBERTA_BIOMEDICAL": DATA_PATH / "roberta_biomedical_eval.csv",
        "ROBERTA_CLINICAL": DATA_PATH / "roberta_clinical_eval.csv",
    }

    report_defs = {
        "TF-IDF": DATA_PATH / "tfidf_classification_report.csv",
        "BETO": DATA_PATH / "beto_classification_report.csv",
        "ROBERTA_BIOMEDICAL": DATA_PATH / "roberta_biomedical_classification_report.csv",
        "ROBERTA_CLINICAL": DATA_PATH / "roberta_clinical_classification_report.csv",
    }

    for modelo, p in base_defs.items():
        if not p.exists():
            continue
        d = pd.read_csv(p)
        if d.empty:
            continue
        r = d.iloc[0].to_dict()

        f1_a = np.nan
        f1_d = np.nan
        sup_a = np.nan
        sup_d = np.nan
        rp = report_defs.get(modelo)
        if rp and rp.exists():
            try:
                dr = pd.read_csv(rp, index_col=0)
                if "ansiedad" in dr.index:
                    f1_a = float(dr.loc["ansiedad", "f1-score"])
                    sup_a = float(dr.loc["ansiedad", "support"])
                if "depresion" in dr.index:
                    f1_d = float(dr.loc["depresion", "f1-score"])
                    sup_d = float(dr.loc["depresion", "support"])
            except Exception:
                pass

        rows.append({
            "source": "baseline_texto",
            "nombre_variante": modelo,
            "run_id_features": np.nan,
            "run_id_features_core": np.nan,
            "run_id_features_py": np.nan,
            "run_id_train": np.nan,
            "perfil": "texto",
            "modelo": modelo,
            "llm_activo": np.nan,
            "sentimiento_activo": np.nan,
            "beto_activo": np.nan,
            "contexto_activo": np.nan,
            "text_backbone": (
                "beto"
                if modelo == "BETO"
                else ("roberta_clinical" if modelo == "ROBERTA_CLINICAL" else ("roberta_biomedical" if modelo == "ROBERTA_BIOMEDICAL" else np.nan))
            ),
            "context_prefixes": np.nan,
            "template_activo": np.nan,
            "feat_activo": np.nan,
            "reglas_activas": np.nan,
            "medicacion_activa": np.nan,
            "seed": np.nan,
            "n_features": np.nan,
            "n_train": r.get("n_train", np.nan),
            "n_eval": r.get("n_eval", r.get("n_dev", np.nan)),
            "macro_f1": r.get("f1_macro", np.nan),
            "balanced_accuracy": r.get("balanced_acc", r.get("recall_macro", np.nan)),
            "precision_macro": r.get("precision_macro", np.nan),
            "recall_macro": r.get("recall_macro", np.nan),
            "f1_ansiedad": f1_a,
            "f1_depresion": f1_d,
            "soporte_ansiedad": sup_a,
            "soporte_depresion": sup_d,
            "eval_split": r.get("eval_split", "dev"),
            "fase": "referencia",
            "cv_macro_f1": "no_aplica",
        })
    return rows


def filas_hibrido_referencia(train_run_id: str, eval_on: str = "dev") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    train_dir = OUTPUTS_PATH / train_run_id
    comp_path = train_dir / f"comparacion_modelos_{eval_on}.csv"
    if not comp_path.exists():
        return rows

    df = pd.read_csv(comp_path)
    if df.empty:
        return rows

    for _, rr in df.iterrows():
        row = rr.to_dict()
        out = normalizar_fila_hibrida(row=row, run_id_train=train_run_id, source="hibrido_referencia")
        out["nombre_variante"] = f"PREV_{out['perfil']}_{out['modelo']}"
        out["fase"] = "referencia"
        rows.append(out)

    return rows


def build_fase_b_ablation_presets() -> list[dict[str, Any]]:
    return [
        {"nombre": "sin_feat", "feat": 0},
        {"nombre": "sin_rules", "rules": 0},
        {"nombre": "sin_medication", "medication": 0},
        {"nombre": "sin_feat_sin_rules", "feat": 0, "rules": 0},
        {"nombre": "sin_feat_sin_medication", "feat": 0, "medication": 0},
        {"nombre": "sin_rules_sin_medication", "rules": 0, "medication": 0},
        {
            "nombre": "solo_beto",
            "beto": 1,
            "feat": 0,
            "rules": 0,
            "medication": 0,
            "sentiment": 0,
            "template": 0,
        },
        {
            "nombre": "solo_reglas_feat_sin_beto",
            "beto": 0,
            "feat": 1,
            "rules": 1,
            "medication": 1,
            "sentiment": 0,
        },
        {
            "nombre": "beto_feat",
            "beto": 1,
            "feat": 1,
            "rules": 0,
            "medication": 0,
            "sentiment": 0,
        },
        {
            "nombre": "beto_reglas",
            "beto": 1,
            "feat": 0,
            "rules": 1,
            "medication": 1,
            "sentiment": 0,
            "template": 0,
        },
        {
            "nombre": "beto_medication",
            "beto": 1,
            "feat": 0,
            "rules": 0,
            "medication": 1,
            "sentiment": 0,
            "template": 0,
        },
        {
            "nombre": "beto_feat_reglas",
            "beto": 1,
            "feat": 1,
            "rules": 1,
            "medication": 1,
            "sentiment": 0,
        },
        {"nombre": "sin_beto", "beto": 0},
    ]


def resolve_feature_base_from_row(cand: pd.Series) -> str | None:
    vals = [
        cand.get("run_id_features_core", np.nan),
        cand.get("run_id_features_py", np.nan),
        cand.get("run_id_features", np.nan),
    ]
    for v in vals:
        if pd.isna(v):
            continue
        s = str(v).strip()
        if not s or s.lower() == "nan":
            continue
        if s.endswith("_core"):
            return s[:-5]
        if s.endswith("_py"):
            return s[:-3]
        return s
    return None


def select_fase_b_candidates(df_a: pd.DataFrame) -> pd.DataFrame:
    if df_a.empty:
        return df_a

    def _top(df: pd.DataFrame, n: int) -> pd.DataFrame:
        if df.empty:
            return df
        return df.sort_values("macro_f1", ascending=False).head(n)

    parts = [
        _top(df_a, 3),
        _top(df_a[df_a["perfil"] == "py"], 2),
        _top(df_a[df_a["perfil"] == "core"], 2),
        _top(df_a[df_a["modelo"].str.upper() == "XGB"], 2),
    ]

    sel = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if sel.empty:
        return sel
    return sel.drop_duplicates(subset=["nombre_variante"]).reset_index(drop=True)


def summarize_interpretativo(
    master: pd.DataFrame,
    barrido: pd.DataFrame,
    estabilidad: pd.DataFrame,
    out_path: Path,
) -> None:
    lines: list[str] = []
    lines.append("# Resumen interpretativo del barrido híbrido")
    lines.append("")

    if barrido.empty:
        lines.append("No se generaron variantes nuevas con resultados válidos.")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return

    b_sorted = barrido.sort_values("macro_f1", ascending=False)
    best = b_sorted.iloc[0]
    lines.append(f"- Mejor variante puntual: `{best['nombre_variante']}` con macro_f1={best['macro_f1']:.4f}.")

    if not estabilidad.empty:
        est = estabilidad.sort_values("macro_f1_media", ascending=False).iloc[0]
        lines.append(
            f"- Mejor variante promedio (estabilidad): `{est['base_variante']}` "
            f"con media={est['macro_f1_media']:.4f} y desvío={est['macro_f1_std']:.4f}."
        )
    else:
        lines.append("- No hubo resumen de estabilidad multi-seed disponible.")

    py_mean = barrido[barrido["perfil"] == "py"]["macro_f1"].mean()
    core_mean = barrido[barrido["perfil"] == "core"]["macro_f1"].mean()
    if pd.notna(py_mean) and pd.notna(core_mean):
        diff = py_mean - core_mean
        signo = "superó" if diff > 0 else "no superó"
        lines.append(f"- PY {signo} a Core en promedio por {diff:.4f} puntos de macro_f1.")

    def efecto_promedio(df: pd.DataFrame, col: str, label: str) -> str:
        g1 = df[df[col] == 1]["macro_f1"].mean()
        g0 = df[df[col] == 0]["macro_f1"].mean()
        if pd.isna(g1) or pd.isna(g0):
            return f"- No hay evidencia suficiente para estimar el efecto de {label}."
        d = g1 - g0
        dir_ = "mejora" if d > 0 else "empeora"
        return f"- {label}: encendido {dir_} en promedio {d:.4f} macro_f1 (1 vs 0)."

    lines.append(efecto_promedio(barrido, "llm_activo", "LLM"))
    lines.append(efecto_promedio(barrido, "sentimiento_activo", "sentimiento"))
    lines.append(efecto_promedio(barrido, "template_activo", "feat_had_template_block"))
    lines.append(efecto_promedio(barrido, "beto_activo", "BETO"))

    # Variante híbrida defendible para reporte metodológico
    # Criterio pragmático: top macro_f1 con toggles explícitos y sin depender de template si existe alternativa cercana.
    top10 = b_sorted.head(10).copy()
    sin_template = top10[top10["template_activo"] == 0]
    if not sin_template.empty:
        cand = sin_template.iloc[0]
        lines.append(
            f"- Variante defendible para reporte metodológico (menor dependencia de template): `{cand['nombre_variante']}` "
            f"(macro_f1={cand['macro_f1']:.4f})."
        )
    else:
        cand = top10.iloc[0]
        lines.append(
            f"- Variante defendible para reporte metodológico: `{cand['nombre_variante']}` "
            f"(macro_f1={cand['macro_f1']:.4f})."
        )

    # Comparación con mejores baselines textuales
    baselines = master[master["source"] == "baseline_texto"].copy()
    if not baselines.empty:
        bbest = baselines.sort_values("macro_f1", ascending=False).iloc[0]
        lines.append(
            f"- Mejor baseline textual de referencia: `{bbest['nombre_variante']}` con macro_f1={bbest['macro_f1']:.4f}."
        )
        diff = float(best["macro_f1"] - bbest["macro_f1"])
        lines.append(f"- Brecha mejor híbrido vs mejor baseline textual: {diff:.4f} macro_f1.")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def analizar_dependencia_beto(barrido: pd.DataFrame, out_path: Path) -> pd.DataFrame:
    if barrido.empty:
        df = pd.DataFrame()
        df.to_csv(out_path, index=False)
        return df

    # Resumen agregado por estado de BETO
    agg = (
        barrido.groupby("beto_activo", dropna=True)
        .agg(
            macro_f1_media=("macro_f1", "mean"),
            f1_ansiedad_media=("f1_ansiedad", "mean"),
            f1_depresion_media=("f1_depresion", "mean"),
            n=("nombre_variante", "count"),
        )
        .reset_index()
    )

    diff_row = {
        "beto_activo": "delta_1_menos_0",
        "macro_f1_media": np.nan,
        "f1_ansiedad_media": np.nan,
        "f1_depresion_media": np.nan,
        "n": np.nan,
    }
    if set(agg["beto_activo"].astype(str)) >= {"0", "1"}:
        a1 = agg.loc[agg["beto_activo"] == 1].iloc[0]
        a0 = agg.loc[agg["beto_activo"] == 0].iloc[0]
        diff_row = {
            "beto_activo": "delta_1_menos_0",
            "macro_f1_media": float(a1["macro_f1_media"] - a0["macro_f1_media"]),
            "f1_ansiedad_media": float(a1["f1_ansiedad_media"] - a0["f1_ansiedad_media"]),
            "f1_depresion_media": float(a1["f1_depresion_media"] - a0["f1_depresion_media"]),
            "n": np.nan,
        }

    out = pd.concat([agg, pd.DataFrame([diff_row])], ignore_index=True)
    out.to_csv(out_path, index=False)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Barrido sistemático del híbrido para análisis metodológico.")
    parser.add_argument("--eval-split", default="dev", choices=["dev", "test"])
    parser.add_argument("--feature-run-base", default="fe_20260310_082139")
    parser.add_argument("--ref-train-run", default="train_20260310_093418")
    parser.add_argument("--seed-fijo", type=int, default=42)
    parser.add_argument("--seeds-estabilidad", default="42,52,62")
    parser.add_argument("--top-c", type=int, default=3, help="Cantidad de variantes top para fase C (3 o 5).")
    parser.add_argument("--fases", default="A,B,C", help="Subconjunto de fases: A,B,C")
    args = parser.parse_args()

    fases_req = {x.strip().upper() for x in args.fases.split(",") if x.strip()}
    fases_validas = {"A", "B", "C"}
    fases_req = fases_req & fases_validas
    if not fases_req:
        raise BarridoError("No se seleccionaron fases válidas.")

    run_ts = ts_now()
    out_root = OUTPUTS_PATH / "barridos_hibridos" / run_ts
    logs_dir = out_root / "logs"
    pred_dir = out_root / "predicciones_por_fila"
    cm_dir = out_root / "matrices_confusion"
    imp_dir = out_root / "importancia_features"

    out_root.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    pred_dir.mkdir(parents=True, exist_ok=True)
    cm_dir.mkdir(parents=True, exist_ok=True)
    imp_dir.mkdir(parents=True, exist_ok=True)

    tmp_scripts = out_root / "_tmp_scripts"
    py06, py07 = convertir_notebooks(tmp_scripts)

    ejecuciones: list[Ejecucion] = []
    filas_barrido: list[dict[str, Any]] = []

    # -------------------------
    # Fase A
    # -------------------------
    fase_a_rows: list[dict[str, Any]] = []
    if "A" in fases_req:
        llm_opts = [0, 1]
        sent_opts = [0, 1]
        beto_opts = [0, 1]
        template_opts = [0, 1]

        for llm in llm_opts:
            for sent in sent_opts:
                for beto in beto_opts:
                    for tpl in template_opts:
                        variant = f"A_llm{llm}_sent{sent}_beto{beto}_tpl{tpl}"
                        train_id = sanitize_name(f"train_{variant}_{run_ts}")
                        flags = {
                            "llm": llm,
                            "beto": beto,
                            "template": tpl,
                            "feat": 1,
                            "rules": 1,
                            "medication": 1,
                            "sentiment": sent,
                        }
                        ex07, dfm = ejecutar_07(
                            py07=py07,
                            logs_dir=logs_dir,
                            run_id_train=train_id,
                            variant_name=variant,
                            feature_run_id=args.feature_run_base,
                            profile=None,
                            model=None,
                            seed=args.seed_fijo,
                            flags=flags,
                            eval_on=args.eval_split,
                        )
                        ex07.fase = "A"
                        ejecuciones.append(ex07)
                        if dfm.empty:
                            continue

                        tdir = OUTPUTS_PATH / train_id
                        for _, rr in dfm.iterrows():
                            row = rr.to_dict()
                            row["fase"] = "A"
                            norm = normalizar_fila_hibrida(row=row, run_id_train=train_id, source="barrido")
                            fase_a_rows.append(norm)
                            filas_barrido.append(norm)

                            profile = str(norm["perfil"])
                            model = str(norm["modelo"]).lower()
                            nv = str(norm["nombre_variante"])
                            pred_src = tdir / f"predicciones_{profile}_{model}_{args.eval_split}.csv"
                            cm_src = tdir / "figures" / f"{profile}_{model}_{args.eval_split}_confusion.png"
                            copiar_si_existe(pred_src, pred_dir / f"{sanitize_name(nv)}.csv")
                            copiar_si_existe(cm_src, cm_dir / f"{sanitize_name(nv)}.png")
                            extraer_importancias(tdir, profile, model.upper(), imp_dir, nv)

    df_a = pd.DataFrame(fase_a_rows)

    # -------------------------
    # Fase B
    # -------------------------
    fase_b_rows: list[dict[str, Any]] = []
    if "B" in fases_req and not df_a.empty:
        cands = select_fase_b_candidates(df_a)
        presets = build_fase_b_ablation_presets()

        for _, cand in cands.iterrows():
            base_flags = {
                "llm": int(cand.get("llm_activo", 1) if pd.notna(cand.get("llm_activo", np.nan)) else 1),
                "beto": int(cand.get("beto_activo", 1) if pd.notna(cand.get("beto_activo", np.nan)) else 1),
                "template": int(cand.get("template_activo", 1) if pd.notna(cand.get("template_activo", np.nan)) else 1),
                "feat": int(cand.get("feat_activo", 1) if pd.notna(cand.get("feat_activo", np.nan)) else 1),
                "rules": int(cand.get("reglas_activas", 1) if pd.notna(cand.get("reglas_activas", np.nan)) else 1),
                "medication": int(cand.get("medicacion_activa", 1) if pd.notna(cand.get("medicacion_activa", np.nan)) else 1),
                "sentiment": int(cand.get("sentimiento_activo", 1) if pd.notna(cand.get("sentimiento_activo", np.nan)) else 1),
            }

            perfil = str(cand["perfil"]).lower()
            modelo = str(cand["modelo"]).lower()
            if modelo == "tf-idf":
                continue

            feature_run = resolve_feature_base_from_row(cand)
            if not feature_run:
                continue

            seen_cfg: set[str] = set()
            for preset in presets:
                flags = dict(base_flags)
                for k, v in preset.items():
                    if k == "nombre":
                        continue
                    flags[k] = int(v)

                sig = json.dumps(flags, sort_keys=True)
                if sig in seen_cfg:
                    continue
                seen_cfg.add(sig)

                if all(v == base_flags.get(k) for k, v in flags.items() if k in base_flags):
                    # redundante con la variante base
                    continue

                var = f"B_{cand['nombre_variante']}_{preset['nombre']}"
                var = sanitize_name(var)
                train_id = sanitize_name(f"train_{var}_{run_ts}")

                ex07, dfm = ejecutar_07(
                    py07=py07,
                    logs_dir=logs_dir,
                    run_id_train=train_id,
                    variant_name=var,
                    feature_run_id=feature_run,
                    profile=perfil,
                    model=modelo,
                    seed=args.seed_fijo,
                    flags=flags,
                    eval_on=args.eval_split,
                )
                ex07.fase = "B"
                ejecuciones.append(ex07)
                if dfm.empty:
                    continue

                tdir = OUTPUTS_PATH / train_id
                for _, rr in dfm.iterrows():
                    row = rr.to_dict()
                    row["fase"] = "B"
                    norm = normalizar_fila_hibrida(row=row, run_id_train=train_id, source="barrido")
                    fase_b_rows.append(norm)
                    filas_barrido.append(norm)

                    profile = str(norm["perfil"])
                    model2 = str(norm["modelo"]).lower()
                    nv = str(norm["nombre_variante"])
                    pred_src = tdir / f"predicciones_{profile}_{model2}_{args.eval_split}.csv"
                    cm_src = tdir / "figures" / f"{profile}_{model2}_{args.eval_split}_confusion.png"
                    copiar_si_existe(pred_src, pred_dir / f"{sanitize_name(nv)}.csv")
                    copiar_si_existe(cm_src, cm_dir / f"{sanitize_name(nv)}.png")
                    extraer_importancias(tdir, profile, model2.upper(), imp_dir, nv)

    df_b = pd.DataFrame(fase_b_rows)

    # -------------------------
    # Fase C (estabilidad)
    # -------------------------
    fase_c_rows: list[dict[str, Any]] = []
    estabilidad_rows: list[dict[str, Any]] = []
    if "C" in fases_req:
        seeds = [int(x.strip()) for x in args.seeds_estabilidad.split(",") if x.strip()]
        base = pd.concat([df_a, df_b], ignore_index=True)
        if "macro_f1" not in base.columns or base.empty:
            top_n = 0
            top_base = pd.DataFrame()
        else:
            base = base.sort_values("macro_f1", ascending=False)
            top_n = max(1, min(args.top_c, len(base)))
            top_base = base.head(top_n)

        for _, cand in top_base.iterrows():
            perfil = str(cand["perfil"]).lower()
            modelo = str(cand["modelo"]).lower()
            feature_run = resolve_feature_base_from_row(cand)
            if not feature_run:
                continue

            base_flags = {
                "llm": int(cand.get("llm_activo", 1) if pd.notna(cand.get("llm_activo", np.nan)) else 1),
                "beto": int(cand.get("beto_activo", 1) if pd.notna(cand.get("beto_activo", np.nan)) else 1),
                "template": int(cand.get("template_activo", 1) if pd.notna(cand.get("template_activo", np.nan)) else 1),
                "feat": int(cand.get("feat_activo", 1) if pd.notna(cand.get("feat_activo", np.nan)) else 1),
                "rules": int(cand.get("reglas_activas", 1) if pd.notna(cand.get("reglas_activas", np.nan)) else 1),
                "medication": int(cand.get("medicacion_activa", 1) if pd.notna(cand.get("medicacion_activa", np.nan)) else 1),
                "sentiment": int(cand.get("sentimiento_activo", 1) if pd.notna(cand.get("sentimiento_activo", np.nan)) else 1),
            }

            base_name = str(cand["nombre_variante"])
            phase_c_this: list[dict[str, Any]] = []

            for seed in seeds:
                var = sanitize_name(f"C_{base_name}_seed{seed}")
                train_id = sanitize_name(f"train_{var}_{run_ts}")

                ex07, dfm = ejecutar_07(
                    py07=py07,
                    logs_dir=logs_dir,
                    run_id_train=train_id,
                    variant_name=var,
                    feature_run_id=feature_run,
                    profile=perfil,
                    model=modelo,
                    seed=seed,
                    flags=base_flags,
                    eval_on=args.eval_split,
                )
                ex07.fase = "C"
                ejecuciones.append(ex07)
                if dfm.empty:
                    continue

                tdir = OUTPUTS_PATH / train_id
                for _, rr in dfm.iterrows():
                    row = rr.to_dict()
                    row["fase"] = "C"
                    norm = normalizar_fila_hibrida(row=row, run_id_train=train_id, source="barrido")
                    norm["base_variante_c"] = base_name
                    phase_c_this.append(norm)
                    fase_c_rows.append(norm)
                    filas_barrido.append(norm)

                    profile = str(norm["perfil"])
                    model2 = str(norm["modelo"]).lower()
                    nv = str(norm["nombre_variante"])
                    pred_src = tdir / f"predicciones_{profile}_{model2}_{args.eval_split}.csv"
                    cm_src = tdir / "figures" / f"{profile}_{model2}_{args.eval_split}_confusion.png"
                    copiar_si_existe(pred_src, pred_dir / f"{sanitize_name(nv)}.csv")
                    copiar_si_existe(cm_src, cm_dir / f"{sanitize_name(nv)}.png")
                    extraer_importancias(tdir, profile, model2.upper(), imp_dir, nv)

            dfc = pd.DataFrame(phase_c_this)
            if not dfc.empty:
                estabilidad_rows.append({
                    "base_variante": base_name,
                    "n_corridas": int(len(dfc)),
                    "macro_f1_media": float(dfc["macro_f1"].mean()),
                    "macro_f1_std": float(dfc["macro_f1"].std(ddof=0)),
                    "macro_f1_max": float(dfc["macro_f1"].max()),
                    "macro_f1_min": float(dfc["macro_f1"].min()),
                })

    df_c = pd.DataFrame(fase_c_rows)
    df_est = pd.DataFrame(estabilidad_rows)

    # -------------------------
    # Consolidación maestra
    # -------------------------
    df_barrido = pd.DataFrame(filas_barrido)

    refs = filas_baselines() + filas_hibrido_referencia(args.ref_train_run, eval_on=args.eval_split)
    df_refs = pd.DataFrame(refs)

    master = pd.concat([df_refs, df_barrido], ignore_index=True, sort=False)

    cols_master = [
        "source", "nombre_variante", "run_id_features", "run_id_features_core", "run_id_features_py",
        "run_id_train", "perfil", "modelo", "llm_activo", "sentimiento_activo", "beto_activo",
        "contexto_activo", "text_backbone", "context_prefixes",
        "template_activo", "feat_activo", "reglas_activas", "medicacion_activa", "seed", "n_features",
        "n_train", "n_eval", "macro_f1", "balanced_accuracy", "precision_macro", "recall_macro",
        "f1_ansiedad", "f1_depresion", "soporte_ansiedad", "soporte_depresion", "eval_split", "fase",
        "cv_macro_f1",
    ]
    for c in cols_master:
        if c not in master.columns:
            master[c] = np.nan
    master = master[cols_master]

    master_path = out_root / "tabla_maestra_comparativa.csv"
    master.to_csv(master_path, index=False)

    xlsx_path = out_root / "tabla_maestra_comparativa.xlsx"
    try:
        master.to_excel(xlsx_path, index=False)
    except Exception:
        pass

    ranking = (
        df_barrido.sort_values("macro_f1", ascending=False)
        if not df_barrido.empty else pd.DataFrame()
    )
    ranking_path = out_root / "ranking_variantes.csv"
    ranking.to_csv(ranking_path, index=False)

    est_path = out_root / "estabilidad_variantes.csv"
    df_est.to_csv(est_path, index=False)

    beto_path = out_root / "analisis_dependencia_beto.csv"
    analizar_dependencia_beto(df_barrido, beto_path)

    resumen_md = out_root / "resumen_interpretativo.md"
    summarize_interpretativo(master=master, barrido=df_barrido, estabilidad=df_est, out_path=resumen_md)

    resumen = {
        "timestamp": run_ts,
        "out_root": str(out_root),
        "fases_ejecutadas": sorted(fases_req),
        "eval_split": args.eval_split,
        "seed_fijo": args.seed_fijo,
        "feature_run_base": args.feature_run_base,
        "seeds_estabilidad": args.seeds_estabilidad,
        "top_c": args.top_c,
        "ref_train_run": args.ref_train_run,
        "n_ejecuciones": len(ejecuciones),
        "n_ok": int(sum(1 for e in ejecuciones if e.ok)),
        "n_fail": int(sum(1 for e in ejecuciones if not e.ok)),
        "n_variantes_fase_a": int(len(df_a)),
        "n_variantes_fase_b": int(len(df_b)),
        "n_variantes_fase_c": int(len(df_c)),
        "n_total_barrido": int(len(df_barrido)),
        "master_csv": str(master_path),
        "ranking_csv": str(ranking_path),
        "resumen_interpretativo_md": str(resumen_md),
        "analisis_dependencia_beto_csv": str(beto_path),
        "ejecuciones": [asdict(e) for e in ejecuciones],
    }
    with open(out_root / "resumen_barrido.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("Barrido finalizado.")
    print("Salida:", out_root)
    print("Master:", master_path)
    print("Ranking:", ranking_path)
    print("Resumen:", out_root / "resumen_barrido.json")


if __name__ == "__main__":
    main()
