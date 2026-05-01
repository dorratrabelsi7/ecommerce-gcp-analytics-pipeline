# 🚀 DÉMARRER MAINTENANT - Pipeline Dataflow GCP

## 5 commandes pour tout mettre en place

### 1️⃣ Authentification GCP
```bash
gcloud auth login
gcloud config set project ecommerce-494010
```

### 2️⃣ Déploiement automatisé (tout se fait automatiquement)
```bash
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1
```

### 3️⃣ Attendre ~30 secondes, puis publier les données de test
```bash
python beam/publish_test_data.py \
    --project ecommerce-494010 \
    --input data/raw/orders.csv \
    --topic orders-realtime \
    --rate 5
```

### 4️⃣ Vérifier que les données arrivent dans BigQuery
```bash
bq query --use_legacy_sql=false '
    SELECT COUNT(*) as total_orders 
    FROM `ecommerce-494010.ecommerce_analytics.orders_stream`
    LIMIT 10
'
```

### 5️⃣ Aller à Looker Studio et créer un dashboard
```
https://lookerstudio.google.com
```

---

## 📁 Fichiers importants

| Fichier | Purpose | Status |
|---------|---------|--------|
| `beam/dataflow_pipeline_gcp.py` | Pipeline Dataflow | ✅ PRÊT |
| `beam/publish_test_data.py` | Simulateur Pub/Sub | ✅ PRÊT |
| `deploy/deploy_dataflow.sh` | Déploiement automatisé | ✅ PRÊT |
| `CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md` | Explication de la correction | ✅ PRÊT |
| `beam/DATAFLOW_GCP_GUIDE.md` | Guide complet | ✅ PRÊT |
| `beam/SOLUTION_FINAL.md` | Solution finale | ✅ PRÊT |

---

## ✨ Ce qui a changé

❌ **ANCIEN (DirectRunner)** → ✅ **NOUVEAU (Dataflow)**

- ❌ Fichiers locaux → ✅ **Pub/Sub temps réel**
- ❌ Batch processing → ✅ **Streaming continu**
- ❌ Fichiers texte → ✅ **BigQuery**
- ❌ Pas cloud-native → ✅ **Cloud-native GCP**

---

## ⏱️ Temps total

- Déploiement: **10-15 minutes**
- Test: **5 minutes**
- Dashboard: **15-30 minutes**
- **TOTAL: ~30-50 minutes**

---

## 📞 Besoin d'aide?

Consultez:
1. **[CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md](CORRECTION_DIRECTRUNNER_TO_DATAFLOW.md)** - Comprendre la correction
2. **[beam/DATAFLOW_GCP_GUIDE.md](beam/DATAFLOW_GCP_GUIDE.md)** - Guide complet
3. **[beam/SOLUTION_FINAL.md](beam/SOLUTION_FINAL.md)** - Résumé complet

---

**Allez-y! Lancez le déploiement maintenant! 🚀**

```bash
bash deploy/deploy_dataflow.sh ecommerce-494010 europe-west1
```
