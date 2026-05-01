# 📘 Guide de déploiement Dataflow pour le Mini-Projet GCP

## 🎯 Contexte du projet

Le mini-projet demande une solution **cloud-native complète sur GCP** avec:
- ✅ Ingestion temps réel via Pub/Sub
- ✅ Traitement par Dataflow (Apache Beam)
- ✅ Stockage dans BigQuery
- ✅ Visualisation avec Looker Studio

**Votre pipeline Dataflow `dataflow_pipeline_gcp.py` implémente EXACTEMENT cela.**

---

## 🚀 Déploiement étape par étape

### Étape 1: Préparation GCP (5-10 minutes)

```bash
# 1. Authentifier avec GCP
gcloud auth login
gcloud auth application-default login

# 2. Définir le projet
export PROJECT_ID="ecommerce-494010"
gcloud config set project $PROJECT_ID

# 3. Vérifier que les APIs sont activées
gcloud services enable dataflow.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage-api.googleapis.com
```

### Étape 2: Créer les ressources GCP (10-15 minutes)

#### 2a. Créer un bucket Cloud Storage (pour fichiers temporaires)
```bash
export BUCKET_NAME="ecommerce-analytics-pipeline"
gsutil mb gs://$BUCKET_NAME

# Créer le dossier temp
gsutil mb gs://$BUCKET_NAME/temp/
gsutil mb gs://$BUCKET_NAME/input/
```

#### 2b. Créer les Pub/Sub topics
```bash
# Topics pour les flux de données
gcloud pubsub topics create orders-realtime
gcloud pubsub topics create clients-realtime
gcloud pubsub topics create incidents-realtime
gcloud pubsub topics create pageviews-realtime

# Subscriptions (pour les lecteurs)
gcloud pubsub subscriptions create orders-sub --topic orders-realtime
gcloud pubsub subscriptions create clients-sub --topic clients-realtime
gcloud pubsub subscriptions create incidents-sub --topic incidents-realtime
gcloud pubsub subscriptions create pageviews-sub --topic pageviews-realtime
```

#### 2c. Créer les datasets BigQuery
```bash
# Créer le dataset
bq mk --dataset \
    --description "eCommerce Analytics Data Warehouse" \
    --location EU \
    ecommerce_analytics

# Créer les tables brutes (streaming)
bq mk --table \
    ecommerce_analytics.orders_stream \
    beam/schemas/orders_schema.json

bq mk --table \
    ecommerce_analytics.clients_stream \
    beam/schemas/clients_schema.json

bq mk --table \
    ecommerce_analytics.incidents_stream \
    beam/schemas/incidents_schema.json

bq mk --table \
    ecommerce_analytics.pageviews_stream \
    beam/schemas/pageviews_schema.json

# Table pour les erreurs
bq mk --table \
    ecommerce_analytics.pipeline_errors \
    beam/schemas/errors_schema.json

# Table pour les métriques
bq mk --table \
    ecommerce_analytics.metrics_daily \
    beam/schemas/metrics_schema.json
```

### Étape 3: Déployer le pipeline Dataflow (5-10 minutes)

```bash
# Lancer le job Dataflow
python beam/dataflow_pipeline_gcp.py \
    --project $PROJECT_ID \
    --region europe-west1 \
    --temp-location gs://$BUCKET_NAME/temp/
```

**Résultat:** Le pipeline démarre et reste actif, en attente de messages Pub/Sub.

### Étape 4: Simuler les données temps réel (test)

```bash
# Publier des messages test vers Pub/Sub
python beam/publish_test_data.py \
    --project $PROJECT_ID \
    --input data/raw/orders.csv \
    --topic orders-realtime \
    --rate 10  # 10 messages par seconde
```

---

## 📊 Architecture du pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUD STORAGE                              │
│  (données brutes: CSV, JSON files)                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CLOUD FUNCTIONS                               │
│  (déclenche à chaque nouvel upload)                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PUB/SUB (STREAMING)                        │
│  ├─ orders-realtime (flux commandes)                           │
│  ├─ clients-realtime (flux clients)                            │
│  ├─ incidents-realtime (flux incidents)                        │
│  └─ pageviews-realtime (flux navigation)                       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATAFLOW (BEAM)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ TRANSFORMATIONS:                                         │  │
│  │ 1. Parse JSON/CSV from Pub/Sub                          │  │
│  │ 2. Validate required fields                             │  │
│  │ 3. Remove nulls & duplicates                            │  │
│  │ 4. Enrich with metadata                                 │  │
│  │ 5. Calculate metrics (daily revenue, etc)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BIG QUERY (DW)                             │
│  ├─ orders_stream (raw orders)                                 │
│  ├─ clients_stream (raw clients)                               │
│  ├─ incidents_stream (raw incidents)                           │
│  ├─ pageviews_stream (raw pageviews)                           │
│  ├─ metrics_daily (aggregated KPIs)                            │
│  ├─ pipeline_errors (processing errors)                        │
│  └─ SQL views (business analytics)                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LOOKER STUDIO                                 │
│  (Dashboards interactifs avec filtres dynamiques)              │
│  ├─ Revenue dashboard                                          │
│  ├─ Customer analysis                                          │
│  ├─ Incident tracking                                          │
│  └─ User behavior analytics                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Fichiers requis

