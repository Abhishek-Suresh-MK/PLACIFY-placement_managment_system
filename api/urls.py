from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
for prefix, view, name in [
    ("users", UserViewSet, "user"),
    ("students", StudentProfileViewSet, "student"),
    ("recruiters", RecruiterProfileViewSet, "recruiter"),
    ("colleges", CollegeViewSet, "college"),
    ("departments", DepartmentViewSet, "department"),
    ("skills", SkillViewSet, "skill"),
    ("companies", CompanyViewSet, "company"),
    ("placement-drives", PlacementDriveViewSet, "placement-drive"),
    ("applications", ApplicationViewSet, "application"),
    ("results", ResultViewSet, "result"),
    ("placement-history", PlacementHistoryViewSet, "placement-history"),
    ("study-materials", StudyMaterialViewSet, "study-material"),
    ("announcements", AnnouncementViewSet, "announcement"),
    ("gallery", GalleryViewSet, "gallery"),
    ("recruiter/search", RecruiterSearchViewSet, "recruiter-search"),
]:
    router.register(prefix, view, basename=name)

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/", AuthTokenView.as_view(), name="api-token"),
    path("auth/logout/", LogoutView.as_view({"post": "create"}), name="api-logout"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
