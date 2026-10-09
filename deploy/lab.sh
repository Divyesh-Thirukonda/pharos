#!/usr/bin/env bash
# Run only on the team's existing workshop VM. Never run this with bash -x.
set +x
set -euo pipefail

pharos_ns=team-12
pharos_host=video-lab-team-12.cosmos.vastdata.com
pharos_bundle=${1:-"$(dirname "$0")/pharos.tar.gz"}
for pharos_cmd in kubectl python3; do
  command -v "$pharos_cmd" >/dev/null || { echo "Missing command: $pharos_cmd" >&2; exit 1; }
done
test -f "$pharos_bundle" || { echo "Missing bundle: upload pharos.tar.gz and pass its path as the first argument." >&2; exit 1; }

# Prefer the workshop's exported kubeconfig. Canonical aliases are documented by
# the public builders-challenge config.example; no other team's files are read.
if [[ -z "${KUBECONFIG:-}" ]]; then
  if [[ -f /config/team-12-k8s.yaml ]]; then
    export KUBECONFIG=/config/team-12-k8s.yaml
  elif [[ -f /config/kubeconfig ]]; then
    export KUBECONFIG=/config/kubeconfig
  else
    echo "Missing KUBECONFIG and /config/team-12-k8s.yaml (or /config/kubeconfig). Use the Team 12 workshop VM." >&2
    exit 1
  fi
fi
[[ -f "$KUBECONFIG" ]] || { echo "KUBECONFIG must name one existing Team 12 configuration file." >&2; exit 1; }
[[ "$(kubectl -n "$pharos_ns" auth can-i get pods)" == yes ]] || { echo "The current workshop credentials cannot read pods in team-12." >&2; exit 1; }

pharos_tmp=$(mktemp -d)
trap 'rm -rf "$pharos_tmp"' EXIT
export PHAROS_DEPLOY_TMP="$pharos_tmp"
export PHAROS_DEPLOY_BUNDLE="$pharos_bundle"

# The workshop's legacy public VSS hostname may not resolve inside pods.
# Prefer the verified same-namespace API service when its expected port exists.
kubectl -n "$pharos_ns" get service video-backend-service --ignore-not-found -o json > "$pharos_tmp/vss-service.json"
export PHAROS_INTERNAL_VSS_URL="$(python3 - <<'PY'
import json, os, pathlib
text = (pathlib.Path(os.environ['PHAROS_DEPLOY_TMP'])/'vss-service.json').read_text().strip()
service = json.loads(text) if text else {}
if any(port.get('port') == 8000 for port in service.get('spec', {}).get('ports', [])):
    print('http://video-backend-service:8000')
PY
)"

# Validate the uploaded bundle before creating any resources.
python3 - <<'PY'
import os, pathlib, tarfile
bundle = pathlib.Path(os.environ['PHAROS_DEPLOY_BUNDLE'])
if bundle.stat().st_size > 1_300_000:
    raise SystemExit('Bundle exceeds the two-ConfigMap limit (1300000 compressed bytes).')
with tarfile.open(bundle, 'r:gz') as archive:
    members = archive.getmembers()
    if any(m.issym() or m.islnk() or m.name.startswith('/') or '..' in pathlib.PurePosixPath(m.name).parts for m in members):
        raise SystemExit('Bundle contains an unsafe archive path or link.')
    if sum(m.size for m in members) > 30_000_000:
        raise SystemExit('Bundle exceeds the expected uncompressed app size.')
    names = {m.name.removeprefix('./') for m in members}
    if not {'backend/main.py', 'backend/requirements.txt', 'dist/index.html'} <= names:
        raise SystemExit('Bundle is missing backend/main.py, backend/requirements.txt or dist/index.html.')
data = bundle.read_bytes()
directory = pathlib.Path(os.environ['PHAROS_DEPLOY_TMP'])
for index in range(2):
    (directory/f'part-{index}').write_bytes(data[index*650_000:(index+1)*650_000])
print('Bundle verified and split into two bounded ConfigMap payloads.')
PY

# Public workshop mapping: INGRESS_URL, USERNAME, PASSWORD are the VSS API values.
# Only selected provider fields are read; never print, save, or shell-evaluate keys.
cat > "$pharos_tmp/secret.py" <<'PY'
import base64, json, os, pathlib, shlex
from urllib.parse import urlparse
cfg = {}
path = pathlib.Path('/config/team-12.config')
if path.is_file():
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith('export '):
            line = line[7:]
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if key not in {'USERNAME','PASSWORD','INGRESS_URL','WANDB_API_KEY','WANDB_TEAM','WANDB_PROJECT','WANDB_MODEL','COSMOS3_REASON_URL','COSMOS3_REASON_MODEL','YOLO_URL','GPU_BEARER_TOKEN'}:
            continue
        try:
            pieces = shlex.split(value, comments=True)
        except ValueError:
            raise SystemExit(f'Cannot parse config field {key}; no values were printed.')
        cfg[key] = ' '.join(pieces)
