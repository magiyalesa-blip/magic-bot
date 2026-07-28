import asyncio
import calendar
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardButton, BotCommand, BotCommandScopeDefault, WebAppInfo, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fastapi import FastAPI
import uvicorn

# --- НАСТРОЙКИ ---
# ==========================================
API_TOKEN = '6254732449:AAFvbHPTLLn4NX2U4Grr-f9_uCabdUTcgsA'
BOOKING_WEBSITE_URL = 'https://bronirovanie.magiyalesa.com/'
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = FastAPI()


@app.get("/")
async def root():
    return {"status": "Bot is running!"}


# --- НАСТРОЙКА КНОПКИ "ЗАПУСТИТЬ" В ТЕЛЕГРАМ ---
async def set_bot_commands(bot_instance: Bot):
    """Регистрирует команду /start ("Запустить") в системном меню Telegram"""
    commands = [
        BotCommand(command="start", description="Запустить бота 🚀"),
    ]
    await bot_instance.set_my_commands(commands, scope=BotCommandScopeDefault())


# --- ЛОГИКА КАЛЕНДАРЯ ---
class CalendarCallback(CallbackData, prefix="cal"):
    act: str  # DAY, PREV, NEXT, IGNORE
    year: int
    month: int
    day: int


def generate_calendar(year: int, month: int):
    builder = InlineKeyboardBuilder()

    # 1. Шапка: Месяц и Год
    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    builder.row(InlineKeyboardButton(
        text=f"📅 {month_names[month]} {year}",
        callback_data=CalendarCallback(act="IGNORE", year=year, month=month, day=0).pack()
    ))

    # 2. Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    row = [InlineKeyboardButton(
        text=day,
        callback_data=CalendarCallback(act="IGNORE", year=year, month=month, day=0).pack()
    ) for day in weekdays]
    builder.row(*row)

    # 3. Числа месяца
    cal = calendar.monthcalendar(year, month)
    today = datetime.now().date()

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(
                    text=" ",
                    callback_data=CalendarCallback(act="IGNORE", year=year, month=month, day=0).pack()
                ))
            else:
                day_date = datetime(year, month, day).date()
                if day_date < today:
                    # Прошедшие даты отмечаем замочком
                    row.append(InlineKeyboardButton(
                        text=f"🔒{day}",
                        callback_data=CalendarCallback(act="IGNORE", year=year, month=month, day=day).pack()
                    ))
                else:
                    row.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=CalendarCallback(act="DAY", year=year, month=month, day=day).pack()
                    ))
        builder.row(*row)

    # 4. Кнопки навигации (назад / вперед)
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=CalendarCallback(act="PREV", year=year, month=month, day=1).pack()
        ),
        InlineKeyboardButton(
            text="🏠 В меню",
            callback_data="back_main"
        ),
        InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=CalendarCallback(act="NEXT", year=year, month=month, day=1).pack()
        )
    )
    return builder.as_markup()


# --- ФУНКЦИИ КЛАВИАТУР ---
def get_main_menu():
    """Главное меню бота (логичное и адаптированное под мобайл)"""
    builder = InlineKeyboardBuilder()

    # 1 ряд (Критическая конверсия - приоритет)
    builder.row(InlineKeyboardButton(text="🏡 Свободные дома и цены", callback_data="check_dates"))

    # 2 ряд (Услуги - что мы предлагаем)
    builder.row(InlineKeyboardButton(text="🌿 Услуги и Баня", callback_data="services"))

    # 3 ряд (Акции - продвижение)
    builder.row(InlineKeyboardButton(text="🔥 Акции", callback_data="promo"))

    # 4 ряд (Условия бронирования - важно прочитать перед)
    builder.row(InlineKeyboardButton(text="📜 Правила бронирования", callback_data="rules_menu"))

    # 5 ряд (FAQ и навигация)
    builder.row(
        InlineKeyboardButton(text="❓ Частые вопросы", callback_data="faq_menu"),
        InlineKeyboardButton(text="📍 Где мы находимся", callback_data="location")
    )

    # 6 ряд (Сайт и связь с администратором)
    builder.row(
        InlineKeyboardButton(text="🌐 Перейти на сайт", url="https://magiyalesa.com/"),
        InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/+375297200003")
    )

    return builder.as_markup()


