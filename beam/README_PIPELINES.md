# Pipelines Beam pour le Projet eCommerce GCP Analytics

Ce dossier contient les pipelines Apache Beam pour traiter les données du projet d'analytics eCommerce sur GCP.

## 📁 Structure des fichiers

```
beam/
├── pipeline.py                    # ❌ Original (problématique avec DirectRunner)
├── pipeline_directrunner.py       # ✅ Pipeline DirectRunner (LOCAL - Dev/Test)
├── dataflow_etl_pipeline.py       # ✅ Pipeline DataflowRunner (GCP - Production)
├── run_pipeline.sh                # Script pour exécuter pipeline.py
├── submit_to_dataflow.sh          # Script pour envoyer à DataflowRunner
├── test_directrunner.sh           # ✅ Script de test DirectRunner
├── DIRECTRUNNER_GUIDE.md          # Guide complet DirectRunner vs Dataflow
└── README.md                      # Ce fichier
```

---

## 🚀 Démarrage rapide

### 1️⃣ DirectRunner (Local - Gratuit)
```bash
# Traiter un fichier unique
python beam/pipeline_directrunner.py --input data/raw/orders.csv

# Traiter TOUS les fichiers
python beam/pipeline_directrunner.py --all

# Avec limite de records
python beam/pipeline_directrunner.py --input data/raw/clients.csv --limit 50

# Via le script de test
bash beam/test_directrunner.sh
```

**Résultats:** Fichiers de sortie dans `output/`
```
output/
├── valid_orders-00000-of-00001.jsonl
├── invalid_orders-00000-of-00001.jsonl
├── valid_clients-00000-of-00001.jsonl
└── invalid_clients-00000-of-00001.jsonl
```

### 2️⃣ DataflowRunner (GCP - Production)
```bash
# 1. Activer Dataflow
source activate_dataflow.sh

# 2. Lancer le pipeline sur GCP
python beam/dataflow_etl_pipeline.py \
    --project ecommerce-494010 \
    --region europe-west1 \
    --runner DataflowRunner

# Ou utiliser le script d'envoi
bash beam/submit_to_dataflow.sh
```

---

## 📊 Comparaison : Quand utiliser quel pipeline?

| Cas d'usage | Pipeline | Runner | Coût |
|------------|----------|--------|------|
| **Développement local** | pipeline_directrunner.py | DirectRunner | $0 |
| **Tests rapides** | pipeline_directrunner.py | DirectRunner | $0 |
| **Debug** | pipeline_directrunner.py | DirectRunner | $0 |
| **Production** | dataflow_etl_pipeline.py | DataflowRunner | $$ |
| **Temps réel** | dataflow_etl_pipeline.py | DataflowRunner | $$ |
| **Scalabilité** | dataflow_etl_pipeline.py | DataflowRunner | $$ |

---

## ❌ Pourquoi pipeline.py (original) ne fonctionne pas avec DirectRunner?

### Le problème

```python
# ❌ Ces composants NE fonctionnent PAS avec DirectRunner
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io import WriteToBigQuery

# DirectRunner = exécution LOCAL sans accès GCP
# ReadFromPubSub = service DISTANT sur GCP
# WriteToBigQuery = service DISTANT sur GCP
# = INCOMPATIBLE!
```

### La solution

**Pour DirectRunner (développement):**
```python
# ✅ Utiliser des sources/destinations locales
from apache_beam.io import ReadFromText, WriteToText

# Lire de fichiers locaux
records = pipeline | "Read" >> ReadFromText("data/raw/orders.csv")

# Écrire vers fichiers locaux
records | "Write" >> WriteToText("output/orders")
```

**Pour DataflowRunner (production):**
```python
# ✅ Utiliser les services GCP
from apache_beam.io.gcp.pubsub import ReadFromPubSub
from apache_beam.io import WriteToBigQuery

# Lire de Pub/Sub réel
messages = pipeline | "Read" >> ReadFromPubSub(subscription=...)

# Écrire vers BigQuery réel
messages | "Write" >> WriteToBigQuery(table=...)
```

Voir [DIRECTRUNNER_GUIDE.md](./DIRECTRUNNER_GUIDE.md) pour plus de détails.

---

## 🔧 Configuration requise

### Dépendances Python
```bash
pip install -r requirements.txt
```

