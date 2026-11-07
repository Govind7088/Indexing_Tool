# URL Indexing Status Tool

Submit a URL and see its **real** Google indexing status. Shows the 5 most recent URLs and a
"View all" list. No login.

**Stack:** React + Vite · Django + Django REST Framework · MySQL 8.0 · Vitest · Django tests

For a simple explanation (which URLs work, why some are rejected, how to test), read
**[docs/GUIDE.md](docs/GUIDE.md)**.

## Quick start (Windows, PowerShell)

Needs: Python 3.12+, **Node.js 22.12+**, MySQL 8.0.

0. **Get the code:**
   ```powershell
   git clone https://github.com/Govind7088/Indexing_Tool.git
   cd Indexing_Tool
   ```
1. **Install:** run `setup.bat` (creates the virtual environment, installs packages, creates `backend\.env`).
2. **Edit `backend\.env`:** set `DB_USER`, `DB_PASSWORD`, `DJANGO_SECRET_KEY`.
   Make a key with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`
3. **Create the database:**
   ```powershell
   mysql -u YOUR_USER -p -e "CREATE DATABASE indexing_tool_db CHARACTER SET utf8mb4;"
   cd backend
   ..\venv\Scripts\activate
   python manage.py migrate
   ```
   (If the `mysql` command is not found, run `CREATE DATABASE indexing_tool_db CHARACTER SET utf8mb4;`
   in MySQL Workbench instead, then run the `migrate` commands.)
4. **Start:** run `start.bat`, then open **http://localhost:5173** (use `localhost`, not `127.0.0.1`).
   Without the .bat file: run `python manage.py runserver` in `backend` (venv active) and
   `npm run dev` in the main folder, in two terminals.

## Two ways to run

| Mode | `.env` setting | What happens |
|---|---|---|
| **Demo** (default) | `GOOGLE_ENABLED=False` | Any valid http/https URL is saved. Nothing is sent to Google. Status shows "Not inspected". Good for checking the UI, validation, Recent 5, View all. |
| **Google** | `GOOGLE_ENABLED=True` | Real Google status. Only URLs inside a Search Console property your Google account can access are accepted. |

### Google mode setup

```powershell
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

Enable **Google Search Console API** in that Google Cloud project. In `backend\.env` set
`GOOGLE_ENABLED=True` and `GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID`, then restart the backend
(`.env` is read only at start).

Never commit `.env` or the credentials file that gcloud creates.

## Which URLs are accepted?

- Always: a full `http://` or `https://` URL (max 2048 characters, no `user:password@`).
- Google mode also needs access to the site in Search Console. Third-party URLs
  (e.g. prezi.com, archive.org, neoncrm.com) are rejected unless your account has access to them.
  Details and reasons: [docs/GUIDE.md](docs/GUIDE.md).

## Tests

```powershell
cd backend
python manage.py test        # Google is always off/mocked in tests
cd ..
```

Frontend tests need Node 22.12+.

```powershell
npm test                     # frontend
npm run build                # production build check
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Invalid HTTP_HOST header` / UI says "not accepted" for everything | In `backend\.env` set `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, restart backend. |
| URL "not accepted" in Google mode | Your Google account has no Search Console access to that site. See the guide. |
| "Google login problem" | Run the `gcloud auth application-default login ...` command again. |
| "Quota exceeded" | Wait, then click **Check again**. The tool never retries by itself. |
| `npm` says package.json not found | Run npm commands from the main folder, not from `frontend`. |

## Limits (by Google, not by this tool)

Google has no official API to *request* indexing for ordinary URLs. The URL Inspection API
only reports status. The Indexing API works only for job-posting and livestream pages and is
off by default. Indexing itself can take days: click **Check again** later.
