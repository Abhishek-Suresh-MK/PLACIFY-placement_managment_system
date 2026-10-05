from django.db.models import Q
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from placements.models import *
from .permissions import IsAdminOrReadOnly, IsAnnouncementManager, IsRecruiterOrAdmin
from .serializers import *


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == Role.ADMIN))


def eligible(profile, drive):
    reasons = []
    if profile.cgpa < drive.minimum_cgpa:
        reasons.append("CGPA below minimum")
    if profile.backlogs > drive.maximum_backlogs:
        reasons.append("Too many backlogs")
    if drive.allowed_colleges.exists() and not drive.allowed_colleges.filter(pk=profile.college_id).exists():
        reasons.append("College not eligible")
    if drive.allowed_departments.exists() and not drive.allowed_departments.filter(pk=profile.department_id).exists():
        reasons.append("Department not eligible")
    years = {int(x) for x in (drive.allowed_graduation_years or [])}
    if years and profile.passout_year not in years:
        reasons.append("Graduation year not eligible")
    required = set(drive.required_skills.filter(is_active=True).values_list("id", flat=True))
    owned = set(profile.skills.filter(is_active=True).values_list("id", flat=True))
    if required - owned:
        reasons.append("Missing required skills")
    now = timezone.now()
    if drive.status != PlacementDriveStatus.OPEN:
        reasons.append("Drive is not open")
    if now < drive.application_start:
        reasons.append("Applications have not started")
    if now > drive.application_deadline:
        reasons.append("Application deadline has passed")
    return not reasons, reasons


class AuthTokenView(ObtainAuthToken):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        token, _ = Token.objects.get_or_create(user=serializer.validated_data["user"])
        return Response({"token": token.key, "user": UserSerializer(serializer.validated_data["user"]).data})


class LogoutView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        if hasattr(request.user, "auth_token"):
            request.user.auth_token.delete()
        return Response({"detail": "Successfully logged out."})


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "name"]
    ordering_fields = ["email", "name", "date_joined", "role"]

    def get_queryset(self):
        if is_admin(self.request.user):
            return User.objects.all().order_by("email")
        return User.objects.filter(pk=self.request.user.pk)

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(self.get_serializer(request.user).data)


class CollegeViewSet(viewsets.ModelViewSet):
    queryset = College.objects.all()
    serializer_class = CollegeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "short_name", "location"]
    ordering_fields = ["name", "created_at"]


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code"]


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "category"]
    ordering_fields = ["name", "category", "created_at"]


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "location"]
    ordering_fields = ["name", "created_at"]


class RecruiterProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RecruiterProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RecruiterProfile.objects.select_related("user", "company") if is_admin(self.request.user) else RecruiterProfile.objects.filter(user=self.request.user).select_related("user", "company")


class StudentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__name", "user__email", "college__name", "department__name", "university_no"]
    ordering_fields = ["id", "user__name", "cgpa", "created_at"]

    def get_queryset(self):
        u = self.request.user
        qs = StudentProfile.objects.select_related("user", "college", "department").prefetch_related("skills")
        if is_admin(u) or u.role == Role.RECRUITER:
            return qs
        return qs.filter(user=u)

    def create(self, request, *args, **kwargs):
        raise PermissionDenied("Student accounts are created through the registration/admin workflow.")

    def update(self, request, *args, **kwargs):
        if request.user.role == Role.RECRUITER:
            raise PermissionDenied("Recruiters can view candidate profiles but cannot edit them.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only administrators can delete student profiles.")
        return super().destroy(request, *args, **kwargs)


class PlacementDriveViewSet(viewsets.ModelViewSet):
    serializer_class = PlacementDriveSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "job_role", "company__name", "location"]
    ordering_fields = ["application_deadline", "drive_date", "created_at", "minimum_cgpa", "salary_package"]

    def get_queryset(self):
        u = self.request.user
        qs = PlacementDrive.objects.select_related("company").prefetch_related("allowed_colleges", "allowed_departments", "required_skills", "recruiters")
        if is_admin(u):
            return qs
        if u.role == Role.RECRUITER:
            return qs.filter(recruiters__user=u).distinct()
        return qs.filter(status=PlacementDriveStatus.OPEN)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def ai_summary(self, request, pk=None):
        from placements.services.ai import summarize_drive
        text = summarize_drive(self.get_object())
        if not text:
            return Response({"detail": "AI feature is unavailable. Configure OPENAI_API_KEY to enable it."}, status=503)
        return Response({"summary": text})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def apply(self, request, pk=None):
        if request.user.role != Role.STUDENT:
            raise PermissionDenied()
        profile = getattr(request.user, "student_profile", None)
        if not profile:
            raise ValidationError("Student profile not found.")
        drive = self.get_object()
        ok, reasons = eligible(profile, drive)
        if not ok:
            return Response({"detail": "Not eligible", "reasons": reasons}, status=400)
        application, created = Application.objects.get_or_create(student=profile, placement_drive=drive)
        if not created:
            return Response({"detail": "Already applied", "application": ApplicationSerializer(application).data}, status=400)
        Result.objects.get_or_create(application=application)
        return Response(ApplicationSerializer(application).data, status=201)


