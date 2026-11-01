@echo off
REM Rexetive v2 demo: API on :8001 (DEMO_MODE + MOCK CHAIN) and the React app on :5173.
cd /d "%~dp0"
set PY=backend\.venv\Scripts\python.exe
if not exist %PY% (
  echo Creating backend venv...
  py -3.11 -m venv backend\.venv 2>nul || py -3.10 -m venv backend\.venv
  %PY% -m pip install torch --index-url https://download.pytorch.org/whl/cpu
  %PY% -m pip install -r backend\requirements.txt
)
if not exist backend\.env copy backend\.env.example backend\.env >nul
if not exist frontend\.env.local copy frontend\.env.example frontend\.env.local >nul
if not exist frontend\node_modules (pushd frontend & call npm install & popd)
if not exist backend\data\rexetive.db (pushd backend & ..\%PY% scripts\seed_db.py & popd)
%PY% -c "import os; os.environ['HF_HUB_OFFLINE']='1'; from sentence_transformers import SentenceTransformer as S, CrossEncoder as C; S('BAAI/bge-small-en-v1.5'); C('cross-encoder/ms-marco-MiniLM-L-6-v2')" 2>nul || %PY% backend\scripts\download_models.py
echo Building / loading the evidence index...
pushd backend
..\%PY% -c "from cases import get_indexes; ix=get_indexes(); print(len(ix.chunks), 'evidence chunks; rebuilt =', ix.rebuilt)"
set DEMO_MODE=true
set SUI_MOCK=1
start "Rexetive API :8001" ..\%PY% -m uvicorn main:app --port 8001
popd
pushd frontend
start "Rexetive web :5173" cmd /c npm run dev -- --port 5173
popd
echo API docs: http://localhost:8001/docs
echo Web app:  http://localhost:5173   (click "Demo login")
