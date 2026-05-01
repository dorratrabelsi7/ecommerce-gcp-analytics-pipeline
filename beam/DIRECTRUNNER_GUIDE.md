# Problèmes DirectRunner vs DataflowRunner

## 🔴 Problème : Pourquoi DirectRunner ne fonctionne pas

### Le code original (`pipeline.py`) est conçu pour **DataflowRunner sur GCP**, pas DirectRunner

```python
# ❌ INCOMPATIBLE avec DirectRunner
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io import WriteToBigQuery

# Ces composants nécessitent une vraie connexion GCP
# DirectRunner ne peut pas les utiliser localement
```

### Problèmes spécifiques :

| Problème | Cause | Solution |
|----------|-------|----------|
| **ReadFromPubSub + DirectRunner** | Pub/Sub est un service GCP distant. DirectRunner exécute localement et ne peut pas se connecter | Lire depuis des fichiers locaux avec `ReadFromText` |
| **WriteToBigQuery + DirectRunner** | BigQuery a besoin d'authentification GCP et d'une vraie base de données. DirectRunner en local n'y a pas accès | Écrire dans des fichiers texte avec `WriteToText` |
| **Authentification GCP** | DirectRunner n'utilise pas les credentials GCP (ou l'authentification échoue) | Pas besoin d'authentification pour les fichiers locaux |
| **Streaming vs Batch** | `streaming = False` + `ReadFromPubSub` = incompatible | Utiliser des patterns batch |

---

## ✅ Solution : Deux pipelines

### 1. **pipeline_directrunner.py** (LOCAL - Pour développement/test)
```python
# ✅ COMPATIBLE avec DirectRunner
from apache_beam.io import ReadFromText, WriteToText
from apache_beam.transforms import DoFn, ParDo

# Lire depuis fichiers locaux
records = pipeline | "Read" >> ReadFromText("data/raw/orders.csv")

# Écrire vers fichiers locaux
records | "Write" >> WriteToText("output/orders")
```

**Avantages:**
- ✓ Exécution locale (pas besoin de GCP)
- ✓ Gratuit (pas de frais GCP)
- ✓ Rapide pour les tests
- ✓ Parfait pour le développement

**Limitations:**
- ✗ Pas de vraie connectivité Pub/Sub
- ✗ Pas de vrai BigQuery
- ✗ Pas de temps réel

---

### 2. **dataflow_etl_pipeline.py** (GCP - Pour production)
```python
# ✅ Pour DataflowRunner sur GCP
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io import WriteToBigQuery

# Lire depuis Pub/Sub réel
messages = pipeline | "Read" >> ReadFromPubSub(subscription=...)

# Écrire vers BigQuery réel
messages | "Write" >> WriteToBigQuery(table=...)
```

**Avantages:**
- ✓ Connecte à Pub/Sub réel
- ✓ Connecte à BigQuery réel
- ✓ Peut traiter en temps réel (streaming)
- ✓ Scalable sur GCP

**Limitations:**
- ✗ Coûts GCP (vCPU-hour)
- ✗ Nécessite authentification GCP
- ✗ Temps d'exécution plus long

---

## 🚀 Comment utiliser chaque pipeline

### Pour le DÉVELOPPEMENT LOCAL (DirectRunner):
```bash
# Traiter un fichier unique
python beam/pipeline_directrunner.py --input data/raw/orders.csv

# Traiter tous les fichiers
python beam/pipeline_directrunner.py --all

# Avec limite de records
python beam/pipeline_directrunner.py --input data/raw/clients.csv --limit 50

# Sortie : fichiers dans output/
# - output/valid_orders-00000-of-00001.jsonl
# - output/invalid_orders-00000-of-00001.jsonl
```

### Pour la PRODUCTION sur GCP (DataflowRunner):
```bash
# Activation de Dataflow
source activate_dataflow.sh

# Lancer le pipeline sur Dataflow
python beam/dataflow_etl_pipeline.py \
    --project ecommerce-494010 \
    --region europe-west1 \
    --runner DataflowRunner

# Ou via le script d'envoi
bash beam/submit_to_dataflow.sh
```

