import os
from datetime import date
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import matplotlib.pyplot as plt

import db as DB
from i18n import t
from catalog import TRADITIONS, SINS, GOODS, THOUGHTS

from aiogram import F
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from io import BytesIO
import matplotlib.pyplot as plt
from datetime import date

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ua")
DEFAULT_TRADITION = os.getenv("DEFAULT_TRADITION", "neutral_values")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

pool = None

def kb_main(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "menu_add"), callback_data="add")
    kb.button(text=t(lang, "menu_day"), callback_data="day")
    kb.button(text=t(lang, "menu_chart"), callback_data="chart")
    kb.button(text=t(lang, "menu_week"), callback_data="week")
    kb.button(text=t(lang, "menu_settings"), callback_data="settings")
    kb.button(text=t(lang, "menu_pro"), callback_data="pro")
    kb.adjust(1)
    return kb.as_markup()

def kb_lang():
    kb = InlineKeyboardBuilder()
    kb.button(text="Українська", callback_data="lang:ua")
    kb.button(text="English", callback_data="lang:en")
    kb.adjust(2)
    return kb.as_markup()

def kb_trad(lang: str):
    kb = InlineKeyboardBuilder()
    for key, names in TRADITIONS:
        kb.button(text=names.get(lang, names["ua"]), callback_data=f"trad:{key}")
    kb.adjust(1)
    return kb.as_markup()

def kb_add_type(lang: str):
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "type_sin"), callback_data="type:sin")
    kb.button(text=t(lang, "type_good"), callback_data="type:good")
    kb.button(text=t(lang, "type_thought"), callback_data="type:thought")
    kb.adjust(1)
    return kb.as_markup()

def kb_items(lang: str, typ: str):
    items = SINS if typ == "sin" else GOODS if typ == "good" else THOUGHTS
    kb = InlineKeyboardBuilder()
    for key, ua, en, w in items:
        name = ua if lang == "ua" else en
        kb.button(text=f"{name} (w{w})", callback_data=f"item:{typ}:{key}:{w}")
    kb.adjust(1)
    return kb.as_markup()

def kb_thought_polarity(lang: str, item_key: str, w: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="➕", callback_data=f"pol:{item_key}:{w}:1")
    kb.button(text="➖", callback_data=f"pol:{item_key}:{w}:-1")
    kb.button(text="0", callback_data=f"pol:{item_key}:{w}:0")
    kb.adjust(3)
    return kb.as_markup()

def chart_png(series, path):
    xs = [d for d,_ in series]
    ys = [v for _,v in series]
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.ylim(0, 100)
    plt.title("Duhometr — Index (14 days)")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()

@dp.message(F.text.in_({"/start", "start"}))
async def start(m: Message):
    global pool
    u = await DB.ensure_user(pool, m.from_user.id, DEFAULT_LANG, DEFAULT_TRADITION)
    lang = u["lang"]
    await m.answer(t(lang, "welcome"), reply_markup=kb_main(lang))

@dp.callback_query(F.data == "add")
async def add(c: CallbackQuery):
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]
    await c.message.answer(t(lang, "add_type"), reply_markup=kb_add_type(lang))
    await c.answer()

@dp.callback_query(F.data.startswith("type:"))
async def pick_type(c: CallbackQuery):
    typ = c.data.split(":")[1]
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]
    await c.message.answer("OK", reply_markup=kb_items(lang, typ))
    await c.answer()

@dp.callback_query(F.data.startswith("item:"))
async def pick_item(c: CallbackQuery):
    _, typ, key, w = c.data.split(":")
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]

    w = int(w)
    if typ == "sin":
        await DB.add_event(pool, c.from_user.id, date.today(), "sin", key, -1, w)
        await c.message.answer(t(lang, "saved"), reply_markup=kb_main(lang))
    elif typ == "good":
        await DB.add_event(pool, c.from_user.id, date.today(), "good", key, 1, w)
        await c.message.answer(t(lang, "saved"), reply_markup=kb_main(lang))
    else:
        await c.message.answer("Polarity?", reply_markup=kb_thought_polarity(lang, key, w))
    await c.answer()

