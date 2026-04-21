#!/bin/bash
# Install Apache Beam with pre-built wheels to avoid grpcio-tools build issues
# This script installs Apache Beam separately after core dependencies

echo "Installing Apache Beam 2.54.0 with pre-built wheels..."
pip install --only-binary :all: apache-beam==2.54.0 2>/dev/null || \
pip install apache-beam==2.54.0 --prefer-binary 2>/dev/null || \
pip install apache-beam==2.54.0

echo "✓ Apache Beam installation complete"
python -c "import apache_beam; print(f'✓ Apache Beam {apache_beam.__version__} ready')"
