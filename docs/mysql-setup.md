# MySQL Setup

Use this to run the assignment demo against MySQL. The runtime database is MySQL by default, with PostgreSQL supported by changing `DATABASE_URL`.

## Option A: Docker Compose

From `C:\Users\Devi\Documents\Jobs`:

```powershell
docker compose -f docker-compose.mysql.yml up -d
```

Set this in the project-root `.env`:

```env
DATABASE_URL=mysql+pymysql://aivoa_user:aivoa_password@localhost:3306/aivoa_crm
```

Restart the backend:

```powershell
cd backend
..\.venv-aivoa\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use this command if PowerShell does not like the space above:

```powershell
cd C:\Users\Devi\Documents\Jobs\backend
C:\Users\Devi\Documents\Jobs\.venv-aivoa\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend creates the required tables automatically through SQLAlchemy.

## One-Command Smoke Test

After Docker Desktop is fully running, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-mysql.ps1
```

The script:

- Starts the MySQL compose service.
- Waits for the MySQL health check.
- Starts FastAPI on port `8010` with `DATABASE_URL=mysql+pymysql://...`.
- Saves one interaction draft through `/api/interactions`.
- Prints the saved interaction id.

If Docker Desktop is still starting or stuck, the script fails fast with a Docker daemon timeout instead of hanging.

If you install/start MySQL yourself instead of Docker, use the same script with `-SkipCompose`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-mysql.ps1 -SkipCompose -DatabaseUrl "mysql+pymysql://aivoa_user:your_password@localhost:3306/aivoa_crm"
```

This skips Docker entirely and verifies the backend against the MySQL server already listening on port `3306`.

## Option B: Existing MySQL Install

Create the database:

```sql
CREATE DATABASE aivoa_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aivoa_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON aivoa_crm.* TO 'aivoa_user'@'localhost';
FLUSH PRIVILEGES;
```

Set:

```env
DATABASE_URL=mysql+pymysql://aivoa_user:your_password@localhost:3306/aivoa_crm
```

## Future Postgres Migration

No model rewrite is needed. Change only the driver URL:

```env
DATABASE_URL=postgresql+psycopg://aivoa_user:your_password@localhost:5432/aivoa_crm
```

The code uses SQLAlchemy models rather than database-specific SQL in the application flow.
