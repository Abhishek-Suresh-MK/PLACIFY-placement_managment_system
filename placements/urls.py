from django.urls import path
from accounts.views import PlacifyLoginView
from . import views

app_name = "placements"

urlpatterns = [
    path("", PlacifyLoginView.as_view(), name="index"),
    path("history/", views.history, name="history"),
    path("materials/", views.materials, name="materials"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_edit, name="profile"),
    path("drives/", views.drive_list, name="drives"),
    path("drives/<int:pk>/", views.drive_detail, name="drive_detail"),
    path("drives/<int:pk>/apply/", views.apply_drive, name="apply_drive"),
    path("applications/", views.applications, name="applications"),
    path("applications/<int:pk>/withdraw/", views.withdraw_application, name="withdraw_application"),
    path("recruiters/", views.recruiter_dashboard, name="recruiter_dashboard"),
    path("recruiters/applications/<int:pk>/candidate/", views.recruiter_candidate, name="recruiter_candidate"),
    path("recruiters/applications/<int:pk>/status/", views.recruiter_update_application, name="recruiter_update_application"),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/students/", views.admin_student_list, name="admin_list"),
    path("admin-panel/students/<int:pk>/edit/", views.admin_student_edit, name="admin_edit"),
    path("admin-panel/students/<int:pk>/delete/", views.admin_student_delete, name="admin_delete"),
    path("admin-panel/applications/", views.admin_application_list, name="admin_applications"),
    path("admin-panel/applications/<int:application_id>/status/", views.admin_application_update, name="admin_application_update"),
    path("admin-panel/applications/<int:application_id>/result/", views.admin_result_update, name="admin_result_update"),
    path("admin-panel/<str:resource>/", views.admin_resource, name="admin_resource"),
    path("admin-panel/<str:resource>/<int:pk>/delete/", views.admin_delete_resource, name="admin_delete_resource"),
]
