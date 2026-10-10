from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from accounts.decorators import admin_required, recruiter_required, student_required
from accounts.models import Role
from .forms import (
    AnnouncementForm, ApplicationStatusForm, CollegeForm, CompanyForm, DepartmentForm,
    GalleryForm, PlacementDriveForm, PlacementHistoryForm, RecruiterProfileForm,
    ResultEditForm, SkillForm, StudentProfileForm, StudyMaterialForm,
)
from .models import *

User = get_user_model()


def _page(request, qs, size=20):
    return Paginator(qs, size).get_page(request.GET.get("page"))


def _eligible(profile, drive):
    reasons = []
    if not profile.is_active:
        reasons.append("Your student account is inactive.")
    if profile.cgpa < drive.minimum_cgpa:
        reasons.append(f"CGPA below required minimum ({drive.minimum_cgpa}).")
    if profile.backlogs > drive.maximum_backlogs:
        reasons.append(f"Backlogs exceed maximum allowed ({drive.maximum_backlogs}).")
    if drive.allowed_colleges.exists() and not drive.allowed_colleges.filter(pk=profile.college_id).exists():
        reasons.append("Your college is not included in this drive.")
    if drive.allowed_departments.exists() and not drive.allowed_departments.filter(pk=profile.department_id).exists():
        reasons.append("Your department is not eligible.")
    years = {int(x) for x in (drive.allowed_graduation_years or [])}
    if years and profile.passout_year not in years:
        reasons.append("Your graduation year is not eligible.")
    required = set(drive.required_skills.filter(is_active=True).values_list("id", flat=True))
    owned = set(profile.skills.filter(is_active=True).values_list("id", flat=True))
    if required - owned:
        reasons.append("You do not have all required skills.")
    now = timezone.now()
    if drive.status != PlacementDriveStatus.OPEN:
        reasons.append("This placement drive is not open.")
    if now < drive.application_start:
        reasons.append("Applications have not started yet.")
    if now > drive.application_deadline:
        reasons.append("The application deadline has passed.")
    return not reasons, reasons


# --------------------------- Public / student ---------------------------

def history(request):
    qs = PlacementHistory.objects.filter(status=PlacementHistoryStatus.PLACED).select_related("student__user", "company", "placement_drive")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(student__user__name__icontains=search) | Q(company__name__icontains=search))
    return render(request, "placements/history.html", {"records": _page(request, qs), "search": search})


def materials(request):
    qs = StudyMaterial.objects.filter(is_published=True).select_related("company", "placement_drive").order_by("-created_at")
    return render(request, "placements/materials.html", {"materials": _page(request, qs)})


@student_required
def dashboard(request):
    profile = get_object_or_404(
        StudentProfile.objects.select_related("user", "college", "department").prefetch_related("skills", "applications__placement_drive__company", "placement_history__company"),
        user=request.user,
    )
    drives = PlacementDrive.objects.filter(status=PlacementDriveStatus.OPEN).select_related("company").prefetch_related("allowed_colleges", "allowed_departments", "required_skills")
    eligible_drives = []
    for drive in drives:
        ok, reasons = _eligible(profile, drive)
        eligible_drives.append((drive, ok, reasons))
    apps = profile.applications.select_related("placement_drive__company").order_by("-applied_at")[:10]
    announcements = Announcement.objects.filter(status=AnnouncementStatus.PUBLISHED).filter(
        Q(audience=AnnouncementAudience.GLOBAL)
        | Q(audience=AnnouncementAudience.COLLEGE, colleges=profile.college)
        | Q(audience=AnnouncementAudience.DRIVE, placement_drive__applications__student=profile)
        | Q(audience=AnnouncementAudience.STUDENT, students=profile)
    ).distinct().order_by("-created_at")[:10]
    fields = [profile.phone, profile.college_id, profile.university_no, profile.address, profile.department_id, profile.current_year, profile.cgpa, profile.passout_year, profile.resume, profile.photo, profile.skills.exists()]
    completion = round(sum(bool(v) for v in fields) / len(fields) * 100)
    return render(request, "placements/dashboard.html", {"profile": profile, "drives": eligible_drives[:8], "applications": apps, "announcements": announcements, "history": profile.placement_history.all()[:5], "completion": completion})


