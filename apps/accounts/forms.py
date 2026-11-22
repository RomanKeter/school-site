from django import forms

from .models import AVATARS


class ChildLoginNameForm(forms.Form):
    login = forms.CharField(label="Твой логин", max_length=40)


class ChildCreateForm(forms.Form):
    display_name = forms.CharField(label="Имя или прозвище (без фамилии)", max_length=20)
    login = forms.SlugField(label="Короткий логин (латиницей)", max_length=30)
    avatar_code = forms.ChoiceField(label="Аватар", choices=[(c, f"{e} {n}") for c, e, n in AVATARS])
    grade = forms.IntegerField(label="Класс", initial=5, min_value=1, max_value=11)
    picture_password = forms.CharField(
        label="Картинный пароль",
        help_text="4 картинки по порядку, через запятую, например: apple,cat,star,ball",
    )

    def clean_picture_password(self):
        from .pictures import PICTURE_CODES

        seq = [s.strip() for s in self.cleaned_data["picture_password"].split(",") if s.strip()]
        if len(seq) != 4 or any(s not in PICTURE_CODES for s in seq):
            raise forms.ValidationError("Нужно ровно 4 картинки из набора: " + ", ".join(sorted(PICTURE_CODES)))
        return seq