def value(*keys):
    for key in keys:
        if os.environ.get(key):
            return os.environ[key]
    for key in keys:
        if cfg.get(key):
            return cfg[key]
    return ''
selected = {
    'VSS_URL': value('VSS_URL') or os.environ.get('PHAROS_INTERNAL_VSS_URL') or value('INGRESS_URL'),
    'VSS_USERNAME': value('VSS_USERNAME','USERNAME'),
    'VSS_PASSWORD': value('VSS_PASSWORD','PASSWORD'),
    'WANDB_API_KEY': value('WANDB_API_KEY'),
    'WANDB_TEAM': value('WANDB_TEAM'),
    'WANDB_PROJECT': value('WANDB_PROJECT') or 'pharos',
    'WANDB_MODEL': value('WANDB_MODEL'),
    'WEAVE_PROJECT': value('WEAVE_PROJECT'),
    'WEAVE_ENABLED': value('WEAVE_ENABLED') or 'false',
    'SOCRATA_APP_TOKEN': value('SOCRATA_APP_TOKEN'),
    # Public workshop gpu/README.md documents these shared endpoints.
    'COSMOS3_REASON_URL': value('COSMOS3_REASON_URL') or 'http://166.19.38.112:8001',
    'COSMOS3_REASON_MODEL': value('COSMOS3_REASON_MODEL'),
    'YOLO_URL': value('YOLO_URL') or 'http://166.19.38.112:8002',
    'GPU_BEARER_TOKEN': value('GPU_BEARER_TOKEN'),
}
missing = [key for key in ('VSS_URL','VSS_USERNAME','VSS_PASSWORD','WANDB_API_KEY','GPU_BEARER_TOKEN') if not selected[key]]
if missing:
    raise SystemExit('Missing provider settings: ' + ', '.join(missing) + '. Check exported workshop variables or /config/team-12.config.')
if selected['VSS_USERNAME'] != 'team-12':
    raise SystemExit('VSS_USERNAME must identify team-12. No credential values were printed.')
url = urlparse(selected['VSS_URL'])
if url.scheme not in {'http','https'} or not url.netloc or url.username or url.password:
    raise SystemExit('VSS_URL must be an HTTP(S) service URL without embedded credentials.')
if os.environ.get('PHAROS_SECRET_VALIDATE_ONLY') == '1':
    print('Required Team 12 provider settings are present; values were not printed.')
else:
    print(json.dumps({'apiVersion':'v1','kind':'Secret','metadata':{'name':'pharos-vss-creds','namespace':'team-12','labels':{'app':'pharos'}},'type':'Opaque','data':{k:base64.b64encode(v.encode()).decode() for k,v in selected.items() if v}}))
PY
PHAROS_SECRET_VALIDATE_ONLY=1 python3 "$pharos_tmp/secret.py"

# Inspect existing routes before mutation. Keep every VSS /api or / route intact.
kubectl -n "$pharos_ns" get ingress -o json > "$pharos_tmp/ingresses.json"
python3 - <<'PY'
import json, os, pathlib
directory = pathlib.Path(os.environ['PHAROS_DEPLOY_TMP'])
data = json.loads((directory/'ingresses.json').read_text())
matches = []
for item in data.get('items', []):
    for ri, rule in enumerate(item.get('spec', {}).get('rules', [])):
        if rule.get('host') != 'video-lab-team-12.cosmos.vastdata.com':
            continue
        for pi, path in enumerate(rule.get('http', {}).get('paths', [])):
            p = path.get('path', '')
            if p == '/app' or p.startswith('/app/') or p.startswith('/app('):
                matches.append((item, ri, pi, path))
if len(matches) > 1:
    raise SystemExit('More than one existing /app route found in team-12. Inspect the intended App ingress before deploying.')
plan = {'action':'create', 'name':'pharos-ingress'}
if matches:
    item, ri, pi, path = matches[0]
    name = item['metadata']['name']
    expected = os.environ.get('PHAROS_APP_INGRESS_NAME', 'pharos-ingress')
    if name != expected:
        raise SystemExit(f'Existing App ingress is {name}. Inspect it, then rerun with PHAROS_APP_INGRESS_NAME={name}; no resources changed.')
    annotations = item['metadata'].get('annotations', {})
    if path.get('path') != '/app(/|$)(.*)' or annotations.get('nginx.ingress.kubernetes.io/rewrite-target') != '/$2':
        raise SystemExit('Existing App ingress does not use the expected /app regex rewrite. No routes were changed.')
    plan = {'action':'patch','name':name,'patch':[
        {'op':'test','path':'/metadata/resourceVersion','value':item['metadata']['resourceVersion']},
        {'op':'replace','path':f'/spec/rules/{ri}/http/paths/{pi}/backend/service','value':{'name':'pharos','port':{'number':80}}},
    ]}
(directory/'ingress-plan.json').write_text(json.dumps(plan))
print(f"App ingress preflight: {plan['action']} {plan['name']} only; VSS routes remain intact.")
PY

