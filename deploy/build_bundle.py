"""Package the already-built frontend and backend for the workshop ConfigMap."""
from io import BytesIO
from pathlib import Path
import hashlib
import tarfile

root = Path(__file__).resolve().parent.parent
output = root / "deploy" / "pharos.tar.gz"
if not (root / "dist" / "index.html").is_file():
    raise SystemExit("Build the frontend first: npm run build")
files = {root / "backend" / name for name in ("main.py", "__init__.py", "requirements.txt", "requirements-tracing.txt", "README.md")}
files.update((root / "backend").glob("*.py"))
# Include reviewable source alongside the runtime. Explicit paths exclude all
# credentials, public-data caches, virtualenvs and node_modules.
for directory in ("dist", "src", "design", "public", "backend/tests"):
    files.update(p for p in (root / directory).rglob("*") if p.is_file() and not p.is_symlink() and "__pycache__" not in p.parts)
for name in ("README.md", "THIRD_PARTY_NOTICES.md", "package.json", "package-lock.json", "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json", "vite.config.ts", "index.html", "deploy/README.md", "deploy/lab.sh", "deploy/build_bundle.py"):
    if (root / name).is_file():
        files.add(root / name)
with tarfile.open(output, "w:gz", compresslevel=9) as archive:
    for path in sorted(files):
        name = path.relative_to(root).as_posix()
        data = path.read_bytes()
        if name == "dist/index.html":
            # Handles both /app and /app/ without changing the local build.
            data = data.replace(b"<head>", b'<head><base href="/app/">', 1)
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mode = 0o644
        archive.addfile(info, BytesIO(data))
size = output.stat().st_size
if size > 1_300_000:
    raise SystemExit(f"Bundle is too large for this deployment method: {size} bytes")
print(f"{output}\n{size} bytes\nSHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}")
