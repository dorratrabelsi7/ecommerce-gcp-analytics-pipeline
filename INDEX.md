# 📑 INDEX - TOUS LES FICHIERS

## 🎯 FICHIERS CRITIQUES (À UTILISER)

### Tests & Déploiement
- **`beam/test_gcp_pipeline.py`** - Tests GCP (nouveau!)
- **`beam/publish_test_data.py`** - Pub/Sub publisher
- **`deploy/deploy_dataflow.sh`** - Déploiement automatisé

### Pipeline Principal
- **`beam/dataflow_pipeline_gcp.py`** - Pipeline production (460+ lignes)

---

## 📖 DOCUMENTATION (À LIRE)

### 🚀 Démarrage rapide
1. **[START_HERE.md](START_HERE.md)** ← LIRE EN PREMIER
   - 5 commandes pour commencer
   - Résultats attendus

2. **[RESUME_FINAL.md](RESUME_FINAL.md)**
   - État complet du projet
   - Commandes rapides
   - Timeline estimée

3. **[QUICK_ACCESS.md](QUICK_ACCESS.md)**
   - Où trouver quoi
   - Workflow complet
   - Checklist d'accès

### 🏗️ Architecture & Explication
4. **[SOLUTION_COMPLETE.md](SOLUTION_COMPLETE.md)**
   - Solution finale complète
   - Tableau comparatif
   - Prochaines étapes

5. **[beam/SOLUTION_FINAL.md](beam/SOLUTION_FINAL.md)**
   - Résumé solution
   - Livrables attendus
   - Architecture

6. **[CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md](CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md)**
   - Pourquoi Dataflow
   - Évolution de la solution
   - Leçons apprises

### ☁️ Guide GCP Détaillé
7. **[beam/DATAFLOW_GCP_GUIDE.md](beam/DATAFLOW_GCP_GUIDE.md)**
   - Déploiement étape par étape
   - Architecture technique
   - Troubleshooting GCP

### 📤 GitHub & Versioning
8. **[README_GITHUB.md](README_GITHUB.md)**
   - README formaté pour GitHub
   - Utilisation et exemples
   - Licence

9. **[GITHUB_PUSH_GUIDE.md](GITHUB_PUSH_GUIDE.md)**
   - Guide push sur GitHub
   - Configuration Git
   - Troubleshooting Git

### 📋 État du Projet
10. **[PIPELINE_READY.md](PIPELINE_READY.md)**
    - État actuel (prêt!)
    - Test GCP en 3 étapes
    - GitHub push en 5 étapes

---

## 🔧 FICHIERS DE CONFIGURATION

### Python & Dépendances
- **`requirements.txt`** - Packages Python à installer
- **`setup.py`** - Setup package Python

### Contrôle de version
- **`.gitignore`** - Fichiers à ignorer (credentials, data, venv)

### Schémas
- **`beam/schemas/`** - Schémas BigQuery JSON

---

## 📊 DONNÉES DE TEST

### Fichiers CSV/JSON
```
data/raw/
├── clients.csv
├── orders.csv
├── incidents.csv
├── page_views.csv
└── products.csv
```

### Utilisation
```bash
python beam/publish_test_data.py \
    --project ecommerce-494010 \
    --input data/raw/orders.csv \
    --topic orders-realtime \
    --rate 5
```

---

## 📂 STRUCTURE COMPLÈTE

```
ecommerce-gcp-analytics-pipeline/
│
├── 📖 DOCUMENTATION (Racine)
│   ├── START_HERE.md ← Lire en premier!
│   ├── RESUME_FINAL.md
│   ├── QUICK_ACCESS.md
│   ├── SOLUTION_COMPLETE.md
│   ├── CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md
│   ├── PIPELINE_READY.md
│   ├── README_GITHUB.md
│   ├── GITHUB_PUSH_GUIDE.md
│   └── INDEX.md (ce fichier)
│
├── beam/
│   ├── 🔧 PIPELINE
│   │   ├── dataflow_pipeline_gcp.py (460+ lignes) ← PRINCIPAL
│   │   ├── publish_test_data.py
│   │   └── test_gcp_pipeline.py (NEW!)
│   │
│   ├── 📖 DOCUMENTATION
│   │   ├── DATAFLOW_GCP_GUIDE.md
│   │   ├── SOLUTION_FINAL.md
│   │   ├── DIRECTRUNNER_GUIDE.md (ancien, ignorer)
│   │   └── README_PIPELINES.md (ancien, ignorer)
│   │
│   ├── 📊 SCHÉMAS
│   │   └── schemas/ (BigQuery JSON schemas)
│   │
│   └── ⚙️ TESTS
│       └── validate_output.py (ancien, ignorer)
│
├── deploy/
│   └── 🚀 DÉPLOIEMENT
│       ├── deploy_dataflow.sh ← UTILISER
│       ├── setup_gcp.sh
│       ├── deploy_function.sh
│       └── load_data.sh
│
├── scripts/
│   ├── generate_data.py
│   ├── load_to_bq.py
│   ├── prepare_data.py
│   ├── simulate_realtime.py
│   └── upload_and_load.py
│
├── sql/
│   ├── 01_create_tables.sql
│   ├── 02_create_views.sql
│   ├── 03_advanced_analytics.sql
│   └── 04_scheduled_queries.sql
│
├── data/
│   ├── raw/ (données brutes CSV/JSON)
│   └── clean/ (données nettoyées)
│
├── docs/
│   ├── architecture.md
│   ├── cleaning_report.txt
│   └── data_generation_report.txt
│
├── monitoring/
│   ├── health_check.py
│   └── setup_alerts.py
│
├── functions/
│   └── process_upload/
│       ├── main.py
│       └── requirements.txt
│
├── ⚙️ CONFIGURATION
│   ├── requirements.txt ← A INSTALLER
│   ├── setup.py
│   ├── .gitignore ← Fichiers ignorés
│   └── .env (local, pas committé)
│
└── venv312/ (ignorer, local)
```

