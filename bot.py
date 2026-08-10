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

# --- ОБЯЗАТЕЛЬНАЯ СТРОКА ДЛЯ RENDER ---
app = FastAPI()


@app.get("/")
async def root():
    return {"status": "Bot is active!"}


@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)
    asyncio.create_task(dp.start_polling(bot))


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
    """Главное меню бота"""
    builder = InlineKeyboardBuilder()

    # Короткие кнопки ставим по две в ряд
    builder.row(
        InlineKeyboardButton(text="❓ Частые вопросы (FAQ)", callback_data="faq_menu"),
        InlineKeyboardButton(text="🔥 Акции", callback_data="promo")
    )

    # Длинные кнопки по одной на всю ширину
    builder.row(InlineKeyboardButton(text="🏡 Свободные дома, цены, бронирование", web_app=WebAppInfo(url=BOOKING_WEBSITE_URL)))
    builder.row(InlineKeyboardButton(text="🌿 Дополнительные платные услуги и баня", callback_data="services"))

    # Две относительно короткие кнопки вместе
    builder.row(
        InlineKeyboardButton(text="📜 Правила бронирования", callback_data="rules_menu"),
        InlineKeyboardButton(text="📍 Как к нам добраться", callback_data="location")
    )

    # Ссылки на сайт и Instagram в одном ряду (без лишних стрелочек в тексте)
    builder.row(
        InlineKeyboardButton(text="🌐 Сайт", url=BOOKING_WEBSITE_URL),
        InlineKeyboardButton(text="📸 Instagram", url="https://www.instagram.com/magya_lesa/")
    )

    # Контакты выносим по одной в ряд
    builder.row(InlineKeyboardButton(text="👩‍💼 Связаться с администратором", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="📞 Связаться с управляющим", url="https://t.me/+375297200003"))

    return builder.as_markup()


def get_rules_menu():
    """Меню правил усадьбы"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚠️ Главное правило", callback_data="rule_main"))
    builder.row(InlineKeyboardButton(text="💳 Правила бронирования и предоплата", callback_data="rule_booking"))
    builder.row(InlineKeyboardButton(text="🏡 Правила проживания", callback_data="rule_living"))
    builder.row(InlineKeyboardButton(text="👥 Отдых большой компанией", callback_data="rule_company"))
    builder.row(InlineKeyboardButton(text="🐾 Проживание с животными", callback_data="rule_pets"))
    builder.row(InlineKeyboardButton(text="📸 Проведение фотосессий", callback_data="rule_photos"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_main"))
    return builder.as_markup()


def get_back_to_rules_button():
    """Кнопка возврата в подменю правил"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к правилам", callback_data="rules_menu"))
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_main"))
    return builder.as_markup()


def get_services_menu():
    """Подменю раздела дополнительных услуг и бани"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🧖‍♀️ Баня и Купели", callback_data="service_bath_pools"))
    builder.row(InlineKeyboardButton(text="🚲 Велосипеды и Активности", callback_data="service_bikes_active"))
    builder.row(InlineKeyboardButton(text="🥩 Беседки и Гриль", callback_data="service_grill"))
    builder.row(InlineKeyboardButton(text="🥃 Домашние эликсиры", callback_data="service_elixirs"))
    builder.row(InlineKeyboardButton(text="💨 Кальян", callback_data="service_hookah"))
    builder.row(InlineKeyboardButton(text="🍯 Мёд с пасеки", callback_data="service_honey"))
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
    builder.row(InlineKeyboardButton(text="🏡 Об усадьбе и территории", callback_data="faq_about"))
    builder.row(InlineKeyboardButton(text="🎁 Что включено в стоимость", callback_data="faq_included"))
    builder.row(InlineKeyboardButton(text="🕒 Время заезда и выезда", callback_data="faq_time"))
    builder.row(InlineKeyboardButton(text="💳 Условия оплаты", callback_data="faq_payment"))
    builder.row(InlineKeyboardButton(text="💵 Окончательный расчёт", callback_data="faq_final_payment"))
    builder.row(InlineKeyboardButton(text="🍽 Питание, магазины, рестораны", callback_data="faq_food"))
    builder.row(InlineKeyboardButton(text="🚗 Трансфер и маршрут", callback_data="faq_transfer"))
    builder.row(InlineKeyboardButton(text="📍 Что рядом", callback_data="faq_nearby"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main"))
    return builder.as_markup()


def get_back_to_faq_button():
    """Кнопка возврата в меню FAQ"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="faq_menu"))
    return builder.as_markup()


