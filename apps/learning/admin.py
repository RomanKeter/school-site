from django.contrib import admin

from .models import Attempt, Block, DiagnosticResult, SkillMastery

admin.site.register(Attempt)
admin.site.register(SkillMastery)
admin.site.register(Block)
admin.site.register(DiagnosticResult)