---

## 🎯 ORDRE DE LECTURE RECOMMANDÉ

### 1️⃣ Commencer (5 min)
→ Lire **[START_HERE.md](START_HERE.md)**

### 2️⃣ Comprendre (10 min)
→ Lire **[RESUME_FINAL.md](RESUME_FINAL.md)**

### 3️⃣ Accéder (2 min)
→ Consulter **[QUICK_ACCESS.md](QUICK_ACCESS.md)**

### 4️⃣ Déployer (15 min)
→ Exécuter:
```bash
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1
```

### 5️⃣ Tester (10 min)
→ Exécuter:
```bash
python beam/publish_test_data.py --project ecommerce-494010 ...
```

### 6️⃣ Approfondir (30 min)
→ Lire **[beam/DATAFLOW_GCP_GUIDE.md](beam/DATAFLOW_GCP_GUIDE.md)**

### 7️⃣ Pousser sur GitHub (5 min)
→ Consulter **[GITHUB_PUSH_GUIDE.md](GITHUB_PUSH_GUIDE.md)**

---

## ✅ CHECKLIST D'ACCÈS

Vérifier que vous pouvez accéder à:

- [ ] `beam/dataflow_pipeline_gcp.py` - Pipeline
- [ ] `beam/publish_test_data.py` - Publisher
- [ ] `beam/test_gcp_pipeline.py` - Tests
- [ ] `deploy/deploy_dataflow.sh` - Déploiement
- [ ] `START_HERE.md` - Documentation
- [ ] `data/raw/` - Données de test
- [ ] `requirements.txt` - Dépendances
- [ ] `.gitignore` - Git config

---

## 🔍 TROUVER RAPIDEMENT

### Je veux...
- **Démarrer** → [START_HERE.md](START_HERE.md)
- **Tester GCP** → `python beam/test_gcp_pipeline.py ...`
- **Déployer** → `bash deploy/deploy_dataflow.sh ...`
- **Publier données** → `python beam/publish_test_data.py ...`
- **Comprendre l'architecture** → [SOLUTION_COMPLETE.md](SOLUTION_COMPLETE.md)
- **Déboguer** → [beam/DATAFLOW_GCP_GUIDE.md](beam/DATAFLOW_GCP_GUIDE.md)
- **Pousser GitHub** → [GITHUB_PUSH_GUIDE.md](GITHUB_PUSH_GUIDE.md)
- **Vue d'ensemble** → [RESUME_FINAL.md](RESUME_FINAL.md)

---

## 📊 RÉSUMÉ PAR TYPE

### 🚀 Exécutables
- `beam/dataflow_pipeline_gcp.py` - Python
- `beam/publish_test_data.py` - Python
- `beam/test_gcp_pipeline.py` - Python (NEW!)
- `deploy/deploy_dataflow.sh` - Bash

### 📖 Documentation
- 10 fichiers Markdown
- Guides complets
- Explications détaillées

### 🔧 Configuration
- `requirements.txt`
- `setup.py`
- `.gitignore`

### 📊 Données
- CSV files in `data/raw/`

### 📦 Dépendances
- Listed in `requirements.txt`
- Install with: `pip install -r requirements.txt`

---

## 🎓 TUTORIELS INTÉGRÉS

### Tutoriel 1: Tester GCP
```bash
python beam/test_gcp_pipeline.py --project ecommerce-494010 --region europe-west1
```
→ Consultez [START_HERE.md](START_HERE.md)

### Tutoriel 2: Déployer
```bash
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1
```
→ Consultez [beam/DATAFLOW_GCP_GUIDE.md](beam/DATAFLOW_GCP_GUIDE.md)

### Tutoriel 3: Publier données
```bash
python beam/publish_test_data.py --project ecommerce-494010 --input data/raw/orders.csv --topic orders-realtime --rate 5
```
→ Consultez [QUICK_ACCESS.md](QUICK_ACCESS.md)

### Tutoriel 4: GitHub
```bash
git push -u origin main
```
→ Consultez [GITHUB_PUSH_GUIDE.md](GITHUB_PUSH_GUIDE.md)

---

**🎉 Prêt? Commencez par [START_HERE.md](START_HERE.md)!**
