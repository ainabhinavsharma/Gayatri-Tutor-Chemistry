
import argparse
import json
import sys
from training.validators.dataset_validator import DatasetValidator

def main():
    parser = argparse.ArgumentParser(description='Validate a JSONL dataset file')
    parser.add_argument('filepath', type=str, help='Path to JSONL file')
    args = parser.parse_args()
    
    data = []
    with open(args.filepath, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                print(f'ERROR: Line {idx} is not valid JSON')
                sys.exit(1)
                
    validator = DatasetValidator()
    errors = validator.validate_dataset(data)
    
    if errors:
        print(f'Found {len(errors)} validation errors:')
        for e in errors:
            print(f'  - {e}')
        sys.exit(1)
        
    print(f'Successfully validated {len(data)} items')
    
if __name__ == '__main__':
    main()