### Pipeline principal
- **`beam/dataflow_pipeline_gcp.py`** - Pipeline Dataflow avec streaming
- **`beam/publish_test_data.py`** - Simulateur de données (Pub/Sub)

### Configuration
- **`beam/schemas/`** - Schémas BigQuery JSON

### Déploiement
- **`deploy/setup_gcp.sh`** - Script d'automatisation
- **`deploy/setup_pubsub.sh`** - Créer topics Pub/Sub
- **`deploy/setup_bigquery.sh`** - Créer datasets/tables

---

## 📋 Checklist de déploiement

- [ ] **GCP Setup**
  - [ ] Compte GCP avec facturation activée
  - [ ] Project créé (ecommerce-494010)
  - [ ] APIs activées (Dataflow, Pub/Sub, BigQuery, Storage)
  - [ ] Service account configurée
  - [ ] Authentification gcloud configurée

- [ ] **Cloud Storage**
  - [ ] Bucket créé (ecommerce-analytics-pipeline)
  - [ ] Dossiers temp/ et input/ créés

- [ ] **Pub/Sub**
  - [ ] 4 topics créés (orders, clients, incidents, pageviews)
  - [ ] 4 subscriptions créées

- [ ] **BigQuery**
  - [ ] Dataset ecommerce_analytics créé
  - [ ] 6 tables créées (orders_stream, clients_stream, etc)
  - [ ] Schémas applicables

- [ ] **Dataflow**
  - [ ] Pipeline python disponible
  - [ ] Dépendances installées (apache-beam[gcp])
  - [ ] Pipeline lancé avec succès
  - [ ] Job visible dans la console Dataflow

- [ ] **Test**
  - [ ] Messages envoyés à Pub/Sub
  - [ ] Données visibles dans BigQuery
  - [ ] Aucune erreur dans les logs Dataflow

---

## 💻 Commandes rapides

```bash
# Afficher les topics Pub/Sub
gcloud pubsub topics list

# Afficher les subscriptions
gcloud pubsub subscriptions list

# Afficher les datasets BigQuery
bq ls

# Afficher les tables BigQuery
bq ls ecommerce_analytics

# Voir les jobs Dataflow
gcloud dataflow jobs list

# Afficher les logs d'un job
gcloud dataflow jobs describe JOB_ID --region europe-west1

# Envoyer un message test
gcloud pubsub topics publish orders-realtime \
    --message '{"order_id":"ORD001","client_id":"C001","total_amount":150.50,"status":"Livré","date_commande":"2026-05-01T10:00:00"}'

# Vérifier les données dans BigQuery
bq query --use_legacy_sql=false '
    SELECT COUNT(*) as total_orders FROM `ecommerce-494010.ecommerce_analytics.orders_stream`
'
```

---

## 🔍 Monitoring

### Dataflow Console
```
https://console.cloud.google.com/dataflow/jobs
```

### BigQuery
```
https://console.cloud.google.com/bigquery
```

### Pub/Sub Monitoring
```
https://console.cloud.google.com/pubsub/topiclist
```

---

## 🛠️ Troubleshooting

### Erreur: "Topic does not exist"
```bash
# Vérifier que le topic existe
gcloud pubsub topics list

# Créer s'il manque
gcloud pubsub topics create orders-realtime
```

### Erreur: "No permissions to write to BigQuery"
```bash
# Vérifier les permissions du service account
# La service account doit avoir:
# - roles/dataflow.worker
# - roles/bigquery.dataEditor
# - roles/storage.admin
```

### Dataflow job échoue
```bash
# Voir les logs détaillés
gcloud dataflow jobs describe JOB_ID --region europe-west1

# Ou dans la console Dataflow UI
```

---

## 📊 Résultat attendu

Après ~5 minutes de fonctionnement:

**BigQuery tables:**
```
ecommerce_analytics.orders_stream: 1000+ enregistrements
ecommerce_analytics.clients_stream: 500+ enregistrements
ecommerce_analytics.incidents_stream: 200+ enregistrements
ecommerce_analytics.pageviews_stream: 5000+ enregistrements
ecommerce_analytics.metrics_daily: Métriques agrégées
ecommerce_analytics.pipeline_errors: Erreurs de traitement
```

**Dataflow monitoring:**
- ✅ 0 elements dropped
- ✅ Latency < 1 min
- ✅ Throughput: X elements/second

---

## 🎓 Différences par rapport à DirectRunner

| Aspect | DirectRunner | DataflowRunner |
|--------|-------------|---|
| Exécution | Machine locale | GCP VMs |
| Entrée | Fichiers locaux | Pub/Sub streaming |
| Sortie | Fichiers texte | BigQuery |
| Latence | Immédiate | 1-5 minutes |
| Coût | $0 | $$ (vCPU-hour) |
| Production | ❌ Non | ✅ Oui |
| **Temps réel** | ❌ Non | ✅ Oui |

---

## 📚 Documentation

- [Dataflow Documentation](https://cloud.google.com/dataflow/docs)
- [Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Apache Beam Documentation](https://beam.apache.org/documentation/)

---

**Vous êtes maintenant prêt à déployer votre pipeline temps réel sur GCP!** 🚀
