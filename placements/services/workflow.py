"""Shared business rules for placement-drive and application workflows."""
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from placements.models import (
    Application,
    ApplicationStatus,
    PlacementDriveStatus,
    Result,
)


def check_eligibility(profile, drive, now=None):
    """Return (is_eligible, reasons) using the same rules for web and API."""
    reasons = []
    if not profile.is_active or not profile.user.is_active:
        reasons.append("Your student account is inactive.")
    if profile.cgpa < drive.minimum_cgpa:
        reasons.append(f"CGPA below required minimum ({drive.minimum_cgpa}).")
    if profile.backlogs > drive.maximum_backlogs:
        reasons.append(f"Backlogs exceed maximum allowed ({drive.maximum_backlogs}).")
    if drive.allowed_colleges.exists() and not drive.allowed_colleges.filter(pk=profile.college_id).exists():
        reasons.append("Your college is not included in this drive.")
    if drive.allowed_departments.exists() and not drive.allowed_departments.filter(pk=profile.department_id).exists():
        reasons.append("Your department is not eligible.")
    years = {int(year) for year in (drive.allowed_graduation_years or [])}
    if years and profile.passout_year not in years:
        reasons.append("Your graduation year is not eligible.")
    required = set(drive.required_skills.filter(is_active=True).values_list("id", flat=True))
    owned = set(profile.skills.filter(is_active=True).values_list("id", flat=True))
    if required - owned:
        reasons.append("You do not have all required skills.")

    now = now or timezone.now()
    if drive.status != PlacementDriveStatus.OPEN:
        reasons.append("This placement drive is not open.")
    if now < drive.application_start:
        reasons.append("Applications have not started yet.")
    if now > drive.application_deadline:
        reasons.append("The application deadline has passed.")
    return not reasons, reasons


# Terminal outcomes cannot be changed by recruiters. Administrators can correct
# records through the admin workflow, but students cannot change application state.
RECRUITER_TRANSITIONS = {
    ApplicationStatus.APPLIED: {
        ApplicationStatus.UNDER_REVIEW, ApplicationStatus.SHORTLISTED,
        ApplicationStatus.ASSESSMENT, ApplicationStatus.INTERVIEW,
        ApplicationStatus.SELECTED, ApplicationStatus.REJECTED,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.SHORTLISTED, ApplicationStatus.ASSESSMENT,
        ApplicationStatus.INTERVIEW, ApplicationStatus.SELECTED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.ASSESSMENT, ApplicationStatus.INTERVIEW,
        ApplicationStatus.SELECTED, ApplicationStatus.REJECTED,
    },
    ApplicationStatus.ASSESSMENT: {
        ApplicationStatus.INTERVIEW, ApplicationStatus.SELECTED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.INTERVIEW: {ApplicationStatus.SELECTED, ApplicationStatus.REJECTED},
    ApplicationStatus.SELECTED: set(),
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
}


def validate_recruiter_transition(current_status, new_status):
    if new_status == current_status:
        return
    if new_status not in RECRUITER_TRANSITIONS.get(current_status, set()):
        raise ValidationError({
            "status": f"Recruiters cannot change an application from {current_status} to {new_status}."
        })


def submit_application(profile, drive):
    """Create one application and its result atomically; safely handle races."""
    eligible, reasons = check_eligibility(profile, drive)
    if not eligible:
        raise ValidationError({"detail": reasons})
    try:
        with transaction.atomic():
            application, created = Application.objects.get_or_create(
                student=profile, placement_drive=drive,
            )
            if not created:
                return application, False
            Result.objects.get_or_create(application=application)
            return application, True
    except IntegrityError:
        # Another request may have won the unique (student, drive) constraint.
        existing = Application.objects.filter(student=profile, placement_drive=drive).first()
        if existing:
            return existing, False
        raise


def withdraw_application(application):
    """Withdraw an application when it has not reached a terminal outcome."""
    if application.status in {
        ApplicationStatus.SELECTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }:
        raise ValidationError({"status": "This application can no longer be withdrawn."})
    application.status = ApplicationStatus.WITHDRAWN
    application.save(update_fields=["status", "updated_at"])
    return application
