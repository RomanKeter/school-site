from django import template

from apps.ai.limits import settings_for

register = template.Library()


@register.simple_tag(takes_context=True)
def ai_settings(context):
    child = context.get("current_child")
    return settings_for(child) if child else None
