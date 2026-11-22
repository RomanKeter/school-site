from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import ChildProfile
from .utils import get_child, get_parent, trusted_family_id


def root(request):
    if get_child(request):
        return redirect("home")
    if get_parent(request):
        return redirect("parent_dashboard")
    return redirect("child_start")


def child_start(request):
    """Э1: «Кто сегодня учится?» — аватарки только на доверенном устройстве."""
    family_id = trusted_family_id(request)
    if family_id:
        children = ChildProfile.objects.filter(family_id=family_id).order_by("id")
        return render(request, "accounts/child_pick.html", {"children": children})
    return render(request, "accounts/child_login_name.html")


def child_pictures(request, child_id):
    """Вход ребёнка: на доверенном устройстве достаточно нажать аватарку (D-1100)."""
    family_id = trusted_family_id(request)
    if not family_id:
        return redirect("child_start")
    child = get_object_or_404(ChildProfile.objects.filter(family_id=family_id), pk=child_id)
    login(request, child.user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.set_expiry(settings.CHILD_SESSION_SECONDS)
    return redirect("home")


class ParentLoginView(LoginView):
    template_name = "accounts/parent_login.html"

    def form_valid(self, form):
        user = form.get_user()
        if user.role == "child":
            form.add_error(None, "Это вход для взрослых.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if not self.request.POST.get("remember"):
            self.request.session.set_expiry(0)
        return response

    def get_success_url(self):
        return self.get_redirect_url() or "/parent/"


@require_POST
def do_logout(request):
    was_child = get_child(request) is not None
    logout(request)
    if not was_child:
        messages.info(request, "Вы вышли из кабинета.")
    return redirect("child_start")