def get_rules_menu():
    """Подменю раздела Правил"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Правила бронирования и предоплата", callback_data="rule_booking"))
    builder.row(InlineKeyboardButton(text="🏡 Правила проживания", callback_data="rule_living"))
    builder.row(InlineKeyboardButton(text="🐾 Проживание с животными", callback_data="rule_animals"))
    builder.row(InlineKeyboardButton(text="📸 Проведение фотосессий", callback_data="rule_photo"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_main"))
    return builder.as_markup()


def get_back_to_rules_button():
    """Кнопка возврата в подменю правил"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к правилам", callback_data="rules_menu"))
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_main"))
    return builder.as_markup()


def get_services_menu():
    """Подменю раздела Дополнительных услуг"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🧖‍♀️ Баня и Купели", callback_data="service_bath"))
    builder.row(InlineKeyboardButton(text="🚲 Велосипеды и Активности", callback_data="service_rent"))
    builder.row(InlineKeyboardButton(text="🥩 Беседки и Гриль", callback_data="service_grill"))
    builder.row(InlineKeyboardButton(text="🎁 Сувенирная лавка", callback_data="service_souvenirs"))

    # Прайс-листы перенесены вниз
    builder.row(InlineKeyboardButton(text="📜 Прайс: Баня и прокат", callback_data="price_main"))
    builder.row(InlineKeyboardButton(text="📜 Прайс: Эликсиры и кальян", callback_data="price_souvenirs"))

    # Кнопка Назад
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main"))
    return builder.as_markup()


def get_back_to_services_button():
    """Кнопка возврата в подменю услуг"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="services"))
    return builder.as_markup()


def get_faq_menu():
    """Подменю раздела FAQ (Частые вопросы)"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🕒 Время заезда и выезда", callback_data="faq_time"))
    builder.row(InlineKeyboardButton(text="💳 Условия оплаты", callback_data="faq_payment"))
    builder.row(InlineKeyboardButton(text="🏡 Об усадьбе и территории", callback_data="faq_about"))
    builder.row(InlineKeyboardButton(text="🍽 Питание и кухня", callback_data="faq_food"))
    builder.row(InlineKeyboardButton(text="📍 Что рядом", callback_data="faq_nearby"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main"))
    return builder.as_markup()


def get_back_to_faq_button():
    """Кнопка возврата в меню FAQ"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="faq_menu"))
    return builder.as_markup()


# --- ОБРАБОТЧИКИ СООБЩЕНИЙ И CALLBACK ---

@dp.message(Command("start"))
@dp.message(F.text.lower().in_(["запустить", "запустить 🚀", "запуск", "/start", "start"]))
async def cmd_start(message: types.Message):
    caption = (
        "Здравствуйте, уважаемый гость! Добро пожаловать в усадьбу 🌲 <b>«Магия леса»</b> (Беловежская пуща).\n\n"
        "Я помогу вам узнать наличие свободных домов, ознакомиться с правилами и забронировать отдых на природе."
    )
    await message.answer_photo(
        photo=FSInputFile("media/welcome.jpg"),
        caption=caption,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.in_(["start", "back_main"]))
