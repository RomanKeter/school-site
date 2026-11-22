from django.db import transaction

from .models import ChildProfile, ChildSettings, Family, ParentProfile, User


@transaction.atomic
def create_parent(username, password, email="", family_name=None):
    user = User.objects.create_user(username=username, password=password, email=email, role="parent")
    family = Family.objects.create(name=family_name or f"Семья {username}")
    ParentProfile.objects.create(user=user, family=family)
    return user.parent_profile


@transaction.atomic
def create_child(family, login, display_name, picture_seq, avatar_code="fox", grade=5):
    user = User.objects.create_user(username=login.lower(), role="child")
    user.set_unusable_password()
    user.save()
    child = ChildProfile(user=user, family=family, display_name=display_name, avatar_code=avatar_code, grade=grade)
    child.set_picture_password(picture_seq)
    child.save()
    ChildSettings.objects.create(child=child)
    return child