def get_back_to_main_button():
    """Кнопка возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_main"))
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

@dp.callback_query(F.data.in_({"rules_menu", "rules"}))
async def process_rules_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "📜 <b>Правила усадьбы «Магия леса»</b>\n\n"
        "Пожалуйста, выберите интересующий вас раздел:",
        reply_markup=get_rules_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "rule_main")
async def process_rule_main(callback: types.CallbackQuery):
    text = (
        "⚠️ <b>Главное правило</b>\n\n"
        "Осуществляя бронирование, вы автоматически соглашаетесь с данными правилами."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к правилам", callback_data="rules_menu"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "rule_booking")
async def process_rule_booking(callback: types.CallbackQuery):
    text = (
        "💳 <b>Правила бронирования и предоплата</b>\n\n"
        "• При бронировании взимается ОБЯЗАТЕЛЬНАЯ предоплата до <b>30%</b>. В праздничные дни — до <b>70%</b>.\n\n"
        "🔄 При отмене или переносе брони предоплата не возвращается, но сохраняется за вами для переноса даты.\n\n"
        "📅 Перенести бронь на другую дату можно <b>1 (один) раз</b> на срок не более 3 месяцев (при наличии свободных мест).\n\n"
        "🚫 Перенос менее чем за 7 дней до заезда невозможен.\n\n"
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

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📞 Связаться с администратором", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к правилам", callback_data="rules_menu"))
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_main"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.in_({"rule_company", "rule_big_company"}))
async def process_rule_big_company(callback: types.CallbackQuery):
    text = (
        "👥 <b>Отдых большой компанией:</b>\n\n"
        "• Если вы планируете поездку большой компанией (например, 6–9 человек), система при выборе общего числа гостей может ограничивать выбор.\n"
        "• Однако вы можете с легкостью арендовать несколько уютных домов, расположенных рядом друг с другом!\n"
        "• Для этого в модуле бронирования указывайте меньшее количество гостей (например, до 3 человек на один дом), подбирайте и бронируйте несколько свободных домиков параллельно.\n\n"
        "💡 <i>Например: компания из 9 человек может с комфортом разместиться в 3 домах по 3 человека, арендованных рядом.</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_rules_button(), parse_mode="HTML")


@dp.callback_query(F.data.in_({"rule_pets", "rule_animals"}))
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


@dp.callback_query(F.data.in_({"rule_photos", "rule_photo"}))
async def process_rule_photo(callback: types.CallbackQuery):
    text = (
        "📸 <b>Проведение фотосессий</b>\n\n"
        "Вы можете провести атмосферную фотосессию на территории усадьбы и в домах по предварительному согласованию.\n\n"
        "📱 <b>Для согласования свяжитесь с нами:</b>\n"
        "Телефон / Viber / WhatsApp / Telegram: <b><a href='tel:+375297200003'>+375 (29) 720-00-03</a></b>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_rules_button(), parse_mode="HTML")


# --- ДОПОЛНИТЕЛЬНЫЕ РАЗДЕЛЫ МЕНЮ ---

@dp.callback_query(F.data == "my_books")
async def process_my_books(callback: types.CallbackQuery):
    text = (
        "📋 <b>Информация о ваших бронированиях</b>\n\n"
        "Чтобы уточнить статус вашего бронирования, внести изменения или получить подтверждение, пожалуйста, укажите ваше имя и номер телефона администратору.\n\n"
        "📞 <b>Отдел бронирования:</b>\n"
        "Телефон / WhatsApp / Telegram: <b><a href='tel:+375297200003'>+375 (29) 720-00-03</a></b>\n"
        "🌐 <b>Сайт:</b> <a href='https://bronirovanie.magiyalesa.com/'>bronirovanie.magiyalesa.com</a>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_main_button(), parse_mode="HTML")


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


@dp.callback_query(F.data.in_({"service_bath", "service_bath_pools"}))
async def process_service_bath_pools(callback: types.CallbackQuery):
    await callback.answer()

    text_caption = (
        "🧖‍♀️ <b>Баня и купели</b>\n\n"
        "На территории усадьбы находятся две бани:\n"
        "1. <b>Баня с горячей купелью</b> (до 6 человек).\n"
        "2. <b>Банный СПА-комплекс Люкс</b> (до 10 человек) — идеально для большой компании.\n\n"
        "🍃 <b>Ваш перезагруз в «Магии леса»</b>\n"
        "Почувствуйте, как горячий пар снимает городскую усталость, а контрастная купель дарит невероятный заряд бодрости. Это идеальное место, чтобы восстановить силы после прогулок по Беловежской пуще, согреться в прохладный вечер или устроить душевный праздник в кругу друзей.\n\n"
        "Аромат натурального дерева, жар парной и чистейший лесной воздух — это отдых, который останется в памяти надолго.\n\n"
        "💳 <i>Актуальные цены на услуги представлены на фото.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Забронировать баню", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="services"))
    keyboard = builder.as_markup()

    photo_path = "media/banya_price_list.jpg" if os.path.exists("media/banya_price_list.jpg") else "banya_price_list.jpg"
    try:
        photo = types.FSInputFile(photo_path) if os.path.exists(photo_path) else None
        if photo:
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo,
                caption=text_caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
        else:
            await callback.message.edit_text(text_caption, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка при отправке фото бани: {e}")
        await callback.message.edit_text(text_caption, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data.in_({"service_rent", "service_bikes_active"}))
async def process_service_bikes(callback: types.CallbackQuery):
    text = (
        "🚲 <b>Прокат велосипедов — свобода, природа и адреналин!</b>\n\n"
        "Хотите почувствовать дыхание древнего леса, промчаться по тропам, где когда-то ходили зубры, и увидеть нетронутую красоту Беловежской пущи? Наши велосипеды — ваш лучший проводник!\n\n"
        "🌳 <b>Лучшие веломаршруты по заповеднику:</b>\n"
        "• <b>«Царская тропа»</b> — живописный путь через дубравы и сосновые боры.\n"
        "• <b>«Зубриный след»</b> — шанс встретить величественных обитателей пущи.\n"
        "• <b>Маршруты на любой вкус</b> — от лёгких прогулочных до экстремальных треков.\n\n"
        "<i>Крутите педали, вдыхайте аромат хвои и открывайте Беловежскую пущу по-новому!</i>\n\n"
        "💳 <b>Аренда велосипеда:</b> 20 BYN / 3 часа\n\n"
        "〰️〰️〰️〰️〰️\n\n"
        "🛴 <b>Прокат самокатов — спокойствие и комфорт</b>\n\n"
        "Приглашаем вас открыть Беловежскую пущу по-новому — на удобных и легких в управлении самокатах. Это отличный способ неспешно насладиться природой и свежим воздухом, не уставая от долгих пеших прогулок.\n\n"
        "✨ <b>Наши самокаты:</b>\n"
        "• Находятся прямо рядом с основными туристическими маршрутами.\n"
        "• Современные, удобные и безопасные.\n"
        "• Подходят взрослым и подросткам (идеально для семейных, романтических поездок и небольших компаний).\n\n"
        "💳 <b>Аренда самоката:</b> 20 BYN / 2 часа\n\n"
        "📞 <i>Узнать о наличии инвентаря можно у администрации.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📞 Связаться с администратором", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="services"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "service_grill")
async def process_service_grill(callback: types.CallbackQuery):
    await callback.answer()

    photo_path = "media/besedka_gril.jpg" if os.path.exists("media/besedka_gril.jpg") else "besedka_gril.jpg"
    try:
        photo = types.FSInputFile(photo_path) if os.path.exists(photo_path) else None
    except Exception:
        photo = None
        logging.error("Файл besedka_gril.jpg не найден")

    text_intro = (
        "🔥 <b>Беседки и Гриль</b>\n\n"
        "Для любителей готовить на открытом огне у нас предусмотрены:\n\n"
        "• Уютные открытые беседки\n"
        "• Специализированные беседки-гриль для любой погоды.\n\n"
        "🏠 <b>Скандинавская беседка</b>"
    )

    text_caption = (
        "🔥 <b>Сердце беседки – настоящий очаг!</b>\n"
        "— Массивная чугунная чаша в центре – греет, создаёт атмосферу и идеально подходит для гриля, казана или котелка.\n"
        "— Можно приготовить шашлык, шурпу, стейки или даже испечь картошку в углях – как душа пожелает!\n\n"
        "🍖 <b>Всё для идеального застолья:</b>\n"
        "— Мангал, решётки, шампуры и казаны – берите продукты, остальное предоставим мы.\n"
        "— Дрова и розжиг – чтобы вы сразу погрузились в процесс.\n\n"
        "🌲 <b>Уютный северный стиль:</b>\n"
        "— Натуральное дерево, тёплый свет фонарей и панорамные окна – внутри тепло даже в прохладный вечер.\n"
        "— Мягкие пледы и меховые накидки – если захочется укутаться в прохладу.\n\n"
        "💳 <b>Аренда:</b> 25 BYN за услугу.\n"
        "📞 <i>Забронировать можно у администратора.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📞 Связаться с администратором", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="services"))
    keyboard = builder.as_markup()

    if photo:
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=photo,
            caption=text_intro + "\n\n" + text_caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=text_intro + "\n\n" + text_caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    try:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    except Exception:
        pass


@dp.callback_query(F.data.in_({"service_elixirs", "service_souvenirs"}))
async def process_service_elixirs(callback: types.CallbackQuery):
    await callback.answer()

    photo_path = "media/eliksiry.jpg" if os.path.exists("media/eliksiry.jpg") else "eliksiry.jpg"
    try:
        photo = types.FSInputFile(photo_path) if os.path.exists(photo_path) else None
    except Exception:
        photo = None
        logging.error("Файл с эликсирами не найден")

    text_caption = (
        "🥃 <b>Домашние эликсиры</b>\n\n"
        "Наш фирменный крафтовый продукт, созданный по традиционным рецептам. Отличный вариант для душевного вечера на природе или в качестве сувенира!\n\n"
        "🌿 <b>Вкусы в наличии:</b>\n"
        "• Имбирь-мята\n"
        "• Кедровый\n"
        "• Зубровка\n"
        "• Колган\n\n"
        "💳 <b>Стоимость:</b> 30,00 BYN за 0,5 л\n\n"
        "📞 <i>Для заказа и уточнения наличия свяжитесь с администратором.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📞 Связаться с администратором", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="services"))
    keyboard = builder.as_markup()

    if photo:
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=photo,
            caption=text_caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=text_caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    try:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    except Exception:
        pass


@dp.callback_query(F.data == "service_hookah")
async def process_service_hookah(callback: types.CallbackQuery):
    text = (
        "💨 <b>Кальян</b>\n\n"
        "Отличный способ расслабиться и насладиться вечером. Выберите вкус по своему предпочтению:\n\n"
        "💪 <b>Крепкие смеси:</b>\n"
        "• с охлаждающим эффектом\n"
        "• лесные ягоды\n"
        "• манго, маракуйя, личи и роза\n\n"
        "🍃 <b>Лёгкие смеси:</b>\n"
        "• малина ежевика\n"
        "• чёрная смородина\n"
        "• арбузная жвачка\n"
        "• дыня с кокосом\n"
        "• лимонные дольки\n"
        "• лимонный йогурт\n\n"
        "🚫 <b>Безтабачные:</b>\n"
        "• киви лайм\n"
        "• ежевика арбуз\n"
        "• гавана лимон\n\n"
        "💳 <b>Стоимость:</b> 50,00 BYN\n"
        "👨‍💨 <b>Кальянный мастер:</b> Виктор\n"
        "📞 <i>Для заказа свяжитесь с мастером напрямую.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📞 Связаться с кальян-мастером", url="https://t.me/+375298124837"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="services"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "service_honey")
async def process_service_honey(callback: types.CallbackQuery):
    text = (
        "🍯 <b>Натуральный мёд с нашей пасеки</b>\n\n"
        "Вдали от дорог и городской суеты, в самом сердце лесной природы, наши трудолюбивые пчёлы собирают нектар с дикорастущих трав и цветов. Этот мёд — настоящее «жидкое золото», вобравшее в себя всю силу и пользу леса.\n\n"
        "🌿 <b>В чём его уникальность?</b>\n"
        "• <b>100% экологичность:</b> Собран в чистейшем районе, абсолютно натуральный продукт без добавок и сиропов.\n"
        "• <b>Природная аптечка:</b> Мощный природный иммуномодулятор! Богат витаминами, антиоксидантами и ферментами. Отлично восстанавливает силы, успокаивает нервную систему и спасает от простуды.\n"
        "• <b>Неповторимый вкус:</b> Густой, насыщенный аромат лесного разнотравья с долгим согревающим послевкусием.\n\n"
        "<i>Идеально дополнит чаепитие после жаркой бани или станет прекрасным, а главное — полезным сувениром для ваших близких!</i>\n\n"
        "💳 <b>Стоимость:</b> 25,00 BYN за 1 литр (1,4 кг)\n\n"
        "📞 <i>Для заказа баночки здоровья свяжитесь с администратором.</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📞 Связаться с администратором", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="services"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


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
        "⚠️ В день приезда обязательно свяжитесь с управляющей Тамарой по телефону +375 29 313-97-02 (Viber / Telegram / WhatsApp) для согласования времени заселения.\n\n"
        "❗️ Если вы задерживаетесь в пути, пожалуйста, предупредите нас. Заселение после 21:00 возможно по предварительному согласованию."
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📞 Связаться с Тамарой", url="https://t.me/+375293139702"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="faq_menu"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_payment")
async def process_faq_payment(callback: types.CallbackQuery):
    text = (
        "💳 <b>Условия оплаты и предоплаты</b>\n\n"
        "• При бронировании взимается ОБЯЗАТЕЛЬНАЯ предоплата до <b>30%</b>. В праздничные дни — до <b>70%</b>.\n"
        "🔄 При отмене или переносе брони предоплата не возвращается, но сохраняется за вами право для переноса даты.\n"
        "📅 Перенести бронь на другую дату можно <b>1 (один) раз</b> на срок не более 3 месяцев (при наличии свободных мест).\n"
        "🚫 Перенос менее чем за 7 дней до заезда невозможен.\n\n"
        "💵 <b>Обратите внимание:</b> окончательный расчет за проживание осуществляется непосредственно при заселении, <b>наличными в белорусских рублях (BYN)</b>. Поэтому гостям из РФ убедительная просьба обменять деньги в обменных пунктах на наличные белорусские рубли заранее в полном объёме."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_about")
async def process_faq_about(callback: types.CallbackQuery):
    text = (
        "🏡 <b>Об усадьбе и территории</b>\n\n"
        "Усадьба <b>«Магия леса»</b> в самом сердце Беловежской пущи, <b>внутри заповедника (въезд через КПП)</b> — это уникальное сочетание комфорта и дикой природы. "
        "Расположенная в уединенном месте на опушке леса, на большой ухоженной территории, она предлагает гостям возможность насладиться атмосферой одного из последних первозданных лесов Европы.\n\n"
        "Основная идея базы отдыха заключается в том, чтобы предоставить комфортную и атмосферную обстановку, гармонично сочетающуюся с природным окружением. "
        "Здесь вас ожидают <b>5 домов</b> и <b>4 уютных глэмпинга</b>, полностью подготовленные для вашего отдыха.\n\n"
        "🧖‍♀️ <b>На территории усадьбы находятся бани:</b>\n"
        "1. Баня с горячей купелью (до 6 человек).\n"
        "2. Банный СПА-комплекс «Люкс» с горячей купелью (до 10 человек). Идеально для большой компании.\n\n"
        "🌲 <b>Активности на территории:</b>\n"
        "Террасы, мангалы (у каждого дома), батут, детская площадка, прогулочные зоны, настольный теннис, волейбол, футбол, бадминтон, прокат велосипедов и парковка для авто."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="faq_menu"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_included")
async def process_faq_included(callback: types.CallbackQuery):
    text = (
        "🎁 <b>Что включено в стоимость</b>\n\n"
        "В стоимость включены дома с террасами и глэмпинги со всем необходимым для комфортного проживания.\n\n"
        "🛏 <b>Оснащение номера и мебель:</b>\n"
        "• Обогреватель\n• Вентилятор\n• Рабочее пространство\n• Шкаф/Гардероб\n• Москитная сетка\n• Светонепроницаемые шторы\n\n"
        "🚿 <b>Ванная комната:</b>\n"
        "• Собственный санузел\n• Тапочки\n• Фен\n• Бассейн\n\n"
        "🍳 <b>Кухня:</b>\n"
        "• Микроволновка\n• Холодильник\n• Столовые приборы\n• Обеденный стол\n\n"
        "🥩 <b>Мангальные зоны:</b>\n"
        "• Возле каждого дома и глэмпинга есть зоны для приготовления еды на открытом воздухе, которые оборудованы всем необходимым (мангалы, охапка дров, шампура, решётки, казан).\n\n"
        "✨ <b>В комплекте:</b>\n"
        "• Чай/кофе, постельное бельё, посуда, полотенца, тапочки, средства гигиены."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_final_payment")
async def process_faq_final_payment(callback: types.CallbackQuery):
    text = (
        "💵 <b>Окончательный расчёт</b>\n\n"
        "Окончательный расчет за проживание осуществляется непосредственно при заселении, <b>наличными в белорусских рублях (BYN)</b>. "
        "Поэтому гостям из РФ убедительная просьба обменять деньги в обменных пунктах на наличные белорусские рубли заранее в полном объёме."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_food")
async def process_faq_food(callback: types.CallbackQuery):
    text = (
        "🍽 <b>Питание, магазины, рестораны</b>\n\n"
        "На данный момент на усадьбе питание не предоставляется. В каждом доме есть полноценная оборудованная кухня со всей необходимой посудой, а также чай и кофе. Вы можете готовить любимые блюда прямо в доме или использовать мангальные зоны на свежем воздухе. <b>Все необходимое для этого (охапка дров, решетки, шампура, казаны) есть.</b>\n\n"
        "💡 <b>Совет:</b> мы рекомендуем приобретать продукты для приготовления еды заранее.\n\n"
        "🛒 <b>Магазины:</b>\n"
        "На территории Беловежской пущи продовольственных магазинов нет. Ближайший магазин с базовыми продуктами питания расположен на расстоянии 3–4 км от усадьбы.\n\n"
        "🍽 <b>Рестораны:</b>\n"
        "Ближайший ресторан находится на расстоянии 300–400 метров от нашей усадьбы (иногда закрыт на спец. обслуживание, поэтому продукты всё же лучше взять с собой).\n\n"
        "Также кафе и рестораны есть возле главного входа в Беловежскую пущу и в резиденции Деда Мороза, где можно отведать блюда белорусской кухни."
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_nearby")
async def process_faq_nearby(callback: types.CallbackQuery):
    text = (
        "📍 <b>Что находится рядом с нами</b>\n\n"
        "Наша усадьба расположена в уникальном историческом и природном месте. Совсем рядом с нами:\n\n"
        "🌲 Реликтовый первобытный лес\n"
        "🦬 Зубры, олени, лоси, косули, кабаны и другие дикие животные в естественной среде обитания\n"
        "🎅 Поместье Деда Мороза\n"
        "🏛 Музей природы\n"
        "🦌 Экскурсионные вольеры с животными\n"
        "🏺 Археологический музей под открытым небом\n"
        "🛖 Музей народного быта и старинных технологий\n"
        "🚲 Велосипедные и пешеходные маршруты\n"
        "👑 Царская поляна\n\n"
        "<i>...и многое другое!</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_faq_button(), parse_mode="HTML")


@dp.callback_query(F.data == "faq_transfer")
async def process_faq_transfer(callback: types.CallbackQuery):
    text = (
        "🚗 <b>Трансфер и маршрут</b>\n\n"
        "Добраться можно самостоятельно на автомобиле.\n\n"
        "🗺 <b>Ваш маршрут:</b>\n"
        "Каменец → Каменюки → Пашуки (КПП) → Гвоздь 1, д. 4\n\n"
        "⚠️ <b>ВАЖНО:</b> Въезд возможен ТОЛЬКО через КПП в д. Пашуки! Через другие пропускные пункты вас не пропустят. От КПП до усадьбы останется проехать около 2 км.\n\n"
        "🚕 <b>Услуги трансфера:</b>\n"
        "• Трансфер до усадьбы из Бреста: 80 BYN\n"
        "• Трансфер из усадьбы в Брест: 80 BYN\n\n"
        "Для заказа трансфера свяжитесь с управляющим, нажав на кнопку ниже:"
    )

    google_url = "https://www.google.com/maps/dir/?api=1&destination=52.528997,23.879703&waypoints=52.561228,23.798991|52.527526,23.860374"
    yandex_url = "https://yandex.ru/maps/?rtext=~52.561228,23.798991~52.527526,23.860374~52.528997,23.879703"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Google Maps", url=google_url), InlineKeyboardButton(text="🗺 Yandex Maps", url=yandex_url))
    builder.row(InlineKeyboardButton(text="📞 Связаться с управляющим", url="https://t.me/+375297200003"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к вопросам", callback_data="faq_menu"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.in_({"promo", "promos"}))
async def process_promo(callback: types.CallbackQuery):
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

    await callback.message.delete()
    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "location")
async def process_location(callback: types.CallbackQuery):
    text = (
        "📍 <b>Как к нам добраться</b>\n\n"
        "Добраться можно самостоятельно на автомобиле.\n\n"
        "🗺 <b>Ваш маршрут:</b>\n"
        "Каменец → Каменюки → Пашуки (КПП) → Гвоздь 1, д. 4\n\n"
        "⚠️ <b>ВАЖНО:</b> Въезд возможен ТОЛЬКО через КПП в д. Пашуки! Через другие пропускные пункты вас не пропустят. От КПП до усадьбы останется проехать около 2 км.\n\n"
        "🚕 <b>Услуги трансфера:</b>\n"
        "• Трансфер до усадьбы из Бреста: 80 BYN\n"
        "• Трансфер из усадьбы в Брест: 80 BYN\n\n"
        "Для заказа трансфера свяжитесь с управляющим, нажав на кнопку ниже:"
    )

    google_url = "https://www.google.com/maps/dir/?api=1&destination=52.528997,23.879703&waypoints=52.561228,23.798991|52.527526,23.860374"
    yandex_url = "https://yandex.ru/maps/?rtext=~52.561228,23.798991~52.527526,23.860374~52.528997,23.879703"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Google Maps", url=google_url), InlineKeyboardButton(text="🗺 Yandex Maps", url=yandex_url))
    builder.row(InlineKeyboardButton(text="📞 Связаться с управляющим", url="https://t.me/+375297200003"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_main"))

    try:
        await callback.message.delete()
    except Exception:
        pass
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


# --- ОБРАБОТЧИК ЛЮБОГО ТЕКСТА ---
@dp.message(F.text)
async def handle_any_text(message: types.Message):
    await message.answer(
        "Я работаю с помощью кнопок меню! 🏡\n"
        "Пожалуйста, выберите нужный раздел с помощью кнопок выше или нажмите /start для возврата в главное меню.",
        reply_markup=get_main_menu()
    )


# --- ЗАПУСК БОТА ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port)
