# FastAPI layered effective-config service

Exact precedence: hardcoded defaults < `config.development.yaml` < `.env` < OS `APP_*` < repeated `?set=key=value` query parameters.

## Run locally

```bash
python -m pip install -r requirements.txt
```

**PowerShell**:

```powershell
$env:APP_DEBUG="true"
$env:APP_LOG_LEVEL="info"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://127.0.0.1:8000/effective-config?set=port=9000&set=debug=false`.

## Public deployment

Deploy this directory as a Docker-based web service on a hosting provider (e.g. Railway).
Set process-level environment variables `APP_DEBUG=true` and `APP_LOG_LEVEL=info`.
Leave `APP_ENV` unset, or set it to `development`.
The public grader URL is `https://<your-real-hostname>/effective-config`.

Use a private repository or securely provision the `.env` content when using real credentials.
A hosting platform's `PORT` selects the listen port; `APP_PORT` is the configuration value returned by the API.

## Expected outputs

No overrides:
```json
{"port":8150,"workers":7,"debug":true,"log_level":"info","api_key":"****"}
```

`?set=port=9000&set=debug=false&set=workers=12`:
```json
{"port":9000,"workers":12,"debug":false,"log_level":"info","api_key":"****"}
```

The `.env`-only alias `NUM_WORKERS=9` maps to `workers=9`. If `.env` also defines `APP_WORKERS`, the explicit `APP_WORKERS` wins. The OS `APP_WORKERS` and CLI `set=workers=N` still have higher precedence.
