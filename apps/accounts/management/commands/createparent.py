import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services import create_parent


class Command(BaseCommand):
    help = "Создать родителя и его семью: createparent <логин> [--email] [--password]"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--email", default="")
        parser.add_argument("--password")
        parser.add_argument("--family", default=None)

    def handle(self, username, email, password, family, **kw):
        password = password or getpass.getpass("Пароль (минимум 10 символов): ")
        if len(password) < 10:
            raise CommandError("Пароль должен быть не короче 10 символов")
        p = create_parent(username, password, email, family)
        self.stdout.write(self.style.SUCCESS(f"Создан родитель {username}, семья «{p.family.name}»"))
