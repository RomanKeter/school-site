from django.db import models

STATUS = [("draft", "черновик"), ("review", "на проверке"), ("published", "опубликовано"), ("archived", "в архиве")]


class ContentBase(models.Model):
    external_key = models.CharField("ключ импорта", max_length=120, unique=True)
    status = models.CharField("статус", max_length=10, choices=STATUS, default="published")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Subject(models.Model):
    code = models.CharField(max_length=10, unique=True)  # math, en, ru, by, hist, bio
    title = models.CharField(max_length=60)
    color_token = models.CharField(max_length=20, default="math")
    icon = models.CharField(max_length=8, default="🔢")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "предмет"
        verbose_name_plural = "предметы"

    def __str__(self):
        return self.title


class Unit(ContentBase):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="units")
    title = models.CharField(max_length=200)
    grade = models.PositiveSmallIntegerField(default=5)
    quarter = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["subject", "order"]
        verbose_name = "раздел"
        verbose_name_plural = "разделы"

    def __str__(self):
        return f"{self.subject}: {self.title}"


class Topic(ContentBase):
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="topics")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    synonyms = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    textbook_refs = models.JSONField(default=list, blank=True)
    badge_code = models.CharField("значок за освоение темы", max_length=40, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["unit__order", "order"]
        verbose_name = "тема"
        verbose_name_plural = "темы"

    def __str__(self):
        return self.title


class Skill(ContentBase):
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name="skills")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    rule_card = models.TextField("карточка правила", blank=True)
    worked_example = models.JSONField(
        "разобранный пример", default=dict, blank=True,
        help_text='{"title": "...", "steps": ["шаг 1", "шаг 2", ...], "model": {...}}',
    )
    prerequisites = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="unlocks")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["topic__unit__order", "topic__order", "order"]
        verbose_name = "навык"
        verbose_name_plural = "навыки"

    def __str__(self):
        return self.title

    @property
    def subject(self):
        return self.topic.unit.subject


EXERCISE_TYPES = [
    ("single_choice", "Выбор одного варианта"),
    ("fill_blank_choice", "Пропуск с выбором"),
    ("number_input", "Ввод числа"),
    ("equation", "Уравнение"),
    ("fraction_input", "Ввод дроби"),
    ("text_input", "Ввод слова"),
    ("matching", "Соедини пары"),
    ("drag_order", "Упорядочить"),
    ("categorize", "Разложи по корзинам"),
    ("letter_tiles", "Собери слово"),
    ("fill_letters", "Вставь букву"),
    ("punctuation", "Поставь запятые"),
    ("morphemes", "Разбор по составу"),
    ("dictation", "Диктант"),
    ("step_by_step", "Задача по шагам"),
    ("audio_text_choice", "Послушай и выбери слово"),
    ("flashcard", "Карточка-знакомство"),
]


class Exercise(ContentBase):
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="exercises")
    type = models.CharField(max_length=30, choices=EXERCISE_TYPES)
    difficulty = models.PositiveSmallIntegerField(default=1, choices=[(1, "лёгкое"), (2, "среднее"), (3, "сложное")])
    payload = models.JSONField(default=dict)
    # Ответ хранится отдельно от payload и никогда не уходит в шаблон до ответа ребёнка (FR-LRN-2)
    answer = models.JSONField(default=dict)
    est_seconds = models.PositiveSmallIntegerField(default=40)
    is_template = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["skill", "difficulty", "id"]
        verbose_name = "задание"
        verbose_name_plural = "задания"

    def __str__(self):
        return f"[{self.type}] {self.payload.get('prompt', '')[:60]}"


class VocabularyWord(ContentBase):
    language = models.CharField(max_length=2, default="en")
    word = models.CharField(max_length=80)
    translation_ru = models.CharField(max_length=120)
    transcription = models.CharField(max_length=80, blank=True)
    part_of_speech = models.CharField(max_length=20, blank=True)
    example = models.CharField(max_length=200, blank=True)
    example_translation = models.CharField(max_length=200, blank=True)
    # MVP: картинка-заглушка — эмодзи. В этапе 2 заменяется на SVG-иллюстрации (MediaAsset).
    picture = models.CharField("картинка (эмодзи-заглушка)", max_length=16, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name="words")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("language", "word", "translation_ru")]
        verbose_name = "слово"
        verbose_name_plural = "словарь"

    def __str__(self):
        return f"{self.word} — {self.translation_ru}"
