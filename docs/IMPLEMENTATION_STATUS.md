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