class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["student__user__name", "student__user__email", "placement_drive__company__name", "placement_drive__title"]
    ordering_fields = ["applied_at", "updated_at", "status"]

    def get_queryset(self):
        u = self.request.user
        qs = Application.objects.select_related("student__user", "placement_drive__company")
        if is_admin(u):
            return qs
        if u.role == Role.STUDENT:
            return qs.filter(student__user=u)
        if u.role == Role.RECRUITER:
            return qs.filter(placement_drive__recruiters__user=u).distinct()
        return qs.none()

    def perform_create(self, serializer):
        if self.request.user.role != Role.STUDENT:
            raise PermissionDenied()
        profile = getattr(self.request.user, "student_profile", None)
        drive = serializer.validated_data["placement_drive"]
        ok, reasons = eligible(profile, drive)
        if not ok:
            raise ValidationError({"detail": reasons})
        application = serializer.save(student=profile)
        Result.objects.get_or_create(application=application)

    def update(self, request, *args, **kwargs):
        if request.user.role == Role.STUDENT:
            raise PermissionDenied("Students cannot edit application records here.")
        if request.user.role == Role.RECRUITER:
            allowed = set(request.data.keys()) - {"status", "remarks"}
            if allowed:
                raise PermissionDenied("Recruiters can update only application status and remarks.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only administrators can delete applications.")
        return super().destroy(request, *args, **kwargs)


class ResultViewSet(viewsets.ModelViewSet):
    serializer_class = ResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = Result.objects.select_related("application__student__user", "application__placement_drive")
        if is_admin(u):
            return qs
        if u.role == Role.STUDENT:
            return qs.filter(application__student__user=u)
        return qs.none()

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only administrators can update results.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only administrators can delete results.")
        return super().destroy(request, *args, **kwargs)


class PlacementHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = PlacementHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = PlacementHistory.objects.select_related("student__user", "company", "placement_drive")
        if is_admin(u):
            return qs
        if u.role == Role.STUDENT:
            return qs.filter(student__user=u)
        return qs.none()

    def perform_create(self, serializer):
        if not is_admin(self.request.user):
            raise PermissionDenied()
        serializer.save(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied()
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied()
        return super().destroy(request, *args, **kwargs)


class StudyMaterialViewSet(viewsets.ModelViewSet):
    queryset = StudyMaterial.objects.select_related("company", "placement_drive")
    serializer_class = StudyMaterialSerializer
    permission_classes = [IsAuthenticated, IsAnnouncementManager]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "category", "company__name", "placement_drive__title"]
    ordering_fields = ["created_at", "title"]

    def get_queryset(self):
        return super().get_queryset() if is_admin(self.request.user) else super().get_queryset().filter(is_published=True)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated, IsAnnouncementManager]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "published_at", "status"]

    def get_queryset(self):
        u = self.request.user
        if is_admin(u):
            return Announcement.objects.all()
        if u.role == Role.STUDENT:
            p = getattr(u, "student_profile", None)
            return Announcement.objects.filter(status=AnnouncementStatus.PUBLISHED).filter(
                Q(audience=AnnouncementAudience.GLOBAL)
                | Q(audience=AnnouncementAudience.COLLEGE, colleges=p.college)
                | Q(audience=AnnouncementAudience.DRIVE, placement_drive__applications__student=p)
                | Q(audience=AnnouncementAudience.STUDENT, students=p)
            ).distinct()
        return Announcement.objects.filter(status=AnnouncementStatus.PUBLISHED)

    @action(detail=False, methods=["get"], url_path="published")
    def published(self, request):
        return Response(self.get_serializer(self.get_queryset().filter(status=AnnouncementStatus.PUBLISHED), many=True).data)


class GalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.select_related("company")
    serializer_class = GallerySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "company__name"]
    ordering_fields = ["display_order", "created_at"]

    def get_queryset(self):
        return super().get_queryset() if is_admin(self.request.user) else super().get_queryset().filter(is_published=True)


class RecruiterSearchViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsRecruiterOrAdmin]
    pagination_class = __import__("api.pagination", fromlist=["StandardResultsSetPagination"]).StandardResultsSetPagination

    def list(self, request):
        qs = StudentProfile.objects.select_related("user", "college", "department").prefetch_related("skills")
        q = request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(Q(user__name__icontains=q) | Q(user__email__icontains=q) | Q(college__name__icontains=q) | Q(department__name__icontains=q))
        if request.query_params.get("cgpa"):
            try:
                qs = qs.filter(cgpa__gte=float(request.query_params["cgpa"]))
            except ValueError:
                pass
        if request.query_params.get("college"):
            qs = qs.filter(college_id=request.query_params["college"])
        if request.query_params.get("department"):
            qs = qs.filter(department_id=request.query_params["department"])
        skill_ids = [x for x in request.query_params.getlist("skills") if x.isdigit()]
        mode = request.query_params.get("skill_mode", "all")
        if skill_ids:
            if mode == "any":
                qs = qs.filter(skills__id__in=skill_ids)
            else:
                for skill_id in skill_ids:
                    qs = qs.filter(skills__id=skill_id)
        qs = qs.distinct().order_by("user__name")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(StudentProfileSerializer(page, many=True).data)
        return Response(StudentProfileSerializer(qs, many=True).data)
