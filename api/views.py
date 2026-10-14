from django.db.models import Q
from django.utils import timezone
from rest_framework import filters, status, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from placements.models import *
from .permissions import IsAdminOrReadOnly, IsAnnouncementManager, IsRecruiterOrAdmin
from .serializers import *
from placements.services.workflow import check_eligibility, submit_application, validate_recruiter_transition, withdraw_application as withdraw_application_record


def is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == Role.ADMIN))


def eligible(profile, drive):
    """Backward-compatible wrapper around shared workflow eligibility rules."""
    return check_eligibility(profile, drive)


class LogoutView(APIView):
    """Blacklist the caller's refresh token; short-lived access tokens expire in 5 minutes."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.data.get("refresh")
        if not raw_refresh:
            return Response({"detail": "The refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(raw_refresh)
            # Do not allow a caller to revoke another user's refresh token.
            if str(token.get("user_id")) != str(request.user.pk):
                return Response({"detail": "Token does not belong to the authenticated user."}, status=status.HTTP_403_FORBIDDEN)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Refresh token is invalid, expired, or already revoked."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "location"]
    search_fields = ["name", "location"]
    ordering_fields = ["name", "created_at"]


class RecruiterProfileViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__name", "user__email", "company__name"]
    ordering_fields = ["user__name", "company__name", "created_at"]

    def get_queryset(self):
        qs = RecruiterProfile.objects.select_related("user", "company")
        return qs.order_by("user__email") if is_admin(self.request.user) else qs.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only administrators can create recruiter profiles.")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not is_admin(request.user):
            if set(request.data.keys()) - {"phone"}:
                raise PermissionDenied("Recruiters may update only their phone number.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only administrators can delete recruiter profiles.")
        return super().destroy(request, *args, **kwargs)


class StudentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["college", "department", "current_year", "cgpa", "backlogs", "passout_year", "is_active", "skills"]
    search_fields = ["user__name", "user__email", "college__name", "department__name", "university_no"]
    ordering_fields = ["id", "user__name", "cgpa", "backlogs", "passout_year", "created_at"]

    def get_queryset(self):
        u = self.request.user
        qs = StudentProfile.objects.select_related("user", "college", "department").prefetch_related("skills")
        if is_admin(u):
            return qs
        if u.role == Role.RECRUITER:
            return qs.filter(applications__placement_drive__recruiters__user=u).distinct()
        return qs.filter(user=u)

    def get_serializer_class(self):
        if self.request.user.role == Role.RECRUITER and not is_admin(self.request.user):
            return RecruiterCandidateProfileSerializer
        return StudentProfileSerializer

    def create(self, request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Student accounts are created through registration; only administrators can create profiles here.")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.role == Role.RECRUITER:
            self.get_object()
            raise PermissionDenied(
                "Recruiters can view candidate profiles but cannot edit them."
            )
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
        try:
            application, created = submit_application(profile, drive)
        except ValidationError as exc:
            detail = exc.detail
            if isinstance(detail, dict) and "detail" in detail and isinstance(detail["detail"], list):
                return Response({"detail": "Not eligible", "reasons": detail["detail"]}, status=status.HTTP_400_BAD_REQUEST)
            raise
        if not created:
            return Response({"detail": "Already applied", "application": ApplicationSerializer(application).data}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


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

    def create(self, request, *args, **kwargs):
        if request.user.role != Role.STUDENT:
            raise PermissionDenied("Only students can submit applications.")
        profile = getattr(request.user, "student_profile", None)
        if profile is None:
            raise ValidationError("Student profile not found.")
        drive_id = request.data.get("placement_drive")
        try:
            drive = PlacementDrive.objects.get(pk=drive_id)
        except (PlacementDrive.DoesNotExist, TypeError, ValueError):
            raise ValidationError({"placement_drive": "A valid placement drive ID is required."})
        application, created = submit_application(profile, drive)
        if not created:
            return Response({"detail": "Already applied", "application": ApplicationSerializer(application).data}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApplicationSerializer(application).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if request.user.role == Role.STUDENT:
            raise PermissionDenied("Students cannot edit application records here.")
        if request.user.role == Role.RECRUITER:
            allowed = set(request.data.keys()) - {"status", "remarks"}
            if allowed:
                raise PermissionDenied("Recruiters can update only application status and remarks.")
            application = self.get_object()
            new_status = request.data.get("status", application.status)
            validate_recruiter_transition(application.status, new_status)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def withdraw(self, request, pk=None):
        if request.user.role != Role.STUDENT:
            raise PermissionDenied("Only the applicant can withdraw an application.")
        application = self.get_object()
        if application.student.user_id != request.user.pk:
            raise PermissionDenied("You can withdraw only your own application.")
        withdraw_application_record(application)
        return Response(ApplicationSerializer(application).data, status=status.HTTP_200_OK)

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
        qs = PlacementHistory.objects.select_related("student__user", "company")
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
        if not is_admin(request.user):
            qs = qs.filter(applications__placement_drive__recruiters__user=request.user).distinct()
        q = request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(Q(user__name__icontains=q) | Q(user__email__icontains=q) | Q(college__name__icontains=q) | Q(department__name__icontains=q))
        cgpa = request.query_params.get("cgpa")
        if cgpa not in (None, ""):
            try:
                minimum_cgpa = float(cgpa)
            except (TypeError, ValueError):
                raise ValidationError({"cgpa": "Enter a number between 0 and 10."})
            if not 0 <= minimum_cgpa <= 10:
                raise ValidationError({"cgpa": "CGPA must be between 0 and 10."})
            qs = qs.filter(cgpa__gte=minimum_cgpa)
        for param, model in (("college", College), ("department", Department)):
            value = request.query_params.get(param)
            if value not in (None, ""):
                if not value.isdigit() or not model.objects.filter(pk=int(value)).exists():
                    raise ValidationError({param: "Select a valid record ID."})
                qs = qs.filter(**{f"{param}_id": int(value)})
        raw_skill_ids = request.query_params.getlist("skills")
        if any(not value.isdigit() for value in raw_skill_ids):
            raise ValidationError({"skills": "Supply valid skill IDs."})
        skill_ids = [int(value) for value in raw_skill_ids]
        mode = request.query_params.get("skill_mode", "all").lower()
        if mode not in {"all", "any"}:
            raise ValidationError({"skill_mode": "Use 'all' or 'any'."})
        if skill_ids:
            if mode == "any":
                qs = qs.filter(skills__id__in=skill_ids)
            else:
                for skill_id in skill_ids:
                    qs = qs.filter(skills__id=skill_id)
        qs = qs.distinct().order_by("user__name")
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = StudentProfileSerializer if is_admin(request.user) else RecruiterCandidateProfileSerializer
            return self.get_paginated_response(serializer(page, many=True).data)
        serializer = StudentProfileSerializer if is_admin(request.user) else RecruiterCandidateProfileSerializer
        return Response(serializer(qs, many=True).data)
