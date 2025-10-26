# 🇵🇾 Psych Phenotyping Paraguay

**Hybrid NLP system for detection of anxiety and depression in clinical notes**,  
adapting the [Spanish Psych Phenotyping](https://github.com/clarafrydman/Spanish_Psych_Phenotyping) project  
to the linguistic and clinical context of Paraguay.

---

## 📘 Structure

psych-phenotyping-paraguay/
├── notebooks/ → reproducible notebooks (Colab-ready)
├── lexicons/ → Paraguayan lexicons and context rules
├── experiments/ → saved models, logs, and reports
├── scripts/ → helper scripts for training and evaluation
└── Spanish_Psych_Phenotyping_PY/ → adapted version of the Colombian project


---

## 🧠 Project objectives

1. Reproduce and evaluate the Spanish Psych Phenotyping pipeline.
2. Adapt lexicons and context rules to Paraguayan Spanish.
3. Integrate rule-based features with machine learning models (TF-IDF / BETO).
4. Extend the dataset using weak labeling.
5. Produce a reproducible, explainable baseline for clinical NLP in Paraguay.

---

## ⚙️ Setup

```bash
git clone https://github.com/manununhez/psych-phenotyping-paraguay.git
cd psych-phenotyping-paraguay
pip install -r requirements.txt

### Setup local
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

