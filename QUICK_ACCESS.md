# 🗂️ STRUCTURE & ACCÈS RAPIDE

## 📁 Où trouver quoi

### 🧪 TESTER EN GCP

**Fichier:** `beam/test_gcp_pipeline.py`

```bash
python beam/test_gcp_pipeline.py \
    --project ecommerce-494010 \
    --region europe-west1
```

**Ce qu'il teste:**
- ✅ Authentification GCP
- ✅ Connexion Pub/Sub
- ✅ Connexion BigQuery
- ✅ Publication messages test
- ✅ Vérification Dataflow

---

### 🚀 DÉPLOYER LE PIPELINE

**Fichier:** `deploy/deploy_dataflow.sh`

```bash
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1
```

**Ce qu'il fait:**
- ✅ Crée Cloud Storage bucket
- ✅ Crée Pub/Sub topics
- ✅ Crée BigQuery dataset
- ✅ Crée tables BigQuery
- ✅ Déploie pipeline Dataflow

---

### 📊 PUBLIER LES DONNÉES

**Fichier:** `beam/publish_test_data.py`

```bash
python beam/publish_test_data.py \
    --project ecommerce-494010 \
    --input data/raw/orders.csv \
    --topic orders-realtime \
    --rate 5
```

**Options:**
- `--input` - Fichier CSV/JSON à publier
- `--topic` - Topic Pub/Sub cible
- `--rate` - Vitesse en msg/sec

**Topics disponibles:**
- `orders-realtime`
- `clients-realtime`
- `incidents-realtime`
- `pageviews-realtime`

---

### 💾 PIPELINE PRINCIPAL

**Fichier:** `beam/dataflow_pipeline_gcp.py` (460+ lignes)

**Composants:**
- ✅ Lecture depuis Pub/Sub (4 streams)
- ✅ Validation des données
- ✅ Nettoyage (nulls, doublons)
- ✅ Enrichissement
- ✅ Calcul de métriques
- ✅ Écriture vers BigQuery
- ✅ Gestion des erreurs

**À NE PAS modifier** - Pipeline de production!

---

### 📖 DOCUMENTATION

#### 🚀 Démarrer
- **[START_HERE.md](START_HERE.md)** - 5 commandes pour commencer
- **[PIPELINE_READY.md](PIPELINE_READY.md)** - État du pipeline

#### 🏗️ Architecture
- **[SOLUTION_COMPLETE.md](SOLUTION_COMPLETE.md)** - Vue complète
- **[beam/SOLUTION_FINAL.md](beam/SOLUTION_FINAL.md)** - Détails architecture
- **[beam/DATAFLOW_GCP_GUIDE.md](beam/DATAFLOW_GCP_GUIDE.md)** - Guide complet

#### 📝 Explications
- **[CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md](CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md)** - Pourquoi Dataflow
- **[beam/SOLUTION_FINAL.md](beam/SOLUTION_FINAL.md)** - Résumé solution

#### 📤 GitHub
- **[README_GITHUB.md](README_GITHUB.md)** - README pour GitHub
- **[GITHUB_PUSH_GUIDE.md](GITHUB_PUSH_GUIDE.md)** - Guide push GitHub

---

### 🔧 CONFIGURATION

**Fichier:** `requirements.txt`

```bash
pip install -r requirements.txt
```

**Packages clés:**
- apache-beam[gcp]
- google-cloud-pubsub
- google-cloud-bigquery
- google-auth

---

### ⚙️ DÉPLOIEMENT AUTOMATISÉ

**Fichier:** `deploy/deploy_dataflow.sh`

```bash
# Utilisation
bash deploy/deploy_dataflow.sh PROJECT_ID REGION

# Exemple
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1
```

---

### 📊 DONNÉES DE TEST

**Fichiers:** `data/raw/`

```
data/raw/
├── clients.csv
├── orders.csv
├── incidents.csv
├── page_views.csv
└── products.csv
```

**Publier les données:**
```bash
python beam/publish_test_data.py \
    --project ecommerce-494010 \
    --input data/raw/orders.csv \
    --topic orders-realtime \
    --rate 5
```

---

## 🎯 WORKFLOW COMPLET

### 1️⃣ Tester GCP (5 minutes)
```bash
python beam/test_gcp_pipeline.py \
    --project ecommerce-494010 \
    --region europe-west1
```

✅ **Attend:** Tous les tests en PASS

---

### 2️⃣ Déployer (15 minutes)
```bash
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1
```

✅ **Attend:** Job ID du pipeline

---

