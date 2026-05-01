# ⚡ DATAFLOW ACTIVATION FOR YOUR PROJECT

## Your Project Info
- **Project ID:** `ecommerce-494010`
- **Project Number:** `751054966924`
- **Region:** `europe-west1`
- **Dataset:** `ecommerce_analytics`

---

## 📋 ÉTAPE 1: Obtenir Credentials JSON

### **Si vous n'avez PAS le fichier credentials.json:**

1. Ouvrez: https://console.cloud.google.com/iam-admin/serviceaccounts?project=ecommerce-494010

2. **"Create Service Account"**
   - Name: `ecommerce-pipeline`
   - Cliquez "Create and Continue"

3. **Grant Roles** (sélectionnez ces rôles):
   ```
   ✓ Dataflow Admin
   ✓ Dataflow Worker  
   ✓ BigQuery Data Editor
   ✓ Storage Object Admin
   ✓ Service Account User
   ```

4. **Create JSON Key**:
   - Cliquez "Continue"
   - Onglet **"Keys"**
   - **"Add Key"** → **"Create new key"**
   - Choisissez **"JSON"**
   - Fichier `.json` se télécharge

5. **Déplacez le fichier**:
   ```powershell
   # Exemple: le fichier est dans Downloads
   Move-Item "C:\Users\LENOVO\Downloads\ecommerce-494010-*.json" `
       "C:\Users\LENOVO\Desktop\ecommerce-gcp-analytics-pipeline\service-account-key.json"
   ```

---

## 🚀 ÉTAPE 2: Lancer l'Activation Dataflow

### **Une fois que vous avez le fichier credentials.json:**

```powershell
# Dans le répertoire du projet
cd C:\Users\LENOVO\Desktop\ecommerce-gcp-analytics-pipeline

# Lancer l'activation
bash activate_dataflow.sh ./service-account-key.json
```

**Ce script va AUTOMATIQUEMENT:**
- ✅ Authentifier avec votre service account
- ✅ Activer toutes les APIs GCP (Dataflow, Compute, BigQuery, Storage)
- ✅ Créer les buckets GCS (staging, temp, data)
- ✅ Créer le dataset BigQuery & tables
- ✅ Configurer les permissions
- ✅ Mettre à jour .env
- ✅ Vérifier la configuration

---

## 📅 Cloud Scheduler - Intégration

Après Dataflow, vous pouvez scheduler les pipelines:

```bash
# Voir les jobs existants
bash deploy/setup_scheduler.sh

# Créer un nouveau job pour Dataflow
gcloud scheduler jobs create pubsub dataflow-daily-etl \
  --schedule="0 6 * * *" \
  --location=europe-west1 \
  --topic=dataflow-trigger \
  --message-body='{"action":"run_etl"}'
```

---

## ✅ Checklist Activation

- [ ] Fichier `service-account-key.json` téléchargé
- [ ] Fichier placé dans le répertoire du projet
- [ ] `bash activate_dataflow.sh ./service-account-key.json` exécuté
- [ ] Script complété avec ✓ success messages
- [ ] BigQuery tables visibles dans Cloud Console
- [ ] GCS buckets créés

---

## 🎯 Après Activation (Étapes Suivantes)

### **1. Générer données test**
```powershell
python scripts/generate_data.py
```

### **2. Soumettre pipeline à Dataflow**
```powershell
bash beam/submit_to_dataflow.sh
```

### **3. Monitorer en temps réel**
```
https://console.cloud.google.com/dataflow/jobs?project=ecommerce-494010
```

### **4. Vérifier les résultats**
```powershell
bq query "SELECT COUNT(*) FROM ecommerce_analytics.orders_processed"
```

---

## 🔧 Dépannage

### **Problème: "Credentials file not found"**
```powershell
# Vérifiez le chemin
ls ./service-account-key.json
# Ou utilisez le chemin complet
bash activate_dataflow.sh "C:\Users\LENOVO\Desktop\ecommerce-gcp-analytics-pipeline\service-account-key.json"
```

### **Problème: "Permission denied"**
Les rôles ne sont pas attribués. Allez sur:
https://console.cloud.google.com/iam-admin?project=ecommerce-494010

Vérifiez que `ecommerce-pipeline@...` a ces rôles:
- Dataflow Admin ✓
- Dataflow Worker ✓

### **Problème: "Dataset already exists"**
C'est normal! Le script le détecte et continue.

---

## 📊 Résultat Final

Une fois complété, vous aurez:

```
GCS Buckets (3):
├── gs://dataflow-staging-ecommerce-494010/     (Staging)
├── gs://dataflow-temp-ecommerce-494010/        (Temp)
└── gs://data-ecommerce-494010/                 (Data)

BigQuery Tables (2):
├── ecommerce_analytics.orders_processed        (Output)
└── ecommerce_analytics.orders_errors           (Errors)

Service Account:
└── ecommerce-pipeline@ecommerce-494010.iam.gserviceaccount.com

Cloud Scheduler (Existant):
├── daily-bq-refresh (06:00 UTC)
├── weekly-kpi-export (Lundi 07:00 UTC)
└── monthly-cleanup (1er mois 03:00 UTC)
```

---

## 🎬 Commandes Rapides

```powershell
# Activation complète
bash activate_dataflow.sh ./service-account-key.json

# Générer données
python scripts/generate_data.py

# Soumettre pipeline
bash beam/submit_to_dataflow.sh

# Monitorer jobs
gcloud dataflow jobs list --region=europe-west1 --project=ecommerce-494010

# Vérifier résultats
bq query "SELECT COUNT(*) FROM ecommerce_analytics.orders_processed"

# Voir logs Dataflow
gcloud logging read "resource.type=dataflow_step" --limit=50 --project=ecommerce-494010
```

---

## 📞 Support

Si vous bloquez:
1. Donnez-moi l'erreur complète
2. Lancez: `bash activate_dataflow.sh ./service-account-key.json` avec mode verbose
3. Je débogue immédiatement

✨ **Vous êtes prêt à utiliser Dataflow!**
