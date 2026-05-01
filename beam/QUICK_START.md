# 🚀 Guide d'exécution rapide

## Avant de commencer

```bash
# 1. Vérifier la structure
ls -la beam/
ls -la data/raw/

# 2. Installer les dépendances (si pas fait)
pip install -r requirements.txt

# 3. Activer l'environnement virtuel (optionnel)
source venv312/Scripts/activate  # Linux/Mac
.\venv312\Scripts\activate.bat   # Windows
```

---

## 🎯 Exécution rapide (5 minutes)

### Option 1: Via le script de test
```bash
# Plus facile! Lance tout automatiquement
bash beam/test_directrunner.sh
```

### Option 2: Commandes directes

```bash
# Traiter un seul fichier (rapide)
python beam/pipeline_directrunner.py --input data/raw/clients.csv --limit 10

# Traiter tous les fichiers
python beam/pipeline_directrunner.py --all

# Avec plus de records
python beam/pipeline_directrunner.py --all --limit 100
```

---

## 📊 Vérifier les résultats

```bash
# Lister les fichiers de sortie
ls -lh output/

# Voir les records valides
cat output/valid_clients-00000-of-00001.jsonl | head -3

# Voir les erreurs (s'il y en a)
cat output/invalid_*.jsonl

# Compter les records
wc -l output/valid_*.jsonl
```

---

## 🔍 Déboguer (si erreur)

```bash
# Vérifier Python
python --version

# Vérifier Apache Beam
python -c "import apache_beam; print(apache_beam.__version__)"

# Vérifier les fichiers de données
ls -la data/raw/

# Vérifier les permissions
ls -la beam/pipeline_directrunner.py
```

---

## 📝 Exemples concrets

### Exemple 1: Traiter les clients
```bash
$ python beam/pipeline_directrunner.py --input data/raw/clients.csv

80 records processed
5 records invalid
75 records valid

Output: output/valid_clients-00000-of-00001.jsonl
         output/invalid_clients-00000-of-00001.jsonl
```

### Exemple 2: Traiter les commandes (limité)
```bash
$ python beam/pipeline_directrunner.py --input data/raw/orders.csv --limit 50

50 records processed (limité)

Output: output/valid_orders-00000-of-00001.jsonl
```

### Exemple 3: Traiter TOUT
```bash
$ python beam/pipeline_directrunner.py --all

Processing data/raw/clients.csv
Processing data/raw/orders.csv
Processing data/raw/incidents.csv
Processing data/raw/page_views.csv
Processing data/raw/products.csv

Total: 5 fichiers traités
Output: output/valid_*.jsonl, output/invalid_*.jsonl
```

---

## ⏱️ Temps d'exécution

| Opération | Temps estimé |
|-----------|--------------|
| 1 fichier (100 records) | < 5 sec |
| 1 fichier (1000 records) | 5-10 sec |
| Tous les fichiers (5k records) | 20-30 sec |

---

## 🛠️ Paramètres disponibles

```bash
# Aide
python beam/pipeline_directrunner.py --help

# Options disponibles
--input FILE          # Fichier d'entrée (CSV ou JSON)
--all                 # Traiter TOUS les fichiers
--limit N             # Limiter à N records (par défaut: aucune limite)
```

---

## 💾 Format de sortie

### Fichier valide (valid_*.jsonl)
```json
{
  "client_id": "C001",
  "nom": "Dupont",
  "prenom": "Alice",
  "email": "alice.dupont@email.com",
  "age": "34",
  "sexe": "F",
  "pays": "France",
  "date_inscription": "2021-03-12",
  "processing_timestamp": "2026-05-01T14:23:45.123456",
  "pipeline_version": "1.0-directrunner",
  "source": "local-batch"
}
```

### Fichier d'erreur (invalid_*.jsonl)
```json
{
  "client_id": "C002",
  "nom": "Dupont",
  "error": "Missing fields: email",
  "timestamp": "2026-05-01T14:23:45.123456"
}
```

---

## ✅ Validation du résultat

```bash
# Les fichiers doivent avoir:
# - Extension .jsonl (un JSON par ligne)
# - Champs processing_timestamp et pipeline_version
# - Séparation valides/invalides

# Vérifier structure
python -c "
import json
with open('output/valid_clients-00000-of-00001.jsonl') as f:
    for line in f:
        record = json.loads(line)
        print(f'Fields: {list(record.keys())}')
        print(f'Has processing_timestamp: {\"processing_timestamp\" in record}')
        break
"
```

---

## 🔄 Phase suivante

Une fois satisfait des résultats locaux:

```bash
# Passer à DataflowRunner sur GCP
source activate_dataflow.sh
python beam/dataflow_etl_pipeline.py --runner DataflowRunner --project YOUR_PROJECT
```

---

## 📚 En cas de problème

### "FileNotFoundError: data/raw/orders.csv"
```bash
# Générer les données
python scripts/generate_data.py
```

### "ModuleNotFoundError: apache_beam"
```bash
# Installer
pip install apache-beam apache-beam[gcp]
```

### "Permission denied"
```bash
# Sur Linux/Mac
chmod +x beam/test_directrunner.sh
chmod +x beam/pipeline_directrunner.py
```

### Lenteur
```bash
# Utiliser --limit pour accélérer
python beam/pipeline_directrunner.py --input data/raw/orders.csv --limit 10
```

---

**🎉 C'est tout! Le pipeline fonctionne maintenant avec DirectRunner!**