async def process_back_main(callback: types.CallbackQuery):
    caption = (
        "Здравствуйте, уважаемый гость! Добро пожаловать в усадьбу 🌲 <b>«Магия леса»</b> (Беловежская пуща).\n\n"
        "Я помогу вам узнать наличие свободных домов, ознакомиться с правилами и забронировать отдых на природе."
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer_photo(
        photo=FSInputFile("media/welcome.jpg"),
        caption=caption,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# --- МЕНЮ ПРАВИЛ ---

@dp.callback_query(F.data == "rules_menu")
async def process_rules_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "📜 <b>Правила усадьбы «Магия леса»</b>\n\n"
        "Пожалуйста, выберите интересующий вас раздел:",
        reply_markup=get_rules_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "rule_booking")
async def process_rule_booking(callback: types.CallbackQuery):
    text = (
        "💳 <b>Правила бронирования и предоплата</b>\n\n"
        "• При бронировании взимается ОБЯЗАТЕЛЬНАЯ предоплата до <b>30%</b>. В праздничные дни — до <b>70%</b>.\n\n"
        "🔄 При отмене или переносе брони предоплата не возвращается, но сохраняется за вами для переноса даты.\n\n"
        "📅 Перенести бронь на другую дату можно <b>1 (один) раз</b> на срок не более 3 месяцев (при наличии свободных мест).\n\n"
        "🚫 Перенос менее чем за 7 дней до заезда невозможен.\n\n"
        "⚠️ <b>Осуществляя бронирование, вы автоматически соглашаетесь с данными правилами.</b>\n\n"
        "❓ <i>Для чего нужна предоплата?</i>\n"
        "💬 <i>Предоплата гарантирует, что вас будут ждать чистые и подготовленные апартаменты.</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_rules_button(), parse_mode="HTML")


@dp.callback_query(F.data == "rule_living")
async def process_rule_living(callback: types.CallbackQuery):
    text = (
        "📜 <b>ПРАВИЛА ПРОЖИВАНИЯ В УСАДЬБЕ</b>\n\n"
        "⏰ <b>Заезд и выезд:</b>\n"
        "• Заезд: с 14:00 до 22:00\n"
        "• Выезд: до 12:00\n\n"
        "👥 <b>Вместимость:</b>\n"
        "• В домах могут проживать строго не более указанного количества человек.\n\n"
        "🌲 <b>Концепция отдыха:</b>\n"
        "• Проживание <b>не предполагает</b> проведение шумных вечеринок и корпоративов. «Магия леса» — это в первую очередь место для единения с природой и близкими.\n\n"
        "🦌 <b>Главный принцип:</b>\n"
        "• Вы — гости в доме дикой природы. Беловежская пуща является заповедником, домом для тысяч видов растений и животных. Ваше пребывание должно быть максимально ненавязчивым.\n\n"
        "❌ <b>Строго ЗАПРЕЩЕНО:</b>\n"
        "• Использование любых пиротехнических средств (круглосуточно!)\n"
        "• Включение громкой музыки, колонок и телевизоров (в домах, на верандах, террасах и во дворе)\n"
        "• Использование звукоусиливающей аппаратуры на открытом воздухе\n"
        "• Курение табачной продукции и кальянов в домах (привозить и курить кальян запрещено)\n"
        "• Громкие крики, пение, шумные игры (особенно в беседках и у мангалов)\n"
        "• Нахождение вблизи зон отдыха других гостей\n"
        "• Пользование уличным бассейном с 22:00 до 10:00\n"
        "• Оставлять детей без присмотра\n"
        "• Самостоятельный выгул животных (питомцы оплачиваются отдельно и находятся только под присмотром хозяев)\n\n"
        "🤫 <b>Режим тишины:</b>\n"
        "• <i>Для животных:</i> шум в вечернее и ночное время вызывает у обитателей пущи сильнейший стресс.\n"
        "• <i>Для гостей:</i> люди приезжают сюда за тишиной.\n"
        "• <i>Статус заповедника:</i> соблюдение тишины — закон на охраняемой территории.\n\n"
        "🧹 <b>Чистота и порядок:</b>\n"
        "• Утилизируйте мусор строго в бытовые контейнеры.\n"
        "• Соблюдайте чистоту на всей территории, используйте урны.\n"
        "• Разведение костров и использование мангалов разрешено <b>только</b> в специально оборудованных местах (абсолютный запрет на костры в лесу).\n\n"
        "⚠️ <b>Ответственность:</b>\n"
        "• Грубое или неоднократное нарушение правил (особенно режима тишины после 22:00 и пожарной безопасности) может стать основанием для досрочного расторжения договора.\n"
        "• Бережно относитесь к имуществу. Обо всех поломках сообщайте администрации.\n\n"
        "📞 <i>По всем возникающим вопросам обращайтесь к администрации. Благодарим за понимание и бережное отношение к заповеднику!</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_rules_button(), parse_mode="HTML")


@dp.callback_query(F.data == "rule_animals")
async def process_rule_animals(callback: types.CallbackQuery):
    text = (
        "🐾 <b>Проживание с животными</b>\n\n"
        "<b>Да, мы рады гостям с питомцами!</b> 🐶🐱\n\n"
        "📋 <b>Важно:</b>\n"
        "• Предупредите нас при бронировании о приезде с питомцем.\n"
        "• Взимается разовый сбор за усиленную уборку и санитарную обработку дома.\n"
        "• Владелец несёт ответственность за соблюдение чистоты и тишины."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_rules_button(), parse_mode="HTML")


@dp.callback_query(F.data == "rule_photo")
async def process_rule_photo(callback: types.CallbackQuery):
    text = (
        "📸 <b>Проведение фотосессий</b>\n\n"
        "Вы можете провести атмосферную фотосессию на территории усадьбы и в домах по предварительному согласованию.\n\n"
        "📱 <b>Для согласования свяжитесь с нами:</b>\n"
        "Телефон / Viber / WhatsApp / Telegram: <b><a href='tel:+375297200003'>+375 (29) 720-00-03</a></b>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_rules_button(), parse_mode="HTML")


# --- ДОПОЛНИТЕЛЬНЫЕ РАЗДЕЛЫ МЕНЮ ---

@dp.callback_query(F.data == "services")
async def process_services(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        text="Усадьба «Магия леса» предлагает множество вариантов сделать ваш отдых еще ярче. Выберите интересующую вас категорию:",
        reply_markup=get_services_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "price_main")
async def process_price_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=FSInputFile("media/price_main.jpg"),
        caption="Актуальные цены на услуги банного комплекса, прокат инвентаря и трансфер.",
        reply_markup=get_back_to_services_button()
    )
    await callback.answer()


@dp.callback_query(F.data == "price_souvenirs")
async def process_price_souvenirs(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=FSInputFile("media/price_souvenirs.jpg"),
        caption="Цены на домашние эликсиры, мёд с пасеки и услуги кальянного мастера.\n\n<i>⚠️ Напоминаем, что курение кальяна разрешено только в открытых беседках.</i>",
        parse_mode="HTML",
        reply_markup=get_back_to_services_button()
    )
    await callback.answer()


@dp.callback_query(F.data == "service_bath")
async def process_service_bath(callback: types.CallbackQuery):
    text = (
        "🧖‍♀️ <b>Наши Банные Комплексы</b>\n\n"
        "Мы предлагаем два формата для идеального расслабления:\n\n"
        "🌿 <b>Обычная баня с купелью:</b> классический пар и освежающая купель для полного релакса.\n"
        "👑 <b>Баня Люкс (до 8-10 человек):</b> просторная зона отдыха, идеальна для большой компании.\n\n"
        "Для бронирования времени, пожалуйста, свяжитесь с нашим менеджером."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_services_button(), parse_mode="HTML")


@dp.callback_query(F.data == "service_rent")
async def process_service_rent(callback: types.CallbackQuery):
    text = (
        "🚲 <b>Активный отдых и Экскурсии</b>\n\n"
        "Исследуйте заповедную природу Беловежской пущи!\n\n"
        "• <b>Прокат велосипедов:</b> отличный способ прокатиться по лесным тропам.\n"
        "• <b>Экскурсии и аренда:</b> поможем организовать ваш досуг на воде и суше.\n\n"
        "Узнать о наличии инвентаря можно у администрации."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_services_button(), parse_mode="HTML")


@dp.callback_query(F.data == "service_grill")
async def process_service_grill(callback: types.CallbackQuery):
    text = (
        "🥩 <b>Беседки и Гриль-зоны</b>\n\n"
        "Для любителей готовить на открытом огне у нас предусмотрены:\n\n"
        "• Уютные открытые беседки\n"
        "• Специализированные беседки-гриль для любой погоды\n\n"
        "Все зоны оборудованы мангалами. Уголь и розжиг можно приобрести на месте."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_services_button(), parse_mode="HTML")


@dp.callback_query(F.data == "service_souvenirs")
async def process_service_souvenirs(callback: types.CallbackQuery):
    text = (
        "🎁 <b>Сувенирная Лавка «Магии леса»</b>\n\n"
        "Заберите частичку пущи с собой или привезите подарок близким:\n\n"
        "🥃 <b>Крафтовые настойки:</b> знаменитая Зубровка, медовуха и другие авторские напитки.\n"
        "🍯 <b>Натуральный мёд:</b> собранный в экологически чистых районах.\n"
        "🪵 <b>Изделия из дерева и керамики:</b> ручная работа местных мастеров.\n"
        "☕️ <b>Брендированные кружки:</b> на долгую память об отдыхе.\n\n"
        "Ассортимент представлен у администратора."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_services_button(), parse_mode="HTML")


# --- РАЗДЕЛ FAQ (ЧАСТЫЕ ВОПРОСЫ) ---

@dp.callback_query(F.data == "faq_menu")
async def process_faq_menu(callback: types.CallbackQuery):
    text = "Здесь мы собрали ответы на самые частые вопросы наших гостей. Выберите интересующую вас тему:"
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=get_faq_menu(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "faq_time")
async def process_faq_time(callback: types.CallbackQuery):
    text = (
        "🕒 <b>Время заезда и выезда</b>\n\n"
        "• <b>Заселение:</b> с 14:00 до 21:00\n"
        "• <b>Выезд:</b> до 12:00\n\n"
        "⚠️ В день приезда обязательно свяжитесь с управляющей Тамарой по телефону <b><a href='tel:+375293139702'>+375 29 313-97-02</a></b> (Viber / Telegram / WhatsApp) для согласования времени заселения.\n\n"
        "❗️ Если вы задерживаетесь в пути, пожалуйста, предупредите нас. Заселение после 21:00 возможно только по предварительному согласованию."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_payment")
async def process_faq_payment(callback: types.CallbackQuery):
    text = (
        "💳 <b>Условия оплаты и предоплаты</b>\n\n"
        "• При бронировании взимается ОБЯЗАТЕЛЬНАЯ предоплата до 30%. В праздничные дни — до 70%.\n"
        "🔄 При отмене или переносе брони предоплата не возвращается, но сохраняется за вами для переноса даты.\n"
        "📅 Перенести бронь на другую дату можно 1 (один) раз на срок не более 3 месяцев (при наличии свободных мест).\n"
        "🚫 Перенос менее чем за 7 дней до заезда невозможен.\n\n"
        "💵 <b>Обратите внимание:</b> окончательный расчет за проживание осуществляется непосредственно при заселении, наличными в белорусских рублях (BYN)."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_about")
async def process_faq_about(callback: types.CallbackQuery):
    text = (
        "🏡 <b>Об усадьбе и территории</b>\n\n"
        "Дома оборудованы всем необходимым для комфортного проживания. В стоимость включены: полотенца, тапочки, средства гигиены.\n\n"
        "🌲 <b>На территории к вашим услугам бесплатно:</b>\n"
        "Террасы, мангалы и принадлежности (у каждого дома), бассейн, батут, детская площадка, прогулочные зоны, настольный теннис, волейбол, футбол, бадминтон, прокат велосипедов и парковка для авто.\n\n"
        "🧖‍♀️ <b>Дополнительные услуги:</b>\n"
        "Вы можете заказать баню, купели и другие активности. Подробнее ознакомиться с ними можно по кнопке ниже."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🧖‍♀️ Услуги и Баня", callback_data="services"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="faq_menu"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_food")
async def process_faq_food(callback: types.CallbackQuery):
    text = (
        "🍽 <b>Питание и кухня</b>\n\n"
        "Мы придерживаемся формата самообслуживания. В каждом доме есть полноценная оборудованная кухня со всей необходимой посудой, а также базовые чай и кофе. Вы можете готовить любимые блюда прямо в доме или использовать мангальные зоны на свежем воздухе.\n\n"
        "🛒 <b>Инфраструктура:</b>\n"
        "Рядом в д. Каменюки есть рестораны и кафе, а также магазины, где можно купить всё необходимое.\n\n"
        "💡 <b>Совет:</b> несмотря на наличие магазинов, мы рекомендуем приобретать основные продукты для отдыха заранее."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_nearby")
async def process_faq_nearby(callback: types.CallbackQuery):
    text = (
        "📍 <b>Что находится рядом с нами</b>\n\n"
        "Наша усадьба расположена в уникальном историческом и природном месте. Совсем рядом с нами:\n\n"
        "🌲 Реликтовый первобытный лес\n"
        "🦬 Зубры в естественной среде обитания\n"
        "🎅 Поместье Деда Мороза\n"
        "🏛 Музей природы\n"
        "🦌 Экскурсионные вольеры с животными\n"
        "🏺 Археологический музей под открытым небом\n"
        "🛖 Музей народного быта и старинных технологий\n"
        "🚲 Велосипедные и пешеходные маршруты\n"
        "👑 Царский тракт"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "promo")
async def process_promo(callback: types.CallbackQuery):
    await callback.message.delete()
    text = (
        "🎁 <b>Специальные предложения усадьбы «Магия леса»</b>\n\n"
        "🎂 <b>СКИДКА 10% В ДЕНЬ РОЖДЕНИЯ</b>\n"
        "<i>Сезонная скидка</i>\n"
        "Ваш праздничный бонус. Покажите паспорт при заселении и заберите подарок! (Действует за 3 дня до и 3 дня после праздника).\n\n"
        "📆 <b>СКИДКА 10% НА ПРОЖИВАНИЕ ОТ 5 ДНЕЙ</b>\n"
        "<i>Выгода очевидна</i>\n"
        "Всё успеть посмотреть и как следует отдохнуть с дополнительной выгодой.\n\n"
        "💼 <b>БУДНИ СО СКИДКОЙ 10%</b>\n"
        "Отдых по будням от 2-х ночей существенно дешевле, чем в выходные.\n\n"
        "🧖‍♀️ <b>НЕДЕЛЯ РЕЛАКСА (Для ценителей)</b>\n"
        "При бронировании отдыха от 7 ночей одна топка бани — абсолютно бесплатно!\n\n"
        "🌲 <b>ОТПУСК В БЕЛОВЕЖСКОЙ ПУЩЕ</b>\n"
        "<i>Постоянная акция</i>\n"
        "При бронировании от 10 дней, одиннадцатый день — в подарок! Отдыхайте в удовольствие!"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎟 Забронировать по акции", web_app=WebAppInfo(url=BOOKING_WEBSITE_URL)))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_main"))

    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "location")
async def process_location(callback: types.CallbackQuery):
    await callback.message.delete()
    text = (
        "📍 <b>Как к нам добраться</b>\n\n"
        "Усадьба «Магия Леса» находится внутри заповедника, в 7 км от центрального входа в д. Каменюки.\n\n"
        "🚗 <b>Ваш маршрут:</b>\n"
        "Каменец → Каменюки → Пашуки (КПП) → Гвоздь 1, д. 4\n\n"
        "⚠️ <b>ВАЖНО: Въезд возможен ТОЛЬКО через КПП в д. Пашуки!</b> Через другие пропускные пункты вас не пропустят. От КПП до усадьбы останется проехать около 2 км.\n\n"
        "Нажмите на кнопку ниже, чтобы построить готовый маршрут прямо до усадьбы (навигатор автоматически поведет вас через нужный пропускной пункт):"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Маршрут в Яндекс.Навигатор", url="https://yandex.ru/maps/?rtext=~52.527526,23.860374~52.528997,23.879703"))
    builder.row(InlineKeyboardButton(text="🗺 Маршрут в Google Maps", url="https://www.google.com/maps/dir/?api=1&destination=52.528997,23.879703&waypoints=52.527526,23.860374&travelmode=driving"))
    builder.row(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_main"))

    await callback.message.answer(text=text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# --- ОБРАБОТКА ПОИСКА И КАЛЕНДАРЯ ---

@dp.callback_query(F.data == "check_dates")
async def process_booking(callback: types.CallbackQuery):
    now = datetime.now()
    await callback.message.delete()
    await callback.message.answer(
        "📅 <b>Выберите дату заезда:</b>\n"
        "<i>(Даты, выделенные 🔒, являются прошедшими и недоступны для выбора)</i>",
        reply_markup=generate_calendar(now.year, now.month),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(CalendarCallback.filter())
async def process_calendar(callback: types.CallbackQuery, callback_data: CalendarCallback):
    act = callback_data.act
    year = callback_data.year
    month = callback_data.month

    if act == "IGNORE":
        if callback_data.day > 0:
            await callback.answer("⚠️ Нельзя выбрать прошедшую дату.", show_alert=True)
        else:
            await callback.answer()
        return

    if act == "PREV":
        if month == 1:
            await callback.message.edit_reply_markup(reply_markup=generate_calendar(year - 1, 12))
        else:
            await callback.message.edit_reply_markup(reply_markup=generate_calendar(year, month - 1))
        await callback.answer()
        return

    if act == "NEXT":
        if month == 12:
            await callback.message.edit_reply_markup(reply_markup=generate_calendar(year + 1, 1))
        else:
            await callback.message.edit_reply_markup(reply_markup=generate_calendar(year, month + 1))
        await callback.answer()
        return

    if act == "DAY":
        selected_date = datetime(year, month, callback_data.day)
        next_day_date = selected_date + timedelta(days=1)

        dfrom = selected_date.strftime("%Y-%m-%d")
        dto = next_day_date.strftime("%Y-%m-%d")

        formatted_checkin = selected_date.strftime("%d.%m.%Y")
        formatted_checkout = next_day_date.strftime("%d.%m.%Y")

        booking_url = f"https://bronirovanie.magiyalesa.com/?dfrom={dfrom}&dto={dto}"

        text = (
            f"📅 <b>Выбрана дата заезда:</b> {formatted_checkin}\n"
            f"📅 <b>Дата выезда (1 ночь):</b> {formatted_checkout}\n\n"
            f"Для просмотра свободных домов и актуальных цен перейдите на наш сайт бронирования:"
        )

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔎 Посмотреть свободные дома", web_app=WebAppInfo(url=booking_url)))
        builder.row(InlineKeyboardButton(text="⬅️ Выбрать другую дату", callback_data="check_dates"))
        builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_main"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer()


# --- ЗАПУСК БОТА ЧЕРЕЗ СОБЫТИЕ СЕРВЕРА ---

@app.on_event("startup")
async def on_startup():
    """Эта функция автоматически сработает при старте сервера на Render"""
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)
    
    # Запускаем поллинг бота в фоновом режиме, чтобы не блокировать веб-сервер
    asyncio.create_task(dp.start_polling(bot))
    logging.info("Бот успешно запущен в фоновом режиме!")


if __name__ == "__main__":
    # Этот блок нужен только если вы запускаете бота локально с компьютера через python bot.py
    async def local_main():
        await bot.delete_webhook(drop_pending_updates=True)
        await set_bot_commands(bot)
        await dp.start_polling(bot)

    asyncio.run(local_main())
