
import json
import hashlib
import os
import subprocess
from datetime import datetime, timezone

def get_git_commit() -> str:
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except Exception:
        return 'unknown'

def hash_file(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def build_manifest(data_dir: str, seed: int, version: str, stats: dict) -> dict:
    manifest = {
        'dataset_version': version,
        'generator_commit': get_git_commit(),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'seed': seed,
        'files': {}
    }
    
    # Add stats
    manifest.update(stats)
    
    # Hash files
    for filename in os.listdir(data_dir):
        if filename.endswith('.jsonl'):
            filepath = os.path.join(data_dir, filename)
            manifest['files'][filename] = {
                'sha256': hash_file(filepath),
                'size_bytes': os.path.getsize(filepath)
            }
            
    return manifest
    
def verify_manifest(manifest_path: str) -> bool:
    if not os.path.exists(manifest_path):
        return False
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    data_dir = os.path.dirname(manifest_path)
    for filename, info in manifest.get('files', {}).items():
        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            return False
        if hash_file(filepath) != info['sha256']:
            return False
            
    return True