**Packages clés:**
- `apache-beam` - Framework ETL
- `apache-beam[gcp]` - Connecteurs GCP
- `google-cloud-pubsub` - Client Pub/Sub
- `google-cloud-bigquery` - Client BigQuery

### Pour DirectRunner (développement)
- ✓ Python 3.8+
- ✓ Apache Beam
- ✓ Fichiers CSV/JSON locaux

### Pour DataflowRunner (production)
- ✓ Compte GCP avec facturaction activée
- ✓ Project ID GCP
- ✓ Authentification GCP (`gcloud auth`)
- ✓ Topics Pub/Sub configurés
- ✓ Dataset BigQuery configuré

---

## 📝 Exemples d'utilisation

### Exemple 1: Traiter un fichier orders.csv avec DirectRunner
```bash
python beam/pipeline_directrunner.py --input data/raw/orders.csv --limit 100
```

**Sortie:**
```
output/valid_orders-00000-of-00001.jsonl
output/invalid_orders-00000-of-00001.jsonl
```

**Contenu (valid_orders):**
```json
{
  "order_id": "ORD001",
  "client_id": "C001",
  "total_amount": "150.50",
  "status": "Livré",
  "processing_timestamp": "2026-05-01T10:30:45.123456",
  "pipeline_version": "1.0-directrunner",
  "source": "local-batch"
}
```

### Exemple 2: Traiter tous les fichiers
```bash
python beam/pipeline_directrunner.py --all
```

Traite: `clients.csv`, `orders.csv`, `incidents.csv`, `page_views.csv`, etc.

### Exemple 3: Exécuter sur DataflowRunner (GCP)
```bash
python beam/dataflow_etl_pipeline.py \
    --project ecommerce-494010 \
    --region europe-west1 \
    --runner DataflowRunner \
    --job-name my-beam-job \
    --temp-location gs://my-bucket/temp/
```

---

## 📚 Documentation

- **[DIRECTRUNNER_GUIDE.md](./DIRECTRUNNER_GUIDE.md)** - Guide complet des différences DirectRunner vs Dataflow
- **[Apache Beam Documentation](https://beam.apache.org/documentation/)** - Docs officielles
- **[Direct Runner Guide](https://beam.apache.org/documentation/runners/direct/)** - Guide DirectRunner
- **[Dataflow Runner](https://beam.apache.org/documentation/runners/dataflow/)** - Guide Dataflow

---

## 🐛 Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'apache_beam'"
```bash
pip install apache-beam apache-beam[gcp]
```

### ❌ "No module named 'google.cloud'"
```bash
pip install google-cloud-pubsub google-cloud-bigquery
```

### ❌ "FileNotFoundError: data/raw/orders.csv"
```bash
# Vérifier que les fichiers existent
ls -la data/raw/

# Générer les données si manquantes
python scripts/generate_data.py
```

### ❌ "DirectRunner ne trouve pas les fichiers"
- Vérifier que vous exécutez depuis le répertoire racine du projet
- Utiliser des chemins absolus si nécessaire

### ❌ "Authentification GCP échouée" (avec Dataflow)
```bash
# Authentifier avec GCP
gcloud auth application-default login

# Vérifier le projet
gcloud config set project ecommerce-494010
```

---

## 🌟 Meilleures pratiques

### Pour le développement (DirectRunner)
1. ✅ Traiter des petits fichiers pour tests rapides
2. ✅ Valider la logique avant DataflowRunner
3. ✅ Tester les transformations localement
4. ✅ Déboguer avec des records d'exemple

### Pour la production (DataflowRunner)
1. ✅ Utiliser des credentials GCP sécurisées
2. ✅ Monitorer les jobs dans la console GCP
3. ✅ Configurer des alertes d'erreur
4. ✅ Utiliser Cloud Logging pour le debug

---

## 📞 Support

Pour toute question sur les pipelines:
- Voir le guide complet: [DIRECTRUNNER_GUIDE.md](./DIRECTRUNNER_GUIDE.md)
- Consulter la doc Apache Beam: https://beam.apache.org/
- Vérifier les logs dans `output/` avec DirectRunner

---

**Version:** 1.0  
**Dernière mise à jour:** 2026-05-01  
**Auteur:** Équipe Analytics GCP
