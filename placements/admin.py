from django.contrib import admin

from .models import (
    Announcement, Application, College, Company, Department, Gallery, PlacementDrive,
    PlacementHistory, RecruiterProfile, Result, Skill, StudentProfile, StudyMaterial,
)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "college", "department", "current_year", "cgpa", "passout_year", "is_active")
    list_filter = ("college", "department", "current_year", "is_active")
    search_fields = ("user__name", "user__email", "university_no", "college__name", "department__name")
    filter_horizontal = ("skills",)


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "phone", "created_at")
    list_filter = ("company",)
    search_fields = ("user__name", "user__email", "company__name")
    autocomplete_fields = ("user", "company")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "company")


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "location", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "short_name", "location")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "location", "contact_name", "contact_email")


@admin.register(PlacementDrive)
class PlacementDriveAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "job_role", "status", "application_deadline")
    list_filter = ("status", "employment_type", "company")
    search_fields = ("title", "job_role", "company__name")
    filter_horizontal = ("allowed_colleges", "allowed_departments", "required_skills", "recruiters")
    autocomplete_fields = ("company",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("student", "placement_drive", "status", "applied_at", "updated_at")
    list_filter = ("status", "placement_drive__company")
    search_fields = ("student__user__name", "student__user__email", "placement_drive__title", "placement_drive__company__name")
    readonly_fields = ("applied_at", "updated_at")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        Result.objects.get_or_create(application=obj)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("application", "test", "gd", "technical_interview", "hr_interview", "updated_at")
    list_filter = ("test", "gd", "technical_interview", "hr_interview")
    search_fields = ("application__student__user__name", "application__student__user__email", "application__placement_drive__title")
    readonly_fields = ("updated_at",)


@admin.register(PlacementHistory)
class PlacementHistoryAdmin(admin.ModelAdmin):
    list_display = ("student", "company", "placement_type", "job_role", "package", "placement_date", "status")
    list_filter = ("placement_type", "status", "company")
    search_fields = ("student__user__name", "student__user__email", "company__name", "job_role")


@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "placement_drive", "is_published", "created_at")
    list_filter = ("is_published", "company")
    search_fields = ("title", "category", "company__name")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "status", "published_at", "created_at")
    list_filter = ("audience", "status")
    search_fields = ("title", "content")
    filter_horizontal = ("colleges", "students")


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "year", "display_order", "is_published")
    list_filter = ("is_published", "company", "year")
    search_fields = ("title", "description", "company__name")
