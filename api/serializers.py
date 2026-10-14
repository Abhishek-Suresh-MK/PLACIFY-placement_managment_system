from rest_framework import serializers
from django.utils import timezone
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
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(role=Role.RECRUITER),
        write_only=True,
        required=False,
    )
    company_name = serializers.CharField(source="company.name", read_only=True)
    email = serializers.EmailField(write_only=True, required=False)
    name = serializers.CharField(write_only=True, required=False, max_length=150)
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False, style={"input_type": "password"})

    class Meta:
        model = RecruiterProfile
        fields = ["id", "user", "user_id", "email", "name", "password", "company", "company_name", "phone", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request and not (request.user.is_superuser or request.user.role == Role.ADMIN):
            # Recruiters may update only their own phone number.
            if self.instance is None:
                raise serializers.ValidationError("Only administrators can create recruiter profiles.")
            forbidden = set(attrs) - {"phone"}
            if forbidden:
                raise serializers.ValidationError("Recruiters may update only their phone number.")
        if self.instance is None and "user" not in attrs:
            required = {"email", "name", "password"}
            missing = sorted(required - set(attrs))
            if missing:
                raise serializers.ValidationError({field: "This field is required when creating a recruiter account." for field in missing})
            if User.objects.filter(email__iexact=attrs["email"]).exists():
                raise serializers.ValidationError({"email": "A user with this email already exists."})
            from django.contrib.auth.password_validation import validate_password
            try:
                validate_password(attrs["password"], user=User(email=attrs["email"], name=attrs["name"]))
            except Exception as exc:
                raise serializers.ValidationError({"password": list(exc.messages) if hasattr(exc, "messages") else str(exc)})
        if "user" in attrs and RecruiterProfile.objects.filter(user=attrs["user"]).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError({"user_id": "This user already has a recruiter profile."})
        return attrs

    def create(self, validated_data):
        user = validated_data.pop("user", None)
        if user is None:
            email = validated_data.pop("email").strip().lower()
            name = validated_data.pop("name")
            password = validated_data.pop("password")
            user = User.objects.create_user(email=email, name=name, password=password, role=Role.RECRUITER)
        else:
            validated_data.pop("email", None)
            validated_data.pop("name", None)
            validated_data.pop("password", None)
        return RecruiterProfile.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        for field in ("email", "name", "password"):
            validated_data.pop(field, None)
        return super().update(instance, validated_data)


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(role=Role.STUDENT),
        write_only=True,
        required=False,
    )
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    college_name = serializers.CharField(source="college.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    department_code = serializers.CharField(source="department.code", read_only=True)
    skills = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.filter(is_active=True), many=True, required=False)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "user", "user_id", "name", "email", "phone", "photo", "college", "college_name",
            "university_no", "address", "age", "department", "department_name", "department_code",
            "current_year", "cgpa", "backlogs", "passout_year", "skills", "resume", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        is_admin = bool(request and request.user.is_authenticated and (
            request.user.is_superuser or request.user.role == Role.ADMIN
        ))
        if self.instance is None:
            if not is_admin:
                raise serializers.ValidationError("Only administrators can create student profiles through this endpoint.")
            if "user" not in attrs:
                raise serializers.ValidationError({"user_id": "This field is required when creating a student profile."})
        elif "user" in attrs and attrs["user"].pk != self.instance.user_id:
            raise serializers.ValidationError({"user_id": "A profile cannot be reassigned to another account."})
        if not is_admin and "user" in attrs:
            raise serializers.ValidationError({"user_id": "You cannot change the account linked to your profile."})
        if "user" in attrs and StudentProfile.objects.filter(user=attrs["user"]).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError({"user_id": "This user already has a student profile."})
        return attrs

    def validate_passout_year(self, value):
        from datetime import date
        current_year = date.today().year
        if value < 2000 or value > current_year + 8:
            raise serializers.ValidationError(f"Graduation year must be between 2000 and {current_year + 8}.")
        return value

    def validate_cgpa(self, value):
        if value < 0 or value > 10:
            raise serializers.ValidationError("CGPA must be between 0 and 10.")
        return value

    def validate_backlogs(self, value):
        if value < 0:
            raise serializers.ValidationError("Backlogs cannot be negative.")
        return value

    def validate_college(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Select an active college.")
        return value

    def validate_department(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Select an active department.")
        return value

    def validate_skills(self, value):
        inactive = [skill.name for skill in value if not skill.is_active]
        if inactive:
            raise serializers.ValidationError("Only active skills from the shared catalogue may be selected.")
        return value

    def validate_photo(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Profile photo must be 5 MB or smaller.")
        return value

    def validate_resume(self, value):
        if value:
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Resume must be 5 MB or smaller.")
            name = value.name.lower()
            if not name.endswith((".pdf", ".doc", ".docx")):
                raise serializers.ValidationError("Resume must be a PDF, DOC, or DOCX file.")
            if name.endswith(".pdf"):
                position = value.tell()
                try:
                    value.seek(0)
                    if value.read(5) != b"%PDF-":
                        raise serializers.ValidationError("The uploaded file is not a valid PDF.")
                finally:
                    value.seek(position)
        return value

    def get_extra_kwargs(self):
        extra = super().get_extra_kwargs()
        request = self.context.get("request")
        if request and request.user.is_authenticated and request.user.role == Role.STUDENT:
            # Eligibility and identity fields are managed by the placement office,
            # not self-reported through the public profile endpoint.
            for field in ("college", "university_no", "age", "department", "current_year", "cgpa", "backlogs", "passout_year", "is_active"):
                extra[field] = {**extra.get(field, {}), "read_only": True}
        return extra


class RecruiterCandidateProfileSerializer(serializers.ModelSerializer):
    """Minimum candidate data visible to recruiters for assigned-drive applicants."""
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    college_name = serializers.CharField(source="college.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = StudentProfile
        fields = ["id", "name", "email", "phone", "college_name", "department_name", "current_year", "cgpa", "backlogs", "passout_year", "skills", "resume"]
        read_only_fields = fields


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
        start = data.get("application_start", getattr(self.instance, "application_start", None))
        deadline = data.get("application_deadline", getattr(self.instance, "application_deadline", None))
        status_value = data.get("status", getattr(self.instance, "status", PlacementDriveStatus.DRAFT))
        company = data.get("company", getattr(self.instance, "company", None))
        if start and deadline and deadline < start:
            raise serializers.ValidationError({"application_deadline": "Application deadline cannot be before application start."})
        if status_value == PlacementDriveStatus.OPEN:
            if deadline and deadline < timezone.now():
                raise serializers.ValidationError({"application_deadline": "An expired drive cannot be published as open."})
            if company and not company.is_active:
                raise serializers.ValidationError({"company": "An inactive company cannot publish a drive."})
        return data


class ApplicationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.name", read_only=True)
    company = serializers.CharField(source="placement_drive.company.name", read_only=True)
    drive_title = serializers.CharField(source="placement_drive.title", read_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.user.role == Role.RECRUITER and self.instance and "status" in attrs:
            from placements.services.workflow import validate_recruiter_transition
            validate_recruiter_transition(self.instance.status, attrs["status"])
        return attrs

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
        fields = ["id", "student", "student_name", "company", "company_name", "job_role", "package", "placement_date", "placement_type", "status", "remarks", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "title", "content", "drive_date", "status", "audience", "colleges", "students", "published_at", "created_at", "updated_at"]
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
