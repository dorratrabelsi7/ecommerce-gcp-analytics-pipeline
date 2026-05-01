"""
Setup configuration for Apache Beam pipeline on Dataflow.

This file is required when using DataflowRunner to properly package
dependencies and distribute them to Dataflow workers.

Author: E-commerce Analytics Team
Date: 2026-04-23
"""

import setuptools

setuptools.setup(
    name='ecommerce-beam-etl',
    version='2.0.0',
    description='E-commerce ETL pipeline on Google Cloud Dataflow',
    packages=setuptools.find_packages(),
    install_requires=[
        # Apache Beam with GCP support (required for Dataflow)
        'apache-beam[gcp]==2.53.0',
        
        # Google Cloud Services
        'google-cloud-bigquery==3.17.0',
        'google-cloud-storage==2.14.0',
        'google-cloud-pubsub==2.19.0',
        'google-cloud-logging==3.8.0',
        
        # Data processing
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        
        # Utilities
        'python-dotenv==1.0.0',
        
        # HTTP/networking (for Dataflow workers)
        'requests>=2.31.0',
    ],
    python_requires='>=3.11',
    author='E-commerce Analytics Team',
    author_email='analytics@example.com',
    url='https://github.com/your-repo/ecommerce-gcp-analytics-pipeline',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
    ],
)
