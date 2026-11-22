"""Полная программа английского 5 кл. РБ (учебник Лапицкой 2020 + программа 29.07.2025 № 134).

Запуск: python content_samples/build_en_program.py
Пишет content_samples/en_program.json (несколько юнитов в одном файле, format_version 1).
Существующие ключи en.g5.u1 / слова / en.gr.hg.ex1–ex5 не переопределяются — только дополнение.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "en_program.json"


def H(*texts):
    return [{"level": i + 1, "text": t} for i, t in enumerate(texts)]


def ch(key, prompt, options, correct, hints, diff=1, typ="fill_blank_choice", explain=None, est=30):
    payload = {
        "prompt": prompt,
        "options": [{"id": chr(97 + i), "text": o} for i, o in enumerate(options)],
        "hints": H(*hints),
    }
    if explain:
        payload["explain"] = explain
    return {
        "key": key, "type": typ, "difficulty": diff, "est_seconds": est,
        "payload": payload,
        "answer": {"correct": [chr(97 + options.index(correct))]},
    }


def sc(key, prompt, options, correct, hints, diff=1, explain=None):
    return ch(key, prompt, options, correct, hints, diff=diff, typ="single_choice", explain=explain)


def audio(key, text, options, correct, hints, diff=1):
    payload = {
        "prompt": "Послушай и выбери, что прозвучало. Listen (послушай) and choose.",
        "audio_text": text,
        "options": [{"id": chr(97 + i), "text": o} for i, o in enumerate(options)],
        "hints": H(*hints),
    }
    return {
        "key": key, "type": "audio_text_choice", "difficulty": diff, "est_seconds": 25,
        "payload": payload,
        "answer": {"correct": [chr(97 + options.index(correct))]},
    }


def txt(key, prompt, value, hints, diff=2, accept=None, explain=None):
    payload = {"prompt": prompt, "hints": H(*hints)}
    if explain:
        payload["explain"] = explain
    ans = {"value": value}
    if accept:
        ans["accept"] = accept
    return {"key": key, "type": "text_input", "difficulty": diff, "est_seconds": 35, "payload": payload, "answer": ans}


def tiles(key, prompt, word, hints, extra="xyz", diff=2):
    letters = list(word) + list(extra)
    return {
        "key": key, "type": "letter_tiles", "difficulty": diff, "est_seconds": 35,
        "payload": {"prompt": prompt, "letters": letters, "hints": H(*hints)},
        "answer": {"value": word},
    }


def match(key, prompt, pairs, hints, diff=1):
    return {
        "key": key, "type": "matching", "difficulty": diff, "est_seconds": 60,
        "payload": {
            "prompt": prompt,
            "left": [{"id": f"l{i}", "text": a} for i, (a, b) in enumerate(pairs)],
            "right": [{"id": f"r{i}", "text": b} for i, (a, b) in enumerate(pairs)],
            "hints": H(*hints),
        },
        "answer": {"pairs": {f"l{i}": f"r{i}" for i in range(len(pairs))}},
    }


def cat(key, prompt, buckets, items, answer, hints, diff=2):
    return {
        "key": key, "type": "categorize", "difficulty": diff, "est_seconds": 60,
        "payload": {
            "prompt": prompt,
            "buckets": [{"id": b, "title": t} for b, t in buckets],
            "items": [{"id": i, "text": t} for i, t in items],
            "hints": H(*hints),
        },
        "answer": {"buckets": {b: list(v) for b, v in answer.items()}},
    }


def order(key, prompt, items, correct, hints, diff=2):
    return {
        "key": key, "type": "drag_order", "difficulty": diff, "est_seconds": 50,
        "payload": {
            "prompt": prompt,
            "items": [{"id": i, "text": t} for i, t in items],
            "hints": H(*hints),
        },
        "answer": {"order": correct},
    }


def w(key, word, ru, ipa, pic, example, ex_ru, order):
    return {
        "key": key, "word": word, "translation_ru": ru, "transcription": ipa,
        "picture": pic, "example": example, "example_translation": ex_ru, "order": order,
    }


def skill(key, title, rule, example_title, steps, exercises, order=0, prerequisites=None):
    s = {
        "key": key, "title": title, "order": order,
        "rule_card": rule,
        "worked_example": {"title": example_title, "steps": steps},
        "exercises": exercises,
    }
    if prerequisites:
        s["prerequisites"] = prerequisites
    return s


# ---------------------------------------------------------------------------
# Vocabulary per textbook unit (skip words already in en_words.json)
# ---------------------------------------------------------------------------
def vocab_u1():
    rows = [
        ("holidays", "каникулы", "/ˈhɒl.ɪ.deɪz/", "🏖️", "Our school holidays are in June.", "Наши школьные каникулы в июне."),
        ("country", "деревня, сельская местность", "/ˈkʌn.tri/", "🌾", "I was in the country with my grandad.", "Я был в деревне с дедушкой."),
        ("town", "город (небольшой)", "/taʊn/", "🏘️", "My parents and I were in town.", "Мы с родителями были в городе."),
        ("seaside", "морское побережье", "/ˈsiː.saɪd/", "🌊", "I was at the seaside in August.", "Я был на море в августе."),
        ("camp", "лагерь", "/kæmp/", "🏕️", "My friend was at summer camp.", "Мой друг был в летнем лагере."),
        ("mountains", "горы", "/ˈmaʊn.tɪnz/", "⛰️", "We were in the mountains last summer.", "Прошлым летом мы были в горах."),
        ("abroad", "за границей", "/əˈbrɔːd/", "✈️", "Mrs Read was abroad with her pupils.", "Миссис Рид была за границей со своими учениками."),
        ("June", "июнь", "/dʒuːn/", "📅", "In June I was at home.", "В июне я был дома."),
        ("July", "июль", "/dʒʊˈlaɪ/", "📅", "It was July, it was a summer day.", "Был июль, был летний день."),
        ("August", "август", "/ˈɔː.ɡəst/", "📅", "We were at the seaside in August.", "В августе мы были на море."),
        ("weather", "погода", "/ˈweð.ə/", "🌤️", "What was the weather like?", "Какая была погода?"),
        ("sunny", "солнечный", "/ˈsʌn.i/", "☀️", "The weather was sunny.", "Погода была солнечная."),
        ("hot", "жаркий", "/hɒt/", "🌡️", "It was hot and sunny.", "Было жарко и солнечно."),
        ("rainy", "дождливый", "/ˈreɪ.ni/", "🌧️", "It was rainy in July.", "В июле было дождливо."),
        ("yesterday", "вчера", "/ˈjes.tə.deɪ/", "⏪", "I was at the zoo yesterday.", "Вчера я был в зоопарке."),
        ("zoo", "зоопарк", "/zuː/", "🦁", "Mike was at the zoo yesterday.", "Майк вчера был в зоопарке."),
        ("circus", "цирк", "/ˈsɜː.kəs/", "🎪", "Nikita was at the circus.", "Никита был в цирке."),
        ("park", "парк", "/pɑːk/", "🌳", "They were in the park.", "Они были в парке."),
        ("visit", "посещать, навещать", "/ˈvɪz.ɪt/", "🚶", "I visited my granny.", "Я навестил бабушку."),
        ("swim", "плавать", "/swɪm/", "🏊", "We swam in the sea.", "Мы плавали в море."),
        ("fun", "веселье, забава", "/fʌn/", "🎉", "We had a lot of fun.", "Нам было очень весело."),
        ("last summer", "прошлым летом", "/lɑːst ˈsʌm.ə/", "🌻", "I went to the park last summer.", "Прошлым летом я ходил в парк."),
    ]
    return [w(f"en.u1.{i+1}.{r[0].replace(' ', '_')}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u2():
    rows = [
        ("nature", "природа", "/ˈneɪ.tʃə/", "🌿", "Go to the country and enjoy nature.", "Поезжай в деревню и наслаждайся природой."),
        ("museum", "музей", "/mjuːˈziː.əm/", "🏛️", "We went to the history museum.", "Мы ходили в исторический музей."),
        ("library", "библиотека", "/ˈlaɪ.brər.i/", "📚", "Mike took Elfin to the library.", "Майк повёл Элфина в библиотеку."),
        ("cinema", "кинотеатр", "/ˈsɪn.ə.mə/", "🎬", "Let's go to the cinema.", "Давай пойдём в кинотеатр."),
        ("film", "фильм", "/fɪlm/", "🎥", "We watched a good film.", "Мы посмотрели хороший фильм."),
        ("amusement park", "парк развлечений", "/əˈmjuːz.mənt pɑːk/", "🎢", "We had fun at the amusement park.", "Нам было весело в парке развлечений."),
        ("trip", "экскурсия, поездка", "/trɪp/", "🚌", "We went on a school trip.", "Мы ездили на школьную экскурсию."),
        ("history", "история", "/ˈhɪs.tər.i/", "📜", "I like history museums.", "Я люблю исторические музеи."),
        ("the past", "прошлое", "/ðə pɑːst/", "⏳", "We learnt about the past.", "Мы узнали о прошлом."),
        ("enjoy", "наслаждаться", "/ɪnˈdʒɔɪ/", "😊", "I enjoy reading books.", "Я люблю читать книги."),
        ("cave", "пещера", "/keɪv/", "🕳️", "The woman made a fire in the cave.", "Женщина развела костёр в пещере."),
        ("fire", "огонь, костёр", "/faɪə/", "🔥", "They made a fire because it was cold.", "Они развели костёр, потому что было холодно."),
        ("walk", "гулять, ходить пешком", "/wɔːk/", "🚶", "We walked in the forest.", "Мы гуляли в лесу."),
        ("forest", "лес", "/ˈfɒr.ɪst/", "🌲", "There are lots of trees in the forest.", "В лесу много деревьев."),
        ("photo", "фотография", "/ˈfəʊ.təʊ/", "📷", "Look at my summer photos.", "Посмотри на мои летние фотографии."),
        ("remember", "помнить, вспоминать", "/rɪˈmem.bə/", "💭", "I remember my summer.", "Я вспоминаю своё лето."),
        ("interesting", "интересный", "/ˈɪn.trə.stɪŋ/", "✨", "The museum was interesting.", "Музей был интересный."),
        ("best", "лучший, самый хороший", "/best/", "🏆", "It was the best thing I did.", "Это было лучшее, что я сделал."),
    ]
    return [w(f"en.u2.{i+1}.{r[0].replace(' ', '_')}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u3():
    rows = [
        ("programme", "передача, программа", "/ˈprəʊ.ɡræm/", "📺", "What's on TV? My favourite programme.", "Что по телевизору? Моя любимая передача."),
        ("comedy", "комедия", "/ˈkɒm.ə.di/", "😂", "I love comedies. I love them.", "Я обожаю комедии. Я их обожаю."),
        ("cartoon", "мультфильм", "/kɑːˈtuːn/", "🧸", "Children often watch cartoons.", "Дети часто смотрят мультфильмы."),
        ("news", "новости", "/njuːz/", "📰", "I always watch the news.", "Я всегда смотрю новости."),
        ("quiz show", "викторина", "/kwɪz ʃəʊ/", "❓", "I often watch quiz shows.", "Я часто смотрю викторины."),
        ("horror film", "фильм ужасов", "/ˈhɒr.ə fɪlm/", "👻", "I never watch horror films.", "Я никогда не смотрю фильмы ужасов."),
        ("channel", "канал", "/ˈtʃæn.əl/", "📡", "What channel is the cartoon on?", "По какому каналу мультфильм?"),
        ("always", "всегда", "/ˈɔːl.weɪz/", "♾️", "I always watch the news.", "Я всегда смотрю новости."),
        ("often", "часто", "/ˈɒf.ən/", "🔁", "I often watch nature programmes.", "Я часто смотрю передачи о природе."),
        ("sometimes", "иногда", "/ˈsʌm.taɪmz/", "〰️", "I sometimes watch comedies.", "Иногда я смотрю комедии."),
        ("rarely", "редко", "/ˈreə.li/", "🌙", "I rarely watch cartoons.", "Я редко смотрю мультфильмы."),
        ("never", "никогда", "/ˈnev.ə/", "🚫", "I never watch horror films.", "Я никогда не смотрю фильмы ужасов."),
        ("o'clock", "час ровно", "/əˈklɒk/", "🕐", "It's five o'clock.", "Сейчас пять часов."),
        ("half past", "половина (время)", "/hɑːf pɑːst/", "🕧", "It's half past five.", "Сейчас половина шестого."),
        ("quarter past", "четверть после", "/ˈkwɔː.tə pɑːst/", "🕒", "It's quarter past three.", "Сейчас четверть четвёртого."),
        ("quarter to", "без четверти", "/ˈkwɔː.tə tuː/", "🕤", "It's quarter to two.", "Сейчас без четверти два."),
        ("silly", "глупый, дурацкий", "/ˈsɪl.i/", "🤪", "Some comedies are silly.", "Некоторые комедии глупые."),
        ("reporter", "репортёр", "/rɪˈpɔː.tə/", "🎤", "The reporter asked them some questions.", "Репортёр задал им несколько вопросов."),
        ("watch", "смотреть, часы", "/wɒtʃ/", "👀", "Do you watch nature programmes?", "Ты смотришь передачи о природе?"),
        ("favourite", "любимый", "/ˈfeɪ.vər.ɪt/", "❤️", "What's your favourite film?", "Какой твой любимый фильм?"),
    ]
    return [w(f"en.u3.{i+1}.{r[0].replace(' ', '_').replace(chr(39), '')}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u4():
    rows = [
        ("special day", "особый день, праздник", "/ˈspeʃ.əl deɪ/", "🎀", "This is a special day for me.", "Это особый день для меня."),
        ("celebrate", "праздновать", "/ˈsel.ə.breɪt/", "🎊", "How do you celebrate holidays?", "Как вы празднуете праздники?"),
        ("Christmas", "Рождество", "/ˈkrɪs.məs/", "🎄", "We celebrate Christmas in December.", "Мы празднуем Рождество в декабре."),
        ("New Year", "Новый год", "/njuː jɪə/", "🎆", "Happy New Year!", "С Новым годом!"),
        ("present", "подарок", "/ˈprez.ənt/", "🎁", "I got a present from my parents.", "Я получил подарок от родителей."),
        ("card", "открытка", "/kɑːd/", "💌", "They give me presents and cards.", "Они дарят мне подарки и открытки."),
        ("decorate", "украшать", "/ˈdek.ə.reɪt/", "🎀", "We decorate the Christmas tree.", "Мы украшаем ёлку."),
        ("Christmas tree", "новогодняя ёлка", "/ˈkrɪs.məs triː/", "🎄", "Decorate the Christmas tree and the room.", "Укрась ёлку и комнату."),
        ("Santa", "Санта-Клаус", "/ˈsæn.tə/", "🎅", "Santa has got presents in his bag.", "У Санты в мешке подарки."),
        ("cracker", "хлопушка", "/ˈkræk.ə/", "🧨", "There were ten crackers in the bag.", "В мешке было десять хлопушек."),
        ("invitation", "приглашение", "/ˌɪn.vɪˈteɪ.ʃən/", "✉️", "I write an invitation to my friends.", "Я пишу приглашение друзьям."),
        ("relative", "родственник", "/ˈrel.ə.tɪv/", "👨‍👩‍👧‍👦", "I invite my relatives to the party.", "Я приглашаю родственников на праздник."),
        ("wish", "желать, пожелание", "/wɪʃ/", "🌟", "They wish me happiness.", "Они желают мне счастья."),
        ("party", "праздник, вечеринка", "/ˈpɑː.ti/", "🎈", "We went to the Christmas party.", "Мы ходили на рождественский праздник."),
        ("candle", "свеча", "/ˈkæn.dəl/", "🕯️", "There are candles on the cake.", "На торте свечи."),
        ("Merry Christmas", "С Рождеством", "/ˈmer.i ˈkrɪs.məs/", "🎄", "Merry Christmas to all our friends!", "С Рождеством всех наших друзей!"),
        ("happiness", "счастье", "/ˈhæp.ɪ.nəs/", "😊", "I wish you happiness.", "Я желаю тебе счастья."),
        ("December", "декабрь", "/dɪˈsem.bə/", "📅", "Christmas is in December.", "Рождество бывает в декабре."),
    ]
    return [w(f"en.u4.{i+1}.{r[0].replace(' ', '_')}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u5():
    rows = [
        ("breakfast", "завтрак", "/ˈbrek.fəst/", "🍳", "What's for breakfast?", "Что на завтрак?"),
        ("lunch", "обед", "/lʌntʃ/", "🥗", "We have lunch at school.", "Мы обедаем в школе."),
        ("dinner", "ужин", "/ˈdɪn.ə/", "🍽️", "We have dinner at 6 p.m.", "Мы ужинаем в 6 вечера."),
        ("sandwich", "бутерброд", "/ˈsæn.wɪdʒ/", "🥪", "I'd like a sandwich.", "Я бы хотел бутерброд."),
        ("jam", "варенье", "/dʒæm/", "🍓", "I'd like some jam.", "Я бы хотел варенья."),
        ("cereal", "хлопья", "/ˈsɪə.ri.əl/", "🥣", "We often have cereal with milk.", "Мы часто едим хлопья с молоком."),
        ("sausage", "сосиска", "/ˈsɒs.ɪdʒ/", "🌭", "Eggs with sausages are tasty.", "Яйца с сосисками вкусные."),
        ("toast", "тост, поджаренный хлеб", "/təʊst/", "🍞", "Tea or coffee with toast.", "Чай или кофе с тостом."),
        ("vegetables", "овощи", "/ˈvedʒ.tə.bəlz/", "🥦", "You should eat a lot of vegetables.", "Тебе следует есть много овощей."),
        ("fruit", "фрукты", "/fruːt/", "🍇", "You should eat a lot of fruit.", "Тебе следует есть много фруктов."),
        ("juice", "сок", "/dʒuːs/", "🧃", "How much juice should we drink a day?", "Сколько сока нам следует пить в день?"),
        ("crisps", "чипсы", "/krɪsps/", "🍟", "You shouldn't eat many crisps.", "Не следует есть много чипсов."),
        ("ice cream", "мороженое", "/ˈaɪs kriːm/", "🍦", "You shouldn't eat much ice cream.", "Не следует есть много мороженого."),
        ("fridge", "холодильник", "/frɪdʒ/", "🧊", "Is there any food in the fridge?", "В холодильнике есть еда?"),
        ("headache", "головная боль", "/ˈhed.eɪk/", "🤕", "I've got a headache.", "У меня болит голова."),
        ("toothache", "зубная боль", "/ˈtuːθ.eɪk/", "😬", "Poor old Mr Owl's got a toothache.", "У бедного старого мистера Совы болит зуб."),
        ("cough", "кашель", "/kɒf/", "🤧", "I've got a cough.", "У меня кашель."),
        ("cold", "простуда", "/kəʊld/", "🥶", "She's got a cold.", "У неё простуда."),
        ("temperature", "температура (болезнь)", "/ˈtem.prə.tʃə/", "🌡️", "He's got a temperature.", "У него температура."),
        ("doctor", "врач", "/ˈdɒk.tə/", "👨‍⚕️", "You should go to the doctor.", "Тебе следует пойти к врачу."),
        ("healthy", "здоровый", "/ˈhel.θi/", "💪", "Eat fruit and be healthy.", "Ешь фрукты и будь здоров."),
        ("stomach", "живот, желудок", "/ˈstʌm.ək/", "🤰", "I've got a stomachache.", "У меня болит живот."),
    ]
    return [w(f"en.u5.{i+1}.{r[0].replace(' ', '_')}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u6():
    rows = [
        ("map", "карта", "/mæp/", "🗺️", "Look at the map of the city.", "Посмотри на карту города."),
        ("street", "улица", "/striːt/", "🛣️", "Go along Green Street.", "Иди по Зелёной улице."),
        ("square", "площадь", "/skweə/", "🟦", "I live not far from Victory Square.", "Я живу недалеко от площади Победы."),
        ("bridge", "мост", "/brɪdʒ/", "🌉", "Go over the bridge.", "Пройди по мосту."),
        ("bank", "банк", "/bæŋk/", "🏦", "How do I get to the nearest bank?", "Как пройти до ближайшего банка?"),
        ("post office", "почта", "/pəʊst ˈɒf.ɪs/", "🏤", "It's next to the post office.", "Это рядом с почтой."),
        ("traffic lights", "светофор", "/ˈtræf.ɪk laɪts/", "🚦", "You must stop when the traffic lights are red.", "Нужно остановиться, когда светофор красный."),
        ("bookshop", "книжный магазин", "/ˈbʊk.ʃɒp/", "📗", "Go past the bookshop.", "Пройди мимо книжного магазина."),
        ("church", "церковь", "/tʃɜːtʃ/", "⛪", "Go past the church.", "Пройди мимо церкви."),
        ("station", "вокзал, станция", "/ˈsteɪ.ʃən/", "🚉", "How do I get to the station?", "Как пройти до вокзала?"),
        ("left", "налево, левый", "/left/", "⬅️", "Then turn left.", "Затем поверни налево."),
        ("right", "направо, правый", "/raɪt/", "➡️", "Then turn right.", "Затем поверни направо."),
        ("straight", "прямо", "/streɪt/", "⬆️", "Go straight ahead.", "Иди прямо."),
        ("seat belt", "ремень безопасности", "/siːt belt/", "💺", "You must wear a seat belt in a car.", "В машине нужно пристегивать ремень."),
        ("flicker", "фликер, световозвращатель", "/ˈflɪk.ə/", "✨", "You must wear a flicker when it's dark.", "В темноте нужно носить фликер."),
        ("city", "город (большой)", "/ˈsɪt.i/", "🏙️", "Minsk is a beautiful city.", "Минск — красивый город."),
        ("avenue", "проспект", "/ˈæv.ə.njuː/", "🛤️", "I live in Nezavisimost Avenue.", "Я живу на проспекте Независимости."),
        ("opposite", "напротив", "/ˈɒp.ə.zɪt/", "↔️", "The bank is opposite the park.", "Банк находится напротив парка."),
        ("behind", "за, позади", "/bɪˈhaɪnd/", "🔙", "The shop is behind the church.", "Магазин за церковью."),
        ("next to", "рядом с", "/nekst tuː/", "📍", "Liz's house is next to the post office.", "Дом Лиз рядом с почтой."),
    ]
    return [w(f"en.u6.{i+1}.{r[0].replace(' ', '_')}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u7():
    rows = [
        ("farm", "ферма", "/fɑːm/", "🏡", "There are many animals on the farm.", "На ферме много животных."),
        ("cow", "корова", "/kaʊ/", "🐄", "You can milk the cows.", "Можно доить коров."),
        ("sheep", "овца, овцы", "/ʃiːp/", "🐑", "Go to the sheep and lambs.", "Иди к овцам и ягнятам."),
        ("pig", "свинья", "/pɪɡ/", "🐷", "I can see pigs on the farm.", "Я вижу свиней на ферме."),
        ("hen", "курица", "/hen/", "🐔", "There are hens in the hen house.", "В курятнике куры."),
        ("chicken", "цыплёнок, курица (мясо)", "/ˈtʃɪk.ɪn/", "🐥", "There are chickens everywhere.", "Цыплята повсюду."),
        ("rooster", "петух", "/ˈruː.stə/", "🐓", "The rooster is running after them.", "Петух бежит за ними."),
        ("lamb", "ягнёнок", "/læm/", "🐣", "You can bottle-feed lambs.", "Можно кормить ягнят из бутылочки."),
        ("tractor", "трактор", "/ˈtræk.tə/", "🚜", "You can drive a tractor at the Tractor School.", "На тракторной школе можно водить трактор."),
        ("field", "поле", "/fiːld/", "🌾", "Cows eat grass in the field.", "Коровы едят траву в поле."),
        ("feed", "кормить", "/fiːd/", "🥣", "We feed the animals every morning.", "Мы кормим животных каждое утро."),
        ("collect", "собирать", "/kəˈlekt/", "🥚", "You can collect eggs in the hen house.", "В курятнике можно собирать яйца."),
        ("grass", "трава", "/ɡrɑːs/", "🌱", "Sheep eat grass.", "Овцы едят траву."),
        ("village", "деревня, село", "/ˈvɪl.ɪdʒ/", "🏡", "I live in a small village.", "Я живу в маленькой деревне."),
        ("country life", "сельская жизнь", "/ˈkʌn.tri laɪf/", "🌻", "Country life is quiet and interesting.", "Сельская жизнь тихая и интересная."),
        ("quiet", "тихий", "/ˈkwaɪ.ət/", "🤫", "The village is quiet.", "В деревне тихо."),
    ]
    return [w(f"en.u7.{i+1}.{r[0].replace(' ', '_')}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u8():
    rows = [
        ("continent", "континент", "/ˈkɒn.tɪ.nənt/", "🌍", "There are seven continents.", "Есть семь континентов."),
        ("Africa", "Африка", "/ˈæf.rɪ.kə/", "🌍", "Elephants live in Africa.", "Слоны живут в Африке."),
        ("Asia", "Азия", "/ˈeɪ.ʃə/", "🌏", "Tigers live in Asia.", "Тигры живут в Азии."),
        ("Europe", "Европа", "/ˈjʊə.rəp/", "🌍", "Belarus is in Europe.", "Беларусь находится в Европе."),
        ("America", "Америка", "/əˈmer.ɪ.kə/", "🌎", "There are high mountains in America.", "В Америке высокие горы."),
        ("Australia", "Австралия", "/ɒˈstreɪ.li.ə/", "🦘", "Kangaroos live in Australia.", "Кенгуру живут в Австралии."),
        ("Antarctica", "Антарктида", "/ænˈtɑːk.tɪ.kə/", "🧊", "Penguins live in Antarctica.", "Пингвины живут в Антарктиде."),
        ("ocean", "океан", "/ˈəʊ.ʃən/", "🌊", "The Pacific is a big ocean.", "Тихий — большой океан."),
        ("desert", "пустыня", "/ˈdez.ət/", "🏜️", "It is very hot in the desert.", "В пустыне очень жарко."),
        ("jungle", "джунгли", "/ˈdʒʌŋ.ɡəl/", "🌴", "There are many birds in the jungle.", "В джунглях много птиц."),
        ("island", "остров", "/ˈaɪ.lənd/", "🏝️", "We were on a small island.", "Мы были на маленьком острове."),
        ("shark", "акула", "/ʃɑːk/", "🦈", "I will see a shark.", "Я увижу акулу."),
        ("giraffe", "жираф", "/dʒɪˈrɑːf/", "🦒", "My mum liked the giraffe.", "Маме понравился жираф."),
        ("penguin", "пингвин", "/ˈpeŋ.ɡwɪn/", "🐧", "A penguin can't fly, but it can swim.", "Пингвин не умеет летать, но умеет плавать."),
        ("elephant", "слон", "/ˈel.ɪ.fənt/", "🐘", "An elephant is a very big animal.", "Слон — очень большое животное."),
        ("whale", "кит", "/weɪl/", "🐋", "A whale lives in the ocean.", "Кит живёт в океане."),
        ("kangaroo", "кенгуру", "/ˌkæŋ.ɡəˈruː/", "🦘", "A kangaroo lives in Australia.", "Кенгуру живёт в Австралии."),
        ("world", "мир, свет", "/wɜːld/", "🌐", "Our wonderful world is full of animals.", "Наш удивительный мир полон животных."),
    ]
    return [w(f"en.u8.{i+1}.{r[0]}", *r, i + 1) for i, r in enumerate(rows)]


def vocab_u9():
    rows = [
        ("travel", "путешествовать", "/ˈtræv.əl/", "🧳", "I like to travel by train.", "Люблю путешествовать на поезде."),
        ("plane", "самолёт", "/pleɪn/", "✈️", "We will go by plane.", "Мы полетим на самолёте."),
        ("train", "поезд", "/treɪn/", "🚆", "The train leaves at half past five.", "Поезд отправляется в половине шестого."),
        ("bus", "автобус", "/bʌs/", "🚌", "We go to school by bus.", "Мы едем в школу на автобусе."),
        ("ship", "корабль", "/ʃɪp/", "🚢", "They travelled by ship.", "Они путешествовали на корабле."),
        ("ticket", "билет", "/ˈtɪk.ɪt/", "🎫", "I have got a ticket to London.", "У меня есть билет в Лондон."),
        ("airport", "аэропорт", "/ˈeə.pɔːt/", "🛬", "We must go to the airport.", "Нам нужно ехать в аэропорт."),
        ("passport", "паспорт", "/ˈpɑːs.pɔːt/", "🛂", "Don't forget your passport.", "Не забудь паспорт."),
        ("the UK", "Соединённое Королевство", "/ðə juː ˈkeɪ/", "🇬🇧", "People speak English in the UK.", "В Соединённом Королевстве говорят по-английски."),
        ("the USA", "США", "/ðə juː es ˈeɪ/", "🇺🇸", "The USA is an English-speaking country.", "США — англоязычная страна."),
        ("England", "Англия", "/ˈɪŋ.ɡlənd/", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "London is the capital of England.", "Лондон — столица Англии."),
        ("London", "Лондон", "/ˈlʌn.dən/", "🎡", "I will see London next summer.", "Следующим летом я увижу Лондон."),
        ("suitcase", "чемодан", "/ˈsuːt.keɪs/", "🧳", "Pack your suitcase, please.", "Пожалуйста, собери чемодан."),
        ("tomorrow", "завтра", "/təˈmɒr.əʊ/", "⏭️", "We will travel tomorrow.", "Мы отправимся в путешествие завтра."),
        ("next", "следующий", "/nekst/", "➡️", "Next year I will go to England.", "В следующем году я поеду в Англию."),
        ("country", "страна", "/ˈkʌn.tri/", "🏳️", "Name English-speaking countries.", "Назови англоязычные страны."),
    ]
    # "country" conflicts with unit 1 translation "деревня". Use "страна" — unique_together is (language, word, translation_ru), so OK.
    # But wait - I used "country" in u1 as "деревня, сельская местность". This is "страна". Good, different translation_ru.
    return [w(f"en.u9.{i+1}.{r[0].replace(' ', '_')}", *r, i + 1) for i, r in enumerate(rows)]



# ---------------------------------------------------------------------------
# Grammar skills
# ---------------------------------------------------------------------------

def exs_have_got_extra():
    """ex6–ex15; ex1–ex5 already in en_words.json."""
    e = []
    e.append(ch("en.gr.hg.ex6",
                "We ___ got a cat (кошка — cat).",
                ["has", "have", "is"], "have",
                ["We (мы) — как I/you/they.", "После we пишем have got (иметь)."],
                explain="We have got. Have got (иметь) с I/you/we/they."))
    e.append(ch("en.gr.hg.ex7",
                "He ___ got a new bag (сумка — bag).",
                ["have", "has", "are"], "has",
                ["He (он) — как she/it.", "He/she/it has got."]))
    e.append(ch("en.gr.hg.ex8",
                "They ___ got two bikes (велосипед — bike).",
                ["has", "have", "is"], "have",
                ["They (они) идёт с have got."]))
    e.append(ch("en.gr.hg.ex9",
                "My mum (мама) ___ got a car (машина — car).",
                ["have", "has", "do"], "has",
                ["My mum = she (она).", "She has got."], diff=2))
    e.append(sc("en.gr.hg.ex10",
                "Как правильно сказать «У неё есть сестра (sister)»?",
                ["She have got a sister.", "She has got a sister.", "She is got a sister."],
                "She has got a sister.",
                ["She (она) → has got (иметь)."]))
    e.append(ch("en.gr.hg.ex11",
                "It ___ got a long tail (хвост — tail).",
                ["have", "has", "am"], "has",
                ["It (оно) — как he/she: has got."]))
    e.append(txt("en.gr.hg.ex12",
                 "Впиши have или has: Tom ___ got a dog (собака — dog).",
                 "has", ["Tom = he (он).", "He has got."], accept=["has"]))
    e.append(txt("en.gr.hg.ex13",
                 "Впиши have или has: You and I ___ got a plan (план — plan).",
                 "have", ["You and I = we (мы).", "We have got."], accept=["have"]))
    e.append(match("en.gr.hg.ex14",
                   "Соедини подлежащее (subject — подлежащее) с верной формой have got (иметь).",
                   [("I", "have got"), ("She", "has got"), ("They", "have got"), ("It", "has got")],
                   ["I/you/we/they — have got; he/she/it — has got."]))
    e.append(cat("en.gr.hg.ex15",
                 "Разложи подлежащие (subjects) по формам have got / has got (иметь).",
                 [("have", "have got"), ("has", "has got")],
                 [("i", "I"), ("you", "you"), ("he", "he"), ("she", "she"), ("we", "we"), ("it", "it")],
                 {"have": ["i", "you", "we"], "has": ["he", "she", "it"]},
                 ["He/she/it — has; остальные — have."]))
    return e


def skill_was_were():
    rule = (
        "Past Simple (прошедшее простое) глагола to be (быть): "
        "I/he/she/it/there was (был, была, было); we/you/they/there were (были). "
        "I am → was, he is → was, they are → were. "
        "Yesterday (вчера), last summer (прошлым летом)."
    )
    steps = [
        "Нужно сказать о прошлом: «Я был на море (at the seaside)».",
        "Подлежащее — I (я). Для I в прошедшем времени — was (был).",
        "I was at the seaside.",
        "Для we/you/they — were: We were in town (в городе).",
    ]
    e = []
    e.append(ch("en.gr.ww.ex1", "I ___ at home (дома) in June (июнь).",
                ["was", "were", "am"], "was",
                ["I (я) в прошлом — was (был)."]))
    e.append(ch("en.gr.ww.ex2", "We ___ in the mountains (в горах) last summer (прошлым летом).",
                ["was", "were", "is"], "were",
                ["We (мы) → were (были)."]))
    e.append(ch("en.gr.ww.ex3", "She ___ at summer camp (в летнем лагере).",
                ["was", "were", "are"], "was",
                ["She (она) как I/he/it — was."]))
    e.append(ch("en.gr.ww.ex4", "They ___ in town (в городе) in August (август).",
                ["was", "were", "is"], "were",
                ["They (они) → were."]))
    e.append(ch("en.gr.ww.ex5", "It ___ hot and sunny (жарко и солнечно).",
                ["was", "were", "are"], "was",
                ["It (это/погода) → was."]))
    e.append(ch("en.gr.ww.ex6", "My parents and I ___ abroad (за границей).",
                ["was", "were", "is"], "were",
                ["My parents and I = we (мы) → were."], diff=2))
    e.append(ch("en.gr.ww.ex7", "There ___ lots of books to read.",
                ["was", "were", "is"], "were",
                ["Lots of books (много книг) — множественное число → there were."], diff=2))
    e.append(ch("en.gr.ww.ex8", "There ___ lots of food to eat.",
                ["was", "were", "are"], "was",
                ["Food (еда) неисчисляемое → there was."], diff=2))
    e.append(sc("en.gr.ww.ex9", "Выбери верное предложение (Past Simple — прошедшее простое).",
                ["I were at the seaside.", "I was at the seaside.", "I am at the seaside yesterday."],
                "I was at the seaside.",
                ["I + was. Yesterday (вчера) требует прошедшего времени."]))
    e.append(txt("en.gr.ww.ex10", "Впиши was или were: He ___ at the zoo (зоопарк) yesterday (вчера).",
                 "was", ["He (он) → was."], accept=["was"]))
    e.append(txt("en.gr.ww.ex11", "Впиши was или were: You ___ in the park (парк).",
                 "were", ["You (ты/вы) → were."], accept=["were"]))
    e.append(match("en.gr.ww.ex12",
                   "Соедини настоящее (Present — настоящее) и прошлое (Past — прошедшее) глагола to be (быть).",
                   [("I am", "I was"), ("he is", "he was"), ("they are", "they were"), ("we are", "we were")],
                   ["am/is → was; are → were."]))
    e.append(audio("en.gr.ww.ex13", "I was at the seaside.",
                   ["I was at the seaside. (Я был на море.)",
                    "I were at the seaside.",
                    "I am at the seaside."],
                   "I was at the seaside. (Я был на море.)",
                   ["Слушай was (был), не were и не am."]))
    e.append(cat("en.gr.ww.ex14",
                 "Разложи по was (был) и were (были).",
                 [("was", "was (был / была / было)"), ("were", "were (были)")],
                 [("i", "I"), ("he", "he"), ("she", "she"), ("we", "we"), ("you", "you"), ("they", "they")],
                 {"was": ["i", "he", "she"], "were": ["we", "you", "they"]},
                 ["I/he/she/it — was; we/you/they — were."]))
    e.append(ch("en.gr.ww.ex15", "The weather (погода) ___ wonderful (чудесная).",
                ["was", "were", "are"], "was",
                ["The weather = it → was."], diff=2))
    return skill(
        "en.gr.was_were",
        "was / were — Past Simple глагола to be (быть)",
        rule,
        "Как сказать: «Я был на море (at the seaside)»?",
        steps, e, order=1,
    )


def skill_was_were_nq():
    rule = (
        "Отрицание (negative — отрицание): was not = wasn’t, were not = weren’t. "
        "I wasn’t at the seaside (на море). We weren’t abroad (за границей). "
        "Общий вопрос (general question): Was I / he / she…? Were you / we / they…? "
        "Краткие ответы: Yes, I was. / No, I wasn’t. Yes, they were. / No, they weren’t. "
        "Специальный вопрос (Wh-question): Where were you? (Где ты был?) What was the weather like? (Какая была погода?)"
    )
    steps = [
        "Нужно сказать: «Я не был на море».",
        "I + was + not → I wasn’t (я не был).",
        "I wasn’t at the seaside.",
        "Вопрос: Were you at the seaside? — Yes, I was. / No, I wasn’t.",
    ]
    e = []
    e.append(ch("en.gr.wwq.ex1", "I ___ at the seaside (на море). (отрицание)",
                ["wasn't", "weren't", "isn't"], "wasn't",
                ["I (я) → wasn’t (не был)."]))
    e.append(ch("en.gr.wwq.ex2", "We ___ abroad (за границей).",
                ["wasn't", "weren't", "aren't"], "weren't",
                ["We (мы) → weren’t (не были)."]))
    e.append(ch("en.gr.wwq.ex3", "She ___ at summer camp (в лагере).",
                ["wasn't", "weren't", "hasn't"], "wasn't",
                ["She → wasn’t."]))
    e.append(ch("en.gr.wwq.ex4", "___ you in the country (в деревне) in June?",
                ["Was", "Were", "Did"], "Were",
                ["You → Were you…?"]))
    e.append(ch("en.gr.wwq.ex5", "___ he at the circus (цирк) yesterday (вчера)?",
                ["Was", "Were", "Does"], "Was",
                ["He → Was he…?"]))
    e.append(sc("en.gr.wwq.ex6", "Выбери верный краткий ответ (short answer) на «Were they in town?»",
                ["Yes, they was.", "Yes, they were.", "Yes, they are."],
                "Yes, they were.",
                ["Вопрос с Were → ответ they were."]))
    e.append(sc("en.gr.wwq.ex7", "Выбери верный краткий ответ на «Was she at home?»",
                ["No, she weren't.", "No, she wasn't.", "No, she isn't."],
                "No, she wasn't.",
                ["Was she → No, she wasn’t."]))
    e.append(ch("en.gr.wwq.ex8", "___ were you in summer? — I was at the seaside.",
                ["Where (где)", "Who (кто)", "What (что)"], "Where (где)",
                ["Ответ — место, значит Where (где)."]))
    e.append(ch("en.gr.wwq.ex9", "___ was the weather like? — It was sunny (солнечно).",
                ["Where", "What", "Who"], "What",
                ["What was the weather like? (Какая была погода?) — устойчивый вопрос."], diff=2))
    e.append(ch("en.gr.wwq.ex10", "Who were you there ___? — With my parents (с родителями).",
                ["with (с)", "at (в)", "on (на)"], "with (с)",
                ["Who … with? (С кем?)"]))
    e.append(txt("en.gr.wwq.ex11", "Впиши wasn’t или weren’t: They ___ at the library (библиотека).",
                 "weren't", ["They → weren’t."], accept=["weren't", "were not"]))
    e.append(txt("en.gr.wwq.ex12", "Впиши Was или Were: ___ it rainy (дождливо) in July?",
                 "Was", ["It → Was it…?"], accept=["Was", "was"]))
    e.append(order("en.gr.wwq.ex13",
                   "Собери вопрос: «Где ты был летом?» (Where were you in summer?)",
                   [("w", "Where"), ("v", "were"), ("y", "you"), ("i", "in summer?")],
                   ["w", "v", "y", "i"],
                   ["Вопросительное слово + were + подлежащее."]))
    e.append(match("en.gr.wwq.ex14",
                   "Соедини вопрос и перевод.",
                   [("Where were you?", "Где ты был?"),
                    ("Was it hot?", "Было ли жарко?"),
                    ("Were they in town?", "Они были в городе?"),
                    ("What was the weather like?", "Какая была погода?")],
                   ["Where — где; What … like — какая (погода)."]))
    e.append(audio("en.gr.wwq.ex15", "I wasn't at the seaside.",
                   ["I wasn't at the seaside. (Я не был на море.)",
                    "I weren't at the seaside.",
                    "I was at the seaside."],
                   "I wasn't at the seaside. (Я не был на море.)",
                   ["Слышится wasn’t (отрицание)."]))
    return skill(
        "en.gr.was_were_neg_q",
        "wasn’t / weren’t и вопросы с to be (быть)",
        rule,
        "Как сказать: «Я не был на море» и спросить «Ты был на море?»",
        steps, e, order=2, prerequisites=["en.gr.was_were"],
    )


def skill_past_regular():
    rule = (
        "Past Simple (прошедшее простое) правильных глаголов (regular verbs): "
        "к инфинитиву (V) добавляем -ed (окончание прошедшего времени): visit → visited (навестил), "
        "play → played (играл), like → liked (понравилось). "
        "Форма одинакова для всех лиц: I/he/we visited. "
        "Правописание: like + d = liked; stop → stopped; study → studied; play → played (после гласной y не меняется)."
    )
    steps = [
        "Нужно сказать: «Я навестил бабушку». Глагол visit (посещать) — правильный.",
        "К visit добавляем -ed → visited (навестил).",
        "I visited my granny.",
        "Так же: We played football every day. She liked the giraffe.",
    ]
    e = []
    e.append(ch("en.gr.pr.ex1", "I ___ my granny (бабушка) last Sunday (в прошлое воскресенье).",
                ["visit", "visited", "visiting"], "visited",
                ["Past Simple правильного глагола: visit + ed."]))
    e.append(ch("en.gr.pr.ex2", "She ___ the giraffe (жираф).",
                ["like", "liked", "likes"], "liked",
                ["like (нравиться) + d = liked (понравилось)."]))
    e.append(ch("en.gr.pr.ex3", "We ___ football every day.",
                ["play", "played", "plays"], "played",
                ["play + ed = played (играли). y после гласной не меняется."]))
    e.append(ch("en.gr.pr.ex4", "They ___ to music (музыка) yesterday (вчера).",
                ["listened", "listen", "listens"], "listened",
                ["listen → listened (слушали)."]))
    e.append(ch("en.gr.pr.ex5", "He ___ in a café (кафе) last Friday.",
                ["walked", "walk", "walks"], "walked",
                ["walk → walked (ходил) — но смотри смысл: если «ел» это другой глагол. Здесь «зашёл/ходил». Хм."]))
    # walk in a cafe is odd. Change prompt:
    e[-1] = ch("en.gr.pr.ex5", "He ___ in the park (парк) yesterday (вчера).",
               ["walked", "walk", "walks"], "walked",
               ["walk (гулять) → walked (гулял)."])
    e.append(ch("en.gr.pr.ex6", "Mum ___ a holiday dinner (праздничный ужин).",
                ["cook", "cooked", "cooking"], "cooked",
                ["cook (готовить) → cooked (приготовила)."]))
    e.append(ch("en.gr.pr.ex7", "The children ___ the Christmas tree (ёлку).",
                ["decorate", "decorated", "decorates"], "decorated",
                ["decorate (украшать) → decorated."], diff=2))
    e.append(sc("en.gr.pr.ex8", "Выбери верную форму Past Simple (прошедшее простое): study (учиться).",
                ["studyed", "studied", "studyd"], "studied",
                ["y после согласной → ied: study → studied."], diff=2))
    e.append(sc("en.gr.pr.ex9", "Выбери верную форму: stop (останавливаться).",
                ["stoped", "stopped", "stopt"], "stopped",
                ["Короткий гласный + согласная: удваиваем p → stopped."], diff=3))
    e.append(txt("en.gr.pr.ex10", "Напиши Past Simple глагола play (играть).",
                 "played", ["play + ed. y не меняется, потому что перед y стоит гласная."], accept=["played"]))
    e.append(txt("en.gr.pr.ex11", "Напиши Past Simple глагола visit (посещать).",
                 "visited", ["visit + ed."], accept=["visited"]))
    e.append(match("en.gr.pr.ex12",
                   "Соедини глагол (verb — глагол) и форму Past Simple.",
                   [("visit (посещать)", "visited"),
                    ("like (нравиться)", "liked"),
                    ("play (играть)", "played"),
                    ("watch (смотреть)", "watched")],
                   ["К правильному глаголу добавляем -ed / -d."]))
    e.append(tiles("en.gr.pr.ex13", "Собери Past Simple глагола cook (готовить).", "cooked",
                   ["cook + ed."], extra="s"))
    e.append(audio("en.gr.pr.ex14", "I visited my granny.",
                   ["I visited my granny. (Я навестил бабушку.)",
                    "I visit my granny.",
                    "I visits my granny."],
                   "I visited my granny. (Я навестил бабушку.)",
                   ["Слышно окончание -ed: visited."]))
    e.append(ch("en.gr.pr.ex15", "Yesterday (вчера) we ___ a good film (фильм).",
                ["watch", "watched", "watches"], "watched",
                ["Yesterday → Past Simple: watched (посмотрели)."]))
    return skill(
        "en.gr.past_regular",
        "Past Simple правильных глаголов (regular verbs, -ed)",
        rule,
        "Как сказать: «Я навестил бабушку» (visit — посещать)?",
        steps, e, order=3, prerequisites=["en.gr.was_were"],
    )


def skill_past_irregular():
    rule = (
        "Неправильные глаголы (irregular verbs) в Past Simple имеют особую форму V2 (вторая форма): "
        "go → went (шёл, ехал), have → had (был, имел), drink → drank (пил), "
        "see → saw (видел), take → took (взял), eat → ate (ел), come → came (пришёл). "
        "Форму нужно запомнить. Она одинакова для всех лиц: I went, she went, they went."
    )
    steps = [
        "Нужно сказать: «Я ходил в парк». Глагол go (идти) — неправильный.",
        "Вторая форма (V2) глагола go — went (шёл, ходил).",
        "I went to the park.",
        "Ещё примеры: Elfin drank orange juice. The friends had a lot of fun.",
    ]
    pairs_irr = [
        ("go (идти)", "went"),
        ("have (иметь)", "had"),
        ("drink (пить)", "drank"),
        ("see (видеть)", "saw"),
        ("take (брать)", "took"),
        ("eat (есть)", "ate"),
    ]
    e = []
    e.append(ch("en.gr.pi.ex1", "I ___ to the park (парк) last summer (прошлым летом).",
                ["go", "went", "goed"], "went",
                ["go (идти) — неправильный: went."]))
    e.append(ch("en.gr.pi.ex2", "Elfin ___ orange juice (апельсиновый сок).",
                ["drink", "drank", "drinked"], "drank",
                ["drink → drank (пил)."]))
    e.append(ch("en.gr.pi.ex3", "The friends ___ a lot of fun (веселье).",
                ["have", "had", "haved"], "had",
                ["have fun (веселиться) → had a lot of fun."]))
    e.append(ch("en.gr.pi.ex4", "We ___ a good film (фильм) at the cinema (кинотеатр).",
                ["saw", "see", "seed"], "saw",
                ["see (видеть, смотреть) → saw."]))
    e.append(ch("en.gr.pi.ex5", "She ___ a present (подарок) from her mum.",
                ["get", "got", "getted"], "got",
                ["get (получать) → got."]))
    e.append(ch("en.gr.pi.ex6", "They ___ lunch (обед) at 2 o'clock.",
                ["eat", "ate", "eated"], "ate",
                ["eat (есть) → ate."]))
    e.append(ch("en.gr.pi.ex7", "Mike ___ Elfin to the library (библиотека).",
                ["take", "took", "taked"], "took",
                ["take (брать, вести) → took."]))
    e.append(ch("en.gr.pi.ex8", "Santa ___ a big bag (мешок).",
                ["have", "had", "has"], "had",
                ["В прошлом: had (имел)."]))
    e.append(sc("en.gr.pi.ex9", "Как НЕЛЬЗЯ сказать Past Simple от go (идти)?",
                ["I went home.", "She went to town.", "He goed to town."],
                "He goed to town.",
                ["Go — неправильный, goed не существует. Нужно went."], diff=2))
    e.append(txt("en.gr.pi.ex10", "Напиши V2 (Past Simple) глагола go (идти).",
                 "went", ["go — went."], accept=["went"]))
    e.append(txt("en.gr.pi.ex11", "Напиши V2 глагола see (видеть).",
                 "saw", ["see — saw."], accept=["saw"]))
    e.append(match("en.gr.pi.ex12", "Соедини инфинитив (V) и Past Simple (V2).",
                   pairs_irr[:4],
                   ["Это неправильные глаголы (irregular verbs) из учебника."]))
    e.append(cat("en.gr.pi.ex13",
                 "Разложи глаголы на правильные (regular, -ed) и неправильные (irregular).",
                 [("reg", "правильные (regular): +ed"), ("irr", "неправильные (irregular): V2")],
                 [("v", "visited"), ("w", "went"), ("p", "played"), ("s", "saw"), ("d", "drank"), ("l", "liked")],
                 {"reg": ["v", "p", "l"], "irr": ["w", "s", "d"]},
                 ["Если есть -ed — скорее правильный; went/saw/drank — неправильные."]))
    e.append(tiles("en.gr.pi.ex14", "Собери V2 глагола go (идти).", "went",
                   ["go → went."], extra="og"))
    e.append(audio("en.gr.pi.ex15", "I went to the park.",
                   ["I went to the park. (Я ходил в парк.)",
                    "I go to the park.",
                    "I goed to the park."],
                   "I went to the park. (Я ходил в парк.)",
                   ["Слышно went, не go и не goed."]))
    return skill(
        "en.gr.past_irregular",
        "Past Simple неправильных глаголов (irregular verbs, V2)",
        rule,
        "Как сказать: «Я ходил в парк» (go — идти)?",
        steps, e, order=4, prerequisites=["en.gr.past_regular"],
    )


def skill_past_did():
    rule = (
        "Отрицание Past Simple (для всех глаголов, кроме to be): did not + V (инфинитив). "
        "did not = didn’t. I didn’t wear jeans. They didn’t live in houses. "
        "Важно: после didn’t глагол БЕЗ -ed и НЕ в форме V2: didn’t go (не didn’t went). "
        "Общий вопрос (general question): Did I/he/she/we/you/they + V …? "
        "Did you go to the country? Yes, I did. / No, I didn’t."
    )
    steps = [
        "Нужно сказать: «Я не ходил в деревню» и спросить «Ты ходил в деревню?»",
        "Отрицание: didn’t + go (инфинитив) → I didn’t go to the country.",
        "Вопрос: Did + you + go…? — Did you go to the country?",
        "Краткий ответ: Yes, I did. / No, I didn’t.",
    ]
    e = []
    e.append(ch("en.gr.pd.ex1", "I ___ go to the country (в деревню).",
                ["didn't", "wasn't", "don't"], "didn't",
                ["Отрицание Past Simple — didn’t + инфинитив (V)."]))
    e.append(ch("en.gr.pd.ex2", "They ___ live in houses. (они не жили в домах)",
                ["didn't", "weren't", "doesn't"], "didn't",
                ["didn’t + live (инфинитив)."]))
    e.append(ch("en.gr.pd.ex3", "She didn't ___ jeans (джинсы).",
                ["wore", "wear", "wears"], "wear",
                ["После didn’t ставим инфинитив wear, не wore."], diff=2))
    e.append(ch("en.gr.pd.ex4", "He didn't ___ to the museum (музей).",
                ["went", "go", "goes"], "go",
                ["didn’t + go, не went."], diff=2))
    e.append(ch("en.gr.pd.ex5", "___ you go to the country?",
                ["Did", "Do", "Were"], "Did",
                ["Вопрос Past Simple: Did + подлежащее + V?"]))
    e.append(ch("en.gr.pd.ex6", "___ she stay in town (осталась в городе)?",
                ["Did", "Does", "Was"], "Did",
                ["Did she stay…? Was — только для to be (быть)."]))
    e.append(sc("en.gr.pd.ex7", "Выбери верный краткий ответ на «Did they play football?»",
                ["Yes, they played.", "Yes, they did.", "Yes, they do."],
                "Yes, they did.",
                ["Краткий ответ: Yes, they did. / No, they didn’t."]))
    e.append(sc("en.gr.pd.ex8", "Какое предложение верное?",
                ["I didn't went to the cinema.", "I didn't go to the cinema.", "I not go to the cinema."],
                "I didn't go to the cinema.",
                ["После didn’t — инфинитив go."], diff=2))
    e.append(sc("en.gr.pd.ex9", "Какое предложение верное?",
                ["Did he went to the library?", "Did he go to the library?", "Does he went to the library?"],
                "Did he go to the library?",
                ["Did + go (инфинитив)."], diff=2))
    e.append(txt("en.gr.pd.ex10", "Впиши didn’t или wasn’t: We ___ watch a film (фильм) yesterday.",
                 "didn't", ["Watch — смысловой глагол, не to be → didn’t."], accept=["didn't", "did not"]))
    e.append(txt("en.gr.pd.ex11", "Впиши Did или Was: ___ you like the museum (музей)?",
                 "Did", ["like — смысловой глагол → Did you like…?"], accept=["Did", "did"]))
    e.append(order("en.gr.pd.ex12",
                   "Собери вопрос: Did you go to the country? (Ты ездил в деревню?)",
                   [("d", "Did"), ("y", "you"), ("g", "go"), ("t", "to the country?")],
                   ["d", "y", "g", "t"],
                   ["Did + подлежащее + инфинитив + остальное."]))
    e.append(match("en.gr.pd.ex13",
                   "Соедини русскую фразу и английскую.",
                   [("Я не ходил.", "I didn't go."),
                    ("Ты ходил?", "Did you go?"),
                    ["Да, ходил.", "Yes, I did."],
                    ("Нет, не ходил.", "No, I didn't.")],
                   ["did / didn’t — вспомогательный глагол Past Simple."]))
    # I made a typo in pairs - third item is a list not tuple. Fix:
    e[-1] = match("en.gr.pd.ex13",
                  "Соедини русскую фразу и английскую.",
                  [("Я не ходил.", "I didn't go."),
                   ("Ты ходил?", "Did you go?"),
                   ("Да, ходил.", "Yes, I did."),
                   ("Нет, не ходил.", "No, I didn't.")],
                  ["did / didn’t — вспомогательный глагол Past Simple."])
    e.append(audio("en.gr.pd.ex14", "Did you go to the country?",
                   ["Did you go to the country? (Ты ездил в деревню?)",
                    "Do you go to the country?",
                    "Were you go to the country?"],
                   "Did you go to the country? (Ты ездил в деревню?)",
                   ["Слышно Did you go…"]))
    e.append(ch("en.gr.pd.ex15", "The Tree Monsters (Лесные монстры) didn't ___ the pearl (жемчужина).",
                ["found", "find", "finds"], "find",
                ["didn’t + find (инфинитив), не found."], diff=2))
    return skill(
        "en.gr.past_did",
        "Past Simple: didn’t и вопросы Did…?",
        rule,
        "Как сказать «Я не ходил в деревню» и спросить «Ты ходил?»",
        steps, e, order=5, prerequisites=["en.gr.past_irregular"],
    )


def skill_past_wh():
    rule = (
        "Специальные вопросы (Wh-questions) в Past Simple: "
        "вопросительное слово + did + подлежащее + V (инфинитив)? "
        "What did you do? (Что ты делал?) Where did she go? (Куда она пошла?) "
        "Why did they make a fire? (Почему они развели костёр?) "
        "Вопросительные слова (question words): what — что, where — где/куда, when — когда, "
        "who — кто, why — почему, how — как. "
        "Для to be (быть) вспомогательный did не нужен: Where were you?"
    )
    steps = [
        "Нужно спросить: «Что она делала утром?»",
        "Вопросительное слово What (что) + did + she + do (инфинитив).",
        "What did she do in the morning?",
        "Нельзя: What did she did? и What she did?",
    ]
    e = []
    e.append(ch("en.gr.pw.ex1", "___ did you do in the morning (утром)?",
                ["What (что)", "Where (где)", "Who (кто)"], "What (что)",
                ["Спрашиваем о действии — What did you do?"]))
    e.append(ch("en.gr.pw.ex2", "___ did she go last summer (прошлым летом)? — To the seaside.",
                ["What", "Where", "Why"], "Where",
                ["Ответ — место → Where (где/куда)."]))
    e.append(ch("en.gr.pw.ex3", "___ did they make a fire (костёр)? — Because it was cold.",
                ["Why (почему)", "When (когда)", "Who (кто)"], "Why (почему)",
                ["Ответ с because (потому что) → Why."]))
    e.append(ch("en.gr.pw.ex4", "___ did you get up? — In the morning.",
                ["When (когда)", "Where", "What"], "When (когда)",
                ["Ответ — время → When."]))
    e.append(ch("en.gr.pw.ex5", "What did he ___ in the cave (пещера)?",
                ["did", "do", "does"], "do",
                ["После did — инфинитив do."], diff=2))
    e.append(ch("en.gr.pw.ex6", "Where did they ___ a fire?",
                ["made", "make", "makes"], "make",
                ["did + make, не made."], diff=2))
    e.append(sc("en.gr.pw.ex7", "Выбери верный вопрос.",
                ["Where she went?", "Where did she went?", "Where did she go?"],
                "Where did she go?",
                ["Wh + did + подлежащее + инфинитив."], diff=2))
    e.append(sc("en.gr.pw.ex8", "Выбери верный вопрос о to be (быть).",
                ["Where did you were?", "Where were you?", "Where you were?"],
                "Where were you?",
                ["С was/were частица did не нужна."], diff=2))
    e.append(txt("en.gr.pw.ex9", "Впиши вопросительное слово: ___ did you stay? — In town (в городе).",
                 "Where", ["Ответ — место → Where."], accept=["Where", "where"]))
    e.append(txt("en.gr.pw.ex10", "Впиши did или were: What ___ you do yesterday (вчера)?",
                 "did", ["do — смысловой глагол → did."], accept=["did", "Did"]))
    e.append(order("en.gr.pw.ex11",
                   "Собери вопрос: What did she do in the morning?",
                   [("w", "What"), ("d", "did"), ("s", "she"), ("o", "do"), ("m", "in the morning?")],
                   ["w", "d", "s", "o", "m"],
                   ["Wh + did + подлежащее + V."]))
    e.append(match("en.gr.pw.ex12",
                   "Соедини вопросительное слово и значение.",
                   [("what", "что"), ("where", "где, куда"), ("when", "когда"), ("why", "почему")],
                   ["How — как; who — кто."]))
    e.append(match("en.gr.pw.ex13",
                   "Соедини вопрос и ответ.",
                   [("Where did you go?", "To the museum."),
                    ("When did you go?", "In the morning."),
                    ("Why did you go?", "Because I like history."),
                    ("What did you do?", "I read a book.")],
                   ["Смотри начало ответа: to/in/because."]))
    e.append(audio("en.gr.pw.ex14", "What did you do in the morning?",
                   ["What did you do in the morning? (Что ты делал утром?)",
                    "What do you do in the morning?",
                    "What you did in the morning?"],
                   "What did you do in the morning? (Что ты делал утром?)",
                   ["Слышно What did you do…"]))
    e.append(ch("en.gr.pw.ex15", "Who ___ a fire in the cave? — The woman (женщина).",
                ["did make", "made", "did made"], "made",
                ["Если who — подлежащее, did часто не ставят: Who made a fire?"], diff=3,
                explain="Когда who (кто) — подлежащее, вопрос: Who made a fire? (без did)."))
    return skill(
        "en.gr.past_wh",
        "Past Simple: специальные вопросы (Wh-questions)",
        rule,
        "Как спросить: «Что она делала утром?»",
        steps, e, order=6, prerequisites=["en.gr.past_did"],
    )




def skill_object_pronouns():
    rule = ("Объектные местоимения (object pronouns) — форма после глагола или предлога: "
            "I → me (меня, мне), you → you, he → him (его, ему), she → her (её, ей), "
            "it → it, we → us (нас, нам), they → them (их, им). I like comedies. I love them.")
    steps = ["I like comedies (комедии). Нужно заменить comedies местоимением.",
             "Comedies = they. Объектная форма — them (их).",
             "I love them. (Я их обожаю.)", "Нельзя: I love they."]
    e = [
        ch("en.gr.op.ex1", "I like comedies (комедии). I love ___.", ["they", "them", "their"], "them",
           ["They → them (их) после глагола love."]),
        ch("en.gr.op.ex2", "This is Mike. I like ___.", ["he", "him", "his"], "him", ["He → him (его)."]),
        ch("en.gr.op.ex3", "This is Liz. I like ___.", ["she", "her", "hers"], "her", ["She → her (её)."]),
        ch("en.gr.op.ex4", "We are here. Look at ___.", ["we", "us", "our"], "us", ["We → us (нас) после at."]),
        ch("en.gr.op.ex5", "Give the book (книга) to ___, please. (я)", ["I", "me", "my"], "me", ["После to — me (мне)."]),
        ch("en.gr.op.ex6", "I don't like horror films (фильмы ужасов). I never watch ___.",
           ["them", "they", "it"], "them", ["Films — множественное число → them."]),
        ch("en.gr.op.ex7", "Where is my bag (сумка)? I can't find ___.", ["it", "them", "her"], "it",
           ["Bag — единственное число, it."]),
        sc("en.gr.op.ex8", "Выбери верное предложение.",
           ["I love they.", "I love them.", "I love their."], "I love them.", ["После love — them."]),
        sc("en.gr.op.ex9", "Выбери верное предложение.",
           ["Look at we!", "Look at us!", "Look at our!"], "Look at us!", ["После at — us."]),
        txt("en.gr.op.ex10", "Впиши объектное местоимение для they (они): I see ___.", "them", ["they → them."], accept=["them"]),
        txt("en.gr.op.ex11", "Впиши объектное местоимение для he (он): I know ___.", "him", ["he → him."], accept=["him"]),
        match("en.gr.op.ex12", "Соедини именительный падеж (subject) и объектный (object pronoun).",
              [("I (я)", "me (меня, мне)"), ("he (он)", "him (его, ему)"),
               ("she (она)", "her (её, ей)"), ("they (они)", "them (их, им)")],
              ["you → you, it → it, we → us."]),
        cat("en.gr.op.ex13", "Разложи местоимения на подлежащие (subject) и объектные (object).",
            [("subj", "подлежащее (I, he, they…)"), ("obj", "объектное (me, him, them…)")],
            [("i", "I"), ("me", "me"), ("he", "he"), ("him", "him"), ("we", "we"), ("us", "us")],
            {"subj": ["i", "he", "we"], "obj": ["me", "him", "us"]},
            ["I/he/we — подлежащие; me/him/us — объектные."]),
        audio("en.gr.op.ex14", "I love them.",
              ["I love them. (Я их обожаю.)", "I love they.", "I love their."],
              "I love them. (Я их обожаю.)", ["Слышно them."]),
        ch("en.gr.op.ex15", "The reporter asked ___ some questions. (они — Moldy and Rotty)",
           ["they", "them", "their"], "them", ["После asked — them (их)."], diff=2),
    ]
    return skill("en.gr.object_pronouns",
                 "Object pronouns (me, him, her, us, them) — объектные местоимения",
                 rule, "Как заменить comedies (комедии) в фразе I love ___?", steps, e, order=1)


def skill_adverbs_freq():
    rule = ("Наречия частотности (adverbs of frequency): always (всегда), often (часто), "
            "sometimes (иногда), rarely (редко), never (никогда). "
            "Место: после am/is/are и перед смысловым глаголом: I always watch the news. She is always happy.")
    steps = ["Новости смотрят каждый день — это always (всегда).",
             "Ставим always перед watch (смотреть).",
             "I always watch the news.",
             "Порядок: always — often — sometimes — rarely — never."]
    e = [
        ch("en.gr.af.ex1", "I ___ watch the news (новости). (каждый день)",
           ["always (всегда)", "never (никогда)", "rarely (редко)"], "always (всегда)", ["Каждый день = always."]),
        ch("en.gr.af.ex2", "I ___ watch horror films (фильмы ужасов). (ни разу)",
           ["always", "often", "never (никогда)"], "never (никогда)", ["Ни разу = never."]),
        ch("en.gr.af.ex3", "She ___ watches quiz shows (викторины). (часто, но не всегда)",
           ["often (часто)", "never", "always"], "often (часто)", ["Часто — often."]),
        ch("en.gr.af.ex4", "We ___ watch cartoons (мультфильмы). (время от времени)",
           ["sometimes (иногда)", "always", "never"], "sometimes (иногда)", ["Время от времени = sometimes."]),
        ch("en.gr.af.ex5", "He ___ watches comedies. (очень редко)",
           ["rarely (редко)", "always", "often"], "rarely (редко)", ["Очень редко = rarely."]),
        sc("en.gr.af.ex6", "Где стоит наречие частотности со смысловым глаголом watch (смотреть)?",
           ["I watch always the news.", "I always watch the news.", "Always I watch the news."],
           "I always watch the news.", ["Наречие — перед смысловым глаголом."], diff=2),
        sc("en.gr.af.ex7", "Где стоит наречие с глаголом to be (быть)?",
           ["She always is happy.", "She is always happy.", "Always she is happy."],
           "She is always happy.", ["С am/is/are наречие после to be."], diff=2),
        order("en.gr.af.ex8", "Расставь наречия от «всегда» к «никогда» (always → never).",
              [("a", "always (всегда)"), ("o", "often (часто)"), ("s", "sometimes (иногда)"),
               ("r", "rarely (редко)"), ("n", "never (никогда)")],
              ["a", "o", "s", "r", "n"], ["always → often → sometimes → rarely → never."]),
        match("en.gr.af.ex9", "Соедини наречие и перевод.",
              [("always", "всегда"), ("often", "часто"), ("sometimes", "иногда"), ("never", "никогда")],
              ["rarely — редко."]),
        txt("en.gr.af.ex10", "Впиши наречие «никогда»: I ___ eat crisps (чипсы) at night.",
            "never", ["never — никогда."], accept=["never"]),
        txt("en.gr.af.ex11", "Впиши наречие «всегда»: They ___ wear a seat belt (ремень безопасности).",
            "always", ["always — всегда."], accept=["always"]),
        cat("en.gr.af.ex12", "Разложи на «часто / всегда» и «редко / никогда».",
            [("freq", "always / often (часто)"), ("rare", "rarely / never (редко)")],
            [("a", "always"), ("o", "often"), ("r", "rarely"), ("n", "never")],
            {"freq": ["a", "o"], "rare": ["r", "n"]}, ["always и often — частые действия."]),
        ch("en.gr.af.ex13", "I ___ watch nature programmes (передачи о природе) on Sundays.",
           ["often", "oftens", "oftenly"], "often", ["often не меняется и не имеет -ly здесь."]),
        audio("en.gr.af.ex14", "I never watch horror films.",
              ["I never watch horror films. (Я никогда не смотрю фильмы ужасов.)",
               "I always watch horror films.", "I never watches horror films."],
              "I never watch horror films. (Я никогда не смотрю фильмы ужасов.)", ["Слышно never watch."]),
        ch("en.gr.af.ex15", "I watch the news every day. Значит, I ___ watch the news.",
           ["always", "never", "rarely"], "always", ["Every day = always."], diff=2),
    ]
    return skill("en.gr.adverbs_freq",
                 "Adverbs of frequency (always, often, sometimes, rarely, never)",
                 rule, "Как сказать: «Я всегда смотрю новости»?", steps, e, order=2)


def skill_time():
    rule = ("What time is it? (Который час?): It's five o'clock (ровно пять). "
            "It's half past five (половина шестого, 5:30). It's quarter past three (четверть четвёртого, 3:15). "
            "It's quarter to two (без четверти два, 1:45). Предлоги: at five o'clock; past — half past two; to — quarter to two.")
    steps = ["На часах 5:30.", "30 минут — half past (половина после текущего часа).",
             "It's half past five.", "5:00 = five o'clock; 5:15 = quarter past five; 5:45 = quarter to six."]
    e = [
        ch("en.gr.tm.ex1", "5:00 — It's five ___.",
           ["o'clock (ровно)", "half past", "quarter to"], "o'clock (ровно)", ["Ровное время — o'clock."]),
        ch("en.gr.tm.ex2", "5:30 — It's ___ five.",
           ["half past (половина)", "quarter past", "quarter to"], "half past (половина)", ["30 минут — half past."]),
        ch("en.gr.tm.ex3", "3:15 — It's ___ three.",
           ["quarter past (четверть после)", "quarter to", "half past"], "quarter past (четверть после)",
           ["15 минут — quarter past."]),
        ch("en.gr.tm.ex4", "1:45 — It's quarter ___ two.",
           ["past (после)", "to (до)", "at (в)"], "to (до)", ["Без четверти два = quarter to two."]),
        ch("en.gr.tm.ex5", "We have dinner ___ 6 o'clock.",
           ["in", "on", "at (в)"], "at (в)", ["Точное время: at 6 o'clock."]),
        sc("en.gr.tm.ex6", "Как сказать 2:30?",
           ["It's half to two.", "It's half past two.", "It's two half."], "It's half past two.",
           ["half past + час, который уже начался."]),
        sc("en.gr.tm.ex7", "Как сказать 4:45?",
           ["It's quarter past four.", "It's quarter to five.", "It's quarter to four."],
           "It's quarter to five.", ["4:45 — quarter to five."], diff=2),
        sc("en.gr.tm.ex8", "Как сказать 7:15?",
           ["It's quarter past seven.", "It's quarter to seven.", "It's half past seven."],
           "It's quarter past seven.", ["15 минут после семи — quarter past seven."]),
        txt("en.gr.tm.ex9", "Впиши слово: It's ___ past five. (5:30)", "half", ["5:30 = half past five."], accept=["half"]),
        txt("en.gr.tm.ex10", "Впиши слово: It's quarter ___ two. (1:45)", "to", ["Без четверти — quarter to."], accept=["to"]),
        match("en.gr.tm.ex11", "Соедини время и английскую фразу.",
              [("5:00", "five o'clock"), ("5:15", "quarter past five"),
               ("5:30", "half past five"), ("5:45", "quarter to six")],
              ["past — после часа; to — до следующего часа."]),
        ch("en.gr.tm.ex12", "The bus (автобус) leaves ___ half past five.",
           ["at", "on", "in"], "at", ["at half past five."]),
        audio("en.gr.tm.ex13", "It's half past five.",
              ["It's half past five. (Половина шестого.)", "It's half to five.", "It's quarter past five."],
              "It's half past five. (Половина шестого.)", ["Слышно half past five."]),
        sc("en.gr.tm.ex14", "What time is it? Перевод вопроса:",
           ["Какой сегодня день?", "Который час?", "Сколько это стоит?"], "Который час?",
           ["What time is it? — Который час?"]),
        sc("en.gr.tm.ex15", "It's quarter past ten. Это:",
           ["10:15", "10:45", "10:30"], "10:15", ["quarter past = 15 минут после."], diff=2),
    ]
    return skill("en.gr.telling_time",
                 "What time is it? (Который час?) — o'clock, half past, quarter past/to",
                 rule, "Как сказать 5:30?", steps, e, order=3)


def skill_countable():
    rule = ("Исчисляемые (countable nouns): a sandwich, two sandwiches. "
            "Неисчисляемые (uncountable): some jam (варенье), some juice, some milk — без a/an. "
            "There is a sweet. There are some sweets. В утверждении some; в вопросе и отрицании any. "
            "Is there any food in the fridge? There aren't any apples. There's no sweet.")
    steps = ["Яблоки (apples) — исчисляемые, множественное число.",
             "Вопрос: Are there any apples in the fridge?",
             "Утверждение: There are some apples. Отрицание: There aren't any apples.",
             "Для food (еда, неисчисляемое): Is there any food? There is some food."]
    e = [
        ch("en.gr.ca.ex1", "I'd like ___ sandwich (бутерброд).", ["a", "some", "any"], "a",
           ["Один исчисляемый — a sandwich."]),
        ch("en.gr.ca.ex2", "I'd like ___ jam (варенье).", ["a", "some", "an"], "some",
           ["Jam — неисчисляемое: some jam."]),
        ch("en.gr.ca.ex3", "I'd like ___ sandwiches.", ["a", "some", "an"], "some",
           ["Множественное число: some sandwiches."]),
        ch("en.gr.ca.ex4", "Is there ___ food in the fridge (холодильник)?", ["some", "any", "a"], "any",
           ["В вопросе обычно any."]),
        ch("en.gr.ca.ex5", "There aren't ___ apples (яблоки) on the table.", ["some", "any", "a"], "any",
           ["В отрицании — any."]),
        ch("en.gr.ca.ex6", "There ___ a sweet (конфета) on the table.", ["is", "are", "aren't"], "is",
           ["A sweet — единственное число: There is."]),
        ch("en.gr.ca.ex7", "There ___ some sweets on the table.", ["is", "are", "isn't"], "are",
           ["Sweets — множественное: There are."]),
        sc("en.gr.ca.ex8", "Какое слово неисчисляемое (uncountable)?",
           ["sandwich (бутерброд)", "apple (яблоко)", "juice (сок)"], "juice (сок)",
           ["Сок, молоко, варенье, еда — неисчисляемые."]),
        sc("en.gr.ca.ex9", "Выбери верное предложение.",
           ["There is some jam in the fridge.", "There are a jam in the fridge.", "There is a jam in the fridge."],
           "There is some jam in the fridge.", ["Jam неисчисляемое: there is some jam."], diff=2),
        txt("en.gr.ca.ex10", "Впиши some или any: We have ___ bread (хлеб) at home.",
            "some", ["Утверждение → some."], accept=["some"]),
        txt("en.gr.ca.ex11", "Впиши some или any: Have we got ___ milk (молоко)?",
            "any", ["Вопрос → any."], accept=["any"]),
        cat("en.gr.ca.ex12", "Разложи на исчисляемые (countable) и неисчисляемые (uncountable).",
            [("c", "countable (исчисляемые)"), ("u", "uncountable (неисчисляемые)")],
            [("s", "a sandwich"), ("ap", "an apple"), ("j", "jam"), ("ju", "juice"), ("m", "milk"), ("cr", "a cracker")],
            {"c": ["s", "ap", "cr"], "u": ["j", "ju", "m"]},
            ["Если можно сказать a/an и посчитать — исчисляемое."]),
        match("en.gr.ca.ex13", "Соедини фразу и перевод.",
              [("There is a sweet.", "Есть одна конфета."), ("There are some sweets.", "Есть несколько конфет."),
               ("Is there any food?", "Есть ли еда?"), ("There isn't any jam.", "Варенья нет.")],
              ["some — в утверждении, any — в вопросе и отрицании."]),
        audio("en.gr.ca.ex14", "Is there any food in the fridge?",
              ["Is there any food in the fridge? (В холодильнике есть еда?)",
               "Are there any food in the fridge?", "Is there some foods in the fridge?"],
              "Is there any food in the fridge? (В холодильнике есть еда?)",
              ["Food неисчисляемое: Is there any food…"]),
        ch("en.gr.ca.ex15", "There's ___ sweet on the table. (отрицание: нет конфеты)",
           ["no (нет ни одной)", "any", "some"], "no (нет ни одной)",
           ["There's no sweet. = There isn't a sweet."], diff=2),
    ]
    return skill("en.gr.countable_some_any",
                 "Countable / uncountable, there is/are, some / any / no",
                 rule, "Как спросить: «В холодильнике есть яблоки?»", steps, e, order=1)


def skill_much_many():
    rule = ("A lot of (много) — и с исчисляемыми, и с неисчисляемыми: a lot of vegetables, a lot of fruit. "
            "Many — с исчисляемыми: How many apples? You shouldn't eat many crisps. "
            "Much — с неисчисляемыми: How much juice? You shouldn't eat much ice cream. "
            "В утверждениях чаще a lot of, much/many — в вопросах и отрицаниях.")
    steps = ["Совет: есть много овощей и не есть много чипсов.",
             "You should eat a lot of vegetables (овощи).",
             "Crisps (чипсы) исчисляемые → many: You shouldn't eat many crisps.",
             "Ice cream неисчисляемое → much: You shouldn't eat much ice cream."]
    e = [
        ch("en.gr.mm.ex1", "You should eat ___ vegetables (овощи).",
           ["a lot of (много)", "much", "a"], "a lot of (много)", ["A lot of подходит всегда."]),
        ch("en.gr.mm.ex2", "How ___ apples should we eat a day?",
           ["much", "many (много, с исчисляемыми)", "a lot"], "many (много, с исчисляемыми)",
           ["Apples — исчисляемые: How many…?"]),
        ch("en.gr.mm.ex3", "How ___ juice (сок) should we drink a day?",
           ["many", "much (много, с неисчисляемыми)", "a"], "much (много, с неисчисляемыми)",
           ["Juice неисчисляемое: How much…?"]),
        ch("en.gr.mm.ex4", "You shouldn't eat ___ crisps (чипсы).", ["much", "many", "a"], "many",
           ["Crisps исчисляемые → many."]),
        ch("en.gr.mm.ex5", "You shouldn't eat ___ ice cream (мороженое).", ["much", "many", "a lot"], "much",
           ["Ice cream неисчисляемое → much."]),
        ch("en.gr.mm.ex6", "You should eat ___ fruit (фрукты, в учебнике часто неисчисляемое).",
           ["a lot of", "many", "a"], "a lot of", ["В учебнике: a lot of fruit."]),
        sc("en.gr.mm.ex7", "Выбери верный вопрос.",
           ["How much apples…?", "How many apples…?", "How many juice…?"], "How many apples…?",
           ["Apples — How many; juice — How much."]),
        sc("en.gr.mm.ex8", "Выбери верное предложение.",
           ["How many milk have we got?", "How much milk have we got?", "How much apples have we got?"],
           "How much milk have we got?", ["Milk неисчисляемое → much."], diff=2),
        txt("en.gr.mm.ex9", "Впиши much или many: How ___ sandwiches (бутерброды) would you like?",
            "many", ["Sandwiches исчисляемые → many."], accept=["many"]),
        txt("en.gr.mm.ex10", "Впиши much или many: How ___ water (вода) should I drink?",
            "much", ["Water неисчисляемое → much."], accept=["much"]),
        cat("en.gr.mm.ex11", "С чем употребляются much и many?",
            [("many", "many (исчисляемые)"), ("much", "much (неисчисляемые)")],
            [("ap", "apples"), ("cr", "crisps"), ("ju", "juice"), ("ic", "ice cream"), ("mi", "milk"), ("eg", "eggs")],
            {"many": ["ap", "cr", "eg"], "much": ["ju", "ic", "mi"]},
            ["Можно посчитать? → many. Нет? → much."]),
        match("en.gr.mm.ex12", "Соедини фразу и перевод.",
              [("a lot of vegetables", "много овощей"), ("How many apples?", "Сколько яблок?"),
               ("How much juice?", "Сколько сока?"), ("many crisps", "много чипсов")],
              ["a lot of — универсальное «много»."]),
        audio("en.gr.mm.ex13", "How much juice should we drink a day?",
              ["How much juice should we drink a day? (Сколько сока нам следует пить в день?)",
               "How many juice should we drink a day?", "How much juices should we drink a day?"],
              "How much juice should we drink a day? (Сколько сока нам следует пить в день?)",
              ["Juice — much, не many."]),
        ch("en.gr.mm.ex14", "There is ___ milk in the bottle (бутылка). (много)",
           ["a lot of", "many", "a"], "a lot of", ["В утверждении чаще a lot of."], diff=2),
        ch("en.gr.mm.ex15", "There aren't ___ eggs (яйца) in the fridge.",
           ["much", "many", "a lot"], "many", ["Отрицание + исчисляемые → many."], diff=2),
    ]
    return skill("en.gr.much_many", "a lot of, much, many (много)", rule,
                 "Как сказать: «Тебе следует есть много овощей, но не много чипсов»?",
                 steps, e, order=2, prerequisites=["en.gr.countable_some_any"])


def skill_should():
    rule = ("Should (следует) — совет (advice). You should stay in bed. "
            "Отрицание: should not = shouldn’t. You shouldn’t go to work. "
            "После should — инфинитив без to: should go, should eat. Форма одна для всех лиц.")
    steps = ["У друга головная боль (a headache).",
             "You should stay in bed.",
             "You shouldn’t play computer games.",
             "You should go to the doctor (врач)."]
    e = [
        ch("en.gr.sh.ex1", "You ___ stay in bed (оставаться в постели). (совет при болезни)",
           ["should (следует)", "mustn’t", "shouldn't"], "should (следует)", ["Полезный совет — should."]),
        ch("en.gr.sh.ex2", "You ___ go to work if you've got a temperature (температура).",
           ["should", "shouldn't (не следует)", "can"], "shouldn't (не следует)",
           ["При температуре на работу не следует — shouldn’t."]),
        ch("en.gr.sh.ex3", "You should ___ to the doctor (врач).",
           ["go", "to go", "going"], "go", ["После should — инфинитив без to."], diff=2),
        ch("en.gr.sh.ex4", "He ___ eat a lot of fruit (фрукты).",
           ["should", "shoulds", "shoulding"], "should", ["Should не меняется: he should…"]),
        sc("en.gr.sh.ex5", "I've got a toothache (зубная боль). I should go to the ___.",
           ["doctor (врач)", "cinema (кинотеатр)", "farm (ферма)"], "doctor (врач)",
           ["При зубной боли — к врачу."]),
        sc("en.gr.sh.ex6", "Выбери верный совет при кашле (a cough).",
           ["You should drink cold juice and run.", "You should drink warm tea and stay in bed.", "You shouldn't sleep."],
           "You should drink warm tea and stay in bed.", ["Тёплый чай и постель — разумный совет."]),
        sc("en.gr.sh.ex7", "Выбери верное предложение.",
           ["You should to eat vegetables.", "You should eat vegetables.", "You should eating vegetables."],
           "You should eat vegetables.", ["should + eat (без to)."], diff=2),
        txt("en.gr.sh.ex8", "Впиши should или shouldn’t: You ___ eat many crisps (чипсы) every day.",
            "shouldn't", ["Много чипсов каждый день — shouldn’t."], accept=["shouldn't", "should not"]),
        txt("en.gr.sh.ex9", "Впиши should или shouldn’t: You ___ wear a flicker (фликер) when it's dark (темно).",
            "should", ["В темноте фликер носить следует."], accept=["should"]),
        match("en.gr.sh.ex10", "Соедини проблему и совет.",
              [("I've got a headache. (головная боль)", "You should stay in bed."),
               ("I've got a toothache. (зубная боль)", "You should go to the doctor."),
               ("I eat many crisps.", "You shouldn't eat many crisps."),
               ("I never eat fruit.", "You should eat a lot of fruit.")],
              ["should — полезно; shouldn’t — не стоит."]),
        order("en.gr.sh.ex11", "Собери совет: You should go to the doctor.",
              [("y", "You"), ("s", "should"), ("g", "go"), ("t", "to the doctor.")],
              ["y", "s", "g", "t"], ["Подлежащее + should + инфинитив."]),
        audio("en.gr.sh.ex12", "You should go to the doctor.",
              ["You should go to the doctor. (Тебе следует пойти к врачу.)",
               "You shouldn't go to the doctor.", "You must go to the shop."],
              "You should go to the doctor. (Тебе следует пойти к врачу.)", ["Слышно should go to the doctor."]),
        ch("en.gr.sh.ex13", "___ I drink more water (вода)? — Yes, you should.",
           ["Should", "Do", "Must"], "Should", ["Вопрос-совет: Should I…?"]),
        sc("en.gr.sh.ex14", "Переведи: «Не следует смотреть телевизор всю ночь».",
           ["You should watch TV all night.", "You shouldn't watch TV all night.", "You must watch TV all night."],
           "You shouldn't watch TV all night.", ["Не следует = shouldn’t."]),
        sc("en.gr.sh.ex15", "To be healthy (чтобы быть здоровым), you should ___ every morning.",
           ["do exercises (делать зарядку)", "eat many crisps", "sleep in the lesson"],
           "do exercises (делать зарядку)",
           ["Зарядка, питание, гигиена — советы программы."], diff=2),
    ]
    return skill("en.gr.should", "should / shouldn’t — совет (advice)", rule,
                 "Какой совет дать при головной боли (a headache)?",
                 steps, e, order=3, prerequisites=["en.gr.much_many"])


def skill_must():
    rule = ("Must (должен) — обязанность и строгое правило. You must stop when the traffic lights are red. "
            "must not = mustn’t — запрет: You mustn’t play on the road. После must — инфинитив без to. "
            "should — совет, must — правило или обязанность.")
    steps = ["На красный светофор нужно остановиться — это правило, must.",
             "You must stop.",
             "Запрет: You mustn’t play on the road.",
             "You must wear a flicker (фликер) when it's dark."]
    e = [
        ch("en.gr.mu.ex1", "You ___ stop when the traffic lights (светофор) are red.",
           ["must (должен)", "shouldn't", "can"], "must (должен)", ["Правило дороги — must."]),
        ch("en.gr.mu.ex2", "You ___ play on the road (на дороге).",
           ["must", "mustn't (нельзя)", "should"], "mustn't (нельзя)", ["Играть на дороге запрещено — mustn’t."]),
        ch("en.gr.mu.ex3", "You must ___ a seat belt (ремень безопасности) in a car.",
           ["wear (носить, пристёгивать)", "to wear", "wearing"], "wear (носить, пристёгивать)",
           ["must + wear, без to."], diff=2),
        sc("en.gr.mu.ex4", "You must wear a flicker (фликер) when it's ___.",
           ["dark (темно)", "sunny (солнечно)", "funny (смешно)"], "dark (темно)",
           ["Фликер носят в темноте."]),
        sc("en.gr.mu.ex5", "You mustn’t drive a car if you’re under ___.",
           ["18 (восемнадцать)", "5", "40"], "18 (восемнадцать)",
           ["По учебнику: нельзя водить машину до 18 лет."]),
        sc("en.gr.mu.ex6", "Выбери верное предложение.",
           ["You must to stop.", "You must stop.", "You must stopping."], "You must stop.",
           ["must + инфинитив без to."]),
        sc("en.gr.mu.ex7", "Совет «стоит поесть фруктов» — should. Правило «остановись на красный» — это:",
           ["should", "must", "can"], "must", ["Строгое правило — must."], diff=2),
        txt("en.gr.mu.ex8", "Впиши must или mustn’t: You ___ cross the street when the lights are green (зелёный).",
            "must", ["На зелёный переходить нужно — must."], accept=["must"]),
        txt("en.gr.mu.ex9", "Впиши must или mustn’t: You ___ ride a bike on the road if you’re under 14.",
            "mustn't", ["По учебнику это запрет — mustn’t."], accept=["mustn't", "must not"]),
        match("en.gr.mu.ex10", "Соедини правило и перевод.",
              [("You must stop.", "Ты должен остановиться."),
               ("You mustn't play on the road.", "Нельзя играть на дороге."),
               ("You must wear a seat belt.", "Нужно пристегнуть ремень."),
               ("You must wear a flicker.", "Нужно носить фликер.")],
              ["must — должен; mustn’t — нельзя."]),
        cat("en.gr.mu.ex11", "Разложи на обязанность (must) и запрет (mustn’t).",
            [("must", "must (должен)"), ("mustnt", "mustn’t (нельзя)")],
            [("s", "stop at red lights"), ("b", "wear a seat belt"),
             ("p", "play on the road"), ("d", "drive a car under 18")],
            {"must": ["s", "b"], "mustnt": ["p", "d"]},
            ["Безопасность — must; опасные действия — mustn’t."]),
        audio("en.gr.mu.ex12", "You must stop when the traffic lights are red.",
              ["You must stop when the traffic lights are red. (Нужно остановиться на красный светофор.)",
               "You mustn't stop when the traffic lights are red.", "You should play on the road."],
              "You must stop when the traffic lights are red. (Нужно остановиться на красный светофор.)",
              ["Слышно must stop."]),
        sc("en.gr.mu.ex13", "First you must look left and then ___ when you cross the street.",
           ["right (направо)", "up (вверх)", "back (назад)"], "right (направо)",
           ["Сначала налево, потом направо."]),
        sc("en.gr.mu.ex14", "You must cross the street when the traffic lights are ___.",
           ["red (красный)", "green (зелёный)", "broken (сломан)"], "green (зелёный)",
           ["Переходить — на зелёный."]),
        ch("en.gr.mu.ex15", "We ___ catch them! (Мы должны их поймать!)",
           ["must", "mustn't", "should to"], "must", ["Must — решительная необходимость."], diff=2),
    ]
    return skill("en.gr.must", "must / mustn’t — долженствование и запрет", rule,
                 "Как сказать правило: «Остановись, когда светофор красный»?", steps, e, order=1)


def skill_prepositions():
    rule = ("Предлоги направления: to (к, в), along (вдоль, по), past (мимо), over (через). "
            "Go along Green Street. Go past the bookshop. Go over the bridge. "
            "Turn left (налево), turn right (направо), go straight ahead (прямо). "
            "Места: at (home), behind (за), in front of (перед), between (между), opposite (напротив), next to (рядом с).")
    steps = ["Путь: по улице, мимо магазина, через мост, налево.",
             "Go along the street. Then go past the bookshop.",
             "Go over the bridge. Then turn left.",
             "Дом Лиз — next to the post office (рядом с почтой)."]
    e = [
        ch("en.gr.prp.ex1", "Go ___ Green Street. (по улице, вдоль)",
           ["along (вдоль, по)", "over", "behind"], "along (вдоль, по)", ["Вдоль улицы — along."]),
        ch("en.gr.prp.ex2", "Go ___ the bridge (мост).",
           ["along", "over (через)", "between"], "over (через)", ["Через мост — over the bridge."]),
        ch("en.gr.prp.ex3", "Go ___ the bookshop (книжный магазин).",
           ["past (мимо)", "under", "in"], "past (мимо)", ["Мимо — past."]),
        ch("en.gr.prp.ex4", "The house is ___ the post office (почта).",
           ["next to (рядом с)", "over", "along"], "next to (рядом с)", ["Рядом — next to."]),
        ch("en.gr.prp.ex5", "The bank is ___ the park. (напротив)",
           ["opposite (напротив)", "along", "over"], "opposite (напротив)", ["Напротив — opposite."]),
        ch("en.gr.prp.ex6", "The shop is ___ the church (церковь). (позади)",
           ["behind (за, позади)", "over", "to"], "behind (за, позади)", ["Позади — behind."]),
        ch("en.gr.prp.ex7", "Then turn ___ at the traffic lights (светофор). (налево)",
           ["left (налево)", "straight", "over"], "left (налево)", ["Turn left — поверни налево."]),
        ch("en.gr.prp.ex8", "Go ___ ahead. (прямо)",
           ["straight (прямо)", "left", "past"], "straight (прямо)", ["Go straight ahead — иди прямо."]),
        ch("en.gr.prp.ex9", "I stay ___ home (дома) on Sundays.",
           ["at (в, у)", "to", "on"], "at (в, у)", ["At home — дома."]),
        sc("en.gr.prp.ex10", "Как спросить дорогу до банка?",
           ["How do I get to the nearest bank?", "How I get the bank?", "Where go bank?"],
           "How do I get to the nearest bank?", ["How do I get to…? — Как пройти к…?"]),
        txt("en.gr.prp.ex11", "Впиши предлог: Go ___ the bridge. (через мост)", "over", ["Через мост — over."], accept=["over"]),
        txt("en.gr.prp.ex12", "Впиши слово: Turn ___ (направо).", "right", ["Turn right — направо."], accept=["right"]),
        match("en.gr.prp.ex13", "Соедини английскую фразу и перевод.",
              [("go along the street", "идти по улице"), ("go past the church", "пройти мимо церкви"),
               ("go over the bridge", "пройти по мосту / через мост"), ("turn left", "повернуть налево")],
              ["along — вдоль; past — мимо; over — через."]),
        audio("en.gr.prp.ex14", "Go straight ahead, then turn left.",
              ["Go straight ahead, then turn left. (Иди прямо, затем поверни налево.)",
               "Go over the bridge, then turn right.", "Turn left, then go past the bank."],
              "Go straight ahead, then turn left. (Иди прямо, затем поверни налево.)",
              ["Слышно straight ahead и turn left."]),
        order("en.gr.prp.ex15", "Собери фразу: Go along the street, then turn right.",
              [("g", "Go along the street,"), ("t", "then"), ("r", "turn right.")],
              ["g", "t", "r"], ["Сначала по улице, потом поворот."]),
    ]
    return skill("en.gr.prepositions",
                 "Предлоги места и направления (to, along, past, over, next to…)",
                 rule, "Как объяснить путь: по улице, мимо магазина, через мост, налево?", steps, e, order=2)


def skill_articles():
    rule = ("Артикли: a/an — неопределённый (впервые): a reporter, an apple (an — перед гласным звуком). "
            "The — определённый (уже известный): The reporter asked them some questions. "
            "Zero article с городами, улицами, площадями, странами (обычно) и континентами: I live in Minsk. "
            "Minsk is the capital of Belarus. Belarus is in Europe. Исключения: the UK, the USA.")
    steps = ["Moldy and Rotty saw a reporter — впервые, a reporter.",
             "Потом the reporter — тот самый.",
             "Город и страна без артикля: I live in Minsk.",
             "Исключения: the UK, the USA."]
    e = [
        ch("en.gr.ar.ex1", "Moldy and Rotty saw ___ reporter (репортёр). (впервые)",
           ["a", "the", "an"], "a", ["Впервые — a."]),
        ch("en.gr.ar.ex2", "___ reporter asked them some questions. (тот самый)",
           ["A", "The", "An"], "The", ["Уже известный — the."]),
        ch("en.gr.ar.ex3", "I'd like ___ apple (яблоко).", ["a", "an", "the"], "an",
           ["Apple начинается с гласного звука — an."]),
        ch("en.gr.ar.ex4", "I live ___ Minsk. (нужный вариант без лишнего артикля)",
           ["in", "in the", "at the"], "in", ["С городами zero article: in Minsk."]),
        ch("en.gr.ar.ex5", "Minsk is the capital of ___.",
           ["the Belarus", "Belarus", "a Belarus"], "Belarus", ["Belarus — без артикля."]),
        ch("en.gr.ar.ex6", "Belarus is in ___.",
           ["the Europe", "Europe", "a Europe"], "Europe", ["Континенты без артикля: in Europe."]),
        ch("en.gr.ar.ex7", "People speak English in ___. (Соединённое Королевство)",
           ["UK", "the UK", "a UK"], "the UK", ["the UK — исключение."], diff=2),
        sc("en.gr.ar.ex8", "I live not far from Pobeda Square. Артикль перед названием площади:",
           ["нужен the", "нужен a", "обычно без артикля (zero article)"],
           "обычно без артикля (zero article)", ["Площади — обычно без артикля."], diff=2),
        sc("en.gr.ar.ex9", "Выбери верное предложение.",
           ["I live in the London.", "I live in London.", "I live in a London."],
           "I live in London.", ["Города без артикля."]),
        txt("en.gr.ar.ex10", "Впиши a или an: ___ hour (час) later we went home.",
            "an", ["Hour начинается с гласного звука — an hour."], accept=["an"]),
        txt("en.gr.ar.ex11", "Впиши a или the: I saw a dog. ___ dog was black.",
            "The", ["Второй раз — the dog."], accept=["The", "the"]),
        cat("en.gr.ar.ex12", "Где нужен the, а где артикль не ставят (zero article)?",
            [("the", "нужен the"), ("zero", "без артикля (zero article)")],
            [("uk", "UK / USA"), ("ms", "Minsk"), ("eu", "Europe"), ("by", "Belarus")],
            {"the": ["uk"], "zero": ["ms", "eu", "by"]},
            ["the UK / the USA — исключения."]),
        match("en.gr.ar.ex13", "Соедини правило и пример.",
              [("впервые, один предмет", "a reporter"), ("уже известный предмет", "the reporter"),
               ("перед гласным звуком", "an apple"), ("город без артикля", "in Minsk")],
              ["a/an — новый; the — известный; города — zero article."]),
        audio("en.gr.ar.ex14", "I live in Minsk.",
              ["I live in Minsk. (Я живу в Минске.)", "I live in the Minsk.", "I live in a Minsk."],
              "I live in Minsk. (Я живу в Минске.)", ["Без артикля: in Minsk."]),
        ch("en.gr.ar.ex15", "People speak English in ___.",
           ["the USA", "USA", "a USA"], "the USA", ["the USA — с артиклем the."], diff=2),
    ]
    return skill("en.gr.articles", "Артикли a/an, the и zero article с названиями мест", rule,
                 "Почему сначала a reporter, а потом the reporter? И почему in Minsk без артикля?",
                 steps, e, order=3)


def skill_because():
    rule = ("Союз because (потому что) вводит причину: Town Mouse liked the town because it was interesting. "
            "Сложносочинённые предложения с and (и) и but (но): I was tired, but I was happy.")
    steps = ["Почему мышонок любил город?",
             "Факт: Town Mouse liked the town.",
             "Причина: because it was interesting.",
             "Полностью: Town Mouse liked the town because it was interesting."]
    e = [
        ch("en.gr.bc.ex1", "Town Mouse liked the town ___ it was interesting (интересный).",
           ["because (потому что)", "but (но)", "or (или)"], "because (потому что)",
           ["Причина вводится союзом because."]),
        ch("en.gr.bc.ex2", "Country Mouse didn't like the town ___ it was noisy (шумный).",
           ["because", "and", "so that"], "because", ["Почему не любил — because."]),
        ch("en.gr.bc.ex3", "They made a fire (костёр) ___ it was cold (холодно).",
           ["because", "but", "or"], "because", ["Причина — because."]),
        ch("en.gr.bc.ex4", "I was tired (устал), ___ I was happy (счастлив).",
           ["because", "but (но)", "or"], "but (но)", ["Противопоставление — but."]),
        ch("en.gr.bc.ex5", "I like apples ___ bananas.",
           ["and (и)", "because", "but"], "and (и)", ["Перечисление — and."]),
        sc("en.gr.bc.ex6", "Выбери верное предложение.",
           ["Because it was cold they, made a fire.",
            "They made a fire because it was cold.",
            "They made a fire why it was cold."],
           "They made a fire because it was cold.", ["Because + причина после главной части."]),
        txt("en.gr.bc.ex7", "Впиши союз причины (потому что): She stayed at home ___ she was ill (больна).",
            "because", ["Причина — because."], accept=["because"]),
        txt("en.gr.bc.ex8", "Впиши but или and: I like comedies ___ I never watch horror films.",
            "but", ["Противопоставление — but."], accept=["but"]),
        match("en.gr.bc.ex9", "Соедини союз и значение.",
              [("because", "потому что"), ("and", "и"), ("but", "но"), ("or", "или")],
              ["because вводит причину."]),
        match("en.gr.bc.ex10", "Соедини начало и конец.",
              [("I went to bed early because", "I was tired."),
               ("I like the farm because", "it is quiet."),
               ("We were happy, but", "it was rainy."),
               ("I like tea and", "toast.")],
              ["because + причина; but + противоположная мысль."]),
        audio("en.gr.bc.ex11", "They made a fire because it was cold.",
              ["They made a fire because it was cold. (Они развели костёр, потому что было холодно.)",
               "They made a fire but it was cold.", "They made a fire and it was cold."],
              "They made a fire because it was cold. (Они развели костёр, потому что было холодно.)",
              ["Слышно because it was cold."]),
        ch("en.gr.bc.ex12", "Why (почему) did you go to the museum? — ___ I like history (история).",
           ["Because", "But", "Or"], "Because", ["Ответ на why часто начинается с Because."]),
        ch("en.gr.bc.ex13", "I wanted to play, ___ I had a headache (головная боль).",
           ["but", "because", "and"], "but", ["Хотел, но не мог — but."]),
        sc("en.gr.bc.ex14", "Какой союз вводит причину (reason — причина)?",
           ["and (и)", "because (потому что)", "but (но)"], "because (потому что)",
           ["Причина — because."]),
        order("en.gr.bc.ex15", "Собери предложение: I stayed at home because I was ill.",
              [("i", "I stayed at home"), ("b", "because"), ("w", "I was ill.")],
              ["i", "b", "w"], ["Сначала факт, потом because и причина."]),
    ]
    return skill("en.gr.because", "Союз because (потому что); and / but", rule,
                 "Как объяснить: «Городской мышонок любил город, потому что он был интересный»?",
                 steps, e, order=4)


def skill_future():
    rule = ("Future Simple (будущее простое): will + V (инфинитив). I will see a shark. will = ’ll (I’ll). "
            "Отрицание: will not = won’t. Вопрос: Will you travel tomorrow? Yes, I will. / No, I won’t. "
            "Указатели: tomorrow (завтра), next summer, next year.")
    steps = ["«Я увижу акулу» — будущее.",
             "will + see → I will see a shark. / I’ll see a shark.",
             "Отрицание: I won’t see a shark.",
             "Вопрос: Will you see a shark? — Yes, I will."]
    e = [
        ch("en.gr.fu.ex1", "I ___ see a shark (акула).",
           ["will (буду / будет)", "was", "did"], "will (буду / будет)", ["Будущее — will + see."]),
        ch("en.gr.fu.ex2", "She ___ travel (путешествовать) next summer (следующим летом).",
           ["will", "wills", "is"], "will", ["Will не меняется: she will travel."]),
        ch("en.gr.fu.ex3", "We ___ go by plane (на самолёте).", ["will", "went", "going"], "will", ["will + go."]),
        ch("en.gr.fu.ex4", "I ___ forget my passport (паспорт). (отрицание)",
           ["won't (не буду)", "will", "didn't"], "won't (не буду)", ["will not = won’t."]),
        ch("en.gr.fu.ex5", "___ you travel tomorrow (завтра)?", ["Will", "Do", "Did"], "Will",
           ["Вопрос: Will + подлежащее + V?"]),
        ch("en.gr.fu.ex6", "He will ___ London next year.", ["see", "saw", "sees"], "see",
           ["После will — инфинитив see, не saw."], diff=2),
        sc("en.gr.fu.ex7", "Выбери верное предложение.",
           ["I will to go to England.", "I will go to England.", "I wills go to England."],
           "I will go to England.", ["will + go, без to и без -s."]),
        sc("en.gr.fu.ex8", "Выбери верный краткий ответ на «Will they go by train?»",
           ["Yes, they will.", "Yes, they do.", "Yes, they went."], "Yes, they will.",
           ["Will → Yes, they will. / No, they won’t."]),
        txt("en.gr.fu.ex9", "Впиши will или won’t: Tomorrow (завтра) we ___ visit the museum (музей).",
            "will", ["Завтра — будущее: will."], accept=["will"]),
        txt("en.gr.fu.ex10", "Впиши will или won’t: I ___ be late. I promise (обещаю). (не опоздаю)",
            "won't", ["Обещание не опоздать — won’t."], accept=["won't", "will not"]),
        match("en.gr.fu.ex11", "Соедини форму и значение.",
              [("I will go.", "Я пойду / поеду."), ("I won't go.", "Я не пойду."),
               ("Will you go?", "Ты пойдёшь?"), ("Yes, I will.", "Да.")],
              ["will — будущее; won’t — отрицание."]),
        order("en.gr.fu.ex12", "Собери вопрос: Will you travel tomorrow?",
              [("w", "Will"), ("y", "you"), ("t", "travel"), ("m", "tomorrow?")],
              ["w", "y", "t", "m"], ["Will + подлежащее + инфинитив."]),
        audio("en.gr.fu.ex13", "I will see a shark.",
              ["I will see a shark. (Я увижу акулу.)", "I saw a shark.", "I won't see a shark."],
              "I will see a shark. (Я увижу акулу.)", ["Слышно will see."]),
        sc("en.gr.fu.ex14", "Указатель будущего времени (future time marker):",
           ["yesterday (вчера)", "last summer (прошлым летом)", "next year (в следующем году)"],
           "next year (в следующем году)", ["next / tomorrow — будущее."]),
        sc("en.gr.fu.ex15", "We will go to England ___ plane (самолёт).",
           ["by (на, посредством)", "on", "with"], "by (на, посредством)",
           ["by plane, by train, by bus — способ передвижения."], diff=2),
    ]
    return skill("en.gr.future_will", "Future Simple: will / ’ll / won’t, вопросы Will…?", rule,
                 "Как сказать: «Я увижу акулу» и спросить «Ты увидишь акулу?»", steps, e, order=1)


def skill_plurals_adj():
    rule = ("Особые множественные числа: man — men, woman — women, child — children, "
            "tooth — teeth, foot — feet, goose — geese, mouse — mice, sheep — sheep (одна форма). "
            "Степени сравнения: good — better — the best (хороший — лучше — самый хороший); "
            "bad — worse — the worst (плохой — хуже — самый плохой).")
    steps = ["«Дети» и «лучше».",
             "Child — children (не childs).",
             "Good — better — the best.",
             "It was the best thing I did."]
    e = [
        ch("en.gr.pl.ex1", "one child (ребёнок) — two ___.",
           ["childs", "children (дети)", "childes"], "children (дети)", ["child — children."]),
        ch("en.gr.pl.ex2", "one man (мужчина) — two ___.",
           ["mans", "men (мужчины)", "manses"], "men (мужчины)", ["man — men."]),
        ch("en.gr.pl.ex3", "one woman (женщина) — two ___.",
           ["womans", "women (женщины)", "womens"], "women (женщины)",
           ["woman — women. Произносится /ˈwɪmɪn/."]),
        ch("en.gr.pl.ex4", "one tooth (зуб) — two ___.",
           ["tooths", "teeth (зубы)", "toothes"], "teeth (зубы)", ["tooth — teeth."]),
        ch("en.gr.pl.ex5", "one foot (ступня) — two ___.",
           ["foots", "feet (ступни, футы)", "feets"], "feet (ступни, футы)", ["foot — feet."]),
        ch("en.gr.pl.ex6", "one sheep (овца) — two ___.",
           ["sheeps", "sheep (овцы)", "sheepes"], "sheep (овцы)",
           ["sheep в единственном и множественном одинаково."], diff=2),
        ch("en.gr.pl.ex7", "one mouse (мышь) — two ___.",
           ["mouses", "mice (мыши)", "mices"], "mice (мыши)", ["mouse — mice."], diff=2),
        ch("en.gr.pl.ex8", "one goose (гусь) — two ___.",
           ["gooses", "geese (гуси)", "geeses"], "geese (гуси)", ["goose — geese."], diff=2),
        ch("en.gr.pl.ex9", "This book is good (хороший). That book is ___.",
           ["gooder", "better (лучше)", "more good"], "better (лучше)", ["good — better."]),
        ch("en.gr.pl.ex10", "It was ___ thing I did. (самое лучшее)",
           ["the best (самый хороший)", "the goodest", "better"], "the best (самый хороший)",
           ["Превосходная степень good — the best."]),
        ch("en.gr.pl.ex11", "The weather was bad yesterday. Today it is ___.",
           ["badder", "worse (хуже)", "worst"], "worse (хуже)", ["bad — worse."], diff=2),
        match("en.gr.pl.ex12", "Соедини единственное и множественное число.",
              [("child (ребёнок)", "children"), ("man (мужчина)", "men"),
               ("tooth (зуб)", "teeth"), ("sheep (овца)", "sheep")],
              ["Особые формы нужно запомнить."]),
        match("en.gr.pl.ex13", "Соедини слово и перевод.",
              [("better", "лучше"), ("the best", "самый хороший"),
               ("worse", "хуже"), ("the worst", "самый плохой")],
              ["good → better → the best; bad → worse → the worst."]),
        txt("en.gr.pl.ex14", "Напиши множественное число child (ребёнок).",
            "children", ["child — children."], accept=["children"]),
        audio("en.gr.pl.ex15", "It was the best thing I did.",
              ["It was the best thing I did. (Это было лучшее, что я сделал.)",
               "It was the goodest thing I did.", "It was the better thing I did."],
              "It was the best thing I did. (Это было лучшее, что я сделал.)",
              ["Слышно the best."]),
    ]
    return skill("en.gr.plurals_adj",
                 "Особые множественные числа; good/better/best, bad/worse/worst",
                 rule, "Как сказать «дети» и «это было самое лучшее»?", steps, e, order=2)


def topic(key, title, order, words=None, skills=None, textbook_refs=None, synonyms=None, keywords=None, badge=""):
    t = {"key": key, "title": title, "order": order}
    if textbook_refs:
        t["textbook_refs"] = textbook_refs
    if synonyms:
        t["synonyms"] = synonyms
    if keywords:
        t["keywords"] = keywords
    if badge:
        t["badge_code"] = badge
    if words:
        t["words"] = words
    if skills:
        t["skills"] = skills
    return t


def unit(key, title, quarter, order, topics):
    return {
        "format_version": 1,
        "subject": "en",
        "unit": {"key": key, "title": title, "grade": 5, "quarter": quarter, "order": order},
        "topics": topics,
    }


def build():
    have_got_unit = unit(
        "en.g5.u1", "Лексика 5 класса", 1, 1,
        [topic(
            "en.grammar", "Грамматика 5 класса", 99,
            skills=[skill(
                "en.gr.have_got", "have got / has got (иметь)",
                "I/you/we/they have got (иметь); he/she/it has got. "
                "I have got a brother (брат). She has got a dog (собака). "
                "Отрицание: haven’t got / hasn’t got. Вопрос: Have you got…? Has she got…?",
                "Как сказать «У неё есть сестра (sister)»?",
                [
                    "Подлежащее — she (она).",
                    "Для he/she/it пишем has got (иметь).",
                    "She has got a sister.",
                    "Для I/you/we/they — have got: I have got a brother.",
                ],
                exs_have_got_extra(),
                order=0,
            )],
        )],
    )
    u1 = unit("en.g5.unit1", "Unit 1. School holidays: places to go (Каникулы: куда поехать)", 1, 2, [
        topic("en.u1.vocab", "Лексика: каникулы и места", 1, words=vocab_u1(),
              textbook_refs=["Лапицкая, 2020, ч. 1, Unit 1"],
              synonyms=["каникулы", "лето", "места отдыха"],
              keywords=["holidays", "seaside", "camp"], badge="en_u1"),
        topic("en.u1.grammar", "Грамматика юнита 1: to be и Past Simple", 2,
              skills=[skill_was_were(), skill_was_were_nq(), skill_past_regular(), skill_past_irregular()],
              textbook_refs=["Unit 1, Grammar secret"],
              keywords=["was", "were", "visited", "went"]),
    ])
    u2 = unit("en.g5.unit2", "Unit 2. School holidays: things to do (Каникулы: чем заняться)", 1, 3, [
        topic("en.u2.vocab", "Лексика: чем заняться на каникулах", 1, words=vocab_u2(),
              textbook_refs=["Лапицкая, 2020, ч. 1, Unit 2"],
              synonyms=["музей", "библиотека", "кино"],
              keywords=["museum", "library", "cinema"], badge="en_u2"),
        topic("en.u2.grammar", "Грамматика юнита 2: вопросы и отрицание Past Simple", 2,
              skills=[skill_past_did(), skill_past_wh()],
              textbook_refs=["Unit 2, Grammar secret"],
              keywords=["did", "didn't", "where", "what"]),
    ])
    u3 = unit("en.g5.unit3", "Unit 3. Do you like TV? (Любишь ли ты телевизор?)", 2, 4, [
        topic("en.u3.vocab", "Лексика: телепередачи и время", 1, words=vocab_u3(),
              textbook_refs=["Лапицкая, 2020, ч. 1, Unit 3"],
              synonyms=["телевидение", "передачи", "время"],
              keywords=["comedy", "news", "o'clock"], badge="en_u3"),
        topic("en.u3.grammar", "Грамматика юнита 3: местоимения, частотность, время", 2,
              skills=[skill_object_pronouns(), skill_adverbs_freq(), skill_time()],
              textbook_refs=["Unit 3, Grammar secret"],
              keywords=["them", "always", "half past"]),
    ])
    u4 = unit("en.g5.unit4", "Unit 4. Special days (Особые дни)", 2, 5, [
        topic("en.u4.vocab", "Лексика: праздники", 1, words=vocab_u4(),
              textbook_refs=["Лапицкая, 2020, ч. 1, Unit 4"],
              synonyms=["праздники", "Рождество", "Новый год"],
              keywords=["Christmas", "present", "celebrate"], badge="en_u4"),
    ])
    u5 = unit("en.g5.unit5", "Unit 5. Be healthy! (Будь здоров!)", 3, 6, [
        topic("en.u5.vocab", "Лексика: еда, здоровье, недомогания", 1, words=vocab_u5(),
              textbook_refs=["Лапицкая, 2020, ч. 2, Unit 5"],
              synonyms=["здоровье", "еда", "врач"],
              keywords=["breakfast", "headache", "should"], badge="en_u5"),
        topic("en.u5.grammar", "Грамматика юнита 5: some/any, much/many, should", 2,
              skills=[skill_countable(), skill_much_many(), skill_should()],
              textbook_refs=["Unit 5, Grammar secret"],
              keywords=["some", "any", "should"]),
    ])
    u6 = unit("en.g5.unit6", "Unit 6. In the city (В городе)", 3, 7, [
        topic("en.u6.vocab", "Лексика: город и дорога", 1, words=vocab_u6(),
              textbook_refs=["Лапицкая, 2020, ч. 2, Unit 6"],
              synonyms=["город", "дорога", "Минск"],
              keywords=["map", "bridge", "must"], badge="en_u6"),
        topic("en.u6.grammar", "Грамматика юнита 6: must, предлоги, артикли", 2,
              skills=[skill_must(), skill_prepositions(), skill_articles()],
              textbook_refs=["Unit 6, Grammar secret"],
              keywords=["must", "along", "the UK"]),
    ])
    u7 = unit("en.g5.unit7", "Unit 7. On the farm (На ферме)", 3, 8, [
        topic("en.u7.vocab", "Лексика: ферма и животные", 1, words=vocab_u7(),
              textbook_refs=["Лапицкая, 2020, ч. 2, Unit 7"],
              synonyms=["ферма", "животные", "деревня"],
              keywords=["farm", "sheep", "tractor"], badge="en_u7"),
        topic("en.u7.grammar", "Грамматика юнита 7: because, and, but", 2,
              skills=[skill_because()],
              textbook_refs=["Unit 6–7, Grammar secret: because"],
              keywords=["because", "and", "but"]),
    ])
    u8 = unit("en.g5.unit8", "Unit 8. Our wonderful world (Наш удивительный мир)", 4, 9, [
        topic("en.u8.vocab", "Лексика: континенты и животный мир", 1, words=vocab_u8(),
              textbook_refs=["Лапицкая, 2020, ч. 2, Unit 8"],
              synonyms=["континенты", "животные", "мир"],
              keywords=["continent", "Africa", "ocean"], badge="en_u8"),
        topic("en.u8.grammar", "Грамматика: особые множественные числа и степени сравнения", 2,
              skills=[skill_plurals_adj()],
              textbook_refs=["Программа 29.07.2025 № 134, грамматика V класса"],
              keywords=["children", "better", "sheep"]),
    ])
    u9 = unit("en.g5.unit9", "Unit 9. Travelling (Путешествия)", 4, 10, [
        topic("en.u9.vocab", "Лексика: путешествия и англоязычные страны", 1, words=vocab_u9(),
              textbook_refs=["Лапицкая, 2020, ч. 2, Unit 9"],
              synonyms=["путешествие", "транспорт", "страны"],
              keywords=["plane", "ticket", "will"], badge="en_u9"),
        topic("en.u9.grammar", "Грамматика юнита 9: Future Simple (will)", 2,
              skills=[skill_future()],
              textbook_refs=["Unit 9, Grammar secret: Future Simple"],
              keywords=["will", "won't", "tomorrow"]),
    ])

    units_docs = [have_got_unit, u1, u2, u3, u4, u5, u6, u7, u8, u9]
    out = {"format_version": 1, "units": units_docs}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    n_words = n_skills = n_ex = 0
    keys = []
    for u in units_docs:
        for t in u["topics"]:
            n_words += len(t.get("words") or [])
            for s in t.get("skills") or []:
                n_skills += 1
                n_ex += len(s.get("exercises") or [])
                need = 10 if s["key"] == "en.gr.have_got" else 15  # +5 уже в en_words.json
                assert len(s["exercises"]) >= need, (s["key"], len(s["exercises"]))
                assert s.get("rule_card") and (s.get("worked_example") or {}).get("steps"), s["key"]
                for ex in s["exercises"]:
                    keys.append(ex["key"])
    dup = [k for k in keys if keys.count(k) > 1]
    assert not dup, f"duplicate exercise keys: {set(dup)}"
    print(f"Wrote {OUT} units={len(units_docs)} words={n_words} skills={n_skills} exercises={n_ex}")


if __name__ == "__main__":
    build()
