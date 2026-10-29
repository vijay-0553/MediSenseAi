import hashlib
from pathlib import Path

samples_dir = Path("backend/samples")
print("=" * 135)
print(f"{'Relative File Path':<40} | {'Size':<10} | {'SHA-256 Hash'}")
print("=" * 135)

for p in sorted(samples_dir.rglob("*")):
    if p.is_file():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rel_path = str(p.relative_to(samples_dir.parent)).replace("\\", "/")
        print(f"{rel_path:<40} | {p.stat().st_size:<10} | {h}")
