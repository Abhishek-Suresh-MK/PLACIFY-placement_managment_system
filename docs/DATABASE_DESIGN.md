# PLACIFY Database Design

## Authentication
- `User.id` is the database primary key.
- `User.email` is unique and is the only login identifier.
- There is no username field in the application model or UI.
- Roles: Student, Recruiter, Administrator.

## Master data
- `College` — approved college names used by student registration and drive eligibility.
- `Department` — approved departments/codes used by student registration and drive eligibility.
- `Skill` — one normalized skill catalogue used by both students and placement drives.
- `Company` — company master data.

## Profiles
- `StudentProfile` is one-to-one with `User` and has `College`, `Department`, photo and many-to-many `Skill` relations.
- `RecruiterProfile` is one-to-one with `User` and belongs to one `Company`.

## Placement workflow
`PlacementDrive` belongs to a `Company`, may target multiple colleges/departments/graduation years/skills, and is assigned to `RecruiterProfile` records.

`Application` connects one student to one placement drive and is unique per student/drive pair.

`Result` is one-to-one with an `Application`. It contains exactly four stages:
- Test
- Group Discussion
- Technical Interview
- HR Interview

Each stage has exactly three statuses: Pending, Passed, Failed.

Recruiters can change only `Application.status` and `Application.remarks`. Results are administrator-controlled.

## Placement history
`PlacementHistory` supports:
- `ON_CAMPUS` — must reference a placement drive.
- `OFF_CAMPUS` — does not reference a placement drive.

Both types reference a registered `Company` and can be created/updated by administrators.

## Content
- `Announcement` supports global, college, drive-applicant and student targeting.
- `StudyMaterial` may optionally reference a company and/or placement drive.
- `Gallery` may optionally reference a company.

## Important integrity rules
1. Student college and department are foreign keys, never free text.
2. Student and drive skills come from the same `Skill` table.
3. Recruiter assignments use `RecruiterProfile`, never arbitrary users.
4. Application status and result status are separate concepts.
5. Recruiters cannot edit student profile data, resumes or results.
6. Application selection creates/updates the corresponding on-campus placement-history record.