@student_required
def profile_edit(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    if request.method == "POST":
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("placements:profile")
    else:
        form = StudentProfileForm(instance=profile)
    return render(request, "placements/profile.html", {"form": form, "profile": profile})


@student_required
def drive_list(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    qs = PlacementDrive.objects.filter(status=PlacementDriveStatus.OPEN).select_related("company").prefetch_related("allowed_colleges", "allowed_departments", "required_skills")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(company__name__icontains=search) | Q(title__icontains=search) | Q(job_role__icontains=search))
    items = [(d, *_eligible(profile, d)) for d in qs]
    page = _page(request, qs)
    return render(request, "placements/drives.html", {"drives": page, "profile": profile, "eligibility": {d.id: _eligible(profile, d) for d in page.object_list}})


@student_required
def drive_detail(request, pk):
    profile = get_object_or_404(StudentProfile, user=request.user)
    drive = get_object_or_404(PlacementDrive.objects.select_related("company").prefetch_related("allowed_colleges", "allowed_departments", "required_skills"), pk=pk)
    eligible, reasons = _eligible(profile, drive)
    application = Application.objects.filter(student=profile, placement_drive=drive).first()
    return render(request, "placements/drive_detail.html", {"drive": drive, "eligible": eligible, "reasons": reasons, "application": application})


@student_required
@require_POST
def apply_drive(request, pk):
    profile = get_object_or_404(StudentProfile, user=request.user)
    drive = get_object_or_404(PlacementDrive, pk=pk)
    eligible, reasons = _eligible(profile, drive)
    if not eligible:
        messages.error(request, "Cannot apply: " + " ".join(reasons))
        return redirect("placements:drive_detail", pk=pk)
    application, created = Application.objects.get_or_create(student=profile, placement_drive=drive)
    if created:
        Result.objects.get_or_create(application=application)
        messages.success(request, "Application submitted successfully.")
    else:
        messages.info(request, "You have already applied to this drive.")
    return redirect("placements:applications")


@student_required
def applications(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    qs = Application.objects.filter(student=profile).select_related("placement_drive__company").prefetch_related("result")
    return render(request, "placements/applications.html", {"applications": _page(request, qs)})


@student_required
@require_POST
def withdraw_application(request, pk):
    app = get_object_or_404(Application, pk=pk, student__user=request.user)
    if app.status not in [ApplicationStatus.SELECTED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]:
        app.status = ApplicationStatus.WITHDRAWN
        app.save(update_fields=["status", "updated_at"])
        messages.success(request, "Application withdrawn.")
    return redirect("placements:applications")


# --------------------------- Recruiter ---------------------------

@recruiter_required
def recruiter_dashboard(request):
    recruiter = get_object_or_404(RecruiterProfile.objects.select_related("company", "user"), user=request.user)
    drives = PlacementDrive.objects.filter(recruiters=recruiter).select_related("company").distinct()
    apps = Application.objects.filter(placement_drive__in=drives).select_related("student__user", "student__college", "student__department", "placement_drive__company").prefetch_related("student__skills")

    q = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()
    college = request.GET.get("college", "").strip()
    department = request.GET.get("department", "").strip()
    min_cgpa = request.GET.get("min_cgpa", "").strip()
    selected_skills = [x for x in request.GET.getlist("skills") if x.isdigit()]
    skill_mode = request.GET.get("skill_mode", "all")
    ordering = request.GET.get("ordering", "-applied_at")

    if q:
        apps = apps.filter(Q(student__user__name__icontains=q) | Q(student__user__email__icontains=q) | Q(placement_drive__title__icontains=q))
    if status_filter:
        apps = apps.filter(status=status_filter)
    if college:
        apps = apps.filter(student__college_id=college) if college.isdigit() else apps.filter(student__college__name__icontains=college)
    if department:
        apps = apps.filter(student__department_id=department) if department.isdigit() else apps.filter(student__department__name__icontains=department)
    if min_cgpa:
        try:
            apps = apps.filter(student__cgpa__gte=float(min_cgpa))
        except ValueError:
            pass
    if selected_skills:
        if skill_mode == "any":
            apps = apps.filter(student__skills__id__in=selected_skills)
        else:
            for skill_id in selected_skills:
                apps = apps.filter(student__skills__id=skill_id)
    ordering_map = {
        "name": "student__user__name", "-name": "-student__user__name",
        "cgpa": "student__cgpa", "-cgpa": "-student__cgpa",
        "college": "student__college__name", "-college": "-student__college__name",
        "applied_at": "applied_at", "-applied_at": "-applied_at",
        "status": "status", "-status": "-status",
    }
    apps = apps.distinct().order_by(ordering_map.get(ordering, "-applied_at"))

    return render(request, "placements/recruiter_dashboard.html", {
        "recruiter": recruiter, "drives": drives, "applications": _page(request, apps),
        "statuses": ApplicationStatus.choices,
        "skills": Skill.objects.filter(is_active=True),
        "colleges": College.objects.filter(is_active=True),
        "departments": Department.objects.filter(is_active=True),
        "filters": request.GET,
        "ordering": ordering,
    })


@recruiter_required
def recruiter_candidate(request, pk):
    recruiter = get_object_or_404(RecruiterProfile, user=request.user)
    application = get_object_or_404(
        Application.objects.select_related("student__user", "student__college", "student__department", "placement_drive__company").prefetch_related("student__skills"),
        pk=pk,
        placement_drive__recruiters=recruiter,
    )
    return render(request, "placements/recruiter_candidate.html", {"application": application})


@recruiter_required
@require_POST
def recruiter_update_application(request, pk):
    recruiter = get_object_or_404(RecruiterProfile, user=request.user)
    app = get_object_or_404(Application, pk=pk, placement_drive__recruiters=recruiter)
    form = ApplicationStatusForm(request.POST, instance=app)
    if form.is_valid():
        updated = form.save()
        if updated.status == ApplicationStatus.SELECTED:
            drive = updated.placement_drive
            history, created = PlacementHistory.objects.get_or_create(
                student=updated.student,
                placement_drive=drive,
                defaults={
                    "company": drive.company,
                    "job_role": drive.job_role,
                    "package": drive.salary_package,
                    "placement_date": timezone.localdate(),
                    "placement_type": PlacementType.ON_CAMPUS,
                    "status": PlacementHistoryStatus.PLACED,
                    "created_by": request.user,
                },
            )
            if not created:
                history.status = PlacementHistoryStatus.PLACED
                history.save(update_fields=["status", "updated_at"])
        messages.success(request, "Application status updated.")
    return redirect("placements:recruiter_dashboard")


# --------------------------- Admin ---------------------------

@admin_required
def admin_dashboard(request):
    context = {
        "student_count": StudentProfile.objects.filter(is_active=True).count(),
        "recruiter_count": RecruiterProfile.objects.filter(user__is_active=True).count(),
        "company_count": Company.objects.filter(is_active=True).count(),
        "college_count": College.objects.filter(is_active=True).count(),
        "department_count": Department.objects.filter(is_active=True).count(),
        "skill_count": Skill.objects.filter(is_active=True).count(),
        "drive_count": PlacementDrive.objects.filter(status=PlacementDriveStatus.OPEN).count(),
        "application_count": Application.objects.count(),
        "selected_count": Application.objects.filter(status=ApplicationStatus.SELECTED).count(),
        "announcement_count": Announcement.objects.filter(status=AnnouncementStatus.PUBLISHED).count(),
        "history_count": PlacementHistory.objects.filter(status=PlacementHistoryStatus.PLACED).count(),
    }
    return render(request, "placements/admin_dashboard.html", context)


@admin_required
def admin_student_list(request):
    qs = StudentProfile.objects.select_related("user", "college", "department").prefetch_related("skills")
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(user__name__icontains=search) | Q(user__email__icontains=search) | Q(college__name__icontains=search) | Q(department__name__icontains=search))
    return render(request, "placements/admin_list.html", {"students": _page(request, qs), "search": search})


@admin_required
def admin_student_edit(request, pk):
    profile = get_object_or_404(StudentProfile, pk=pk)
    if request.method == "POST":
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Student updated.")
            return redirect("placements:admin_list")
    else:
        form = StudentProfileForm(instance=profile)
    return render(request, "placements/profile.html", {"form": form, "profile": profile, "admin_mode": True})


@admin_required
@require_POST
def admin_student_delete(request, pk):
    profile = get_object_or_404(StudentProfile, pk=pk)
    profile.user.delete()
    messages.success(request, "Student account deleted.")
    return redirect("placements:admin_list")


RESOURCE_CONFIG = {
    "companies": (Company, CompanyForm),
    "colleges": (College, CollegeForm),
    "departments": (Department, DepartmentForm),
    "skills": (Skill, SkillForm),
    "recruiters": (RecruiterProfile, RecruiterProfileForm),
    "drives": (PlacementDrive, PlacementDriveForm),
    "announcements": (Announcement, AnnouncementForm),
    "materials": (StudyMaterial, StudyMaterialForm),
    "gallery": (Gallery, GalleryForm),
    "history": (PlacementHistory, PlacementHistoryForm),
}


@admin_required
def admin_resource(request, resource):
    config = RESOURCE_CONFIG.get(resource)
    if not config:
        return redirect("placements:admin_dashboard")
    model, Form = config
    obj = get_object_or_404(model, pk=request.GET.get("edit")) if request.GET.get("edit") else None
    if request.method == "POST":
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            if resource == "recruiters":
                form.save()
            else:
                item = form.save(commit=False)
                if resource == "materials":
                    item.uploaded_by = request.user
                if resource == "history":
                    item.created_by = item.created_by or request.user
                if resource == "announcements" and item.status == AnnouncementStatus.PUBLISHED and not item.published_at:
                    item.published_at = timezone.now()
                item.save()
                form.save_m2m()
            messages.success(request, f"{resource.replace('_', ' ').title()} saved.")
            return redirect("placements:admin_resource", resource=resource)
    else:
        form = Form(instance=obj)
    items = model.objects.all()
    if resource == "recruiters":
        items = items.select_related("user", "company")
    elif resource == "history":
        items = items.select_related("student__user", "company", "placement_drive")
    elif resource == "drives":
        items = items.select_related("company")
    return render(request, "placements/admin_resource.html", {"resource": resource, "form": form, "items": _page(request, items, 20)})


@admin_required
@require_POST
def admin_delete_resource(request, resource, pk):
    config = RESOURCE_CONFIG.get(resource)
    if not config:
        return redirect("placements:admin_dashboard")
    model, _ = config
    obj = get_object_or_404(model, pk=pk)
    if resource == "recruiters":
        user = obj.user
        obj.delete()
        user.delete()
    else:
        obj.delete()
    messages.success(request, "Record removed.")
    return redirect("placements:admin_resource", resource=resource)


@admin_required
def admin_application_list(request):
    qs = Application.objects.select_related("student__user", "placement_drive__company").order_by("-updated_at")
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)
    return render(request, "placements/admin_applications.html", {"applications": _page(request, qs), "statuses": ApplicationStatus.choices, "selected_status": status})


@admin_required
@require_POST
def admin_application_update(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    form = ApplicationStatusForm(request.POST, instance=application)
    if form.is_valid():
        updated = form.save()
        if updated.status == ApplicationStatus.SELECTED:
            drive = updated.placement_drive
            PlacementHistory.objects.update_or_create(
                student=updated.student, placement_drive=drive,
                defaults={
                    "company": drive.company, "job_role": drive.job_role, "package": drive.salary_package,
                    "placement_date": timezone.localdate(), "placement_type": PlacementType.ON_CAMPUS,
                    "status": PlacementHistoryStatus.PLACED, "created_by": request.user,
                },
            )
        messages.success(request, "Application updated.")
    return redirect("placements:admin_applications")


@admin_required
@require_POST
def admin_result_update(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    result, _ = Result.objects.get_or_create(application=application)
    form = ResultEditForm(request.POST, instance=result)
    if form.is_valid():
        form.save()
        messages.success(request, "Candidate result updated.")
    else:
        messages.error(request, "Please correct the result fields.")
    return redirect("placements:admin_applications")
