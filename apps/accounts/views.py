from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ChildLoginNameForm
from .models import ChildProfile, User
from .pictures import PICTURES
from .utils import get_child, get_parent, trusted_family_id


def root(request):
    if get_child(request):
        return redirect("home")
    if get_parent(request):
        return redirect("parent_dashboard")
    return redirect("child_start")


def child_start(request):
    """Э1: «Кто сегодня учится?» — аватарки на доверенном устройстве, иначе ввод логина."""
    family_id = trusted_family_id(request)
    if family_id:
        children = ChildProfile.objects.filter(family_id=family_id).order_by("id")
        return render(request, "accounts/child_pick.html", {"children": children})
    form = ChildLoginNameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.filter(username=form.cleaned_data["login"].strip().lower(), role="child").first()
        if user and hasattr(user, "child_profile"):
            request.session["pending_child"] = user.child_profile.pk
            return redirect("child_pictures", child_id=user.child_profile.pk)
        form.add_error("login", "Такого логина нет. Спроси у взрослого.")
    return render(request, "accounts/child_login_name.html", {"form": form})


def _lock_key(child_id):
    return f"child-login-fails:{child_id}"


def child_pictures(request, child_id):
    family_id = trusted_family_id(request)
    qs = ChildProfile.objects.all()
    if family_id:
        qs = qs.filter(family_id=family_id)
    elif request.session.get("pending_child") != child_id:
        return redirect("child_start")
    child = get_object_or_404(qs, pk=child_id)

    fails = cache.get(_lock_key(child.pk), 0)
    locked = fails >= settings.CHILD_LOGIN_MAX_FAILS
    retry = False
    if request.method == "POST" and not locked:
        seq = [s for s in request.POST.get("sequence", "").split(",") if s]
        if child.check_picture_password(seq):
            cache.delete(_lock_key(child.pk))
            login(request, child.user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.set_expiry(settings.CHILD_SESSION_SECONDS)
            return redirect("home")
        fails += 1
        cache.set(_lock_key(child.pk), fails, settings.CHILD_LOGIN_LOCK_SECONDS)
        locked = fails >= settings.CHILD_LOGIN_MAX_FAILS
        retry = True
    return render(
        request,
        "accounts/child_pictures.html",
        {"child": child, "pictures": PICTURES, "locked": locked, "retry": retry},
    )


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
