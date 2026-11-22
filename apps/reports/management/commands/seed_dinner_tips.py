from django.core.management.base import BaseCommand

from apps.content.models import Skill, Subject
from apps.reports.models import DinnerTip

TIPS = {
    "math": [
        "Спросите: как поделить пиццу на 8 человек поровну, если её уже разрезали на 4 части?",
        "Вспомните вместе: где дома можно найти прямой угол?",
        "Попросите объяснить, как понять, что число делится на 3, на примере номеров домов на вашей улице.",
    ],
    "en": [
        "Попросите научить вас 3 английским словам про еду, которые она выучила.",
        "Составьте вместе короткую фразу с have got про что-то из вашей кухни.",
    ],
    "ru": [
        "Вспомните вместе слово с -тся или -ться и придумайте к нему своё предложение.",
        "Попросите найти в любой фразе за ужином обращение — и поставить мысленно запятые.",
    ],
}

SKILL_TIPS = {
    "math.fr.add": "Спросите: как поделить пиццу на 8 человек поровну, если её уже разрезали на 4 части?",
    "math.fr.compare": "Спросите, какая доля пирога больше: половина или две четверти — и почему они равны.",
    "en.gr.have_got": "Попросите научить вас фразе с have got про что-то, что есть на столе.",
    "ru.or.tsya": "Вспомните вместе слово с -тся или -ться и придумайте к нему своё предложение.",
}


class Command(BaseCommand):
    help = "Банк советов за ужином и подписи у нескольких навыков"

    def handle(self, *args, **opts):
        created = 0
        for code, texts in TIPS.items():
            subj = Subject.objects.filter(code=code).first()
            if not subj:
                continue
            for text in texts:
                _, is_new = DinnerTip.objects.get_or_create(subject=subj, text=text, defaults={"is_active": True})
                created += int(is_new)
        updated = 0
        for key, text in SKILL_TIPS.items():
            n = Skill.objects.filter(external_key=key, dinner_tip="").update(dinner_tip=text)
            updated += n
        self.stdout.write(f"советов создано {created}, навыков с советом {updated}")
