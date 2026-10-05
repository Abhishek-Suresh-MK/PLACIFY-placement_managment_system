# PLACIFY — Placement Management Platform

PLACIFY is a Django-based placement management platform for students, recruiters and placement administrators.

## Architecture
- **Authentication:** email only; no username.
- **Student:** owns and updates their profile, skills, photo and resume; applies to eligible drives.
- **Recruiter:** has an individual recruiter account/profile linked to a company; sees assigned drives and read-only candidate profiles; can update only application status and recruiter remarks.
- **Administrator:** manages colleges, departments, skills, companies, recruiter profiles, placement drives, applications, results, placement history and content.

## Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_data
python manage.py check
python manage.py test
python manage.py runserver
```

If you are migrating from an older local PLACIFY database, **back it up first**. This release contains a major schema redesign. For a clean evaluation, a fresh database is recommended.

## Seeded accounts
`python manage.py seed_data` creates:

- Admin: `admin@placify.local` / `AdminPass123!`
- Recruiter: `recruiter@placify.local` / `RecruiterPass123!`

Override the values with `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, `SEED_RECRUITER_EMAIL` and `SEED_RECRUITER_PASSWORD`.

The seed command also creates a sample college, departments, skills and company.

## Main routes
- `/` — email login
- `/accounts/register/` — student registration
- `/dashboard/` — student dashboard
- `/profile/` — student profile
- `/drives/` — placement drives
- `/applications/` — student applications and result visibility
- `/recruiters/` — recruiter workspace
- `/admin-panel/` — administrator dashboard
- `/django-admin/` — Django administrative interface

## API
Both `/api/` and `/api/v1/` are available.

Important resources:
- `/api/v1/users/`
- `/api/v1/students/`
- `/api/v1/recruiters/`
- `/api/v1/colleges/`
- `/api/v1/departments/`
- `/api/v1/skills/`
- `/api/v1/companies/`
- `/api/v1/placement-drives/`
- `/api/v1/applications/`
- `/api/v1/results/`
- `/api/v1/placement-history/`
- `/api/v1/announcements/`
- `/api/v1/study-materials/`
- `/api/v1/gallery/`
- `/api/v1/recruiter/search/`

Swagger: `/api/v1/docs/`
ReDoc: `/api/v1/redoc/`
OpenAPI schema: `/api/v1/schema/`

List endpoints use the standard pagination class and support search/filter/ordering where appropriate.

## Production notes
Use PostgreSQL, a strong `SECRET_KEY`, `DEBUG=False`, explicit `ALLOWED_HOSTS`, secure media storage and properly configured email. Run `python manage.py check --deploy` before deployment. Never commit `.env`, databases, virtual environments or uploaded media.