---

## 📊 Comparaison des runners

```
┌─────────────────┬──────────────────┬──────────────────┐
│ Caractéristique │  DirectRunner    │  DataflowRunner  │
├─────────────────┼──────────────────┼──────────────────┤
│ Exécution       │ Machine locale    │ VMs GCP          │
│ Pub/Sub         │ ❌ Non           │ ✅ Oui           │
│ BigQuery        │ ❌ Non           │ ✅ Oui           │
│ Streaming       │ ❌ Limité        │ ✅ Oui           │
│ Coût            │ $0               │ $$ (vCPU-hour)   │
│ Latence         │ Immédiate        │ 2-5 min départ   │
│ Scalabilité     │ Limitée (RAM)    │ Illimitée        │
│ Développement   │ ✅ Idéal         │ ❌ Trop lent     │
└─────────────────┴──────────────────┴──────────────────┘
```

---

## 🔧 Changements clés dans pipeline_directrunner.py

### 1. Lecture depuis fichiers locaux
```python
# Au lieu de : ReadFromPubSub(subscription=...)
if input_path.endswith('.csv'):
    records = pipeline | ReadCSV(input_path)
elif input_path.endswith('.json'):
    records = pipeline | ReadJSON(input_path)
```

### 2. Écriture locale
```python
# Au lieu de : WriteToBigQuery(table=...)
records | "Write" >> WriteToText(
    f"{OUTPUT_DIR}/output",
    file_name_suffix=".jsonl"
)
```

### 3. Pas d'authentification GCP
```python
# DirectRunner ne nécessite pas :
# - from google.cloud import bigquery
# - credentials d'authentification
# - PROJECT_ID de GCP
```

---

## 📝 Workflow recommandé

```
1. DÉVELOPPEMENT LOCAL
   ├─ Modifier pipeline_directrunner.py
   ├─ Tester avec : python beam/pipeline_directrunner.py --all
   ├─ Vérifier output/ 
   └─ DirectRunner (gratuit, rapide)

2. VALIDATION SUR GCP
   ├─ Adapter à dataflow_etl_pipeline.py
   ├─ Créer/configurer Pub/Sub topics
   ├─ Créer/configurer BigQuery datasets
   └─ Tester avec DataflowRunner ($)

3. PRODUCTION
   ├─ Scheduler lance Cloud Functions
   ├─ Cloud Functions déclenche Dataflow
   ├─ Dataflow lit Pub/Sub → BigQuery
   └─ Looker Studio affiche les données
```

---

## ✅ Checklist pour DirectRunner

- [x] Lire depuis fichiers locaux (CSV/JSON)
- [x] Parser et valider les records
- [x] Enrichir les données avec timestamp
- [x] Écrire les valides dans des fichiers
- [x] Écrire les erreurs dans des fichiers d'erreur
- [x] Pas de dépendances GCP
- [x] Exécution avec `python` (pas `gcloud dataflow`)

---

## ❓ FAQ

**Q: Puis-je utiliser WriteToBigQuery avec DirectRunner?**
A: Non, WriteToBigQuery nécessite une vraie connexion GCP. Utilisez WriteToText pour DirectRunner.

**Q: Comment tester Pub/Sub localement?**
A: Utilisez l'émulateur Pub/Sub (complexe) ou simulez les messages en JSON. Pour DirectRunner, utilisez des fichiers.

**Q: DirectRunner est plus lent?**
A: Non, DirectRunner est plus rapide pour les petits datasets car il exécute localement sans latence réseau.

**Q: Peux-je utiliser DirectRunner en production?**
A: Non, DirectRunner n'est que pour le développement. La production nécessite DataflowRunner pour la scalabilité et la fiabilité.

---

## 🔗 Ressources

- [Apache Beam Runners](https://beam.apache.org/documentation/runners/capability-matrix/)
- [Direct Runner Guide](https://beam.apache.org/documentation/runners/direct/)
- [Dataflow Runner Guide](https://beam.apache.org/documentation/runners/dataflow/)
- [Beam I/O Connectors](https://beam.apache.org/documentation/io/connectors/)
