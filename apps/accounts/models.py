import datetime as dt

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models

from .pictures import PICTURE_CODES


class User(AbstractUser):
    ROLE_CHOICES = [
        ("parent", "Родитель"),
        ("child", "Ребёнок"),
        ("admin", "Администратор"),
        ("editor", "Редактор контента"),
    ]
    role = models.CharField("роль", max_length=10, choices=ROLE_CHOICES, default="parent")

    @property
    def is_child(self):
        return self.role == "child"

    @property
    def is_parent(self):
        return self.role in ("parent", "admin") and hasattr(self, "parent_profile")


class Family(models.Model):
    name = models.CharField("название", max_length=100)
    timezone = models.CharField(max_length=50, default="Europe/Minsk")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "семья"
        verbose_name_plural = "семьи"

    def __str__(self):
        return self.name


class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="parent_profile")
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="parents")
    telegram_chat_id = models.CharField(max_length=40, blank=True)  # этап 2
    weekly_report_format = models.CharField(
        "формат недельного отчёта",
        max_length=8,
        choices=[("text", "текст"), ("image", "картинка"), ("both", "текст и картинка")],
        default="image",
    )

    class Meta:
        verbose_name = "профиль родителя"
        verbose_name_plural = "профили родителей"

    def __str__(self):
        return f"{self.user.username} ({self.family})"


AVATARS = [
    ("fox", "🦊", "Лиса"),
    ("owl", "🦉", "Сова"),
    ("cat", "🐱", "Котик"),
    ("hare", "🐰", "Зайка"),
    ("bear", "🐻", "Мишка"),
    ("stork", "🕊️", "Бусел"),
]
AVATAR_EMOJI = {c: e for c, e, _ in AVATARS}


class ChildProfile(models.Model):
    """FR-AUTH-6: только имя/прозвище и класс. Фамилия, фото, дата рождения НЕ хранятся."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="child_profile")
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="children")
    display_name = models.CharField("имя или прозвище", max_length=20)
    grade = models.PositiveSmallIntegerField("класс", default=5)
    avatar_code = models.CharField("аватар", max_length=20, default="fox", choices=[(c, f"{e} {n}") for c, e, n in AVATARS])
    picture_password_hash = models.CharField(max_length=256, blank=True)
    font_scale = models.FloatField(default=1.0, choices=[(1.0, "обычный"), (1.15, "крупный"), (1.3, "очень крупный")])
    sound_on = models.BooleanField(default=True)
    reduce_motion = models.BooleanField(default=False)

    class Meta:
        verbose_name = "профиль ребёнка"
        verbose_name_plural = "профили детей"

    def __str__(self):
        return self.display_name

    @property
    def avatar(self):
        return AVATAR_EMOJI.get(self.avatar_code, "🦊")

    @staticmethod
    def _seq(seq):
        seq = list(seq)
        if len(seq) != 4 or any(s not in PICTURE_CODES for s in seq):
            raise ValueError("Картинный пароль — ровно 4 картинки из набора")
        return "-".join(seq)

    def set_picture_password(self, seq):
        self.picture_password_hash = make_password(self._seq(seq))

    def check_picture_password(self, seq):
        try:
            raw = self._seq(seq)
        except ValueError:
            return False
        return bool(self.picture_password_hash) and check_password(raw, self.picture_password_hash)


class ChildSettings(models.Model):
    """Меняет только родитель (FR-PAR-3)."""

    child = models.OneToOneField(ChildProfile, on_delete=models.CASCADE, related_name="settings")
    daily_limit_min = models.PositiveSmallIntegerField(
        "дневной лимит, мин", default=30, choices=[(15, "15"), (20, "20"), (30, "30"), (45, "45")]
    )
    break_every_min = models.PositiveSmallIntegerField("перерыв каждые, мин", default=15)
    quiet_from = models.TimeField("тихие часы с", default=dt.time(20, 30))
    quiet_to = models.TimeField("тихие часы до", default=dt.time(7, 30))
    days_off = models.JSONField("дни без миссии (0=Пн … 6=Вс)", default=list, blank=True)
    srs_daily_limit = models.PositiveSmallIntegerField("повторений в миссии", default=15)
    en_variant = models.CharField("вариант английского", max_length=2, default="gb", choices=[("gb", "британский"), ("us", "американский")])
    show_transcription = models.BooleanField("показывать транскрипцию", default=True)
    rest_mode_until = models.DateField("режим отдыха до", null=True, blank=True)
    extra_minutes_date = models.DateField(null=True, blank=True)
    extra_minutes = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "настройки ребёнка"
        verbose_name_plural = "настройки детей"

    def limit_for(self, day):
        extra = self.extra_minutes if self.extra_minutes_date == day else 0
        return self.daily_limit_min + extra
