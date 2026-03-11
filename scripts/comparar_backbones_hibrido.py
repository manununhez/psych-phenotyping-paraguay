#!/usr/bin/env python3
"""Comparación controlada de backbones contextuales dentro del híbrido (solo dev).

Escenario fijo por variante:
- perfil: py
- modelo: XGB
- llm: 0
- sentimiento: 0
- template: 0
- feat: 0
- rules: 1
- medication: 0
- contexto: 1
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
OUTPUTS_PATH = REPO_ROOT / "data" / "outputs"
DATA_PATH = REPO_ROOT / "data"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PYTHON_EXEC = (
    os.getenv("BACKBONE_PYTHON")
    or (str(VENV_PY) if VENV_PY.exists() else sys.executable)
)


@dataclass
class Corrida:
    backbone: str
    ok: bool
    run_id_features: str | None
    run_id_train: str | None
    duracion_seg: float
    mensaje: str
    log_06: str | None = None
    log_07: str | None = None


def ts_now() -> str:
    return pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")


def sanitize(s: str, max_len: int = 120) -> str:
    s = re.sub(r"[^a-zA-Z0-9_\-\.]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len]


def run_cmd(cmd: list[str], env: dict[str, str], log_path: Path) -> tuple[bool, float, int]:
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
    return proc.returncode == 0, time.time() - start, proc.returncode


def convertir_notebooks(tmp_dir: Path) -> tuple[Path, Path]:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cmds = [
        ["jupyter", "nbconvert", "--to", "script", str(NB06), "--output-dir", str(tmp_dir)],
        ["jupyter", "nbconvert", "--to", "script", str(NB07), "--output-dir", str(tmp_dir)],
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    for cmd in cmds:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                "Falló nbconvert.\n"
                f"CMD: {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
    py06 = tmp_dir / "06_ingenieria_features_hibridas.py"
    py07 = tmp_dir / "07_entrenamiento_modelos_hibridos.py"
    if not py06.exists() or not py07.exists():
        raise RuntimeError("No se generaron scripts de 06/07 tras nbconvert.")
    return py06, py07


def _leer_metricas_baseline_textual() -> pd.DataFrame:
    defs = {
        "TF-IDF": DATA_PATH / "tfidf_eval.csv",
        "BETO": DATA_PATH / "beto_eval.csv",
        "ROBERTA_CLINICAL": DATA_PATH / "roberta_clinical_eval.csv",
        "ROBERTA_BIOMEDICAL": DATA_PATH / "roberta_biomedical_eval.csv",
        "DUMMY": DATA_PATH / "dummy_eval.csv",
    }
    rows = []
    for nombre, path in defs.items():
        if not path.exists():
            continue
        d = pd.read_csv(path)
        if d.empty:
            continue
        r = d.iloc[0].to_dict()
        rows.append(
            {
                "modelo": nombre,
                "macro_f1": float(r.get("f1_macro", np.nan)),
                "balanced_accuracy": float(r.get("balanced_acc", r.get("recall_macro", np.nan))),
                "eval_split": str(r.get("eval_split", "dev")),
            }
        )
    return pd.DataFrame(rows)


def _copiar_si_existe(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _run_backbone(
    py06: Path,
    py07: Path,
    backbone: str,
    ts: str,
    seed: int,
    logs_dir: Path,
) -> tuple[Corrida, pd.DataFrame]:
    run_id_features = f"fe_backbone_{backbone}_{ts}"
    run_id_train = sanitize(f"train_backbone_{backbone}_{ts}")

    env06 = os.environ.copy()
    env06["PYTHONPATH"] = str(REPO_ROOT)
    env06["FE_RUN_ID"] = run_id_features
    env06["FE_USE_LLM"] = "0"
    env06["FE_COMPUTE_SENTIMENT"] = "0"
    env06["FE_COMPUTE_CONTEXT"] = "1"
    env06["FE_COMPUTE_BETO"] = "1"  # alias legacy
    env06["FE_TEXT_BACKBONE"] = backbone
    env06["FE_CACHE_KEY"] = run_id_features

    log06 = logs_dir / f"06_{backbone}.log"
    ok06, dur06, rc06 = run_cmd([PYTHON_EXEC, str(py06)], env06, log06)
    if not ok06:
        return (
            Corrida(
                backbone=backbone,
                ok=False,
                run_id_features=run_id_features,
                run_id_train=None,
                duracion_seg=dur06,
                mensaje=f"fallo_06_exit_{rc06}",
                log_06=str(log06),
                log_07=None,
            ),
            pd.DataFrame(),
        )

    env07 = os.environ.copy()
    env07["PYTHONPATH"] = str(REPO_ROOT)
    env07["TRAIN_RUN_ID"] = run_id_train
    env07["TRAIN_VARIANT_NAME"] = f"cmp_backbone_{backbone}"
    env07["TRAIN_EVAL_ON"] = "dev"
    env07["TRAIN_FEATURE_RUN_ID_CORE"] = f"{run_id_features}_core"
    env07["TRAIN_FEATURE_RUN_ID_PY"] = f"{run_id_features}_py"
    env07["TRAIN_MODELS"] = "xgb"
    env07["TRAIN_PROFILES"] = "py"
    env07["TRAIN_USE_RANDOM_SEARCH"] = "0"
    env07["TRAIN_SEED"] = str(seed)
    env07["TRAIN_USE_XGB"] = "1"
    env07["TRAIN_USE_LLM"] = "0"
    env07["TRAIN_USE_TEMPLATE"] = "0"
    env07["TRAIN_USE_FEAT"] = "0"
    env07["TRAIN_USE_RULES"] = "1"
    env07["TRAIN_USE_MEDICATION"] = "0"
    env07["TRAIN_USE_SENTIMENT"] = "0"
    env07["TRAIN_USE_CONTEXT"] = "1"
    env07["TRAIN_USE_BETO"] = "1"  # alias legacy

    log07 = logs_dir / f"07_{backbone}.log"
    ok07, dur07, rc07 = run_cmd([PYTHON_EXEC, str(py07)], env07, log07)
    if not ok07:
        return (
            Corrida(
                backbone=backbone,
                ok=False,
                run_id_features=run_id_features,
                run_id_train=run_id_train,
                duracion_seg=dur06 + dur07,
                mensaje=f"fallo_07_exit_{rc07}",
                log_06=str(log06),
                log_07=str(log07),
            ),
            pd.DataFrame(),
        )

    comp_path = OUTPUTS_PATH / run_id_train / "comparacion_modelos_dev.csv"
    if not comp_path.exists():
        return (
            Corrida(
                backbone=backbone,
                ok=False,
                run_id_features=run_id_features,
                run_id_train=run_id_train,
                duracion_seg=dur06 + dur07,
                mensaje="sin_comparacion_modelos_dev",
                log_06=str(log06),
                log_07=str(log07),
            ),
            pd.DataFrame(),
        )

    dfm = pd.read_csv(comp_path)
    dfm = dfm[
        (dfm["profile"].astype(str).str.lower() == "py")
        & (dfm["model"].astype(str).str.upper() == "XGB")
    ].copy()
    return (
        Corrida(
            backbone=backbone,
            ok=not dfm.empty,
            run_id_features=run_id_features,
            run_id_train=run_id_train,
            duracion_seg=dur06 + dur07,
            mensaje="ok" if not dfm.empty else "sin_fila_py_xgb",
            log_06=str(log06),
            log_07=str(log07),
        ),
        dfm,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparación controlada de backbones en híbrido.")
    parser.add_argument("--backbones", default="beto,roberta_clinical", help="Lista separada por comas.")
    parser.add_argument("--incluir-biomedical", default="0", choices=["0", "1"])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    backbones = [x.strip().lower() for x in args.backbones.split(",") if x.strip()]
    valid = {"beto", "roberta_clinical", "roberta_biomedical"}
    backbones = [b for b in backbones if b in valid]
    if args.incluir_biomedical == "1" and "roberta_biomedical" not in backbones:
        backbones.append("roberta_biomedical")
    if not backbones:
        raise RuntimeError("No se indicaron backbones válidos.")

    ts = ts_now()
    out_root = OUTPUTS_PATH / f"comparacion_backbones_hibrido_{ts}"
    logs_dir = out_root / "logs"
    pred_dir = out_root / "predicciones_por_fila"
    meta_dir = out_root / "metadatos_backbone"
    out_root.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    pred_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    py06, py07 = convertir_notebooks(out_root / "_tmp_scripts")

    corridas: list[Corrida] = []
    rows: list[dict[str, Any]] = []
    for backbone in backbones:
        corrida, dfm = _run_backbone(
            py06=py06,
            py07=py07,
            backbone=backbone,
            ts=ts,
            seed=args.seed,
            logs_dir=logs_dir,
        )
        corridas.append(corrida)
        if dfm.empty:
            continue

        row = dfm.iloc[0].to_dict()
        out_row = {
            "backbone": backbone,
            "perfil": "py",
            "modelo": "XGB",
            "macro_f1": float(row.get("macro_f1", np.nan)),
            "balanced_accuracy": float(row.get("balanced_acc", np.nan)),
            "f1_ansiedad": float(row.get("f1_ansiedad", np.nan)),
            "f1_depresion": float(row.get("f1_depresion", np.nan)),
            "n_features": float(row.get("n_features", np.nan)),
            "seed": float(row.get("seed", args.seed)),
            "run_id_features": corrida.run_id_features,
            "run_id_train": corrida.run_id_train,
            "text_backbone": row.get("text_backbone", backbone),
            "context_prefixes": row.get("context_prefixes", np.nan),
            "eval_split": row.get("eval_split", "dev"),
        }
        rows.append(out_row)

        # Copias de predicciones y metadatos
        tdir = OUTPUTS_PATH / str(corrida.run_id_train)
        pred_src = tdir / "predicciones_py_xgb_dev.csv"
        _copiar_si_existe(pred_src, pred_dir / f"{backbone}_predicciones_py_xgb_dev.csv")
        meta_train = tdir / "resumen_entrenamiento.json"
        _copiar_si_existe(meta_train, meta_dir / f"{backbone}_resumen_entrenamiento.json")
        cfg_feat = (REPO_ROOT / "data" / "processed" / f"{corrida.run_id_features}_config.json")
        _copiar_si_existe(cfg_feat, meta_dir / f"{backbone}_config_features.json")

    df = pd.DataFrame(rows)
    baselines = _leer_metricas_baseline_textual()
    best_baseline_macro = np.nan
    if not baselines.empty and "macro_f1" in baselines.columns:
        best_baseline_macro = float(baselines["macro_f1"].max())

    if not df.empty:
        df["brecha_vs_mejor_baseline_textual"] = df["macro_f1"] - best_baseline_macro
        if (df["backbone"] == "beto").any():
            beto_macro = float(df.loc[df["backbone"] == "beto", "macro_f1"].iloc[0])
            df["brecha_vs_hibrido_beto"] = df["macro_f1"] - beto_macro
        else:
            df["brecha_vs_hibrido_beto"] = np.nan
    else:
        df["brecha_vs_mejor_baseline_textual"] = []
        df["brecha_vs_hibrido_beto"] = []

    csv_path = out_root / "comparacion_backbones_hibrido.csv"
    json_path = out_root / "comparacion_backbones_hibrido.json"
    md_path = out_root / "resumen_backbones_hibrido.md"

    df.to_csv(csv_path, index=False)

    selection_latest = OUTPUTS_PATH / "transformer_baseline_selection_latest.json"
    selection_payload = {}
    if selection_latest.exists():
        try:
            selection_payload = json.loads(selection_latest.read_text(encoding="utf-8"))
            shutil.copy2(selection_latest, out_root / selection_latest.name)
        except Exception:
            selection_payload = {}

    payload = {
        "timestamp": ts,
        "out_root": str(out_root),
        "seed": args.seed,
        "backbones_solicitados": backbones,
        "corridas": [asdict(c) for c in corridas],
        "tabla_comparativa_csv": str(csv_path),
        "best_baseline_textual_macro_f1": best_baseline_macro,
        "transformer_selection_04c": selection_payload.get("mejor_transformer_baseline", {}),
        "filas_validas": df.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Resumen de comparación de backbones en híbrido")
    lines.append("")
    lines.append("- Split evaluado: `dev`.")
    lines.append("- Configuración fija: `py + XGB`, sin `feat_*`, sin `rule_medication_*`, sin template, sin sentimiento, sin LLM.")
    lines.append(f"- Seed: {args.seed}.")
    if selection_payload:
        sel = (selection_payload.get("mejor_transformer_baseline", {}) or {}).get("modelo")
        lines.append(f"- Mejor Transformer baseline en 04c (artefacto): `{sel}`.")
    lines.append("")
    if df.empty:
        lines.append("No se obtuvieron filas válidas de comparación.")
    else:
        best = df.sort_values("macro_f1", ascending=False).iloc[0]
        lines.append(
            f"- Mejor backbone híbrido en este barrido controlado: `{best['backbone']}` con macro_f1={best['macro_f1']:.4f}."
        )
        if (df["backbone"] == "beto").any() and (df["backbone"] == "roberta_clinical").any():
            m_beto = float(df.loc[df["backbone"] == "beto", "macro_f1"].iloc[0])
            m_rc = float(df.loc[df["backbone"] == "roberta_clinical", "macro_f1"].iloc[0])
            lines.append(f"- Delta roberta_clinical vs beto (macro_f1): {m_rc - m_beto:.4f}.")
    lines.append("")
    lines.append(f"- Tabla completa: `{csv_path}`.")
    lines.append(f"- Metadatos: `{json_path}`.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Actualiza manifiesto de validez de artefactos de backbone para consumo posterior (09b).
    manifest_cmd = [
        PYTHON_EXEC,
        str(REPO_ROOT / "scripts" / "audit" / "registrar_artefactos_backbone.py"),
    ]
    try:
        subprocess.run(
            manifest_cmd,
            cwd=str(REPO_ROOT),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        pass

    print(out_root)


if __name__ == "__main__":
    main()