@dp.callback_query(F.data.startswith("pol:"))
async def pick_pol(c: CallbackQuery):
    _, key, w, pol = c.data.split(":")
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]
    await DB.add_event(pool, c.from_user.id, date.today(), "thought", key, int(pol), int(w))
    await c.message.answer(t(lang, "saved"), reply_markup=kb_main(lang))
    await c.answer()

@dp.callback_query(F.data == "day")
async def my_day(c: CallbackQuery):
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]
    pos, neg, idx = await DB.day_summary(pool, c.from_user.id, date.today())
    await c.message.answer(t(lang, "today_summary", d=date.today().isoformat(), pos=pos, neg=neg, idx=idx),
                           reply_markup=kb_main(lang))
    await c.answer()

@dp.callback_query(F.data == "week")
async def week(c: CallbackQuery):
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]
    d1, d2, pos, neg, avg = await DB.week_summary(pool, c.from_user.id)
    await c.message.answer(t(lang, "week_summary", d1=d1, d2=d2, pos=pos, neg=neg, avg=avg),
                           reply_markup=kb_main(lang))
    await c.answer()
    
@dp.message(F.text == "📈 Графік")
async def chart(m):
    await DB.ensure_user(pool, m.from_user.id)

    series = await DB.series_last_days(pool, m.from_user.id, days=14)
    xs = [d.strftime("%d.%m") for (d, idx, pos, neg) in series]
    ys = [idx for (d, idx, pos, neg) in series]

    fig = plt.figure()
    plt.plot(xs, ys)
    plt.ylim(0, 100)
    plt.title("Духовний індекс за 14 днів")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    await m.answer_photo(BufferedInputFile(buf.read(), filename="chart.png"),
                         caption="Ось твій графік за 14 днів (0–100).")

@dp.callback_query(F.data == "chart")
async def chart(c: CallbackQuery):
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]
    series = await DB.series_14d(pool, c.from_user.id, 13)
    path = f"chart_{c.from_user.id}.png"
    chart_png(series, path)
    await c.message.answer_photo(photo=open(path, "rb"),
                                 caption="📈 14 days",
                                 reply_markup=kb_main(lang))
    await c.answer()

@dp.callback_query(F.data == "pro")
async def pro(c: CallbackQuery):
    u = await DB.get_user(pool, c.from_user.id)
    lang = u["lang"]
    await c.message.answer(t(lang, "pro_soon"), reply_markup=kb_main(lang))
    await c.answer()

async def main():
    global pool
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var is required")
    pool = await DB.pool()
    await DB.init_db(pool)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    
def settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇦 Українська", callback_data="set_lang:ua"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en")],
        [InlineKeyboardButton(text="⚖️ Neutral values", callback_data="set_trad:neutral_values"),
         InlineKeyboardButton(text="☦️ Orthodox", callback_data="set_trad:orthodox")],
        [InlineKeyboardButton(text="🕒 TZ +02:00", callback_data="set_tz:+02:00"),
         InlineKeyboardButton(text="🕒 TZ +01:00", callback_data="set_tz:+01:00")],
    ])

@dp.message(F.text == "⚙️ Налаштування")
async def settings(m):
    await DB.ensure_user(pool, m.from_user.id)
    await m.answer("Налаштування:", reply_markup=settings_kb())

@dp.callback_query(F.data.startswith("set_lang:"))
async def cb_set_lang(c):
    lang = c.data.split(":", 1)[1]
    await DB.set_lang(pool, c.from_user.id, lang)
    await c.answer("Мову збережено ✅", show_alert=False)

@dp.callback_query(F.data.startswith("set_trad:"))
async def cb_set_trad(c):
    trad = c.data.split(":", 1)[1]
    await DB.set_tradition(pool, c.from_user.id, trad)
    await c.answer("Традицію збережено ✅", show_alert=False)

@dp.callback_query(F.data.startswith("set_tz:"))
async def cb_set_tz(c):
    tz = c.data.split(":", 1)[1]
    await DB.set_tz_offset(pool, c.from_user.id, tz)
    await c.answer("Часовий пояс збережено ✅", show_alert=False)
