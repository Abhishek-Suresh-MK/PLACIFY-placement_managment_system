from rest_framework import serializers
from accounts.models import Role, User
from placements.models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RecruiterProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = RecruiterProfile
        fields = ["id", "user", "company", "company_name", "phone", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    college_name = serializers.CharField(source="college.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    department_code = serializers.CharField(source="department.code", read_only=True)
    skills = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.filter(is_active=True), many=True, required=False)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "user", "name", "email", "phone", "photo", "college", "college_name",
            "university_no", "address", "age", "department", "department_name", "department_code",
            "current_year", "cgpa", "backlogs", "passout_year", "skills", "resume", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at", "is_active"]


class PlacementDriveSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    required_skill_names = serializers.SlugRelatedField(source="required_skills", many=True, read_only=True, slug_field="name")

    class Meta:
        model = PlacementDrive
        fields = [
            "id", "company", "company_name", "title", "description", "job_role", "location", "employment_type",
            "salary_package", "eligibility_description", "minimum_cgpa", "maximum_backlogs", "allowed_colleges",
            "allowed_departments", "allowed_graduation_years", "required_skills", "required_skill_names", "recruiters",
            "application_start", "application_deadline", "drive_date", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        start = data.get("application_start")
        deadline = data.get("application_deadline")
        if start and deadline and deadline < start:
            raise serializers.ValidationError("Application deadline cannot be before application start.")
        return data


class ApplicationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.name", read_only=True)
    company = serializers.CharField(source="placement_drive.company.name", read_only=True)
    drive_title = serializers.CharField(source="placement_drive.title", read_only=True)

    class Meta:
        model = Application
        fields = ["id", "student", "student_name", "placement_drive", "drive_title", "company", "status", "applied_at", "updated_at", "remarks"]
        read_only_fields = ["id", "applied_at", "updated_at", "student"]


class ResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="application.student.user.name", read_only=True)
    drive_title = serializers.CharField(source="application.placement_drive.title", read_only=True)

    class Meta:
        model = Result
        fields = ["id", "application", "student_name", "drive_title", "test", "gd", "technical_interview", "hr_interview", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class PlacementHistorySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = PlacementHistory
        fields = ["id", "student", "student_name", "company", "company_name", "placement_drive", "job_role", "package", "placement_date", "placement_type", "status", "remarks", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "title", "content", "drive_date", "status", "audience", "colleges", "placement_drive", "students", "published_at", "created_at", "updated_at"]
        read_only_fields = ["id", "published_at", "created_at", "updated_at"]


class StudyMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyMaterial
        fields = ["id", "title", "description", "category", "file", "external_url", "uploaded_by", "company", "placement_drive", "drive_link", "is_published", "created_at", "updated_at"]
        read_only_fields = ["id", "uploaded_by", "created_at", "updated_at"]


class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
