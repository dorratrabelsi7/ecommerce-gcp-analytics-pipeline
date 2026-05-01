#!/usr/bin/env python3
"""
Validation script for DirectRunner pipeline output

Vérifie que les fichiers de sortie du pipeline DirectRunner sont corrects.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

def validate_jsonl_file(file_path):
    """Valider un fichier JSONL."""
    errors = []
    valid_count = 0
    invalid_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    record = json.loads(line)
                    
                    # Vérifications de base
                    if not isinstance(record, dict):
                        errors.append(f"Line {line_num}: Not a JSON object")
                        invalid_count += 1
                        continue
                    
                    # Vérifier les champs de métadonnées
                    if "processing_timestamp" not in record:
                        errors.append(f"Line {line_num}: Missing processing_timestamp")
                    if "pipeline_version" not in record:
                        errors.append(f"Line {line_num}: Missing pipeline_version")
                    
                    # Vérifier le format du timestamp
                    if "processing_timestamp" in record:
                        try:
                            datetime.fromisoformat(record["processing_timestamp"].replace('Z', '+00:00'))
                        except ValueError:
                            errors.append(f"Line {line_num}: Invalid timestamp format")
                    
                    valid_count += 1
                    
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: Invalid JSON - {e}")
                    invalid_count += 1
        
        return {
            "file": file_path,
            "status": "OK" if not errors else "ISSUES",
            "valid_records": valid_count,
            "invalid_records": invalid_count,
            "errors": errors[:5]  # Show first 5 errors
        }
    
    except FileNotFoundError:
        return {
            "file": file_path,
            "status": "NOT FOUND",
            "valid_records": 0,
            "invalid_records": 0,
            "errors": ["File not found"]
        }
    except Exception as e:
        return {
            "file": file_path,
            "status": "ERROR",
            "valid_records": 0,
            "invalid_records": 0,
            "errors": [str(e)]
        }


def main():
    """Valider les fichiers de sortie."""
    output_dir = "output"
    
    if not os.path.exists(output_dir):
        print(f"❌ Output directory not found: {output_dir}")
        return 1
    
    output_files = list(Path(output_dir).glob("*.jsonl"))
    
    if not output_files:
        print(f"❌ No JSONL files found in {output_dir}")
        return 1
    
    print("=" * 80)
    print("VALIDATION: Pipeline DirectRunner Output")
    print("=" * 80)
    print("")
    
    total_valid = 0
    total_invalid = 0
    all_good = True
    
    for output_file in sorted(output_files):
        result = validate_jsonl_file(str(output_file))
        
        status_icon = "✅" if result["status"] == "OK" else "⚠️" if result["status"] == "ISSUES" else "❌"
        print(f"{status_icon} {result['file']}")
        print(f"   Status: {result['status']}")
        print(f"   Valid records: {result['valid_records']}")
        print(f"   Invalid records: {result['invalid_records']}")
        
        if result['errors']:
            all_good = False
            print(f"   Errors (showing first 5):")
            for error in result['errors']:
                print(f"     - {error}")
        print("")
        
        total_valid += result['valid_records']
        total_invalid += result['invalid_records']
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total valid records: {total_valid}")
    print(f"Total invalid records: {total_invalid}")
    print(f"Total records: {total_valid + total_invalid}")
    print(f"Overall status: {'✅ ALL OK' if all_good else '⚠️  ISSUES FOUND'}")
    print("")
    
    # Sample record
    sample_file = list(Path(output_dir).glob("valid_*.jsonl"))[0] if list(Path(output_dir).glob("valid_*.jsonl")) else None
    if sample_file:
        print("SAMPLE RECORD:")
        with open(sample_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line:
                sample = json.loads(first_line)
                print(json.dumps(sample, indent=2, ensure_ascii=False))
    
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
