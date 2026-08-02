# Pressure OS

PressureOS is an execution operating system built around real pressure, execution, and measurable daily progress.

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the sample environment file and set your local values:

```bash
copy .env.example .env
```

4. Set `DATABASE_URL` for Neon PostgreSQL if you want the app to use PostgreSQL. If `DATABASE_URL` is not set, the project will continue to use the local SQLite database for development.

## Neon PostgreSQL setup

1. Create a Neon project and database.
2. Copy the Neon connection string from the dashboard.
3. Add it to `.env`:

```env
DATABASE_URL=postgresql://<user>:<password>@<host>/<database>?sslmode=require
```

## Environment variables

The project uses `django-environ` to read environment settings from `.env`.

Required variables:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL` (optional, PostgreSQL-only when provided)

The sample file is available at `.env.example`.

## Migration steps

### Local development with SQLite

- Keep `.env` unset for `DATABASE_URL`.
- Run:

```bash
python manage.py migrate
python manage.py runserver
```

### PostgreSQL with Neon

1. Add `DATABASE_URL` to `.env`.
2. Run:

```bash
python manage.py migrate
python manage.py runserver
```

### Existing SQLite data migration

If you need to migrate an existing SQLite database to PostgreSQL, use the standard Django data export/import flow:

```bash
python manage.py dumpdata > data.json
python manage.py loaddata data.json
```

Do not run destructive commands as part of this migration.

## Local development

- SQLite is the fallback for local development when `DATABASE_URL` is missing.
- PostgreSQL will be used automatically whenever `DATABASE_URL` is present.
- The app and URL structure remain unchanged.

## Codespaces setup

In GitHub Codespaces, set the same environment variables inside the Codespaces environment or a local `.env` file. The project is compatible with Windows, Linux, and Codespaces because the database switch happens through environment configuration rather than OS-specific code.
