# PLACIFY — Placement Management Platform

**PLACIFY** is a full-stack **college placement management platform** built with Django. It provides a centralized system for managing students, recruiters, companies, placement drives, applications, candidate evaluation, placement results, placement history, announcements, study materials, and gallery content.

The platform is designed around three primary roles:

- **Student**
- **Recruiter**
- **Administrator**

PLACIFY replaces fragmented placement activities with a structured digital workflow where students can maintain their profiles and apply for eligible opportunities, recruiters can evaluate candidates and manage applications, and administrators can control the complete placement ecosystem.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [User Roles](#user-roles)
- [Student Workflow](#student-workflow)
- [Recruiter Workflow](#recruiter-workflow)
- [Administrator Workflow](#administrator-workflow)
- [Placement Eligibility System](#placement-eligibility-system)
- [Application and Result Management](#application-and-result-management)
- [Placement History](#placement-history)
- [Content Management](#content-management)
- [Optional AI Feature](#optional-ai-feature)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Database Design](#database-design)
- [REST API](#rest-api)
- [API Authentication](#api-authentication)
- [Project Structure](#project-structure)
- [Installation and Setup](#installation-and-setup)
- [Environment Configuration](#environment-configuration)
- [Seed Data](#seed-data)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Important Routes](#important-routes)
- [Security and Access Control](#security-and-access-control)
- [Data Integrity](#data-integrity)
- [Production Configuration](#production-configuration)

---

# Project Overview

Managing campus placements manually can involve spreadsheets, emails, forms, documents, and multiple disconnected systems.

PLACIFY provides a centralized placement ecosystem where:

```text
                    ┌─────────────────────┐
                    │       PLACIFY       │
                    │ Placement Platform  │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
     ┌─────────┐          ┌──────────┐        ┌─────────────┐
     │ Student │          │ Recruiter│        │    Admin    │
     └────┬────┘          └────┬─────┘        └──────┬──────┘
          │                    │                     │
          ▼                    ▼                     ▼
     Profile & Skills     Candidate Search      Master Data
     Placement Drives     Applications          Placement Drives
     Applications         Status Updates        Applications
     Results              Remarks               Results
     Announcements                              Announcements
     Materials                                  Placement History
```

The system uses a normalized database design and role-based access control to ensure that each user can perform only the operations appropriate to their role.

---

# Key Features

## Authentication

- Email-based authentication.
- No username-based login.
- Three application roles:
  - Student
  - Recruiter
  - Administrator
- Password-based authentication.
- Django authentication system.
- Token authentication for REST API access.
- Logout support.
- Password reset workflow.

---

## Student Management

Students can:

- Register using their email.
- Maintain their personal profile.
- Select their college and department from predefined master data.
- Add skills from the centralized skill catalogue.
- Upload a profile photo.
- Upload a resume.
- Maintain CGPA.
- Maintain backlog information.
- Specify current academic year.
- Specify graduation/pass-out year.
- View their profile completion status.
- View available placement drives.
- Check eligibility for each drive.
- Apply for eligible placement drives.
- View submitted applications.
- Withdraw applications where permitted.
- View application status.
- View placement evaluation results.
- View relevant announcements.
- Access published study materials.

---

# User Roles

## 1. Student

Students are the candidates participating in placement activities.

A student can:

- Register an account.
- Maintain their placement profile.
- Add academic information.
- Add skills.
- Upload resume and photo.
- Browse placement opportunities.
- Check eligibility.
- Apply to placement drives.
- Track applications.
- View results.
- View placement history.
- Access announcements and study materials.

Students cannot directly modify administrative placement data or recruiter-controlled application decisions.

---

## 2. Recruiter

Recruiters represent companies participating in campus placements.

A recruiter:

- Has an individual recruiter account.
- Is linked to a registered company.
- Can access assigned placement drives.
- Can view candidates who applied to those drives.
- Can search and filter candidates.
- Can inspect candidate profiles.
- Can filter candidates using:
  - Name
  - Email
  - College
  - Department
  - Minimum CGPA
  - Skills
  - Application status
- Supports matching candidates by:
  - All selected skills
  - Any selected skill
- Can update application status.
- Can add recruiter remarks.

Recruiters cannot modify:

- Student profile information
- Student resume
- Student skills
- Student academic information
- Candidate results
- Administrative master data

---

## 3. Administrator

The administrator controls the placement ecosystem.

Administrators can manage:

- Students
- Recruiters
- Companies
- Colleges
- Departments
- Skills
- Placement drives
- Applications
- Results
- Placement history
- Announcements
- Study materials
- Gallery content

The administrator also has access to the Django administrative interface.

---

# Student Workflow

The typical student workflow is:

```text
Register
   │
   ▼
Complete Profile
   │
   ├── College
   ├── Department
   ├── CGPA
   ├── Backlogs
   ├── Graduation Year
   ├── Skills
   ├── Resume
   └── Photo
   │
   ▼
Browse Placement Drives
   │
   ▼
Check Eligibility
   │
   ▼
Apply
   │
   ▼
Track Application
   │
   ▼
Recruiter Evaluation
   │
   ▼
Application Status
   │
   ▼
Placement Result
   │
   ▼
Placement History
```

The platform automatically evaluates eligibility before allowing an application.

---

# Recruiter Workflow

The recruiter workflow is:

```text
Recruiter Login
      │
      ▼
Recruiter Dashboard
      │
      ▼
Assigned Placement Drives
      │
      ▼
Candidate Applications
      │
      ▼
Search / Filter Candidates
      │
      ▼
View Candidate Profile
      │
      ▼
Update Application Status
      │
      ▼
Add Recruiter Remarks
      │
      ▼
Candidate Selection / Rejection
```

When an application is marked as **Selected**, the system can create or update the corresponding on-campus placement-history record.

---

# Administrator Workflow

Administrators have centralized control:

```text
Admin Login
     │
     ▼
Admin Dashboard
     │
     ├── Students
     ├── Recruiters
     ├── Companies
     ├── Colleges
     ├── Departments
     ├── Skills
     ├── Placement Drives
     ├── Applications
     ├── Results
     ├── Placement History
     ├── Announcements
     ├── Study Materials
     └── Gallery
```

The administrator dashboard also provides placement-related statistics such as:

- Number of students
- Number of recruiters
- Number of companies
- Number of colleges
- Number of departments
- Number of skills
- Open placement drives
- Total applications
- Selected candidates
- Published announcements
- Placement-history records

---

# Placement Eligibility System

One of the core features of PLACIFY is its automatic placement eligibility engine.

Before an application is accepted, the system checks multiple conditions.

## Eligibility Criteria

### 1. CGPA

The student's CGPA must satisfy the minimum CGPA defined by the placement drive.

Example:

```text
Student CGPA: 7.8
Required CGPA: 7.5

Result: Eligible
```

---

### 2. Backlogs

The student's number of backlogs must not exceed the maximum allowed by the drive.

```text
Student Backlogs: 1
Maximum Allowed: 2

Result: Eligible
```

---

### 3. College

A placement drive can optionally restrict eligible colleges.

If no college restriction is specified, students from all colleges can be considered.

---

### 4. Department

Placement drives can optionally target specific departments.

For example:

```text
CSE
ECE
IT
```

---

### 5. Graduation Year

A drive can specify permitted graduation years.

For example:

```text
2026
2027
```

---

### 6. Required Skills

Placement drives can specify required skills using the centralized `Skill` catalogue.

For example:

```text
Python
Django
SQL
AWS
```

The student's active skills are compared against the drive's required skills.

---

### 7. Application Dates

The system checks:

- Application start date
- Application deadline
- Current drive status

Applications are accepted only while the drive is open and within the configured application period.

---

## Eligibility Result

If a student is not eligible, the system provides reasons such as:

```text
CGPA below required minimum
Backlogs exceed maximum allowed
College is not eligible
Department is not eligible
Graduation year is not eligible
Missing required skills
Applications have not started
Application deadline has passed
Placement drive is not open
```

This makes the eligibility system transparent rather than simply displaying a generic rejection.

---

# Application Management

Each application connects:

```text
Student
   │
   ▼
Application
   │
   ▼
Placement Drive
   │
   ▼
Company
```

A student cannot create multiple applications for the same placement drive.

The database enforces a unique student/drive relationship.

---

# Application Status

Applications maintain their own status independently from interview results.

Recruiters can update application status and remarks.

This separation is important because:

```text
Application Status
        ≠
Evaluation Result
```

For example:

```text
Application:
    Selected

Evaluation:
    Test       → Passed
    GD         → Passed
    Technical  → Passed
    HR         → Pending
```

---

# Result Management

Each application has its own result record.

The evaluation system contains four stages:

1. **Test**
2. **Group Discussion**
3. **Technical Interview**
4. **HR Interview**

Each stage supports:

- Pending
- Passed
- Failed

Example:

```text
Candidate: John Doe

Test                → Passed
Group Discussion    → Passed
Technical Interview → Passed
HR Interview        → Pending
```

Results are controlled by administrators.

Recruiters cannot directly modify result records.

---

# Placement History

PLACIFY maintains historical placement records independently from current applications.

Two placement types are supported:

## On-Campus

An on-campus placement is associated with a placement drive.

```text
Student
   │
   ▼
Company
   │
   ▼
Placement Drive
   │
   ▼
Placement History
```

## Off-Campus

An off-campus placement can be recorded without a placement drive.

Both types can contain:

- Student
- Company
- Job role
- Package
- Placement date
- Placement type
- Status
- Remarks
- Created by
- Timestamps

When an application is selected, the system can automatically create or update the corresponding on-campus placement-history record.

---

# Content Management

PLACIFY also provides a centralized content-management system.

## Announcements

Announcements can be targeted to:

- Everyone
- Specific colleges
- Applicants of a placement drive
- Specific students

This allows placement administrators to distribute relevant information without manually contacting each student.

---

## Study Materials

Administrators can publish study and placement preparation materials.

Materials can contain:

- Title
- Description
- Category
- Uploaded file
- External URL
- Company
- Placement drive
- Drive link
- Publication status

---

## Gallery

The gallery can contain placement-related images and can optionally associate content with a company.

---

# Optional AI Feature

PLACIFY includes an optional AI-powered placement-drive summarization feature.

The feature can generate a concise summary of a placement opportunity based on information such as:

- Company
- Job role
- Drive title
- Job description
- Eligibility requirements
- Salary package

The AI functionality is implemented as an optional service and uses the OpenAI API when an API key is configured.

The core PLACIFY application does not depend on the AI feature for normal placement management.

---

# Technology Stack

## Backend

- **Python**
- **Django**
- **Django REST Framework**

## Database

- **PostgreSQL**
- `psycopg2-binary`

## API Documentation

- **drf-spectacular**
- OpenAPI
- Swagger UI
- ReDoc

## Image and File Processing

- **Pillow**

## Optional AI

- **OpenAI API**

---

# System Architecture

PLACIFY follows a modular Django architecture.

```text
PLACIFY
│
├── accounts
│   ├── Authentication
│   ├── Custom User
│   ├── Roles
│   ├── Registration
│   └── Password Reset
│
├── placements
│   ├── Students
│   ├── Recruiters
│   ├── Companies
│   ├── Colleges
│   ├── Departments
│   ├── Skills
│   ├── Placement Drives
│   ├── Applications
│   ├── Results
│   ├── Placement History
│   ├── Announcements
│   ├── Study Materials
│   └── Gallery
│
├── api
│   ├── Serializers
│   ├── ViewSets
│   ├── Permissions
│   ├── Pagination
│   └── OpenAPI Documentation
│
├── templates
│   └── HTML interface
│
├── static
│   └── CSS and images
│
└── config
    └── Django configuration
```

---

# Database Design

The database is normalized around reusable master data.

## Authentication

### User

The custom user model uses:

```text
email
name
role
password
```

Email is the unique login identifier.

There is no username field.

---

## Master Data

### College

Stores approved college information.

### Department

Stores department names and department codes.

Example:

```text
CSE
ECE
EEE
ME
CE
IT
```

### Skill

Provides a centralized skill catalogue.

The same skill records are used by:

- Student profiles
- Placement drives
- Recruiter candidate filtering

### Company

Stores registered companies participating in placements.

---

# Profile Relationships

A student has a one-to-one relationship with a user account.

```text
User
 │
 └── StudentProfile
       ├── College
       ├── Department
       ├── Skills
       ├── Resume
       └── Photo
```

A recruiter also has a one-to-one profile:

```text
User
 │
 └── RecruiterProfile
       │
       └── Company
```

---

# Placement Relationships

```text
Company
   │
   └── PlacementDrive
          │
          ├── Required Skills
          ├── Allowed Colleges
          ├── Allowed Departments
          ├── Allowed Graduation Years
          └── Recruiters
                  │
                  ▼
              Applications
                  │
                  ├── Result
                  │
                  └── Placement History
```

This structure keeps placement information normalized and avoids storing important relationships as free-text fields.

---

# REST API

PLACIFY provides a REST API using Django REST Framework.

Both API prefixes are available:

```text
/api/
```

and

```text
/api/v1/
```

---

# API Resources

## Users

```text
/api/v1/users/
```

Provides authenticated access to user information.

---

## Students

```text
/api/v1/students/
```

Provides student profile operations according to role permissions.

---

## Recruiters

```text
/api/v1/recruiters/
```

Provides recruiter profile information.

---

## Colleges

```text
/api/v1/colleges/
```

---

## Departments

```text
/api/v1/departments/
```

---

## Skills

```text
/api/v1/skills/
```

---

## Companies

```text
/api/v1/companies/
```

---

## Placement Drives

```text
/api/v1/placement-drives/
```

Placement drives can be searched and ordered through the API.

---

## Applications

```text
/api/v1/applications/
```

---

## Results

```text
/api/v1/results/
```

---

## Placement History

```text
/api/v1/placement-history/
```

---

## Announcements

```text
/api/v1/announcements/
```

---

## Study Materials

```text
/api/v1/study-materials/
```

---

## Gallery

```text
/api/v1/gallery/
```

---

## Recruiter Search

```text
/api/v1/recruiter/search/
```

Provides recruiter-oriented candidate search functionality.

---

# API Authentication

Token authentication is available through:

```text
POST /api/v1/auth/token/
```

A successful authentication returns a token and user information.

Logout is available through:

```text
POST /api/v1/auth/logout/
```

Authenticated API requests can use:

```text
Authorization: Token <token>
```

---

# API Documentation

PLACIFY automatically exposes OpenAPI documentation.

### Swagger UI

```text
/api/v1/docs/
```

### ReDoc

```text
/api/v1/redoc/
```

### OpenAPI Schema

```text
/api/v1/schema/
```

The API supports standard pagination and provides search and ordering functionality for relevant resources.

---

# Project Structure

```text
PLACIFY/
│
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── accounts/
│   ├── migrations/
│   ├── decorators.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
│
├── placements/
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py
│   ├── migrations/
│   ├── services/
│   │   └── ai.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
│
├── api/
│   ├── pagination.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
│   ├── accounts/
│   └── placements/
│
├── static/
│   ├── css/
│   └── images/
│
└── docs/
    ├── DATABASE_DESIGN.md
    └── IMPLEMENTATION_STATUS.md
```

---

# Installation and Setup

## 1. Clone or extract the project

Open a terminal inside the project directory.

Example:

```powershell
cd PLACIFY
```

---

## 2. Create a virtual environment

```powershell
python -m venv .venv
```

---

## 3. Activate the virtual environment

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation succeeds, the terminal will display something similar to:

```text
(.venv) PS C:\...\PLACIFY>
```

---

## 4. Install dependencies

```powershell
pip install -r requirements.txt
```

The main dependencies include:

```text
Django
Django REST Framework
psycopg2-binary
django-filter
drf-spectacular
OpenAI
Pillow
```

---

## 5. Configure environment variables

Copy the example environment file:

```powershell
copy .env.example .env
```

Configure the required settings according to your local environment.

---

## 6. Apply database migrations

```powershell
python manage.py migrate
```

---

## 7. Create demo data

Run:

```powershell
python manage.py seed_data
```

The command creates the administrator, recruiter and basic master data required for evaluation.

---

# Seed Data

The default administrator account is:

```text
Email: admin@placify.local
Password: AdminPass123!
```

The default recruiter account is:

```text
Email: recruiter@placify.local
Password: RecruiterPass123!
```

The seed command also creates:

- Demo company
- College
- Departments
- Skills
- Recruiter profile

The default credentials can be overridden using environment variables:

```text
SEED_ADMIN_EMAIL
SEED_ADMIN_PASSWORD
SEED_RECRUITER_EMAIL
SEED_RECRUITER_PASSWORD
```

For example:

```env
SEED_ADMIN_EMAIL=admin@example.com
SEED_ADMIN_PASSWORD=YourSecurePassword
```

---

# Running the Application

After activating the virtual environment and applying migrations:

```powershell
python manage.py runserver
```

The development server will normally be available at:

```text
http://127.0.0.1:8000/
```

Open the URL in a browser.

---

# Main Application Routes

## Login

```text
/
```

The login page uses email-based authentication.

---

## Student Registration

```text
/accounts/register/
```

---

## Student Dashboard

```text
/dashboard/
```

---

## Student Profile

```text
/profile/
```

---

## Placement Drives

```text
/drives/
```

---

## Student Applications

```text
/applications/
```

---

## Recruiter Workspace

```text
/recruiters/
```

---

## Administrator Dashboard

```text
/admin-panel/
```

---

## Django Admin

```text
/django-admin/
```

---

# Testing

PLACIFY includes automated tests for the application, account functionality, and API.

Run the complete test suite using:

```powershell
python manage.py test
```

Before running the server, it is also useful to verify the Django configuration:

```powershell
python manage.py check
```

For deployment-specific validation:

```powershell
python manage.py check --deploy
```

---

# Development Workflow

A typical development workflow is:

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Populate demo data
python manage.py seed_data

# Verify configuration
python manage.py check

# Run tests
python manage.py test

# Start development server
python manage.py runserver
```

---

# Security and Access Control

PLACIFY implements role-based permissions throughout the application.

## Students

Students can access their own placement information and profile.

They cannot:

- Modify other students.
- Modify placement-drive configuration.
- Modify results.
- Modify administrator-managed master data.

---

## Recruiters

Recruiters are restricted to placement drives assigned to them.

They can:

- View assigned applications.
- View candidate profiles.
- Update application status.
- Add application remarks.

They cannot:

- Edit candidate profiles.
- Modify candidate resumes.
- Modify candidate academic data.
- Modify candidate results.
- Access unrelated placement drives.

---

## Administrators

Administrators have management access to the placement system and can manage the application's core data.

---

# Data Integrity

PLACIFY uses database relationships and validation rules to maintain consistent placement data.

Important rules include:

### Student College

Student college information is stored using a foreign-key relationship rather than arbitrary text.

### Student Department

Department information is also normalized.

### Skills

Students and placement drives use the same centralized skill catalogue.

### Recruiter Assignment

Recruiters are assigned through `RecruiterProfile` records rather than arbitrary users.

### Applications

A student cannot have duplicate applications for the same placement drive.

### Results

Results belong to a specific application.

### Placement History

On-campus placement history is connected to the relevant placement drive.

### Application vs Result

Application status and evaluation results are intentionally separate concepts.

---

# Pagination, Search and Ordering

The REST API supports pagination for list-based resources.

Relevant API endpoints also support search and ordering.

Examples include searching by:

```text
Student name
Student email
Company
Placement drive
College
Department
Skill
```

Ordering can be performed using relevant fields such as:

```text
Name
CGPA
Application date
Deadline
Drive date
Salary package
Creation date
Status
```

---

# Recruiter Candidate Filtering

The recruiter dashboard provides candidate filtering functionality.

Recruiters can filter applications using:

```text
Search
College
Department
Minimum CGPA
Application Status
Skills
```

Skill matching supports two modes.

### ALL

Candidate must have every selected skill.

Example:

```text
Python + Django + SQL
```

Candidate must possess all three.

### ANY

Candidate must possess at least one of the selected skills.

Example:

```text
Python / Java / C++
```

Candidate can match any one of them.

This allows recruiters to perform more targeted candidate screening.

---

# Optional AI Configuration

The AI placement-summary functionality can be enabled by configuring an OpenAI API key.

Example:

```env
OPENAI_API_KEY=your_api_key
```

An optional model can also be configured:

```env
OPENAI_MODEL=gpt-5-mini
```

The application invokes AI summarization through the placement-drive API endpoint.

```text
POST /api/v1/placement-drives/<id>/ai_summary/
```

The AI service generates a concise placement opportunity summary using the drive information.

---

# Production Configuration

For production deployment, configure:

```text
DEBUG=False
```

Use a strong Django secret key.

Configure explicit:

```text
ALLOWED_HOSTS
```

Use PostgreSQL as the production database.

Configure secure media storage for:

- Student photos
- Resumes
- Study materials
- Gallery images

Configure a production email backend for password reset and other email functionality.

Before deployment, run:

```powershell
python manage.py check --deploy
```

Do not commit sensitive files such as:

```text
.env
db.sqlite3
media/
.venv/
```

to version control.

---

# Documentation

Additional project documentation is available in the `docs/` directory.

### Database Design

```text
docs/DATABASE_DESIGN.md
```

Contains the normalized database structure and integrity rules.

### Implementation Status

```text
docs/IMPLEMENTATION_STATUS.md
```

Contains the implemented architecture and major functionality.

---

# Quick Start

For a quick local demonstration:

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

Then open:

```text
http://127.0.0.1:8000/
```

Use the seeded administrator account:

```text
Email: admin@placify.local
Password: AdminPass123!
```

or the seeded recruiter account:

```text
Email: recruiter@placify.local
Password: RecruiterPass123!
```

---

# PLACIFY at a Glance

| Area | Functionality |
|---|---|
| Authentication | Email-based authentication |
| Roles | Student, Recruiter, Administrator |
| Student Profiles | Academic and professional information |
| Skills | Centralized skill catalogue |
| Companies | Company master management |
| Placement Drives | Eligibility-based opportunities |
| Applications | Student application tracking |
| Recruiter Management | Candidate filtering and evaluation |
| Results | Test, GD, Technical, HR |
| Placement History | On-campus and off-campus |
| Announcements | Targeted placement communication |
| Study Materials | Placement preparation resources |
| Gallery | Placement-related media |
| REST API | Django REST Framework |
| API Documentation | Swagger, ReDoc, OpenAPI |
| Search | API and recruiter candidate search |
| Filtering | Multi-criteria candidate filtering |
| Pagination | API list pagination |
| AI | Optional placement-drive summarization |
| Database | PostgreSQL-compatible architecture |

---

# Conclusion

PLACIFY provides a centralized platform for managing the complete college placement lifecycle.

The system connects:

```text
Students
    ↓
Profiles & Skills
    ↓
Placement Drives
    ↓
Eligibility Verification
    ↓
Applications
    ↓
Recruiter Evaluation
    ↓
Results
    ↓
Selection
    ↓
Placement History
```

By combining role-based access control, normalized database relationships, automated eligibility verification, recruiter candidate filtering, application tracking, evaluation management, placement history, content management, and a documented REST API, PLACIFY provides a structured digital platform for managing campus placement operations.
