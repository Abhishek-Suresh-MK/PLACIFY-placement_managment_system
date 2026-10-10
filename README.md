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

## Seeded demo accounts

Run `python manage.py seed_data` after migrations. The command is idempotent: rerunning it updates the named demo records instead of duplicating them.

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@placify.local` | `AdminPass123!` |
| Recruiter (TCS) | `recruiter@placify.local` | `RecruiterPass123!` |
| Student 1 — Ananya Nair | `student01@placify.local` | `StudentPass123!` |
| Student 2 — Nikhil Raj | `student02@placify.local` | `StudentPass123!` |

Override credentials with `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, `SEED_RECRUITER_EMAIL`, `SEED_RECRUITER_PASSWORD`, and `SEED_STUDENT_PASSWORD`. These credentials are for local demos only; never use them in production.

The seed creates CEM as the primary college, plus two comparison colleges for testing. Every seeded drive allows CEM; only the explicitly marked Federal Bank demo drive allows the two external colleges. It also creates six departments, a shared skills catalogue, six companies, eight drives in mixed states, two student profiles, applications with recruitment-stage results, on-campus placement history, targeted/global/draft announcements, published and draft study materials, and locally generated gallery placeholder images. All people, outcomes and contact details are synthetic demo data.

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
