# PLACIFY — Placement Management Platform

PLACIFY is a Django-based placement management platform for students, recruiters and placement administrators.

## Architecture
- **Authentication:** email only; no username.
- **Student:** owns and updates their profile, skills, photo and resume; applies to eligible drives.
- **Recruiter:** has an individual recruiter account/profile linked to a company; sees assigned drives and read-only candidate profiles; can update only application status and recruiter remarks.
- **Administrator:** manages colleges, departments, skills, companies, recruiter profiles, placement drives, applications, results, independent historical placement outcomes and content.
- **Historical outcomes:** placement history is a standalone record; it does not require or reference a placement drive, so legacy/off-campus outcomes can be recorded even when the student never attended a campus drive.
- **Announcements:** target everyone, selected colleges or selected students. Student targeting and long dropdowns have inline search; drive-specific announcement targeting has been removed.
- **Company and recruiter forms:** company contact name is not collected, website URLs may use HTTP or HTTPS (or be entered without a scheme), and placement-drive recruiter choices are scoped to the selected company.
- **Master data:** colleges, departments, skills and companies default to active when created. The internal active flag remains available for future lifecycle management but is not a required registration field.

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

If you are migrating from an older local PLACIFY database, **back it up first**. This release contains schema updates (including removal of drive links from placement history and announcements and removal of company contact name); `python manage.py migrate` applies them. For a clean evaluation, a fresh database is recommended.

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


## API authentication and authorization

The API uses **Simple JWT** bearer authentication. Install dependencies, apply migrations (including `rest_framework_simplejwt.token_blacklist`), and then use:

- `POST /api/auth/token/` with `{"email":"...", "password":"..."}` to obtain `access` and `refresh` tokens.
- Send the access token as `Authorization: Bearer <access>`; access tokens expire after 5 minutes.
- `POST /api/auth/token/refresh/` with `{"refresh":"<refresh>"}` to rotate the refresh token. The previous refresh token is blacklisted.
- `POST /api/auth/logout/` with a valid access bearer token and `{"refresh":"<refresh>"}` to blacklist the caller's refresh token. A refresh token belonging to another user is rejected. Already-issued access tokens are stateless and remain valid for at most their 5-minute lifetime; clients should discard them immediately on logout.

Refresh-token blacklisting requires running `python manage.py migrate`. Schedule `python manage.py flushexpiredtokens` periodically to remove expired blacklist records.

### Authorization boundaries

- Public registration always creates a `student`; submitted role values are not accepted.
- An application administrator (`role=admin`) is not automatically a Django staff user or Django superuser. Django admin-site access requires Django's separate staff/superuser flags.
- Students can read only their own profile, applications and results. Student profile updates cannot change placement-office-controlled eligibility fields (college, department, university number, academic year, CGPA, backlogs or graduation year).
- Recruiters can read only candidates who have applied to drives assigned to that recruiter. Recruiter candidate responses omit address and university number. Recruiters can access only assigned drives and their applications, and may update only application status and remarks. Recruiters cannot edit student profiles or official results.
- Application administrators manage placement records through application APIs; only Django superusers/staff with permissions can access `/django-admin/`.

Run the authorization matrix with `python manage.py test api.tests.JWTAuthorizationMatrixTests api.tests.APIArchitectureTests`.

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

### Login form note

The login page submits the email address through Django’s `AuthenticationForm` field named `username`. This is required by Django’s default login form even when the custom user model uses email as `USERNAME_FIELD`. The visible field remains an email input.
