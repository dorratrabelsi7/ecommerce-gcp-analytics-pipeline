# 📤 Guide: Pusher sur GitHub

## 🔑 Étape 1: Créer un repository GitHub

### 1. Sur GitHub.com
1. Aller à https://github.com/new
2. **Repository name**: `ecommerce-gcp-analytics-pipeline`
3. **Description**: "Cloud-native e-commerce analytics pipeline with Apache Beam & BigQuery on GCP"
4. Sélectionner: **Public** (ou Private selon vos préférences)
5. ✅ Cliquer **Create repository**

### 2. Copier l'URL du repository
```
https://github.com/YOUR_USERNAME/ecommerce-gcp-analytics-pipeline.git
```

---

## 🚀 Étape 2: Initialiser Git localement

```bash
# Naviguer au dossier du projet
cd C:\Users\LENOVO\Desktop\ecommerce-gcp-analytics-pipeline

# Initialiser Git
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Vérifier la configuration
git config --list
```

---

## 📝 Étape 3: Ajouter les fichiers

```bash
# Vérifier le statut
git status

# Ajouter TOUS les fichiers (sauf ceux du .gitignore)
git add .

# Vérifier les fichiers à committer
git status

# Alternative: Ajouter sélectivement
# git add beam/dataflow_pipeline_gcp.py
# git add deploy/deploy_dataflow.sh
# git add START_HERE.md
# etc.
```

---

## 💬 Étape 4: Faire le premier commit

```bash
git commit -m "Initial commit: Complete Dataflow pipeline for GCP

- Implemented Apache Beam Dataflow pipeline
- Real-time data ingestion via Pub/Sub
- Processing: validation, cleaning, enrichment, metrics
- Storage: BigQuery integration
- Deployment: Automated GCP setup script
- Documentation: Comprehensive guides"
```

---

## 🔗 Étape 5: Connecter au repository distant

```bash
# Ajouter le remote (remplacer YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ecommerce-gcp-analytics-pipeline.git

# Vérifier la connexion
git remote -v
```

---

## ⬆️ Étape 6: Pousser le code

```bash
# Renommer la branche principale en "main"
git branch -M main

# Pousser vers GitHub
git push -u origin main

# Vérifier
git status
# Doit afficher: "On branch main, Your branch is up to date with 'origin/main'."
```

**Cela peut demander votre authentification GitHub.**

---

## ✅ Vérification

Allez sur: `https://github.com/YOUR_USERNAME/ecommerce-gcp-analytics-pipeline`

Vérifiez que vous voyez:
- ✅ Tous les fichiers du projet
- ✅ Le README
- ✅ Les documents de documentation
- ✅ Les scripts de déploiement

---

## 📋 Fichiers importants à vérifier

| Fichier | Status |
|---------|--------|
| `beam/dataflow_pipeline_gcp.py` | ✅ Doit être là |
| `beam/publish_test_data.py` | ✅ Doit être là |
| `beam/test_gcp_pipeline.py` | ✅ Doit être là |
| `deploy/deploy_dataflow.sh` | ✅ Doit être là |
| `START_HERE.md` | ✅ Doit être là |
| `SOLUTION_COMPLETE.md` | ✅ Doit être là |
| `requirements.txt` | ✅ Doit être là |
| `.gitignore` | ✅ Doit être là |
| `data/raw/*.csv` | ❌ NE doit PAS être là (ignoré) |
| `venv/` ou `venv312/` | ❌ NE doit PAS être là (ignoré) |
| `output/` | ❌ NE doit PAS être là (ignoré) |

---

## 🔄 Commits futurs

Après des modifications:

```bash
# Voir les changements
git status
git diff

# Ajouter les fichiers modifiés
git add .

# Committer
git commit -m "Description des changements"

# Pousser
git push
```

---

## 📌 Tags pour les versions

```bash
# Créer un tag pour la version 1.0
git tag -a v1.0 -m "Version 1.0: Initial production release"

# Pousser les tags
git push origin --tags

# Voir les tags
git tag -l
```

---

## 🔒 Configurer les branches protégées (optionnel)

1. Aller à **Settings** → **Branches**
2. Ajouter une règle pour `main`
3. Activer:
   - "Require pull request reviews"
   - "Require status checks to pass"
   - "Dismiss stale pull request approvals"

---

## 🚨 Troubleshooting

### Erreur: "fatal: remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/...
```

### Erreur: "fatal: 'origin' does not appear to be a 'git' repository"
```bash
git remote add origin https://github.com/YOUR_USERNAME/ecommerce-gcp-analytics-pipeline.git
```

### Les fichiers ne se poussent pas
```bash
# Vérifier le .gitignore
cat .gitignore

# Forcer l'ajout (attention!)
git add -f fichier

# Ou supprimer du .gitignore si nécessaire
```

### Credentials GitHub
```bash
# Générer un Personal Access Token
# https://github.com/settings/tokens

# Cache les credentials
git config credential.helper store
git push  # Entrer username et token
```

---

## 📊 Structurer les branche futurs

```bash
# Branche de développement
git checkout -b develop

# Branche de feature
git checkout -b feature/new-feature

# Faire des changements
git add .
git commit -m "Add new feature"

# Retour à main
git checkout main
git merge develop

# Pousser
git push
```

---

## 📝 README sur GitHub

Le fichier `README.md` à la racine s'affichera automatiquement sur GitHub.

**Structure recommandée:**
1. Title & description
2. Quick Start
3. Features
4. Project Structure
5. Technologies
6. Installation
7. Usage
8. Documentation
9. Contributing
10. License

---

## 🎯 Checklist avant de pousser

- [x] Tous les fichiers Python testés
- [x] `.gitignore` configuré
- [x] `requirements.txt` à jour
- [x] Documentation complète
- [x] Aucune clé d'API exposée
- [x] Aucun fichier de données sensibles
- [x] Scripts exécutables

---

## 📚 Ressources GitHub

- [GitHub Docs](https://docs.github.com/)
- [Git Cheat Sheet](https://github.github.com/training-kit/downloads/github-git-cheat-sheet.pdf)
- [Hello World](https://guides.github.com/activities/hello-world/)

---

## 🎉 Résumé des commandes

```bash
# Configuration initiale
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Ajouter & committer
git add .
git commit -m "Initial commit"

# Connecter & pousser
git remote add origin https://github.com/YOUR_USERNAME/...
git branch -M main
git push -u origin main

# Vérifier
git status
git log
git remote -v
```

---

**Fin! Votre code est maintenant sur GitHub! 🚀**

Pour une aide supplémentaire:
- GitHub Docs: https://docs.github.com/
- Community Forum: https://github.community/
