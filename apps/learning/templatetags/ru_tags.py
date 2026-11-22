"""Фильтры для заданий по русскому языку (D-208)."""
from django import template

from apps.learning.ru_types import say_b64

register = template.Library()


@register.filter(name="say_b64")
def say_b64_filter(text):
    return say_b64(text)
