import pytest

import os
import json
import subprocess
from glob import glob
from training.validators.dataset_validator import DatasetValidator

BENCHMARK_DIR = os.path.join(os.path.dirname(__file__), '..', 'training', 'benchmark')

def test_benchmark_files_exist():
    expected_files = [
        'beginner_python.jsonl',
        'intermediate_python.jsonl',
        'math.jsonl',
        'tutoring_behavior.jsonl',
        'safety.jsonl',
        'agent_routing.jsonl',
        'privacy.jsonl'
    ]
    
    for f in expected_files:
        assert os.path.exists(os.path.join(BENCHMARK_DIR, f)), f'Missing benchmark file: {f}'

def test_benchmark_files_are_valid_jsonl():
    files = glob(os.path.join(BENCHMARK_DIR, '*.jsonl'))
    assert len(files) >= 7
    
    for file_path in files:
        validator = DatasetValidator()
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    pytest.fail(f'Invalid JSON in {file_path} at line {idx}')
                    
        errors = validator.validate_dataset(data)
        assert len(errors) == 0, f'Validation errors in {file_path}: {errors}'

def test_run_benchmark_smoke():
    env = os.environ.copy()
    env['PYTHONPATH'] = '.'
    result = subprocess.run(
        ['python', 'training/benchmark/run_benchmark.py', '--model-stub'],
        env=env,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'BENCHMARK PASSED' in result.stdout
