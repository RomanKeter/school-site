# Сетка картинного пароля 3×3 (FR-AUTH-2). Порядок фиксирован (чтобы ребёнок запоминал положение).
PICTURES = [
    ("apple", "🍎", "яблоко"),
    ("cat", "🐱", "кот"),
    ("star", "⭐", "звезда"),
    ("ball", "⚽", "мяч"),
    ("moon", "🌙", "луна"),
    ("bike", "🚲", "велосипед"),
    ("flower", "🌸", "цветок"),
    ("balloon", "🎈", "шарик"),
    ("fish", "🐟", "рыбка"),
]
PICTURE_CODES = {c for c, _, _ in PICTURES}
PICTURE_EMOJI = {c: e for c, e, _ in PICTURES}
