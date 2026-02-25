# Healthcare Chatbot Backend

Flask backend for the Healthcare Chatbot project.

This service handles authentication, chat workflows, questionnaire flow, document ingestion, vector search, and admin operations.

## Stack

- Flask
- MongoDB (via `Flask-PyMongo`)
- OpenAI API
- Qdrant (vector search)
- JWT auth (`PyJWT` custom helper)

## Current API Prefixes

Registered in app factory:

- `/users`
- `/chat`
- `/admin`
- `/documents`

Health route:

- `GET /` → `server is running`

## Project Structure

```text
Backend/
├─ app/
│  ├─ __init__.py
│  ├─ extensions.py
│  ├─ models/
│  ├─ routes/
│  ├─ schemas/
│  └─ utils/
├─ requirements.txt
├─ wsgi.py
├─ docker-compose.yml
├─ Dockerfile
└─ mcp_server.py
```

## Environment Variables

Create a `.env` file in `Backend/`.

Required:

```env
MONGO_URI=<your-mongodb-connection-string>
OPENAI_API_KEY=<your-openai-api-key>
JWT_SECRET=<your-jwt-secret>
```

Notes:

- `JWT_SECRET` has a fallback in code, but set it explicitly in production.
- Keep `.env` out of version control.

## Local Run (Windows PowerShell)

From `Backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python wsgi.py
```

Server starts on:

- `http://127.0.0.1:5002`

## Production Run (Gunicorn)

From `Backend/`:

```bash
gunicorn wsgi:app
```

You can also configure host/port explicitly in your platform settings.

## Docker

Use the included Docker artifacts:

```bash
docker compose up --build
```

## Integration with Frontend

Set frontend env on Vercel:

```env
VITE_API_URL=https://<your-backend-domain>
```

If running locally, use:

```env
VITE_API_URL=http://127.0.0.1:5002
```

## Important Security Note

Before publishing backend publicly, verify secrets are not hardcoded in source files.

If any key/token was committed in code history, rotate it immediately and move it to environment variables.