# Server-side apply avoids the 256 KiB last-applied annotation limit on bundles.
for pharos_part in 0 1; do
  kubectl -n "$pharos_ns" create configmap "pharos-bundle-$pharos_part" --from-file="part-$pharos_part=$pharos_tmp/part-$pharos_part" --dry-run=client -o json |
    kubectl -n "$pharos_ns" apply --server-side --field-manager=pharos-deploy -f -
done
python3 "$pharos_tmp/secret.py" |
  kubectl -n "$pharos_ns" apply --server-side --field-manager=pharos-deploy -f -

kubectl -n "$pharos_ns" apply --server-side --field-manager=pharos-deploy -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pharos
  namespace: team-12
  labels: {app: pharos}
spec:
  replicas: 1
  progressDeadlineSeconds: 600
  selector:
    matchLabels: {app: pharos}
  template:
    metadata:
      labels: {app: pharos}
    spec:
      containers:
        - name: pharos
          image: python:3.12-slim
          imagePullPolicy: IfNotPresent
          workingDir: /code
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: pharos-vss-creds
          env:
            - {name: PHAROS_CACHE_DIR, value: /code/backend/.cache}
            - {name: PYTHONUNBUFFERED, value: "1"}
            - {name: IMAGEIO_FFMPEG_EXE, value: /usr/bin/ffmpeg}
          command: ["sh", "-ec"]
          args:
            - |
              cat /bundle/part-0 /bundle/part-1 | tar -xz -C /code
              # The wheel's Linux static FFmpeg segfaults on these HLS feeds.
              # Use Debian's supported binary for both capture and metadata.
              apt-get update -qq
              DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ffmpeg ca-certificates
              rm -rf /var/lib/apt/lists/*
              if [ -n "${WEAVE_PROJECT:-}" ] || [ "${WEAVE_ENABLED:-false}" = "true" ]; then
                python -m pip install --no-cache-dir -q -r /code/backend/requirements-tracing.txt
              else
                python -m pip install --no-cache-dir -q -r /code/backend/requirements.txt
              fi
              exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --no-access-log
          readinessProbe:
            httpGet: {path: /health, port: 8080}
            initialDelaySeconds: 10
            periodSeconds: 5
          resources:
            requests: {cpu: 100m, memory: 256Mi}
            limits: {cpu: "1", memory: 1Gi}
          volumeMounts:
            - {name: bundle, mountPath: /bundle, readOnly: true}
            - {name: code, mountPath: /code}
      volumes:
        - name: bundle
          projected:
            sources:
              - configMap: {name: pharos-bundle-0}
              - configMap: {name: pharos-bundle-1}
        - name: code
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: pharos
  namespace: team-12
  labels: {app: pharos}
spec:
  selector: {app: pharos}
  ports:
    - {name: http, port: 80, targetPort: 8080}
  type: ClusterIP
YAML

python3 - <<'PY'
import json, os, pathlib, subprocess
plan = json.loads((pathlib.Path(os.environ['PHAROS_DEPLOY_TMP'])/'ingress-plan.json').read_text())
if plan['action'] == 'patch':
    subprocess.run(['kubectl','-n','team-12','patch','ingress',plan['name'],'--type=json','-p',json.dumps(plan['patch'])],check=True)
else:
    manifest = {'apiVersion':'networking.k8s.io/v1','kind':'Ingress','metadata':{'name':'pharos-ingress','namespace':'team-12','labels':{'app':'pharos'},'annotations':{'nginx.ingress.kubernetes.io/use-regex':'true','nginx.ingress.kubernetes.io/rewrite-target':'/$2'}},'spec':{'ingressClassName':'nginx','rules':[{'host':'video-lab-team-12.cosmos.vastdata.com','http':{'paths':[{'path':'/app(/|$)(.*)','pathType':'ImplementationSpecific','backend':{'service':{'name':'pharos','port':{'number':80}}}}]}}]}}
    subprocess.run(['kubectl','-n','team-12','apply','--server-side','--field-manager=pharos-deploy','-f','-'],input=json.dumps(manifest),text=True,check=True)
PY

# A restart is required to extract changed ConfigMap bytes on repeated deploys.
kubectl -n "$pharos_ns" rollout restart deployment/pharos
kubectl -n "$pharos_ns" rollout status deployment/pharos --timeout=600s
kubectl -n "$pharos_ns" get pods,service,ingress -l app=pharos
kubectl -n "$pharos_ns" exec -i deployment/pharos -- python - <<'PY'
import json, urllib.request
base = 'http://127.0.0.1:8080'
for path in ('/health','/api/health'):
    with urllib.request.urlopen(base+path,timeout=30) as response:
        data = json.load(response)
    if data.get('status') != 'ok':
        raise SystemExit('App readiness did not return ok.')
    if path.endswith('/api/health'):
        print('Provider configuration:', ', '.join(f"{name}={service.get('configured', False)}" for name, service in data['services'].items()))
print('Pod ready. Open https://team-12-app.thecosmoslabs.com/app/ or the workshop App button.')
PY
