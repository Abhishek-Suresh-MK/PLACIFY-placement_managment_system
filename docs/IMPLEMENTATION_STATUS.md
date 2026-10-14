# PLACIFY Implementation Status

The current architecture has been redesigned around three explicit roles: Student, Recruiter and Administrator.

Implemented:
- Email-only authentication.
- College and Department master tables.
- Normalized Skill catalogue shared by students and placement drives.
- Student photo and resume support.
- Current year restricted to 1st–4th year.
- Recruiter profiles linked to companies.
- Placement drives assigned only to recruiter profiles belonging to the drive company.
- Multi-skill recruiter filtering with all/any matching.
- Recruiter candidate profiles are read-only.
- Recruiters can change only application status and remarks.
- Results are application-specific and administrator-controlled.
- Four result stages: Test, GD, Technical Interview, HR Interview.
- Three result states: Pending, Passed, Failed.
- On-campus and off-campus placement history.
- Administrator management of master data, drives, applications, results and content.
- DRF pagination, search, filtering, ordering and OpenAPI/Swagger/ReDoc.

## Migration note
The architecture change removes the legacy username/skill/college-text concepts. Back up an existing database before migrating. The migration chain includes data cleanup where practical, but old result records are intentionally recreated as application-specific results.


## Student and recruiter management API verification (October 2026)

The student/recruiter management slice has been extended and covered by API tests:

- Students can retrieve and edit their own permitted profile fields, including phone, address, active catalogue skills, profile photo, and resume. College, department, university number, age, current year, CGPA, backlogs, graduation year, account identity, and active state remain placement-office/admin controlled for student self-service.
- Administrators can create and manage student profiles linked to existing student accounts. Public student account/profile creation remains available through the registration workflow.
- Student profile validation checks CGPA (0–10), non-negative backlogs, current-year choices (1–4), graduation-year bounds, active college/department selections, shared active skills, and uploaded-file type/size limits. Resume files are limited to PDF/DOC/DOCX and 5 MB; PDF uploads are checked for a PDF signature. Photos must be valid images and no larger than 5 MB.
- Administrators can create recruiter accounts and profiles through the recruiter API, or link a profile to an existing recruiter-role account. Recruiters can edit only their own phone number; account identity and company association are protected.
- Company, department, college, and skill catalogues are admin-managed; authenticated users can read them. Company catalogue supports search, filtering, ordering, and pagination.
- Student listing supports pagination, search, ordering, and filters for college, department, current year, CGPA, backlogs, graduation year, active state, and shared skills. Recruiter candidate search validates CGPA thresholds, college/department IDs, skill IDs, and `skill_mode=all|any` rather than silently ignoring malformed filters.
- API paths are available under both `/api/` and `/api/v1/`. Upload requests should use `multipart/form-data`; ordinary profile updates can use JSON.

### Verification status

Added API tests cover permitted profile edits, shared skill selection, invalid CGPA/backlogs/graduation year, account reassignment protection, resume extension validation, admin student-profile creation, recruiter phone-only editing, recruiter account/profile creation, company permissions, and invalid recruiter-search filters. Python syntax compilation is run on the modified project. Django's test runner could not be executed in the authoring environment because Django and the other requirements are not installed and package-network access is unavailable; run `python manage.py test api` in the project's configured virtual environment to complete runtime verification.
