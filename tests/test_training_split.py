import json
import os


# We'll just run the script and check the manifest, or we can check the split directly
def test_no_family_leakage_in_training_data(tmp_path, monkeypatch):
    from training.generate_data import main
    import sys

    # Mock output directory and argv
    def mock_abspath(path):
        return str(tmp_path / "mock_file.py")

    monkeypatch.setattr(os.path, "abspath", mock_abspath)
    monkeypatch.setattr(sys, "argv", ["generate_data.py"])

    # Run the generator
    main()

    data_dir = tmp_path / "processed"
    manifest_path = data_dir / "manifest.json"

    assert manifest_path.exists(), "Manifest should be generated"

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["total_families"] == manifest["train_families"] + manifest["val_families"], "Families must not overlap between train and val"
    assert manifest["train_families"] > 0
    assert manifest["val_families"] > 0

def test_split_ratio_is_close_to_target(tmp_path, monkeypatch):
    from training.generate_data import main
    import sys
    
    def mock_abspath(path):
        return str(tmp_path / "mock_file.py")
        
    monkeypatch.setattr(os.path, "abspath", mock_abspath)
    monkeypatch.setattr(sys, "argv", ["generate_data.py"])

    main()

    manifest_path = tmp_path / "processed" / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    assert 0.8 < manifest["split_ratio"] < 1.0


import subprocess

def test_manifest_has_sha256(tmp_path, monkeypatch):
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    subprocess.run(['python', 'training/generate_data.py', '--output-dir', str(tmp_path)], env=env, check=True)
    manifest_path = tmp_path / 'manifest.json'
    assert manifest_path.exists()
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        
    assert 'files' in manifest
    assert 'train.jsonl' in manifest['files']
    assert 'val.jsonl' in manifest['files']
    
    for filename, info in manifest['files'].items():
        assert 'sha256' in info
        assert len(info['sha256']) == 64
        assert 'size_bytes' in info

def test_manifest_seed_matches_arg(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    subprocess.run(['python', 'training/generate_data.py', '--output-dir', str(tmp_path), '--seed', '99'], env=env, check=True)
    manifest_path = tmp_path / 'manifest.json'
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        
    assert manifest.get('seed') == 99

def test_generator_commit_present(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    subprocess.run(['python', 'training/generate_data.py', '--output-dir', str(tmp_path)], env=env, check=True)
    manifest_path = tmp_path / 'manifest.json'
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        
    assert 'generator_commit' in manifest
    assert len(manifest['generator_commit']) > 0


def test_split_leakage_detection():
    """TRAIN-002: Verify that near-duplicate samples across train/val splits are caught."""
    from training.validators.dataset_validator import SplitLeakageCheck

    train_samples = [
        {"messages": [{"role": "user", "content": "What is the capital of France?"}, {"role": "assistant", "content": "The capital of France is Paris."}]},
        {"messages": [{"role": "user", "content": "How do you calculate the area of a circle?"}, {"role": "assistant", "content": "The area is pi times r squared."}]},
    ]

    # Exactly or nearly duplicate validation sample
    leaked_val_samples = [
        {"messages": [{"role": "user", "content": "What is the capital city of France?"}, {"role": "assistant", "content": "The capital of France is Paris."}]},
    ]

    # Clean distinct validation sample
    clean_val_samples = [
        {"messages": [{"role": "user", "content": "Explain Newton's third law of motion in physics."}, {"role": "assistant", "content": "For every action there is an equal opposite reaction."}]},
    ]

    checker = SplitLeakageCheck(threshold=0.70)
    leaks = checker.check_splits(train_samples, leaked_val_samples)
    assert len(leaks) > 0
    assert "Leakage detected" in leaks[0]

    clean = checker.check_splits(train_samples, clean_val_samples)
    assert len(clean) == 0