### 3️⃣ Publier les données (5 minutes)
```bash
python beam/publish_test_data.py \
    --project ecommerce-494010 \
    --input data/raw/orders.csv \
    --topic orders-realtime \
    --rate 5
```

✅ **Attend:** Messages publiés

---

### 4️⃣ Vérifier BigQuery (1 minute)
```bash
bq query --use_legacy_sql=false '
    SELECT COUNT(*) as total 
    FROM `ecommerce-494010.ecommerce_analytics.orders_stream`
'
```

✅ **Attend:** Nombre de records > 0

---

### 5️⃣ Pousser sur GitHub (5 minutes)
```bash
git init
git add .
git commit -m "Initial commit: Dataflow pipeline"
git remote add origin https://github.com/YOUR_USERNAME/...
git branch -M main
git push -u origin main
```

✅ **Attend:** Code sur GitHub

---

## 📋 FICHIERS CRITIQUES

### À utiliser
```
✅ beam/dataflow_pipeline_gcp.py     - Pipeline production
✅ beam/publish_test_data.py         - Pub/Sub publisher
✅ beam/test_gcp_pipeline.py         - Tests (NEW!)
✅ deploy/deploy_dataflow.sh         - Déploiement
✅ requirements.txt                  - Dependencies
✅ START_HERE.md                     - Quick start
```

### À ignorer (dans .gitignore)
```
❌ venv312/                          - Virtual env
❌ data/raw/*.csv                    - Fichiers bruts
❌ output/                           - Résultats
❌ *.json                            - Credentials
❌ logs/                             - Log files
```

---

## 🔐 CREDENTIALS & SECRETS

**IMPORTANT:** Ne JAMAIS committer:
- ❌ `credentials.json`
- ❌ `service-account-key.json`
- ❌ `.env` avec API keys
- ❌ Tokens d'accès

**Utiliser à la place:**
- ✅ `gcloud auth` (CLI)
- ✅ Service accounts (GCP)
- ✅ Environment variables (locales)

---

## 📈 COMMANDES ESSENTIELLES

### GCP
```bash
# Auth
gcloud auth login
gcloud config set project ecommerce-494010

# Dataflow
gcloud dataflow jobs list --region europe-west1
gcloud dataflow jobs describe JOB_ID --region europe-west1

# BigQuery
bq ls ecommerce_analytics
bq query 'SELECT * FROM ecommerce_analytics.orders_stream LIMIT 10'

# Pub/Sub
gcloud pubsub topics list
gcloud pubsub topics publish orders-realtime --message '...'
```

### Git
```bash
# Init
git init
git config user.name "Your Name"

# Add & Commit
git add .
git commit -m "Message"

# Push
git remote add origin https://github.com/...
git push -u origin main

# Status
git status
git log
```

### Python
```bash
# Venv
python -m venv venv
source venv/bin/activate

# Install
pip install -r requirements.txt

# Test
python beam/test_gcp_pipeline.py --project ecommerce-494010

# Publish
python beam/publish_test_data.py --project ecommerce-494010 ...
```

---

## 🎯 RAPIDE REFERENCE

| Besoin | Fichier | Commande |
|--------|---------|----------|
| Démarrer | START_HERE.md | Lire |
| Tester GCP | test_gcp_pipeline.py | `python beam/test_gcp_pipeline.py ...` |
| Déployer | deploy_dataflow.sh | `bash deploy/deploy_dataflow.sh ...` |
| Publier data | publish_test_data.py | `python beam/publish_test_data.py ...` |
| Voir archi | SOLUTION_COMPLETE.md | Lire |
| Push GitHub | GITHUB_PUSH_GUIDE.md | Lire |
| Code main | dataflow_pipeline_gcp.py | À ne pas modifier |

---

## ✅ CHECKLIST D'ACCÈS

Avant de commencer, vérifier:

- [ ] Dossier `beam/` existe
- [ ] `dataflow_pipeline_gcp.py` présent
- [ ] `publish_test_data.py` présent
- [ ] `test_gcp_pipeline.py` présent (NEW!)
- [ ] Dossier `deploy/` existe
- [ ] `deploy_dataflow.sh` présent
- [ ] `requirements.txt` présent
- [ ] Fichiers de données dans `data/raw/`
- [ ] `.gitignore` configuré
- [ ] Documentation dans racine

---

**🚀 Prêt à commencer!**

```bash
# Commande de démarrage
python beam/test_gcp_pipeline.py --project ecommerce-494010 --region europe-west1
```

Consultez [START_HERE.md](START_HERE.md) pour la suite! 📖
