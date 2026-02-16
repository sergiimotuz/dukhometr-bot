def t(lang: str, key: str, **kwargs) -> str:
    lang = (lang or "ua").lower()
    if lang not in ("ua", "en"):
        lang = "ua"

    UA = {
        "welcome": "Духометр — приватний щоденник стану.\n\nОбери дію:",
        "menu_add": "➕ Додати запис",
        "menu_day": "🧾 Мій день",
        "menu_chart": "📈 Графік",
        "menu_week": "📊 Тижневий звіт",
        "menu_settings": "⚙️ Налаштування",
        "menu_pro": "⭐ Pro (скоро)",
        "add_type": "Що фіксуємо?",
        "type_sin": "😔 Гріх",
        "type_good": "🤝 Добра справа",
        "type_thought": "💭 Думка",
        "saved": "Записано ✅",
        "today_summary": "Сьогодні ({d}):\nПлюс: {pos}\nМінус: {neg}\nІндекс: {idx}/100",
        "week_summary": "Останні 7 днів ({d1}—{d2}):\nПлюс: {pos}\nМінус: {neg}\nСередній індекс: {avg}/100",
        "pro_soon": "⭐ Pro буде пізніше.",
        "settings": "Налаштування:",
        "choose_lang": "Обери мову:",
        "choose_tradition": "Обери традицію:",
        "lang_set": "Мову встановлено: {lang}",
        "trad_set": "Традицію встановлено: {trad}",
    }

    EN = {
        "welcome": "Duhometr — private inner state journal.\n\nChoose action:",
        "menu_add": "➕ Add entry",
        "menu_day": "🧾 My day",
        "menu_chart": "📈 Chart",
        "menu_week": "📊 Weekly report",
        "menu_settings": "⚙️ Settings",
        "menu_pro": "⭐ Pro (soon)",
        "add_type": "What to log?",
        "type_sin": "😔 Sin",
        "type_good": "🤝 Good deed",
        "type_thought": "💭 Thought",
        "saved": "Saved ✅",
        "today_summary": "Today ({d}):\nPlus: {pos}\nMinus: {neg}\nIndex: {idx}/100",
        "week_summary": "Last 7 days ({d1}—{d2}):\nPlus: {pos}\nMinus: {neg}\nAvg index: {avg}/100",
        "pro_soon": "⭐ Pro will be added later.",
        "settings": "Settings:",
        "choose_lang": "Choose language:",
        "choose_tradition": "Choose tradition:",
        "lang_set": "Language set: {lang}",
        "trad_set": "Tradition set: {trad}",
    }

    table = UA if lang == "ua" else EN
    txt = table.get(key, key)
    return txt.format(**kwargs)
