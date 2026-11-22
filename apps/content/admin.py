from django.contrib import admin

from .models import Exercise, Skill, Subject, Topic, Unit, VocabularyWord


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "order")


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    fields = ("external_key", "title", "order", "status")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "grade", "quarter", "status")
    list_filter = ("subject", "grade")
    inlines = [TopicInline]


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0
    fields = ("external_key", "title", "order", "status")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "badge_code", "status")
    inlines = [SkillInline]


class ExerciseInline(admin.StackedInline):
    model = Exercise
    extra = 0
    fields = ("external_key", "type", "difficulty", "est_seconds", "payload", "answer", "status")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "order", "status")
    search_fields = ("title", "external_key")
    filter_horizontal = ("prerequisites",)
    inlines = [ExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("external_key", "type", "skill", "difficulty", "status")
    list_filter = ("type", "difficulty", "status")
    search_fields = ("external_key", "payload")


@admin.register(VocabularyWord)
class WordAdmin(admin.ModelAdmin):
    list_display = ("word", "translation_ru", "topic", "order", "status")
    list_filter = ("language", "topic")
    search_fields = ("word", "translation_ru")
