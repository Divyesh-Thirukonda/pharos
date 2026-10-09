#!/bin/bash
# Local-only PharOS: map, crash data and public cameras. No workshop keys here, so live video analysis and VAST search show as offline.
cd "$(dirname "$0")"
git pull -q --ff-only 2>/dev/null
backend/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 >/tmp/pharos-api.log 2>&1 &
API=$!
trap "kill $API 2>/dev/null" EXIT
sleep 3
( sleep 4; open http://127.0.0.1:5173 ) &
npm run dev
