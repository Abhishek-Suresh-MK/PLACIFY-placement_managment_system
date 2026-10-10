from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy

from placements.models import Announcement, AnnouncementStatus, Gallery, StudentProfile
from .forms import RegistrationForm
from .models import Role, User


class PlacifyLoginView(LoginView):
    template_name = "placements/index.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["announcements"] = Announcement.objects.filter(status=AnnouncementStatus.PUBLISHED)[:5]
        context["gallery"] = Gallery.objects.filter(is_published=True).select_related("company")
        context["just_registered"] = self.request.GET.get("registered") == "1"
        return context

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.role == Role.ADMIN:
            return reverse("placements:admin_dashboard")
        if user.role == Role.RECRUITER:
            return reverse("placements:recruiter_dashboard")
        return reverse("placements:dashboard")


class PlacifyLogoutView(LogoutView):
    next_page = reverse_lazy("placements:index")


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            with transaction.atomic():
                user = User.objects.create_user(
                    email=data["email"], password=data["password"], name=data["name"], role=Role.STUDENT
                )
                profile = StudentProfile.objects.create(
                    user=user,
                    phone=data["phone"], photo=data.get("photo"), college=data["college"],
                    university_no=data["university_no"], address=data["address"], age=data["age"],
                    department=data["department"], current_year=int(data["current_year"]),
                    cgpa=data["cgpa"], backlogs=data["backlogs"], passout_year=data["passout_year"],
                    resume=data.get("resume"),
                )
                profile.skills.set(data.get("skills", []))
            messages.success(request, "Registration successful! Please sign in with your email.")
            return redirect(reverse("placements:index") + "?registered=1")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})
