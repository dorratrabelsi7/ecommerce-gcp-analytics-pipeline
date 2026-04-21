# 📦 Installation Guide - Apache Beam Workaround

## Status: Core Dependencies Installing

The main Python dependencies are currently being installed. This guide explains the Apache Beam workaround.

---

## ⚠️ Apache Beam Known Issue

**Problem:** Apache Beam 2.54.0 has complex build dependencies on Windows, particularly `grpcio-tools` which requires `pkg_resources` at build time.

**Error:**
```
ModuleNotFoundError: No module named 'pkg_resources'
ERROR: Failed to build 'grpcio-tools' when getting requirements to build wheel
```

**Root Cause:** The setuptools `pkg_resources` module is not available in the build environment when installing from source.

---

## ✅ Solution: Two-Stage Installation

### Stage 1: Install Core Dependencies (Running Now)
```bash
pip install -r requirements.txt
# This installs all packages EXCEPT Apache Beam:
# - setuptools
# - wheel  
# - faker
# - pandas
# - numpy
# - google-cloud-bigquery
# - google-cloud-storage
# - google-cloud-pubsub
# - python-dotenv
# - functions-framework
```

### Stage 2: Install Apache Beam (After Stage 1 Completes)

**Option A: Use Pre-Built Wheels (Recommended)**
```bash
pip install --only-binary :all: apache-beam==2.54.0
```

**Option B: Use Prefer-Binary Flag**
```bash
pip install --prefer-binary apache-beam==2.54.0
```

**Option C: Automatic Script**
```bash
bash install_beam.sh
```

**Option D: Manual Installation**
```bash
pip install apache-beam==2.54.0
```

---

## 📋 Installation Steps

### Step 1: Wait for Core Dependencies (In Progress)
**Current terminal:** `55c03c1c-17a7-4551-b5f4-00384fa2b6f2`

Building pandas from source takes 3-5 minutes. You'll see:
```
Preparing metadata (pyproject.toml) ... done
Building wheel for pandas...
Installing collected packages: faker, pandas, numpy, ...
Successfully installed faker-24.0.0 pandas-2.2.0 ...
```

### Step 2: Verify Core Installation
Once Stage 1 completes, verify the installation:
```bash
python -c "import faker, pandas, numpy, google.cloud.bigquery, python_dotenv; print('✓ Core packages OK')"
```

**Expected output:**
```
✓ Core packages OK
```

### Step 3: Install Apache Beam

**Recommended approach:**
```bash
pip install --prefer-binary apache-beam==2.54.0
```

Verify:
```bash
python -c "import apache_beam; print(f'✓ Apache Beam {apache_beam.__version__} OK')"
```

---

## 🔍 Checking Installation Progress

### Check pip Status (While Installing)
Terminal ID: `55c03c1c-17a7-4551-b5f4-00384fa2b6f2`

Current phase: Pandas wheel building (normal for source build)

### Check Each Package
```bash
# Check Faker
python -c "import faker; print(f'✓ Faker {faker.__version__}')"

# Check Pandas
python -c "import pandas; print(f'✓ Pandas {pandas.__version__}')"

# Check NumPy
python -c "import numpy; print(f'✓ NumPy {numpy.__version__}')"

# Check Google Cloud BigQuery
python -c "import google.cloud.bigquery; print('✓ BigQuery client OK')"

# Check Google Cloud Storage
python -c "import google.cloud.storage; print('✓ Storage client OK')"

# Check Google Cloud Pub/Sub
python -c "import google.cloud.pubsub_v1; print('✓ Pub/Sub client OK')"

# Check Functions Framework
python -c "import functions_framework; print('✓ Functions Framework OK')"

# Check python-dotenv
python -c "import dotenv; print('✓ python-dotenv OK')"

# Check Apache Beam (after Stage 2)
python -c "import apache_beam; print(f'✓ Apache Beam {apache_beam.__version__}')"
```

---

## 🛠️ Troubleshooting

### If Pandas Build Fails
```bash
# Use pre-built wheel instead
pip install --only-binary :all: pandas==2.2.0
```

### If pip Complains About site-packages
```bash
# Use user installation (already happening)
pip install --user -r requirements.txt
```

### If Apache Beam Install Fails with grpcio-tools
```bash
# Use pre-built binaries
pip install --prefer-binary apache-beam==2.54.0

# Or try older Beam version with better Windows support
pip install apache-beam==2.53.0
```

### If You See "wheel.exe not on PATH"
```bash
# This is just a warning, not an error
# To fix: add to PATH or use python -m pip instead
python -m pip install apache-beam==2.54.0
```

---

## ✅ What Should Succeed

| Package | Version | Status |
|---------|---------|--------|
| setuptools | >=65.0 | ✅ Should install |
| wheel | latest | ✅ Should install |
| faker | 24.0.0 | ✅ Should install |
| pandas | 2.2.0 | ⏳ Building from source (normal) |
| numpy | 1.26.4 | ✅ Should install (pre-built) |
| google-cloud-bigquery | 3.17.0 | ✅ Should install |
| google-cloud-storage | 2.14.0 | ✅ Should install |
| google-cloud-pubsub | 2.19.0 | ✅ Should install |
| python-dotenv | 1.0.0 | ✅ Should install |
| functions-framework | 3.5.0 | ✅ Should install |
| **apache-beam** | **2.54.0** | **⏸️ Install separately** |

---

## 📍 After Installation: Next Steps

Once ALL packages are installed (including Apache Beam), verify everything:

```bash
# Quick verification
python scripts/generate_data.py --help

# Full dependency check
python -c "
import faker, pandas, numpy
from google.cloud import bigquery, storage, pubsub_v1
import apache_beam
import python_dotenv
import functions_framework
print('✅ All dependencies installed successfully!')
"
```

**Expected output:**
```
✅ All dependencies installed successfully!
```

---

## 📚 Related Files

- `requirements.txt` - Core dependencies (no Apache Beam)
- `install_beam.sh` - Automated Beam installation script
- `README.md` - Project overview
- `QUICKSTART.md` - Quick reference guide

---

## 🚀 Ready to Continue?

Once all packages are installed:

1. ✅ Run `python --version` (verify 3.11+)
2. ✅ Follow SETUP_GUIDE.md for GCP setup
3. ✅ Execute the 11-step pipeline

---

## 📞 Support

If installation fails:
1. Check the error message carefully
2. Try the alternative installation method
3. Consult troubleshooting section above
4. Ensure you have ~500MB free disk space
5. Ensure Python 3.11+ is installed

**Remember:** The multi-stage installation is a **workaround for a known Windows build issue**, not a problem with your setup. This is a common issue with Apache Beam on Windows.
