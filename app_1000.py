import telebot
from telebot import types
import json
import random
import logging
import time
import requests
from datetime import datetime, timedelta
from telebot.formatting import escape_html
from flyerapi import Flyer, APIError
flyer = None
# --- НАСТРОЙКИ ЛОГИРОВАНИЯ ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (ЗАМЕНИТЕ ВАШИ ЗНАЧЕНИЯ) ---
BOT_TOKEN = ''
ADMIN_ID = 6677500867 # Замените на ваш реальный ID администратора Telegram (число)
CRYPTO_BOT_API_TOKEN = ''

bot = telebot.TeleBot(BOT_TOKEN)

# Получаем username бота для ссылок
BOT_USERNAME = bot.get_me().username


BOT_DATA = {} # Будет загружено из bot_data.json

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---
def save_data(data):
    """Сохраняет данные бота в файл bot_data.json."""
    try:
        with open('bot_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Ошибка при сохранении данных: {e}")

def load_data():
    """Загружает данные бота из файла bot_data.json и инициализирует новые поля."""
    global BOT_DATA
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            BOT_DATA = json.load(f)
        logging.error("Данные бота успешно загружены.")
    except FileNotFoundError:
        logging.warning("Файл bot_data.json не найден. Создаем новый.")
        BOT_DATA = {} # Начинаем с пустого словаря, затем добавим все по умолчанию
    except json.JSONDecodeError:
        logging.error("Ошибка декодирования JSON. Файл bot_data.json поврежден или пуст. Создаем новый.")
        BOT_DATA = {} # Начинаем с пустого словаря

    # Инициализация необходимых полей, если их нет (для новых или старых файлов)
    if 'users' not in BOT_DATA:
        BOT_DATA['users'] = {}
    if 'checks' not in BOT_DATA:
        BOT_DATA['checks'] = {}
    if 'currency' not in BOT_DATA:
        BOT_DATA['currency'] = {
            'name': 'USDT',          # Назва валюти
            'rate_to_usdt': 1   # 1 unit = USDT
        }
    if 'limits' not in BOT_DATA:
        BOT_DATA['limits'] = {
            'min_deposit': 0.1,   # минимальное пополнение (в USDT)
            'min_withdraw': 0.5, # минимальный вывод (в валюте)
            'min_bet': 0.10        # минимальная ставка (в валюте)
        }
    if 'game_coeffs' not in BOT_DATA:
        BOT_DATA['game_coeffs'] = {
            'cube': 6.0,                # точное число 1-6
            'duel': 1.85,                # дуэль 50/50
            'even': 1.85,                # чёт
            'odd': 1.85,                 # нечет
            'more': 20.0,                # больше (>3)
            'less': 20.0,                # меньше (<4)
            'red': 20.0,                 # дартс красный
            'white': 20.0,               # дартс белый
            'darts_center': 50.0,        # дартс центр
            'basket_score': 20.0,        # баскет корзина
            'basket_miss': 20.0,         # баскет мимо
            'football_goal': 20.0,       # футбол гол
            'football_miss': 20.0,       # футбол мимо
            'bowling': 50.0,             # боулинг страйк
            'slots': 1000.0,               # слоты 777/тройка
            'pvp_darts': 20.0,
            'pvp_basket': 20.0,
            'pvp_football': 20.0,
            'pvp_bowling': 20.0
        } 
    if 'admin_stats' not in BOT_DATA:
        BOT_DATA['admin_stats'] = {
            'total_bets': 0.0,
            'total_winnings': 0.0,
            'total_deposits': 0.0,
            'total_withdraws': 0.0,
            'total_fees': 0.0
        }
    if 'daily_bonus' not in BOT_DATA:
        BOT_DATA['daily_bonus'] = 1.0  # по замовчуванню 1
    if 'crypto_bot_token' not in BOT_DATA:
        BOT_DATA['crypto_bot_token'] = CRYPTO_BOT_API_TOKEN
    if 'game_logs' not in BOT_DATA:
        BOT_DATA['game_logs'] = []
    if 'required_subscriptions' not in BOT_DATA:
        BOT_DATA['required_subscriptions'] = {} # {channel_id: {'link': '...', 'name': '...'}}
    if 'banned_users' not in BOT_DATA:
        BOT_DATA['banned_users'] = []  # список user_id
    if 'pending_withdrawals' not in BOT_DATA:
        BOT_DATA['pending_withdrawals'] = {} # {message_id_to_admin: {user_id: ..., amount: ..., telegram_username: ...}}
    if 'deposit_logs' not in BOT_DATA:
        BOT_DATA['deposit_logs'] = []
    if 'referral_bonus' not in BOT_DATA:
        BOT_DATA['referral_bonus'] = 2.0  # стандартно 2 монети
    if 'stats_links' not in BOT_DATA:
        BOT_DATA['stats_links'] = []  # список словників [{"name": "Google", "url": "https://google.com"}]
    if 'withdraw_commission' not in BOT_DATA:
        BOT_DATA['withdraw_commission'] = 0.05  # по замовчуванню 5% (0.05)
    if "flyer_key" not in BOT_DATA:
        BOT_DATA["flyer_key"] = "FL-JgbLCA-EYGELi-MVobGx-ZNzpbJ"
    default_game_coeffs = {
        'cube': 6.0,
        'duel': 2.0,
        'even': 2.0,
        'odd': 2.0,
        'more': 2.0,
        'less': 2.0,
        'red': 2.0,
        'white': 2.0,
        'darts_center': 5.0,
        'basket_score': 2.0,
        'basket_miss': 2.0,
        'football_goal': 2.0,
        'football_miss': 2.0,
        'bowling': 5.0,
        'slots': 10.0,
        'pvp_darts': 2.0,
        'pvp_basket': 2.0,
        'pvp_football': 2.0,
        'pvp_bowling': 2.0
    }
    default_admin_stats = {
        'total_bets': 0.0,
        'total_winnings': 0.0,
        'total_deposits': 0.0,
        'total_withdraws': 0.0,
        'total_fees': 0.0
    }
    if 'game_coeffs' not in BOT_DATA:
        BOT_DATA['game_coeffs'] = default_game_coeffs.copy()
    else:
        for k, v in default_game_coeffs.items():
            BOT_DATA['game_coeffs'].setdefault(k, v)

    # ініціалізація або оновлення admin_stats
    if 'admin_stats' not in BOT_DATA:
        BOT_DATA['admin_stats'] = default_admin_stats.copy()
    else:
        for k, v in default_admin_stats.items():
            BOT_DATA['admin_stats'].setdefault(k, v)


    if BOT_DATA["flyer_key"]:
        try:
            flyer = Flyer(BOT_DATA["flyer_key"])
        except Exception as e:
            flyer = None
            print(f"❌ Ошибка инициализации Flyer: {e}")

    if 'withdraw_logs' not in BOT_DATA:
        BOT_DATA['withdraw_logs'] = []
    BOT_DATA.setdefault('deposit_logs', [])
    BOT_DATA.setdefault('withdraw_logs', [])
    BOT_DATA.setdefault('game_logs', [])
    BOT_DATA.setdefault('pending_withdrawals', {})
    BOT_DATA.setdefault('checks', {})
    save_data(BOT_DATA)

def get_user_data(user_id):
    """Возвращает данные пользователя, создавая их при необходимости и инициализируя новые поля."""
    user_id_str = str(user_id)
    if user_id_str not in BOT_DATA['users']:
        BOT_DATA['users'][user_id_str] = {
            'balance': 0.0, # Начальный баланс для новых пользователей
            'reserved_balance': 0.0,
            'status': 'main',
            'active_bet': None,
            'referrer_id': None,
            'referrer_username': None, # Для хранения юзернейма приглашенного пользователя (или ID)
            'referrer_bonus_given': False, # <-- Флаг, был ли уже выдан бонус рефереру за этого пользователя
            'pending_deposit': None,
            'is_processing_deposit': False,
            'is_processing_game': False,
            'last_bonus_claim': 0 # timestamp последнего получения бонуса
        }
        save_data(BOT_DATA)
    else:
        # Проверка и добавление новых полей для существующих пользователей
        user_data = BOT_DATA['users'][user_id_str]
        # Если каких-то полей нет, добавляем их со значениями по умолчанию
        if 'referrer_username' not in user_data:
            user_data['referrer_username'] = None
        if 'referrer_bonus_given' not in user_data:
            user_data['referrer_bonus_given'] = False
        if 'pending_deposit' not in user_data:
            user_data['pending_deposit'] = None
        if 'is_processing_deposit' not in user_data:
            user_data['is_processing_deposit'] = False
        if 'is_processing_game' not in user_data:
            user_data['is_processing_game'] = False
        if 'last_bonus_claim' not in user_data:
            user_data['last_bonus_claim'] = 0
        if 'reserved_balance' not in user_data:
            user_data['reserved_balance'] = 0.0

        save_data(BOT_DATA) # Сохраняем после обновления данных пользователя

    return BOT_DATA['users'][user_id_str]

# --- ПРОВЕРКА БАНА ---
def is_banned(user_id: int) -> bool:
    """Проверяет, забанен ли пользователь"""
    return str(user_id) in BOT_DATA.get('banned_users', [])

# --- ФУНКЦИИ ДЛЯ ЧЕКОВ (Остаются для создания собственных чеков) ---
def generate_check_number():
    """Генерирует уникальный ID для чека."""
    while True:
        check_id = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=8))
        if check_id not in BOT_DATA['checks']:
            return check_id

# Отримуємо юзернейм бота динамічно
bot_info = bot.get_me()  # bot - це твій TeleBot
BOT_USERNAME = bot_info.username  # наприклад, 'KubikMH_Bot'

def generate_check_link(check_id):
    """Генерирует ссылку для активации чека."""
    return f"https://t.me/{BOT_USERNAME}?start=check_{check_id}"

# --- ИНТЕГРАЦИЯ С CRYPTO BOT API --- 
def create_invoice(amount, asset='USDT', description='Пополнение баланса', user_id=None):

    """Создает инвойс через Crypto Bot API."""

    url = "https://pay.crypt.bot/api/createInvoice"

    headers = {

        "Crypto-Pay-API-Token": BOT_DATA['crypto_bot_token'],

        "Content-Type": "application/json"

    }

    payload = {

        "asset": asset,

        "amount": str(float(amount)),

        "description": description,

        "hidden_message": f"Пополнение для пользователя {user_id}",

        "allow_anonymous": True,

        "expires_at": int(time.time()) + 3600 # Инвойс действителен 1 час

    }

    try:

        logging.error(f"Отправка запроса на создание инвойса Crypto Bot: {payload}")

        response = requests.post(url, headers=headers, json=payload, timeout=10) # Добавлен таймаут

        response.raise_for_status() # Вызывает исключение для ошибок HTTP

        result = response.json()

        logging.info(f"Ответ Crypto Bot на создание инвойса: {result}")

        return result

    except requests.exceptions.RequestException as e:

        logging.error(f"Ошибка при создании счета Crypto Bot: {e}")

        if hasattr(e, 'response') and e.response is not None:

            logging.error(f"Crypto Bot API Error Response: {e.response.text}")

        return {'ok': False, 'error': str(e)}



def check_invoice_status(invoice_id):
    """Проверяет статус инвойса через Crypto Bot API."""
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {
        "Crypto-Pay-API-Token": BOT_DATA['crypto_bot_token'],
        "Content-Type": "application/json"
    }
    payload = {
        "invoice_ids": str(invoice_id)
    }
    try:
        logging.error(f"Отправка запроса на проверку статуса инвойса Crypto Bot: {payload}")
        response = requests.post(url, headers=headers, json=payload, timeout=10) # Добавлен таймаут
        response.raise_for_status()
        result = response.json()
        logging.info(f"Ответ Crypto Bot на проверку статуса инвойса: {result}")
        if result and result.get('ok') and result.get('result') and result['result'].get('items'):
            invoice = result['result']['items'][0]
            return invoice['status']
        return 'error'
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при проверке статуса счета Crypto Bot: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Crypto Bot API Error Response: {e.response.text}")
        return 'error'

# --- ФУНКЦИИ ДЛЯ СОЗДАНИЯ КЛАВИАТУР ---
def main_menu_markup(user_id	):
    """Возвращает ReplyKeyboardMarkup для главного меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🎲 Играть', '👤 Профиль')

    markup.add('📊 Статистика')
    return markup

def admin_panel_markup():
    """Возвращает InlineKeyboardMarkup для админ-панели."""
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(types.InlineKeyboardButton(f"💸 Комиссия вывода: {BOT_DATA['withdraw_commission']*100:.1f}%",callback_data="change_withdraw_commission"))
    markup.add(types.InlineKeyboardButton("🔗 Стат. ссылки", callback_data="admin_manage_stats_links"),
               types.InlineKeyboardButton("🎁 Бонус", callback_data="admin_change_bonus"))
    markup.add(types.InlineKeyboardButton("💱 Валюта", callback_data="admin_change_currency"),
               types.InlineKeyboardButton("🔍 Проверить юзера", callback_data="admin_check_user"))
    markup.add(types.InlineKeyboardButton("📢 ОП", callback_data="admin_manage_subscriptions"),
               types.InlineKeyboardButton("✉️  Рассылка", callback_data="admin_start_broadcast"),
               types.InlineKeyboardButton("🔗 Чек", callback_data="admin_create_check"))
    markup.add(types.InlineKeyboardButton("⚙️ Лимиты", callback_data="admin_change_limits"),
               types.InlineKeyboardButton("🔑 Tокен CryptoBot", callback_data="admin_change_token"),
               types.InlineKeyboardButton(f"🔑 Flyer API Key", callback_data="change_flyer_key"))
    markup.add(types.InlineKeyboardButton("⚖️ Коеф.", callback_data="admin_change_coeffs"),
               types.InlineKeyboardButton("👥 Реф выплата", callback_data="admin_change_ref_bonus"))
    markup.add(types.InlineKeyboardButton("📤 Экспорт", callback_data="admin_export_users"),
               types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    markup.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main"))
    return markup

def manage_subscriptions_markup():
    """Возвращает InlineKeyboardMarkup для управления подписками."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Добавить", callback_data="admin_add_subscription"),
               types.InlineKeyboardButton("➖ Удалить", callback_data="admin_remove_subscription"))
    markup.add(types.InlineKeyboardButton("👁️ Список", callback_data="admin_list_subscriptions"))
    markup.add(types.InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_panel_back"))
    return markup

def personal_cabinet_markup(user_balance, reserved_balance):
    """Возвращает InlineKeyboardMarkup для личного кабинета."""
    markup = types.InlineKeyboardMarkup(row_width=2)

    # Текст для кнопки вывода, если есть зарезервированные средства
    withdraw_button_text = "💸 Вывести"
    if reserved_balance > 0:
        withdraw_button_text += f" (В обработке: {reserved_balance:.2f} BOT_DATA['currency']['name'])"

    markup.add(types.InlineKeyboardButton("💳 Пополнить", callback_data="personal_cabinet_deposit"),
               types.InlineKeyboardButton(withdraw_button_text, callback_data="personal_cabinet_withdraw"))
    markup.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main"))
    return markup

def game_menu_markup():
    """Возвращает InlineKeyboardMarkup для выбора числа в игре."""
    markup = types.InlineKeyboardMarkup(row_width=4)
    markup.add(types.InlineKeyboardButton("1", callback_data="game_1"),
               types.InlineKeyboardButton("2", callback_data="game_2"),
               types.InlineKeyboardButton("3", callback_data="game_3"),
               types.InlineKeyboardButton("4", callback_data="game_4"),
               types.InlineKeyboardButton("5", callback_data="game_5"),
               types.InlineKeyboardButton("6", callback_data="game_6"))
    markup.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main"))
    return markup

def game_after_roll_markup(chosen_game=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if chosen_game:
        markup.add(types.InlineKeyboardButton("🎲 Играть снова", callback_data=f"play_again_{chosen_game}"))
    else:
        markup.add(types.InlineKeyboardButton("🎲 Играть снова", callback_data="play_game_again"))
    markup.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main"))
    return markup

def back_to_main_menu_inline():
    """Возвращает InlineKeyboardMarkup с одной кнопкой "Назад в главное меню"."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main"))
    return markup

def subscription_check_markup():
    """Возвращает InlineKeyboardMarkup с кнопками для подписки и проверки."""
    markup = types.InlineKeyboardMarkup(row_width=1)

    for channel_id, channel_info in BOT_DATA['required_subscriptions'].items():
        markup.add(types.InlineKeyboardButton(f"🔗 {channel_info.get('name', 'Канал/Чат')}", url=channel_info['link']))

    markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_my_subscriptions"))
    return markup

import asyncio

def require_flyer_check(func):
    def wrapper(message, *args, **kwargs):
        global flyer
        user_id = message.from_user.id
        lang = getattr(message.from_user, 'language_code', 'en')

        # Якщо ключа нема → просто працюємо без Flyer
        if flyer is None:
            func(message, *args, **kwargs)
            return

        flyer_message = {
            'text': '<b>Для продолжения подпишитесь на канал</b>\nи нажмите кнопку "Проверить подписку"',
            'button_channel': 'Перейти',
            'button_fp': 'Проверить подписку'
        }

        try:
            passed = asyncio.run(
                flyer.check(user_id=user_id, language_code=lang, message=flyer_message)
            )
            if not passed:
                # Якщо не підписаний – не запускаємо функцію
                return
        except Exception as e:
            bot.send_message(user_id, "⚠️ Не удалось проверить подписку. Попробуйте позже.")
            print(f"Ошибка при проверке Flyer для {user_id}: {e}")
            return

        # Якщо все ок → виконуємо функцію
        func(message, *args, **kwargs)
    return wrapper

# --- ФУНКЦИЯ ПРОВЕРКИ ПОДПИСОК ---
def check_subscription(user_id):
    """
    Проверяет, подписан ли пользователь на все обязательные каналы/чаты.
    Возвращает True, если подписан на все, False в противном случае.
    """
    required_channels = BOT_DATA.get('required_subscriptions', {})

    if not required_channels: # Если нет обязательных подписок, считаем, что все хорошо
        return True

    unsubscribed_channels = []
    for channel_id, channel_info in required_channels.items():
        try:
            # Важно: get_chat_member может выдать ошибку, если бот не админ или канал приватный
            member = bot.get_chat_member(channel_id, user_id)
            # Проверяем статусы, которые означают, что пользователь не является полноценным участником
            if member.status in ['left', 'kicked', 'banned']:
                unsubscribed_channels.append(channel_info)
        except telebot.apihelper.ApiTelegramException as e:
            # Обработка ошибок, когда канал недоступен или бот не имеет прав
            logging.warning(f"Ошибка при проверке подписки для {user_id} на {channel_id}: {e}")
            # Если канал недоступен для проверки, лучше считать, что пользователь не подписан
            unsubscribed_channels.append(channel_info)

    if unsubscribed_channels:
        channels_text = ""
        for channel in unsubscribed_channels:
            channels_text += f"- <a href='{channel['link']}'>{escape_html(channel.get('name', 'Канал/Чат'))}</a>\n" # Используем HTML

        bot.send_message(user_id, 
                         "✋ <b>Для продолжения работы с ботом, пожалуйста, подпишитесь на следующие каналы/чаты:</b>\n\n" # Используем HTML
                         f"{channels_text}\n"
                         "После подписки нажмите кнопку '✅ Я подписался'.",
                         parse_mode='HTML', # Изменено на HTML
                         reply_markup=subscription_check_markup(), 
                         disable_web_page_preview=True)
        return False
    return True

# --- ОБРАБОТЧИК КОМАНДЫ /start ---
@bot.message_handler(commands=['start'])
@require_flyer_check
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    user_data = get_user_data(user_id) # Получаем/создаем данные пользователя
    user_data['first_name'] = message.from_user.first_name
    user_data['last_name'] = message.from_user.last_name
    user_data['username'] = message.from_user.username

    # --- Обработка реферальной ссылки ---
    referrer_id = None
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            potential_referrer_id = int(args[1].replace('ref_', ''))
            if str(potential_referrer_id) != str(user_id): # Нельзя быть реферером самому себе
                if user_data['referrer_id'] is None: # Присваиваем реферера только один раз
                    referrer_id = str(potential_referrer_id)
                    user_data['referrer_id'] = referrer_id
                    # Сохраняем юзернейм приглашенного, если он есть, или его ID
                    user_data['referrer_username'] = message.from_user.username if message.from_user.username else f"ID:{user_id}"
                    logging.info(f"Пользователь {user_id} пришел по реферальной ссылке {referrer_id}")
            else:
                bot.send_message(user_id, "❌ Вы не можете быть реферером самому себе.", parse_mode='HTML') # Используем HTML
        except ValueError:
            logging.warning(f"Некорректный ID реферера в ссылке: {args[1]}")

# --- Обработка активации чека ---
    if len(args) > 1 and args[1].startswith('check_'):
        check_id = args[1].replace('check_', '')
        if check_id in BOT_DATA['checks']:
            check_info = BOT_DATA['checks'][check_id]
            creator_id = str(check_info['creator_id'])
            amount = check_info['amount']

            if check_info['is_claimed']:
                bot.send_message(user_id, "❌ Неверный или уже активированный чек.")
            elif str(user_id) == creator_id:
                bot.send_message(user_id, "❌ Вы не можете активировать свой собственный чек.")
            else:
            # Обновляем баланс пользователя
                user_data['balance'] += amount
                BOT_DATA['checks'][check_id]['is_claimed'] = True
                save_data(BOT_DATA)

            # Отправляем сообщение об успешной активации
                bot.send_message(
                    user_id, 
                    f"✅ Чек активирован! На ваш баланс зачислено {amount:.2f} {BOT_DATA['currency']['name']}.", 
                    parse_mode='HTML'
                )
                try:
                    # Отправляем уведомление создателю чека, используя HTML и escape_html
                    creator_info = bot.get_chat_member(user_id, user_id).user
                    claimer_name = escape_html(creator_info.first_name)
                    if creator_info.last_name:
                        claimer_name += " " + escape_html(creator_info.last_name)                                     
                    if creator_info.username:
                        claimer_mention = f"<a href='tg://user?id={user_id}'>@{escape_html(creator_info.username)}</a>"
                    else:
                        claimer_mention = f"<a href='tg://user?id={user_id}'>{claimer_name}</a> (ID: <code>{user_id}</code>)"

                    bot.send_message(creator_id,
                                     f"🎉 Ваш чек на {amount:.2f} {BOT_DATA['currency']['name']} был активирован пользователем {claimer_mention}!",
                                     parse_mode='HTML') # Используем HTML
                except Exception as e:
                    logging.error(f"Не удалось отправить уведомление создателю чека {creator_id}: {e}")
        else:
            bot.send_message(user_id, "❌ Неверный или уже активированный чек.")

    save_data(BOT_DATA) # Сохраняем все изменения после обработки параметров /start

    if not check_subscription(user_id):
        return

    bot.send_photo(

    chat_id=user_id,

    photo=open('photo.jpg', 'rb'),  # имя файла картинки

    caption=(

        "👋 Добро пожаловать! vest bet - где поднимают миллионы"

       

    ),

    parse_mode='HTML'
,
# Изменено на HTML
                     reply_markup=main_menu_markup(user_id))

# --- ОБРАБОТЧИК КОМАНД (ТОЛЬКО ДЛЯ АДМИНА) ---
@bot.message_handler(commands=['admin', 'a'])
def admin_panel(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        bot.send_message(user_id, f"<pre>⚙️ Админ-панель</pre>", parse_mode='HTML', reply_markup=admin_panel_markup()) # Используем HTML
    else:
        bot.send_message(user_id, "❌ У вас нет прав доступа к админ-панели.")

# --- ОБРАБОТЧИКИ КНОПОК (ReplyKeyboardMarkup) ---
@bot.message_handler(func=lambda message: message.text == '🎲 Играть')
@require_flyer_check
def handle_game(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, "⛔ Вы забанены администрацией")
        return
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)
    user_data['status'] = 'choose_game'
    save_data(BOT_DATA)

    bot.send_message(
        user_id,
        "<pre>🎮 <b>Выберите игру:</b></pre>",
        parse_mode="HTML",
        reply_markup=games_menu_markup()
    )

def games_menu_markup():
    coeffs = BOT_DATA['game_coeffs']  # беремо словник з коефами
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(types.InlineKeyboardButton("🛡️ PVP", callback_data="pvp_menu"))
    # 🎲 Кубик / Дуэль
    markup.add(
        types.InlineKeyboardButton(f"🎲 Кубик (1–6) x{coeffs['cube']}", callback_data="game_cube")
    )

    # 🎲 Чётное / Нечётное
    markup.add(
        types.InlineKeyboardButton(f"🎲 Чётное x{coeffs['even']}", callback_data="game_even"),
        types.InlineKeyboardButton(f"🎲 Нечётное x{coeffs['odd']}", callback_data="game_odd")
    )

    # 🎲 Больше / Меньше
    markup.add(
        types.InlineKeyboardButton(f"🎲 Больше x{coeffs['more']}", callback_data="game_more"),
        types.InlineKeyboardButton(f"🎲 Меньше x{coeffs['less']}", callback_data="game_less")
    )

    # 🎯 Дартс
    markup.add(
        types.InlineKeyboardButton(f"🎯 Красный x{coeffs['red']}", callback_data="game_red"),
        types.InlineKeyboardButton(f"🎯 Белый x{coeffs['white']}", callback_data="game_white"),
        types.InlineKeyboardButton(f"🎯 Центр x{coeffs['darts_center']}", callback_data="game_darts_center")
    )

    # 🏀 Баскетбол
    markup.add(
        types.InlineKeyboardButton(f"🏀 Корзина x{coeffs['basket_score']}", callback_data="game_basket_score"),
        types.InlineKeyboardButton(f"🏀 Мимо x{coeffs['basket_miss']}", callback_data="game_basket_miss")
    )

    # ⚽️ Футбол
    markup.add(
        types.InlineKeyboardButton(f"⚽️ Гол x{coeffs['football_goal']}", callback_data="game_football_goal"),
        types.InlineKeyboardButton(f"⚽️ Промах x{coeffs['football_miss']}", callback_data="game_football_miss")
    )

    # 🎳 Боулинг
    markup.add(types.InlineKeyboardButton(f"🎳 Страйк x{coeffs['bowling']}", callback_data="game_bowling"),
               types.InlineKeyboardButton(f"🎰 Слоты x{coeffs['slots']}", callback_data="game_slots"))

    # Назад в меню
    markup.add(
        types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")
    )
    return markup

def pvp_games_menu():
    coeffs = BOT_DATA['game_coeffs']  # берем звичайні коефи

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"🎲 Дуэль x{coeffs['duel']}", callback_data="game_duel"),
        types.InlineKeyboardButton(f"🎯 Дартс x{coeffs['pvp_darts']}", callback_data="pvp_darts")
    )
    markup.add(
        types.InlineKeyboardButton(f"🏀 Баскетбол x{coeffs['pvp_basket']}", callback_data="pvp_basket"),
        types.InlineKeyboardButton(f"⚽ Футбол x{coeffs['pvp_football']}", callback_data="pvp_football")
    )
    markup.add(
        types.InlineKeyboardButton(f"🎳 Боулинг x{coeffs['pvp_bowling']}", callback_data="pvp_bowling")
    )
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_games"))
    return markup

def cube_choice_markup():
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(str(i), callback_data=f"cube_{i}") for i in range(1, 7)]
    markup.add(*buttons)  # передаємо всі кнопки разом
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith('game_'))
def handle_game_choice(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id

    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    if user_data.get('is_processing_game', False):
        bot.send_message(user_id, "⏳ Пожалуйста, подождите, предыдущая игра еще обрабатывается.")
        return

    user_data['chosen_game'] = call.data
    user_data['status'] = 'set_bet'  # Ждем ввод ставки
    save_data(BOT_DATA)

    if call.data == "game_cube":
        bot.send_message(user_id, "<pre>🎲 Введите вашу ставку для кубика:</pre>", parse_mode="HTML")
        user_data['status'] = 'set_bet_cube'
    else:
        bot.send_message(user_id, "<pre>✍️ Введите ставку для этой игры:</pre>", parse_mode="HTML")

# --- Хендлер вводу ставки ---
@bot.message_handler(func=lambda message: get_user_data(message.from_user.id).get('status') == 'set_bet_cube')
def handle_cube_bet_input(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    ignored_texts = ["🎲 Играть", "📊 Статистика", "🎁 Бонус", "👤 Партнёры", "🖥️ Профиль"]
    if message.text in ignored_texts:
        return

    try:
        bet_amount = float(message.text.replace(',', '.'))
    except ValueError:
        bot.send_message(user_id, "❌ Пожалуйста, введите числовое значение для ставки.")
        return

    if bet_amount < BOT_DATA['limits']['min_bet']:
        bot.send_message(user_id, f"❌ Минимальная ставка: {BOT_DATA['limits']['min_bet']} {BOT_DATA['currency']['name']}")
        return
    elif bet_amount > user_data['balance']:
        bot.send_message(user_id, "❌ Недостаточно средств на балансе.")
        return

    # Сохраняем ставку и меняем статус
    user_data['active_bet'] = bet_amount
    user_data['status'] = 'cube_choice'
    save_data(BOT_DATA)

    bot.send_message(
        user_id,
        f"🎲 Ваша ставка: <b>{bet_amount:.2f} {BOT_DATA['currency']['name']}</b>\n\nВыберите число, на которое ставите:",
        parse_mode="HTML",
        reply_markup=cube_choice_markup()  # Кнопки 1–6
    )
@bot.callback_query_handler(func=lambda call: call.data == "pvp_menu")
def handle_pvp_menu(call):
    bot.edit_message_text(
        "🛡️ <b>Выберите PVP игру:</b>",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML",
        reply_markup=pvp_games_menu()
    )

# --- Хендлер выбора числа кубика ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("cube_"))
def handle_cube_choice(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    user_data = get_user_data(user_id)

    if user_data.get('status') != 'cube_choice':
        bot.send_message(user_id, "⚠️ Пожалуйста, сначала выберите игру и введите ставку.")
        return

    # число, которое выбрал игрок
    chosen_number = int(call.data.split("_")[1])
    bet = user_data.get('active_bet', 0)
    game_key = "game_cube"

    # Кидаем кубик 🎲
    dice_msg = bot.send_dice(user_id, emoji="🎲")
    rolled_number = dice_msg.dice.value
    time.sleep(2)

    # Передаем и выпавшее число, и выбранное число!
    text, win_amount = play_game(user_id, game_key, rolled_number, chosen_number)

    # Очистка данных
    user_data['active_bet'] = None
    user_data['status'] = None
    user_data['is_processing_game'] = False
    save_data(BOT_DATA)

    bot.send_message(user_id, text, parse_mode='HTML', reply_markup=game_after_roll_markup())

# --- МЕНЮ ЛИМИТОВ ---
def limits_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            f"💳 Пополнение: {BOT_DATA['limits']['min_deposit']} USDT", 
            callback_data="change_limit_min_deposit"
        ),
        types.InlineKeyboardButton(
            f"💵 Вывод: {BOT_DATA['limits']['min_withdraw']} {BOT_DATA['currency']['name']}", 
            callback_data="change_limit_min_withdraw"
        ),
        types.InlineKeyboardButton(
            f"🎲 Ставка: {BOT_DATA['limits']['min_bet']} {BOT_DATA['currency']['name']}", 
            callback_data="change_limit_min_bet"
        ),
        types.InlineKeyboardButton("🔙 Назад", callback_data="admin_panel_back")
    )
    return markup

# словник зрозумілих назв ігор
GAME_NAMES = {
    "cube": "🎲 Кубик (1–6)",
    "even": "⚪ Чётное",
    "odd": "⚫ Нечётное",
    "more": "⬆️ Больше",
    "less": "⬇️ Меньше",
    "red": "🎯 Красный",
    "white": "🎯 Белый",
    "darts_center": "🎯 Центр",
    "basket_score": "🏀 Корзина",
    "basket_miss": "🏀 Мимо",
    "football_goal": "⚽ Гол",
    "football_miss": "⚽ Промах",
    "bowling": "🎳 Страйк",
    "slots": "🎰 Слоты",
    "duel": "⚔️ PVP Кубик"
}

def coeffs_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)  # тепер по 2 кнопки
    buttons = []

    for key, val in BOT_DATA['game_coeffs'].items():
        game_name = GAME_NAMES.get(key, key)
        btn = types.InlineKeyboardButton(f"{game_name} x{val}", callback_data=f"coeff_{key}")
        buttons.append(btn)

    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i + 1])
        else:
            markup.row(buttons[i])  # якщо лишилася одна кнопка

    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_panel_back"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_coeffs")
def admin_change_coeffs(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.edit_message_text(
        "⚖️ <b>Выберите коэффициент для изменения:</b>",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML",
        reply_markup=coeffs_menu_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_again_"))
def handle_play_again(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    user_data = get_user_data(user_id)

    chosen_game = call.data.replace("play_again_", "")
    user_data["chosen_game"] = chosen_game
    user_data["status"] = f"set_bet_{chosen_game}"
    save_data(BOT_DATA)

    bot.send_message(user_id, "<pre>✍️ Введите сумму ставки для этой игры:</pre>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "change_withdraw_commission")
def ask_new_withdraw_commission(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data["status"] = "awaiting_withdraw_commission"
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, "✍️ Введите новую комиссию для вывода (в процентах, например 3.5):")

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id).get("status") == "awaiting_withdraw_commission")
def set_new_withdraw_commission(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        value = float(message.text.replace(",", "."))
        if value < 0 or value > 100:
            bot.send_message(message.chat.id, "❌ Введите число от 0 до 100.")
            return
        BOT_DATA['withdraw_commission'] = value / 100.0
        get_user_data(message.from_user.id)["status"] = "main"
        save_data(BOT_DATA)
        bot.send_message(message.chat.id, f"✅ Комиссия для вывода изменена на {value:.1f}%")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")

@bot.callback_query_handler(func=lambda call: call.data == "change_flyer_key")
def ask_flyer_key(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data["status"] = "awaiting_flyer_key"
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, "✍️ Введите новый Flyer API Key:")

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id).get("status") == "awaiting_flyer_key")
def set_flyer_key(message):
    global flyer
    if message.from_user.id != ADMIN_ID:
        return
    new_key = message.text.strip()
    BOT_DATA["flyer_key"] = new_key
    get_user_data(message.from_user.id)["status"] = "main"
    save_data(BOT_DATA)
    try:
        flyer = Flyer(new_key)
        bot.send_message(message.chat.id, "✅ Flyer API Key успешно обновлен и активирован.")
    except Exception as e:
        flyer = None
        bot.send_message(message.chat.id, f"❌ Ошибка при инициализации Flyer: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("coeff_"))
def admin_choose_coeff(call):
    if call.from_user.id != ADMIN_ID:
        return
    key = call.data.replace("coeff_", "")
    user_data = get_user_data(call.from_user.id)
    user_data["status"] = f"awaiting_coeff_{key}"
    save_data(BOT_DATA)

    # красиве ім’я для сообщения админу
    game_name = GAME_NAMES.get(key, key)
    bot.send_message(call.from_user.id, f"✍️ Введите новое значение коэффициента для {game_name}:")

import csv
import io
from datetime import datetime

# --- Меню выбора формата ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_export_users")
def export_users_menu(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 CSV - Все данные", callback_data="export_csv_full"),
               types.InlineKeyboardButton("📋 CSV - Основные", callback_data="export_csv_basic"))
    markup.add(types.InlineKeyboardButton("📝 Инфа в сообщении", callback_data="export_txt"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_panel_back"))

    bot.edit_message_text(
        "📤 Выберите формат экспорта:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


REPORT_PAGES = {}
USERS_PER_PAGE = 4
MAX_MESSAGE_LENGTH = 4000

def generate_report_pages():
    users_list = list(BOT_DATA["users"].items())
    pages = []
    page_lines = []
    count_on_page = 0

    total_pages = (len(users_list) + USERS_PER_PAGE - 1) // USERS_PER_PAGE

    page_index = 0
    for i, (user_id, user_data) in enumerate(users_list, 1):
        # Беремо тільки first_name (юзернейм ігноруємо)
        display_name = user_data.get("first_name")

        # Якщо в BOT_DATA нема — пробуємо підтягнути з Telegram
        if not display_name:
            try:
                chat = bot.get_chat(user_id)
                display_name = chat.first_name or "Без имени"
                user_data["first_name"] = chat.first_name
                save_data(BOT_DATA)
            except Exception:
                display_name = "Без имени"

        # Клікабельне посилання тільки з ім'ям
        user_link = f'<a href="tg://user?id={user_id}">{display_name}</a>'

        line = (
            f"<pre>ID: {user_id}</pre>\n"
            f"├{user_link}\n"
            f"├<b>Баланс:</b> {user_data.get('balance', 0)}\n"
            f"├<b>Рефералов:</b> {sum(1 for u in BOT_DATA['users'].values() if u.get('referrer_id') == user_id)}\n"
            f"└<b>Статус:</b> {'Активен' if user_data.get('balance', 0) > 0 else 'Неактивен'}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
        )

        if len("\n".join(page_lines + [line])) > MAX_MESSAGE_LENGTH or count_on_page >= USERS_PER_PAGE:
            page_text = f"<pre>🗒️ Страница {page_index+1}/{total_pages}</pre>\n\n" + "".join(page_lines)
            pages.append(page_text)
            page_lines = []
            count_on_page = 0
            page_index += 1

        page_lines.append(line)
        count_on_page += 1

    if page_lines:
        page_text = f"<pre>🗒️ Страница {page_index+1}/{total_pages}</pre>\n\n" + "".join(page_lines)
        pages.append(page_text)

    return pages

# --- Обработчик выбора экспорта ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("export_"))
def handle_export(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    export_type = call.data
    referrer_counts = {}

    for user_obj in BOT_DATA["users"].values():
        if user_obj.get("referrer_id"):
            ref_id = user_obj["referrer_id"]
            referrer_counts[ref_id] = referrer_counts.get(ref_id, 0) + 1

    try:
        if export_type in ("export_csv_full", "export_csv_basic"):
            import csv, io
            buffer = io.StringIO()
            writer = csv.writer(buffer)

            if export_type == "export_csv_full":
                writer.writerow([
                    "ID", "Username", "Баланс", "Рефералов",
                    "Статус", "Referrer_ID", "Last Bonus"
                ])
                for user_id, user_data in BOT_DATA["users"].items():
                    writer.writerow([
                        user_id,
                        user_data.get("referrer_username", "—"),
                        user_data.get("balance", 0),
                        referrer_counts.get(user_id, 0),
                        "Активен" if user_data.get("balance", 0) > 0 else "Неактивен",
                        user_data.get("referrer_id", "Нет"),
                        user_data.get("last_bonus_claim", "Никогда")
                    ])
                filename = f"users_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            else:
                writer.writerow(["ID", "Баланс", "Рефералов", "Статус"])
                for user_id, user_data in BOT_DATA["users"].items():
                    writer.writerow([
                        user_id,
                        user_data.get("balance", 0),
                        referrer_counts.get(user_id, 0),
                        "Активен" if user_data.get("balance", 0) > 0 else "Неактивен"
                    ])
                filename = f"users_basic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            buffer.seek(0)
            file = io.BytesIO(buffer.getvalue().encode("utf-8"))
            file.name = filename

            bot.send_document(
                call.message.chat.id,
                file,
                caption="📊 Экспорт пользователей"
            )

        elif export_type == "export_txt":
            # Генерация страниц отчета
            pages = generate_report_pages()
            REPORT_PAGES[call.message.chat.id] = pages
            page = 0
            text = pages[page]

            markup = types.InlineKeyboardMarkup()
            nav_buttons = []
            if len(pages) > 1:
                nav_buttons.append(types.InlineKeyboardButton("➡ Вперед", callback_data=f"report_page_{page+1}"))
                markup.row(*nav_buttons)
            markup.add(types.InlineKeyboardButton("🏠 Админ панель", callback_data="admin_panel_back"))

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode="HTML"
            )

        bot.answer_callback_query(call.id, "✅ Экспорт завершен")

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Ошибка при экспорте: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("report_page_"))
def report_pagination(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    page = int(call.data.split("_")[-1])
    pages = REPORT_PAGES.get(call.message.chat.id, [])
    if not pages:
        bot.answer_callback_query(call.id, "❌ Страницы отчета не найдены.")
        return

    text = pages[page]
    markup = types.InlineKeyboardMarkup()

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅ Назад", callback_data=f"report_page_{page-1}"))
    if page < len(pages) - 1:
        nav_buttons.append(types.InlineKeyboardButton("➡ Вперед", callback_data=f"report_page_{page+1}"))
    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(types.InlineKeyboardButton("🏠 Админ панель", callback_data="admin_panel_back"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_ref_bonus")
def admin_change_ref_bonus(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data["status"] = "awaiting_ref_bonus"
    save_data(BOT_DATA)
    bot.send_message(
        call.from_user.id,
        f"✍️ Введите новый размер бонуса за реферала (сейчас {BOT_DATA['referral_bonus']:.2f} {BOT_DATA['currency']['name']}):"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_check_user")
def admin_check_user(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data['status'] = 'awaiting_user_id_check'
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, "✍️ Введите ID пользователя для проверки:")

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id).get("status") == "awaiting_user_id_check")
def handle_user_check(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.strip())
        if str(target_id) not in BOT_DATA['users']:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
            return

        user_data = get_user_data(target_id)
        invited = [uid for uid, u in BOT_DATA['users'].items() if u.get('referrer_id') == str(target_id)]
        user_link = f'<a href="tg://user?id={target_id}">{target_id}</a>'
        # собираем инфо
        info = (
            f"<b>📋 Пользователь: {user_link}</b> \n"
            f"<b>├Баланс: {user_data['balance']:.2f} {BOT_DATA['currency']['name']}</b>\n"
            f"<b>├Ожидается к выплате: {user_data['reserved_balance']:.2f} {BOT_DATA['currency']['name']}</b>\n"
            f"<b>├Рефералов: {len(invited)}</b>\n"
            f"<b>└Статус: {'🚫 Забанен' if str(target_id) in BOT_DATA['banned_users'] else '✅ Активен'}</b>"
        )

        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(types.InlineKeyboardButton("✏️ Изменить баланс", callback_data=f"user_edit_balance_{target_id}"),
                   types.InlineKeyboardButton("➕ Пополнить", callback_data=f"user_add_balance_{target_id}"),
                   types.InlineKeyboardButton("➖ Списать", callback_data=f"user_sub_balance_{target_id}"))
        markup.add(types.InlineKeyboardButton("👥 Рефералы", callback_data=f"user_refs_{target_id}"))

        if str(target_id) in BOT_DATA['banned_users']:
            markup.add(types.InlineKeyboardButton("✅ Разбанить", callback_data=f"user_unban_{target_id}"))
        else:
            markup.add(types.InlineKeyboardButton("🚫 Забанить", callback_data=f"user_ban_{target_id}"))

        bot.send_message(message.chat.id, info, parse_mode="HTML", reply_markup=markup)
        get_user_data(message.from_user.id)['status'] = "main"
        save_data(BOT_DATA)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный ID (число).")

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_ban_"))
def ban_user(call):
    if call.from_user.id != ADMIN_ID:
        return
    target_id = call.data.replace("user_ban_", "")
    BOT_DATA['banned_users'].append(str(target_id))
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, f"⛔ Пользователь {target_id} забанен.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_unban_"))
def unban_user(call):
    if call.from_user.id != ADMIN_ID:
        return
    target_id = call.data.replace("user_unban_", "")
    BOT_DATA['banned_users'].remove(str(target_id))
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, f"✅ Пользователь {target_id} разбанен.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_refs_"))
def show_user_refs(call):
    if call.from_user.id != ADMIN_ID:
        return
    target_id = call.data.replace("user_refs_", "")
    invited = [uid for uid, u in BOT_DATA['users'].items() if u.get('referrer_id') == target_id]

    if not invited:
        bot.send_message(call.from_user.id, "❌ У пользователя нет рефералов.")
        return

    text = f"<pre>👥 Рефералы {target_id}:\nАйди | Баланс | Рефералов</pre>"

    for i, uid in enumerate(invited):
        u = BOT_DATA['users'][uid]
        refs_count = sum(1 for x in BOT_DATA['users'].values() if x.get('referrer_id') == uid)
        user_link = f'<a href="tg://user?id={uid}">{uid}</a>'

    # ├ для всех кроме последнего, └ для последнего
        prefix = "<b>├</b>" if i < len(invited) - 1 else "<b>└</b>"
        text += f"\n<b>{prefix}{i+1}. {user_link} | {u['balance']:.2f} | {refs_count}</b>"

    bot.send_message(call.from_user.id, text, parse_mode="HTML", disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data == "admin_manage_stats_links")
def admin_manage_stats_links(call):
    if call.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Добавить", callback_data="admin_add_stats_link"))
    markup.add(types.InlineKeyboardButton("➖ Удалить", callback_data="admin_remove_stats_link"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_panel_back"))
    bot.edit_message_text("🔗 Управление ссылками для статистики:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_edit_balance_"))
def admin_edit_balance(call):
    if call.from_user.id != ADMIN_ID:
        return
    target_id = call.data.replace("user_edit_balance_", "")
    admin_data = get_user_data(call.from_user.id)
    admin_data['status'] = f"awaiting_edit_balance_{target_id}"
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, f"✍️ Введите новый баланс для пользователя {target_id}:")


@bot.callback_query_handler(func=lambda call: call.data.startswith("user_add_balance_"))
def admin_add_balance(call):
    if call.from_user.id != ADMIN_ID:
        return
    target_id = call.data.replace("user_add_balance_", "")
    admin_data = get_user_data(call.from_user.id)
    admin_data['status'] = f"awaiting_add_balance_{target_id}"
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, f"✍️ Введите сумму для начисления пользователю {target_id}:")


@bot.callback_query_handler(func=lambda call: call.data.startswith("user_sub_balance_"))
def admin_sub_balance(call):
    if call.from_user.id != ADMIN_ID:
        return
    target_id = call.data.replace("user_sub_balance_", "")
    admin_data = get_user_data(call.from_user.id)
    admin_data['status'] = f"awaiting_sub_balance_{target_id}"
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, f"✍️ Введите сумму для списания у пользователя {target_id}:")
@bot.message_handler(func=lambda m: (get_user_data(m.from_user.id).get("status") or "").startswith("awaiting_edit_balance_"))
def set_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_data = get_user_data(message.from_user.id)
    target_id = admin_data['status'].replace("awaiting_edit_balance_", "")
    try:
        new_balance = float(message.text.replace(",", "."))
        user_data = get_user_data(target_id)
        user_data['balance'] = new_balance
        admin_data['status'] = "main"
        save_data(BOT_DATA)
        bot.send_message(message.chat.id, f"✅ Баланс пользователя {target_id} установлен на {new_balance:.2f} {BOT_DATA['currency']['name']}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")


@bot.message_handler(func=lambda m: (get_user_data(m.from_user.id).get("status") or "").startswith("awaiting_add_balance_"))
def add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_data = get_user_data(message.from_user.id)
    target_id = admin_data['status'].replace("awaiting_add_balance_", "")
    try:
        add_amount = float(message.text.replace(",", "."))
        user_data = get_user_data(target_id)
        user_data['balance'] += add_amount
        admin_data['status'] = "main"
        save_data(BOT_DATA)
        bot.send_message(message.chat.id, f"✅ Баланс пользователя {target_id} увеличен на {add_amount:.2f}. Текущий баланс: {user_data['balance']:.2f} {BOT_DATA['currency']['name']}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")


@bot.message_handler(func=lambda m: (get_user_data(m.from_user.id).get("status") or "").startswith("awaiting_sub_balance_"))
def sub_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_data = get_user_data(message.from_user.id)
    target_id = admin_data['status'].replace("awaiting_sub_balance_", "")
    try:
        sub_amount = float(message.text.replace(",", "."))
        user_data = get_user_data(target_id)
        if user_data['balance'] < sub_amount:
            bot.send_message(message.chat.id, f"❌ Недостаточно средств. Баланс: {user_data['balance']:.2f}")
            return
        user_data['balance'] -= sub_amount
        admin_data['status'] = "main"
        save_data(BOT_DATA)
        bot.send_message(message.chat.id, f"✅ С баланса пользователя {target_id} списано {sub_amount:.2f}. Текущий баланс: {user_data['balance']:.2f} {BOT_DATA['currency']['name']}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")

# Добавление
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_stats_link")
def admin_add_stats_link(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data['status'] = "awaiting_stats_link"
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, "✍️ Введите название и ссылку через запятую:\nНапример: Google, https://google.com")

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id).get("status") == "awaiting_stats_link")
def admin_save_stats_link(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        name, url = message.text.split(",", 1)
        BOT_DATA['stats_links'].append({"name": name.strip(), "url": url.strip()})
        get_user_data(message.from_user.id)['status'] = "main"
        save_data(BOT_DATA)
        bot.send_message(message.chat.id, f"✅ Ссылка добавлена: {name.strip()} → {url.strip()}")
    except Exception:
        bot.send_message(message.chat.id, "❌ Ошибка. Формат: Название, https://ссылка")

# Удаление
@bot.callback_query_handler(func=lambda call: call.data == "admin_remove_stats_link")
def admin_remove_stats_link(call):
    if call.from_user.id != ADMIN_ID:
        return
    if not BOT_DATA['stats_links']:
        bot.send_message(call.from_user.id, "⚠️ Нет ссылок для удаления.")
        return

    markup = types.InlineKeyboardMarkup()
    for i, link in enumerate(BOT_DATA['stats_links']):
        markup.add(types.InlineKeyboardButton(f"❌ {link['name']}", callback_data=f"remove_stats_link_{i}"))
    bot.send_message(call.from_user.id, "Выберите ссылку для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_stats_link_"))
def confirm_remove_stats_link(call):
    if call.from_user.id != ADMIN_ID:
        return
    index = int(call.data.replace("remove_stats_link_", ""))
    if 0 <= index < len(BOT_DATA['stats_links']):
        removed = BOT_DATA['stats_links'].pop(index)
        save_data(BOT_DATA)
        bot.edit_message_text(f"✅ Ссылка удалена: {removed['name']}", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id).get("status") == "awaiting_ref_bonus")
def set_new_ref_bonus(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        value = float(message.text.replace(",", "."))
        BOT_DATA['referral_bonus'] = value
        user_data = get_user_data(message.from_user.id)
        user_data["status"] = "main"
        save_data(BOT_DATA)
        bot.send_message(message.chat.id, f"✅ Бонус за реферала изменен на {value:.2f} {BOT_DATA['currency']['name']}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")

@bot.message_handler(func=lambda m: (get_user_data(m.from_user.id).get('status') or "").startswith("awaiting_coeff_"))
def set_new_coeff(message):
    if message.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(message.from_user.id)
    key = user_data["status"].replace("awaiting_coeff_", "")
    try:
        value = float(message.text.replace(",", "."))

        # --- записуємо в правильний словник ---
        if key in BOT_DATA['game_coeffs']:
            BOT_DATA['game_coeffs'][key] = value
        elif key in BOT_DATA.get('pvp_coeffs', {}):
            BOT_DATA['pvp_coeffs'][key] = value
        else:
            bot.send_message(message.chat.id, "❌ Ключ коэффициента не найден.")
            return

        user_data['status'] = "main"
        save_data(BOT_DATA)

        game_name = GAME_NAMES.get(key, key)
        bot.send_message(
            message.chat.id,
            f"✅ Коэффициент для {game_name} изменен на {value}",
            reply_markup=coeffs_menu_markup()
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")

def play_game(user_id: int, game_key: str, rolled_number: int, chosen_number: int = None):
    user_data = get_user_data(user_id)
    bet = user_data.get("active_bet", 0)
    coeffs = BOT_DATA["game_coeffs"]
    currency = BOT_DATA['currency']['name']

    win_amount = 0.0
    text = ""

    # --- Кубик (1–6) ---
    if game_key == "game_cube":
        if chosen_number is None:
            text = "⚠️ Ошибка: не выбрано число для ставки."
        else:
            if chosen_number == rolled_number:
                win_amount = bet * float(coeffs["cube"])
                user_data["balance"] += win_amount
                bot.send_photo(

    chat_id=user_id,

    photo=open('photo.jpg', 'rb'),

    caption=text,

    parse_mode='HTML'
                    )
                text = (

                    f"<pre>🎲 Вы выбрали {chosen_number} | Выпало {rolled_number}</pre>\n"

                    f"<pre>🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"

                )
                bot.send_photo(

    chat_id=user_id,

    photo=open('win.jpg', 'rb'),

    caption=text,

    parse_mode='Markdown'

)
                
            else:
                user_data["balance"] -= bet
                text = (
                    f"<pre>🎲 Вы выбрали {chosen_number} | Выпало {rolled_number}</pre>\n"
                    f"<pre>❌ Проигрыш -{bet:.2f} {currency}</pre>"
                )
    # --- Чёт / Нечёт ---
    elif game_key in ("game_even", "game_odd"):

        if (rolled_number % 2 == 0 and game_key == "game_even") or (rolled_number % 2 == 1 and game_key == "game_odd"):

            coef = coeffs["even"] if game_key == "game_even" else coeffs["odd"]

            win_amount = bet * float(coef)

            user_data["balance"] += win_amount
            bot.send_photo(

    chat_id=user_id,

    photo=open('win.jpg', 'rb'),

    caption=text,

    parse_mode='HTML'
                )

            text = f"<pre>🎲 Выпало {rolled_number}\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"

        else:

            user_data["balance"] -= bet
            bot.send_photo(

    chat_id=user_id,

    photo=open('d.jpg', 'rb'),

    caption=text,

    parse_mode='HTML'
                )

            text = f"<pre>🎲 Выпало {rolled_number}\n❌ Проигрыш. -{bet:.2f} {currency}</pre>"

    

    # --- Больше / Меньше ---
    elif game_key in ("game_more", "game_less"):
        if (rolled_number >= 4 and game_key == "game_more") or (rolled_number <= 3 and game_key == "game_less"):
            coef = coeffs["more"] if game_key == "game_more" else coeffs["less"]
            win_amount = bet * float(coef)
            user_data["balance"] += win_amount
            text = f"<pre>🎲 Выпало {rolled_number}\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            
            user_data["balance"] -= bet
            text = f"<pre>🎲 Выпало {rolled_number}\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    # --- Дартс ---
    elif game_key == "game_darts_center":  # центр
        if rolled_number == 6:
            win_amount = bet * float(coeffs["darts_center"])
            user_data["balance"] += win_amount
            text = f"<pre>🎯 Дартс: центр!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            user_data["balance"] -= bet
            text = f"<pre>🎯 Дартс: мимо\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    elif game_key == "game_red":  # красный сектор
        if rolled_number in (2, 4):
            win_amount = bet * float(coeffs["red"])
            user_data["balance"] += win_amount
            text = f"<pre>🎯 Дартс: красный!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            user_data["balance"] -= bet
            text = f"<pre>🎯 Дартс: белый\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    elif game_key == "game_white":  # белый сектор
        if rolled_number in (1, 3, 5):
            win_amount = bet * float(coeffs["white"])
            user_data["balance"] += win_amount
            text = f"<pre>🎯 Дартс: белый!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            user_data["balance"] -= bet
            text = f"<pre>🎯 Дартс: красный\n❌ Проигрыш -{bet:.2f} {currency}"

    # --- Баскетбол ---
    elif game_key == "game_basket_score":
        if rolled_number in (4, 5):
            win_amount = bet * float(coeffs["basket_score"])
            user_data["balance"] += win_amount
            text = f"<pre>🏀 Баскет: попал!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            user_data["balance"] -= bet
            text = f"<pre>🏀 Баскет: мимо\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    elif game_key == "game_basket_miss":
        if rolled_number in (1, 2, 3):
            win_amount = bet * float(coeffs["basket_miss"])
            user_data["balance"] += win_amount
            text = f"<pre>🏀 Баскет: мимо, как и ожидалось!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            user_data["balance"] -= bet
            text = f"<pre>🏀 Баскет: всё-таки корзина\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    # --- Футбол ---
    elif game_key == "game_football_goal":

        if rolled_number >= 3:  # гол

            win_amount = bet * float(coeffs["football_goal"])

            user_data["balance"] += win_amount

            text = f"<pre>⚽ Футбол: гол!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"

        else:

            user_data["balance"] -= bet

            text = f"<pre>⚽ Футбол: промах\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    elif game_key == "game_football_miss":

        if rolled_number <= 2:  # промах

            win_amount = bet * float(coeffs["football_miss"])

            user_data["balance"] += win_amount

            text = f"<pre>⚽ Футбол: промах, как и ожидалось!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"

        else:

            user_data["balance"] -= bet

            text = f"<pre>⚽ Футбол: всё-таки гол\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    # --- Боулинг ---
    elif game_key == "game_bowling":
        if rolled_number == 6:  # страйк
            win_amount = bet * float(coeffs["bowling"])
            user_data["balance"] += win_amount
            text = f"<pre>🎳 Боулинг: страйк!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            user_data["balance"] -= bet
            text = f"<pre>🎳 Боулинг: не страйк\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    # --- Слоты ---
    elif game_key == "game_slots":
        if rolled_number in (1, 22, 43, 64):
            win_amount = bet * float(coeffs["slots"])
            user_data["balance"] += win_amount
            text = f"<pre>🎰 Слоты: джекпот!\n🏆 Вы выиграли {win_amount:.2f} {currency}</pre>"
        else:
            user_data["balance"] -= bet
            text = f"<pre>🎰 Слоты: не повезло\n❌ Проигрыш -{bet:.2f} {currency}</pre>"

    else:
        text = "<pre>❌ Игра не найдена.</pre>"

    # Логируем
    BOT_DATA['game_logs'].append({
        'user_id': user_id,
        'bet_amount': bet,
        'win': win_amount > 0,
        'winnings': win_amount if win_amount > 0 else -bet,
        'timestamp': int(time.time())
    })

    # Сохраняем
    save_data(BOT_DATA)
    return text, win_amount
@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_"))
def handle_pvp_choice(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    user_data = get_user_data(user_id)

    if not check_subscription(user_id):
        return

    if user_data.get("is_processing_game", False):
        bot.send_message(user_id, "<pre>⏳ Пожалуйста, дождитесь завершения предыдущей игры.</pre>", parse_mode="HTML")
        return

    user_data["chosen_game"] = call.data  # например "pvp_darts"
    user_data["status"] = f"set_bet_{call.data}"  # например "set_bet_pvp_darts"
    save_data(BOT_DATA)

    bot.send_message(user_id, "<pre>✍️ Введите ставку для этой PVP-игры:</pre>", parse_mode="HTML")

@bot.message_handler(func=lambda m: (get_user_data(m.from_user.id).get("status") or "").startswith("set_bet_pvp_"))
def handle_pvp_bet(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    try:
        bet = float(message.text.replace(",", "."))
    except ValueError:
        bot.send_message(user_id, "❌ Введите числовое значение ставки.")
        return

    if bet < BOT_DATA['limits']['min_bet']:
        bot.send_message(user_id, f"❌ Минимальная ставка: {BOT_DATA['limits']['min_bet']} {BOT_DATA['currency']['name']}")
        return
    if bet > user_data['balance']:
        bot.send_message(user_id, "❌ Недостаточно средств.")
        return

    # Сохраняем ставку
    user_data["active_bet"] = bet
    chosen_game = user_data["chosen_game"]  # например "pvp_darts"
    user_data["status"] = "playing_pvp"
    save_data(BOT_DATA)

    # Запускаем игру
    if chosen_game == "pvp_darts":
        start_pvp_darts(user_id, bet)
    elif chosen_game == "pvp_basket":
        start_pvp_basket(user_id, bet)
    elif chosen_game == "pvp_football":
        start_pvp_football(user_id, bet)
    elif chosen_game == "pvp_bowling":
        start_pvp_bowling(user_id, bet)

# --- PVP 🎯 Дартс ---
def start_pvp_darts(user_id, bet):
    user_data = get_user_data(user_id)
    user_data["balance"] -= bet
    save_data(BOT_DATA)

    bot.send_message(user_id, f"<pre>🎯 PVP Дартс!\nВаша ставка: {bet} {BOT_DATA['currency']['name']}</pre>", parse_mode="HTML")

    user_throw = bot.send_dice(user_id, emoji="🎯")
    time.sleep(3)
    bot_throw = bot.send_dice(user_id, emoji="🎯")
    time.sleep(3)

    u = user_throw.dice.value
    b = bot_throw.dice.value

    if abs(u - 6) < abs(b - 6):
        win = bet * BOT_DATA['game_coeffs']['pvp_darts']
        user_data["balance"] += win
        result = f"<pre>✅ Вы ближе к центру!\nВы выиграли {win:.2f} {BOT_DATA['currency']['name']}</pre>"
    elif abs(u - 6) > abs(b - 6):
        result = f"<pre>❌ Бот оказался ближе к центру.\nВы проиграли {bet:.2f} {BOT_DATA['currency']['name']}</pre>"
    else:
        user_data["balance"] += bet
        result = f"<pre>🤝 Ничья! Ставка возвращена.</pre>"

    user_data["active_bet"] = None
    user_data["status"] = None
    save_data(BOT_DATA)

    bot.send_message(
        user_id,
        result,
        parse_mode="HTML",
        reply_markup=game_after_roll_markup(user_data["chosen_game"])
    )


# --- PVP 🏀 Баскетбол ---
def start_pvp_basket(user_id, bet):
    user_data = get_user_data(user_id)
    user_data["balance"] -= bet
    save_data(BOT_DATA)

    bot.send_message(user_id, f"<pre>🏀 PVP Баскетбол!\nВаша ставка: {bet} {BOT_DATA['currency']['name']}</pre>", parse_mode="HTML")

    user_throw = bot.send_dice(user_id, emoji="🏀")
    time.sleep(3)
    bot_throw = bot.send_dice(user_id, emoji="🏀")
    time.sleep(3)

    u = user_throw.dice.value
    b = bot_throw.dice.value

    user_goal = (u >= 4)   # попадание
    bot_goal = (b >= 4)

    if user_goal and not bot_goal:
        win = bet * BOT_DATA['game_coeffs']['pvp_basket']
        user_data["balance"] += win
        result = f"<pre>✅ Чёткое попадание!\nВы выиграли {win:.2f} {BOT_DATA['currency']['name']}</pre>"
    elif bot_goal and not user_goal:
        result = f"<pre>❌ На этот раз не повезло.\nВы проиграли {bet:.2f} {BOT_DATA['currency']['name']}</pre>"
    else:
        user_data["balance"] += bet
        result = f"<pre>🤝 Ничья! Ставка возвращена.</pre>"

    user_data["active_bet"] = None
    user_data["status"] = None
    save_data(BOT_DATA)

    bot.send_message(
        user_id,
        result,
        parse_mode="HTML",
        reply_markup=game_after_roll_markup(user_data["chosen_game"])
    )


# --- PVP ⚽ Футбол ---
def start_pvp_football(user_id, bet):
    user_data = get_user_data(user_id)
    user_data["balance"] -= bet
    save_data(BOT_DATA)

    bot.send_message(user_id, f"<pre>⚽ PVP Футбол!\nВаша ставка: {bet} {BOT_DATA['currency']['name']}</pre>", parse_mode="HTML")

    user_throw = bot.send_dice(user_id, emoji="⚽")
    time.sleep(3)
    bot_throw = bot.send_dice(user_id, emoji="⚽")
    time.sleep(3)

    u = user_throw.dice.value
    b = bot_throw.dice.value

    user_goal = (u == 3)   # гол
    bot_goal = (b == 3)

    if user_goal and not bot_goal:
        win = bet * BOT_DATA['game_coeffs']['pvp_football']
        user_data["balance"] += win
        result = f"<pre>✅ Чёткий гол!\nВы выиграли {win:.2f} {BOT_DATA['currency']['name']}</pre>"
    elif bot_goal and not user_goal:
        result = f"<pre>❌ На этот раз не повезло.\nВы проиграли {bet:.2f} {BOT_DATA['currency']['name']}</pre>"
    else:
        user_data["balance"] += bet
        result = f"<pre>🤝 Ничья! Ставка возвращена.</pre>"

    user_data["active_bet"] = None
    user_data["status"] = None
    save_data(BOT_DATA)

    bot.send_message(
        user_id,
        result,
        parse_mode="HTML",
        reply_markup=game_after_roll_markup(user_data["chosen_game"])
    )


# --- PVP 🎳 Боулинг ---
def start_pvp_bowling(user_id, bet):
    user_data = get_user_data(user_id)
    user_data["balance"] -= bet
    save_data(BOT_DATA)

    bot.send_message(user_id, f"<pre>🎳 PVP Боулинг!\nВаша ставка: {bet} {BOT_DATA['currency']['name']}</pre>", parse_mode="HTML")

    user_throw = bot.send_dice(user_id, emoji="🎳")
    time.sleep(3)
    bot_throw = bot.send_dice(user_id, emoji="🎳")
    time.sleep(3)

    u = user_throw.dice.value
    b = bot_throw.dice.value

    if u > b:
        win = bet * BOT_DATA['game_coeffs']['pvp_bowling']
        user_data["balance"] += win
        result = f"<pre>✅ Вы сбили больше кеглей!\nВы выиграли {win:.2f} {BOT_DATA['currency']['name']}</pre>"
    elif b > u:
        result = f"<pre>❌ На этот раз не повезло.\nВы проиграли {bet:.2f} {BOT_DATA['currency']['name']}</pre>"
    else:
        user_data["balance"] += bet
        result = f"<pre>🤝 Ничья! Ставка возвращена.</pre>"

    user_data["active_bet"] = None
    user_data["status"] = None
    save_data(BOT_DATA)

    bot.send_message(
        user_id,
        result,
        parse_mode="HTML",
        reply_markup=game_after_roll_markup(user_data["chosen_game"])
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_limits")
def admin_change_limits(call):
    if call.from_user.id != ADMIN_ID:
        return
    bot.edit_message_text(
        "⚙️ <b>Управление лимитами:</b>\n\n"
        "Выберите, что изменить:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML",
        reply_markup=limits_menu_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_bonus")
def admin_change_bonus(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data["status"] = "awaiting_bonus"
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, f"✍️ Введите новый размер ежедневного бонуса (сейчас {BOT_DATA['daily_bonus']}):")

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id)['status'] == "awaiting_bonus")
def set_new_bonus(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        value = float(message.text.replace(",", "."))
        BOT_DATA['daily_bonus'] = value
        get_user_data(message.from_user.id)["status"] = "main"
        save_data(BOT_DATA)
        bot.send_message(message.chat.id, f"✅ Ежедневный бонус изменен на {value}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")

# --- ХЕНДЛЕРЫ ДЛЯ УСТАНОВКИ ЛИМИТОВ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("change_limit_"))
def ask_new_limit(call):
    if call.from_user.id != ADMIN_ID:
        return
    limit_type = call.data.replace("change_limit_", "")
    user_data = get_user_data(call.from_user.id)
    user_data["status"] = f"awaiting_limit_{limit_type}"
    save_data(BOT_DATA)

    text_map = {
        "min_deposit": "💳 Введите минимальную сумму пополнения (в USDT):",
        "min_withdraw": f"💵 Введите минимальную сумму вывода (в {BOT_DATA['currency']['name']}):",
        "min_bet": f"🎲 Введите минимальную ставку (в {BOT_DATA['currency']['name']}):"
    }
    bot.send_message(call.from_user.id, text_map.get(limit_type, "Введите новое значение:"))


@bot.message_handler(func=lambda m: (get_user_data(m.from_user.id).get("status") or "").startswith("awaiting_limit_"))
def set_new_limit(message):
    if message.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(message.from_user.id)
    limit_type = user_data["status"].replace("awaiting_limit_", "")
    try:
        value = float(message.text)
        BOT_DATA["limits"][limit_type] = value
        user_data["status"] = "main"
        save_data(BOT_DATA)
        bot.send_message(
            message.chat.id,
            f"✅ Лимит {limit_type} успешно изменен на {value}",
            reply_markup=limits_menu_markup()
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число.")

# --- ХЕНДЛЕРЫ ДЛЯ ИЗМЕНЕНИЯ ВАЛЮТЫ ---
@bot.callback_query_handler(func=lambda call: call.data == 'admin_change_currency')
def admin_change_currency(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data['status'] = 'awaiting_currency_name'
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, "✍️ Введите название валюты (например, RUB, BTC, COIN):")

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id)['status'] == 'awaiting_currency_name')
def set_currency_name(message):
    if message.from_user.id != ADMIN_ID:
        return
    BOT_DATA['currency']['name'] = message.text.strip().upper()
    user_data = get_user_data(message.from_user.id)
    user_data['status'] = 'awaiting_currency_rate'
    save_data(BOT_DATA)
    bot.send_message(message.chat.id, "✍️ Введите курс (сколько 1 единица валюты в USDT):")

@bot.message_handler(func=lambda m: get_user_data(m.from_user.id)['status'] == 'awaiting_currency_rate')
def set_currency_rate(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        # Заміняємо кому на крапку
        rate_text = message.text.replace(',', '.')
        rate = float(rate_text)
        
        BOT_DATA['currency']['rate_to_usdt'] = rate
        get_user_data(message.from_user.id)['status'] = 'main'
        save_data(BOT_DATA)
        bot.send_message(
            message.chat.id,
            f"✅ Валюта изменена!\n"
            f"Текущая: {BOT_DATA['currency']['name']}, курс: {rate} USDT"
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите число для курса.")

@bot.message_handler(func=lambda message: message.text == '🎁 Бонус')
@require_flyer_check
def handle_daily_bonus(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, "⛔ Вы забанены администрацией")
        return
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    current_time = int(time.time())
    # Проверяем, прошло ли 24 часа с момента последнего получения бонуса
    if current_time - user_data['last_bonus_claim'] >= 24 * 60 * 60:
        bonus_amount = BOT_DATA.get('daily_bonus', 1.0)
        user_data['balance'] += bonus_amount
        user_data['last_bonus_claim'] = current_time
        save_data(BOT_DATA)
        bot.send_message(user_id, f"<pre>🎉 Вы получили ежедневный бонус!</pre>\n" # Используем HTML
                                  f"<b>├Получено: {bonus_amount:.2f} {BOT_DATA['currency']['name']}</b>.\n"
                                  f"<b>└Текущий баланс: {user_data['balance']:.2f} {BOT_DATA['currency']['name']}</b>", # Используем HTML
                                  parse_mode='HTML') # Изменено на HTML

        # --- Логика реферального бонуса (для пригласивших) ---
        # Начисляем бонус, если есть реферер и бонус еще не был выдан
        if user_data['referrer_id'] and not user_data['referrer_bonus_given']:
            referrer_id = user_data['referrer_id']
            referrer_data = get_user_data(referrer_id)
            if referrer_data: # Убедитесь, что реферер существует
                referrer_bonus_amount = BOT_DATA.get('referral_bonus', 2.0)
                referrer_data['balance'] += referrer_bonus_amount
                user_data['referrer_bonus_given'] = True # Устанавливаем флаг, что бонус выдан
                save_data(BOT_DATA) # Сохраняем изменения для обоих пользователей

                try:
                    # Безопасное формирование имени приглашенного для уведомления реферера
                    invited_user_first_name = escape_html(message.from_user.first_name)
                    invited_user_mention = f"<a href='tg://user?id={user_id}'>{invited_user_first_name}</a>"

                    bot.send_message(referrer_id, 
                                     f"<pre>👤 Новый реферал</pre>\n" # Используем HTML
                                     f"<b>└{invited_user_mention}</b>\n"
                                     f"<b>На ваш баланс зачислено {referrer_bonus_amount:.2f} {BOT_DATA['currency']['name']}</b>!", # Используем HTML
                                     parse_mode='HTML') # Изменено на HTML
                except Exception as e:
                    logging.error(f"Не удалось отправить уведомление рефереру {referrer_id}: {e}")
            else:
                logging.warning(f"Реферер с ID {referrer_id} не найден для пользователя {user_id}")

        save_data(BOT_DATA) # Сохраняем изменения user_data (включая referrer_bonus_given)

    else:
        time_left_seconds = (24 * 60 * 60) - (current_time - user_data['last_bonus_claim'])
        hours = int(time_left_seconds // 3600)
        minutes = int((time_left_seconds % 3600) // 60)
        seconds = int(time_left_seconds % 60)
        bot.send_message(user_id, f"<pre>⏳ Ежедневный бонус можно получать раз в 24 часа.</pre>\n" # Используем HTML
                                  f"<b>Попробуйте снова через {hours:02d}ч {minutes:02d}м {seconds:02d}с.</b>",
                                  parse_mode='HTML') # Изменено на HTML

@bot.message_handler(func=lambda message: message.text == '👥 Партнёры')
@require_flyer_check
def handle_referral(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, "⛔ Вы забанены администрацией")
        return
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

    # Считаем и выводим рефералов
    invited_referrals = []
    for uid, u_data in BOT_DATA['users'].items():
        if u_data.get('referrer_id') == str(user_id):
            # Проверяем, есть ли юзернейм, если нет, используем ID
            referrer_username_or_id = u_data.get('referrer_username') 

            # Безопасное отображение имени реферала
            if referrer_username_or_id and not referrer_username_or_id.startswith("ID:"):
                invited_referrals.append(f"<a href='tg://user?id={uid}'>@{escape_html(referrer_username_or_id)}</a>") # Используем HTML
            else:
                # Если это "ID:...", или нет юзернейма, то получаем имя через API
                try:
                    ref_user_info = bot.get_chat_member(uid, uid).user
                    ref_name_escaped = escape_html(ref_user_info.first_name)
                    if ref_user_info.last_name:
                        ref_name_escaped += " " + escape_html(ref_user_info.last_name)
                    invited_referrals.append(f"<a href='tg://user?id={uid}'>{ref_name_escaped}</a> (ID: <code>{uid}</code>)") # Используем HTML
                except Exception as e:
                    logging.warning(f"Не удалось получить инфо о реферале {uid} для реф. системы: {e}")
                    invited_referrals.append(f"Пользователь ID: <code>{uid}</code>") # Используем HTML


    referral_text = (
        f"<pre>Бонусы:</pre>\n"
        f"└<b>{BOT_DATA.get('referral_bonus', 2.0)} {BOT_DATA['currency']['name']} после получения бонуса</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<pre>🔗 Ваша реферальная ссылка:</pre>\n"
        f"└<code>{referral_link}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<pre>👥 Ваши приглашенные рефералы </pre>\n└{len(invited_referrals)}:\n"
    )
    if invited_referrals:
        referral_text += "\n".join([f"├{r}" for r in invited_referrals])
    else:
        referral_text += "У вас пока нет приглашенных рефералов."

    bot.send_message(user_id, referral_text, parse_mode='HTML', reply_markup=back_to_main_menu_inline(), disable_web_page_preview=True) # Изменено на HTML

@bot.message_handler(func=lambda message: message.text == '📊 Статистика')
def handle_user_stats(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        return

    # Основная статистика из админских данных
    stats = BOT_DATA['admin_stats']
    users_count = len(BOT_DATA['users'])

    stats_message = (
        f"<pre>📊 Статистика Бота:</pre>\n"
        f"├👥 Пользователей: {users_count}\n"
        f"├💰 Пoполнено: {stats['total_deposits']:.2f} {BOT_DATA['currency']['name']}\n"
        f"└📤 Выведено: {stats['total_withdraws']:.2f} {BOT_DATA['currency']['name']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<pre>🏆 Топ-3 игроков за 24 часа:</pre>\n"
    )

# Топ-3 игрока за последние 24 часа
    now = datetime.now()
    cutoff_time = now - timedelta(hours=24)
    player_winnings = {}

    recent_game_logs = [
        log for log in BOT_DATA['game_logs']
        if datetime.fromtimestamp(log['timestamp']) >= cutoff_time
    ]

    for log in recent_game_logs:
        player_id = str(log['user_id'])
        player_winnings[player_id] = player_winnings.get(player_id, 0.0) + log['winnings']

    sorted_players = sorted(player_winnings.items(), key=lambda item: item[1], reverse=True)

    top_players_text = []
    for i, (player_id, net_winnings) in enumerate(sorted_players[:3]):
        try:
            player_info = bot.get_chat(int(player_id))
            if player_info.username:
                player_display = f"@{escape_html(player_info.username)}"
            else:
                player_display = escape_html(player_info.first_name)
                if player_info.last_name:
                    player_display += f" {escape_html(player_info.last_name)}"

            top_players_text.append(
                f"{i+1}. {player_display} ({net_winnings:+.2f} {BOT_DATA['currency']['name']})"
            )
        except Exception as e:
            logging.error(f"Не удалось получить информацию о пользователе {player_id}: {e}")
            top_players_text.append(
                f"{i+1}. Пользователь ({net_winnings:+.2f} {BOT_DATA['currency']['name']})"
            )

# Делаем символы ├ и └
    for idx, line in enumerate(top_players_text):
        if idx < len(top_players_text) - 1:
            top_players_text[idx] = f"├{line}"
        else:
            top_players_text[idx] = f"└{line}"

# Добавляем топ-3 к сообщению
    if top_players_text:
        stats_message += "\n".join(top_players_text)
    else:
        stats_message += "Пока нет данных об играх за последние 24 часа."

    markup = types.InlineKeyboardMarkup(row_width=2)

# 👑 Админ отдельной строкой
    markup.row(types.InlineKeyboardButton(text="👑 Администратор", url=f"tg://user?id={ADMIN_ID}"))

# Динамические ссылки из BOT_DATA['stats_links'] (по 2 в ряд)
    links = BOT_DATA.get('stats_links', [])
    for i in range(0, len(links), 2):
        if i + 1 < len(links):
        # два в ряд
            markup.row(
                types.InlineKeyboardButton(text=links[i]['name'], url=links[i]['url']),
                types.InlineKeyboardButton(text=links[i+1]['name'], url=links[i+1]['url'])
            )
        else:
        # если осталась одна
            markup.row(types.InlineKeyboardButton(text=links[i]['name'], url=links[i]['url']))

# 🚀 Создано в отдельной строке
    

    bot.send_message(
        user_id,
        stats_message,
        parse_mode='HTML',
        reply_markup=markup,
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda message: message.text == '👤 Профиль')
@require_flyer_check
def handle_personal_cabinet(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.send_message(user_id, "⛔ Вы забанены администрацией")
        return
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    # Добавлено: ID пользователя и курс MH к USDT
    usdt_value = user_data['balance'] * BOT_DATA['currency']['rate_to_usdt']

    reserved_usdt_value = user_data['reserved_balance'] * BOT_DATA['currency']['rate_to_usdt']

    bot.send_message(user_id, f"<pre>👤 Личный кабинет</pre>\n" # Используем HTML
                               f"<b>├🆔 ID: </b><code>{user_id}</code>\n" # Используем HTML
                               f"<b>├💳 Баланс: {user_data['balance']:.2f} {BOT_DATA['currency']['name']}</b> (~{usdt_value:.2f} USDT)\n" # Используем HTML
                               f"<b>└📤 Ожидается к выплате: {user_data['reserved_balance']:.2f} {BOT_DATA['currency']['name']}</b> (~{reserved_usdt_value:.2f} USDT)\n" # Используем HTML
                               f"━━━━━━━━━━━━━━━━━━━━━\n"
                               f"<pre>♻️ Курс: 1 {BOT_DATA['currency']['name']} = {BOT_DATA['currency']['rate_to_usdt']:.2f} USDT</pre>\n" # Используем HTML
                               f"━━━━━━━━━━━━━━━━━━━━━",
                               parse_mode='HTML', reply_markup=personal_cabinet_markup(user_data['balance'], user_data['reserved_balance'])) # Изменено на HTML

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'set_deposit_amount')
def handle_set_deposit_amount(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    try:
        deposit_amount_usdt = float(message.text)

        if deposit_amount_usdt < BOT_DATA['limits']['min_deposit']:
            bot.send_message(user_id, f"<pre>❌ Минимальная сумма пополнения: {BOT_DATA['limits']['min_deposit']} USDT</pre>", parse_mode='HTML')
            return

        # Курс 1 USDT = 100 MH
        mh_amount_to_receive = deposit_amount_usdt / BOT_DATA['currency']['rate_to_usdt']

        # Создаем инвойс через Crypto Bot
        invoice_result = create_invoice(deposit_amount_usdt, asset="USDT", description=f"Пополнение баланса для {user_id}", user_id=user_id)

        if invoice_result and invoice_result.get('ok') and invoice_result.get('result'):
            invoice_data = invoice_result['result']
            invoice_url = invoice_data['pay_url']
            invoice_id = invoice_data['invoice_id']

            user_data['pending_deposit'] = {
                'invoice_id': invoice_id,
                'mh_amount': mh_amount_to_receive
            }

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('💳 Оплатить', url=invoice_url))
            markup.add(types.InlineKeyboardButton('✅ Проверить оплату', callback_data=f'check_payment_cryptobot_{invoice_id}'))

            bot.send_message(user_id, f"<pre>🧾 Создан счет на пополнение:</pre>\n"
                                      f"<b>├Сумма: {deposit_amount_usdt:.2f} USDT</b>\n" # Используем HTML
                                      f"<b>└К получению: {mh_amount_to_receive:.2f} {BOT_DATA['currency']['name']}</b>\n" # Используем HTML
                                      f"━━━━━━━━━━━━━━━━━━━━━\n"
                                      f"<pre> Не забудьте нажать 'Проверить оплату' после совершения перевода.</pre>\n",
                                      parse_mode='HTML', reply_markup=markup)

            user_data['status'] = 'main'
            user_data['is_processing_deposit'] = False
            save_data(BOT_DATA)

        else:
            error_message = invoice_result.get('error', {}).get('message', 'Неизвестная ошибка') if invoice_result else 'Пустой ответ'
            bot.send_message(user_id, f"<pre>❌ Ошибка при создании счета Crypto Bot. Попробуйте позже.</pre>", parse_mode='HTML', reply_markup=main_menu_markup(user_id)) # Используем HTML и escape_html
            user_data['status'] = 'main' 
            user_data['is_processing_deposit'] = False
            save_data(BOT_DATA)

    except ValueError:
        bot.send_message(user_id, "<pre>❌ Неверный формат суммы. Пожалуйста, введите число.</pre>", parse_mode='HTML') # Используем HTML
        save_data(BOT_DATA)
    except Exception as e:
        bot.send_message(user_id, f"<pre>❌ Произошла непредвиденная ошибка при обработке пополнения.</pre>", parse_mode='HTML') # Используем HTML и escape_html
        user_data['status'] = 'main'
        user_data['is_processing_deposit'] = False
        save_data(BOT_DATA)

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'withdraw')
def handle_set_withdraw_amount_and_address(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.send_message(
                user_id,
                f"<b>❌ Неверный формат.\nВведите сумму и свой юзернейм через пробел.</b>\n"
                f"<pre>Пример: 100 @{message.from_user.username or 'username'}</pre>",
                parse_mode='HTML'
            )
            return

        withdraw_amount = float(parts[0])   # ← сначала создаём переменную
        telegram_username = parts[1].strip()

        # Проверка на положительное число
        if withdraw_amount <= 0:
            bot.send_message(user_id, "<pre>❌ Сумма должна быть больше 0.</pre>", parse_mode='HTML')
            return

        # Проверка минимального лимита
        if withdraw_amount < BOT_DATA['limits']['min_withdraw']:
            bot.send_message(
                user_id,
                f"<pre>❌ Минимальная сумма для вывода: {BOT_DATA['limits']['min_withdraw']} {BOT_DATA['currency']['name']}</pre>", parse_mode='HTML'
            )
            return

        # Проверка доступного баланса
        if (user_data['balance'] - user_data['reserved_balance']) < withdraw_amount:
            bot.send_message(
                user_id,
                f"<pre>❌ Недостаточно средств. Доступно: {(user_data['balance'] - user_data['reserved_balance']):.2f} "
                f"{BOT_DATA['currency']['name']}</pre>",
                parse_mode="HTML"
            )
            user_data['status'] = 'main'
            save_data(BOT_DATA)
            return

        # Проверка юзернейма
        if not telegram_username.startswith('@'):
            bot.send_message(
                user_id,
                "<pre>❌ Неверный формат юзернейма. Должен начинаться с '@'.\nПример: @quyfa</pre>",
                parse_mode="HTML"
            )
            return

        # --- ЛОГИКА ЗАЯВКИ ---
        commission_rate = BOT_DATA.get('withdraw_commission', 0.05)
        commission = withdraw_amount * commission_rate
        amount_after_commission = withdraw_amount - commission

        user_data['reserved_balance'] += withdraw_amount
        save_data(BOT_DATA)

        # Сообщение админу
        admin_text = (
            f"<pre>📤 Новая заявка на вывод</pre>\n"
            f"<b>├Пользователь:</b> <a href='tg://user?id={user_id}'>{escape_html(message.from_user.first_name)}</a>\n"
            f"<b>├Сумма: {withdraw_amount:.2f} {BOT_DATA['currency']['name']}</b>\n"
            f"<b>├Комиссия: {commission_rate*100:.1f}%</b>\n"
            f"<b>├К выплате: {amount_after_commission:.2f}</b>\n"
            f"<b>└User: {escape_html(telegram_username)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_approve_withdraw"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_withdraw")
        )
        sent = bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=markup)

        # Сохраняем заявку
        BOT_DATA.setdefault('pending_withdrawals', {})
        BOT_DATA['pending_withdrawals'][str(sent.message_id)] = {
            'user_id': user_id,
            'amount': withdraw_amount,
            'telegram_username': telegram_username,
            'commission': commission,
            'amount_after_commission': amount_after_commission
        }
        save_data(BOT_DATA)
        commission_rate = BOT_DATA.get('withdraw_commission', 0.05)

        # Сообщение пользователю
        bot.send_message(
            user_id,
            f"<pre>✅ Заявка на вывод создана!</pre>\n"
            f"<b>├Сумма: {withdraw_amount:.2f} {BOT_DATA['currency']['name']}</b>\n"
            f"<b>├Комиссия: {commission_rate*100:.1f}%</b>\n"
            f"<b>└К получению: {amount_after_commission:.2f} {BOT_DATA['currency']['name']}</b>\n"
            f"<pre>Ожидайте ответa от администрации бота</pre>",
            parse_mode="HTML",
            reply_markup=main_menu_markup(user_id)
        )

        user_data['status'] = 'main'
        save_data(BOT_DATA)

    except ValueError:
        bot.send_message(user_id, "❌ Введите число и юзернейм через пробел.\nПример: 100 @username")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при выводе: <code>{escape_html(str(e))}</code>", parse_mode="HTML")
        user_data['status'] = 'main'
        save_data(BOT_DATA)

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'admin_set_check_amount')
def admin_handle_set_check_amount(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "❌ У вас нет прав.")
        return

    user_data = get_user_data(user_id)

    try:
        check_amount = float(message.text)
        if check_amount <= 0:
            bot.send_message(user_id, "❌ Сумма чека должна быть больше 0.")
        else:
            check_id = generate_check_number()
            BOT_DATA['checks'][check_id] = {
                'creator_id': user_id,
                'amount': check_amount,
                'is_claimed': False
            }
            save_data(BOT_DATA)

            check_link = generate_check_link(check_id)
            bot.send_message(user_id, f"✅ <b>Админ-чек на {check_amount:.2f} {BOT_DATA['currency']['name']} создан!</b>\n\n" # Используем HTML
                                      f"Ссылка: <code>{check_link}</code>", # Используем HTML
                                      parse_mode='HTML', reply_markup=main_menu_markup(user_id), disable_web_page_preview=True) # Изменено на HTML
            user_data['status'] = 'main'
            save_data(BOT_DATA)
    except ValueError:
        bot.send_message(user_id, "❌ Пожалуйста, введите числовое значение для суммы чека.")
    except Exception as e:
        logging.error(f"Ошибка при создании админ-чека: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при создании админ-чека. Попробуйте позже.")
        user_data['status'] = 'main'
        save_data(BOT_DATA)

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'admin_change_balance_awaiting_id')
def handle_admin_awaiting_user_id(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "❌ У вас нет прав.")
        return

    user_data = get_user_data(user_id)
    try:
        target_user_id = int(message.text)
        if str(target_user_id) not in BOT_DATA['users']:
            bot.send_message(user_id, "❌ Пользователь с таким ID не найден. Пожалуйста, введите корректный ID или вернитесь в главное меню.", reply_markup=back_to_main_menu_inline())
            return

        user_data['temp_target_user_id'] = target_user_id
        user_data['status'] = 'admin_change_balance_awaiting_amount'
        save_data(BOT_DATA)

        target_balance = BOT_DATA['users'][str(target_user_id)]['balance']
        target_reserved_balance = BOT_DATA['users'][str(target_user_id)].get('reserved_balance', 0.0)
        bot.send_message(user_id, 
                         f"<pre><a href='tg://user?id={target_user_id}'>Пользователь</a> (<code>{target_user_id}</code>).</pre>\n"
                         f"<b>├Баланс: {target_balance:.2f} {BOT_DATA['currency']['name']}</b>\n" # Используем HTML
                         f"<b>└Ожидается к выплате: {target_reserved_balance:.2f} {BOT_DATA['currency']['name']}</b>\n\n" # Используем HTML
                         f"<pre>✍️ <b>Введите сумму, на которую нужно изменить баланс.</b><i>(Например, <code>+10</code> или <code>-5.5</code></i></pre>", # Используем HTML
                         parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove()) # Изменено на HTML
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат ID пользователя. Пожалуйста, введите числовой ID.", parse_mode='HTML') # Используем HTML
    except Exception as e:
        logging.error(f"Ошибка при обработке ID пользователя в админ-панели: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка. Попробуйте снова.")
        user_data['status'] = 'main'
        save_data(BOT_DATA)

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'admin_change_balance_awaiting_amount')
def handle_admin_change_balance_amount(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "❌ У вас нет прав.")
        return

    user_data = get_user_data(user_id)
    target_user_id = user_data.get('temp_target_user_id')

    if target_user_id is None:
        bot.send_message(user_id, "❌ Ошибка: Не удалось определить целевого пользователя. Начните сначала.", reply_markup=admin_panel_markup())
        user_data['status'] = 'main'
        save_data(BOT_DATA)
        return

    try:
        change_amount = float(message.text.replace(',', '.').strip())

        target_user_data = get_user_data(target_user_id)
        old_balance = target_user_data['balance']

        target_user_data['balance'] += change_amount

        # Убедимся, что баланс не становится меньше зарезервированного (если это не обнуление)
        if target_user_data['balance'] < target_user_data['reserved_balance'] and change_amount < 0:
             bot.send_message(user_id, f"⚠️ Вы не можете уменьшить баланс пользователя ниже зарезервированного (<b>{target_user_data['reserved_balance']:.2f} {BOT_DATA['currency']['name']}</b>).", parse_mode='HTML') # Используем HTML
             user_data['status'] = 'main' # Сбрасываем статус
             del user_data['temp_target_user_id']
             save_data(BOT_DATA)
             return

        if target_user_data['balance'] < 0: # Общее обнуление, если ушел в минус
            target_user_data['balance'] = 0.0
            target_user_data['reserved_balance'] = 0.0 # Обнуляем и резерв, если баланс 0
            bot.send_message(user_id, f"⚠️ Баланс пользователя {target_user_id} стал бы отрицательным, установлен в 0 (зарезервированный баланс также обнулен).", parse_mode='HTML') # Используем HTML

        save_data(BOT_DATA)

        bot.send_message(user_id, 
                         f"<pre>✅ Баланс Пользователя<code>{target_user_id}</code> успешно изменен.</pre>\n" # Используем HTML
                         f"<b>├Изменение: {change_amount:+.2f} {BOT_DATA['currency']['name']}</b>\n" # Используем HTML
                         f"<b>└Новый баланс: {target_user_data['balance']:.2f} {BOT_DATA['currency']['name']}</b>", # Используем HTML
                         parse_mode='HTML', reply_markup=main_menu_markup(user_id)) # Изменено на HTML

        try:
            notification_text = (
                f"<pre>🔔 Баланс изменён администратором!</pre>\n" # Используем HTML
                f"<b>├Изменение: {change_amount:+.2f} {BOT_DATA['currency']['name']}</b>\n" # Используем HTML
                f"<b>└Новый баланс: {target_user_data['balance']:.2f} {BOT_DATA['currency']['name']}</b>" # Используем HTML
            )
            bot.send_message(target_user_id, notification_text, parse_mode='HTML') # Изменено на HTML
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю {target_user_id} об изменении баланса: {e}")

    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат суммы. Пожалуйста, введите число (например, <code>10</code>, <code>-5.5</code>).", parse_mode='HTML') # Используем HTML
    except Exception as e:
        logging.error(f"Ошибка при изменении баланса пользователя админом: {e}")
        bot.send_message(user_id, "❌ Произошла непредвиденная ошибка. Попробуйте снова.")
    finally:
        user_data['status'] = 'main'
        if 'temp_target_user_id' in user_data:
            del user_data['temp_target_user_id']
        save_data(BOT_DATA)

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_token")
def admin_change_token(call):
    if call.from_user.id != ADMIN_ID:
        return
    user_data = get_user_data(call.from_user.id)
    user_data['status'] = 'awaiting_new_token'
    save_data(BOT_DATA)
    bot.send_message(call.from_user.id, "✍️ Введите новый токен для CryptoBot:")
@bot.message_handler(func=lambda m: get_user_data(m.from_user.id)['status'] == 'awaiting_new_token')
def set_new_token(m):
    if m.from_user.id != ADMIN_ID:
        return
    BOT_DATA['crypto_bot_token'] = m.text.strip()
    user_data = get_user_data(m.from_user.id)
    user_data['status'] = 'main'
    save_data(BOT_DATA)
    bot.send_message(m.chat.id, "✅ Токен успешно обновлен!", reply_markup=admin_panel_markup())

# --- НОВЫЕ ОБРАБОТЧИКИ ДЛЯ УПРАВЛЕНИЯ ПОДПИСКАМИ ---
@bot.callback_query_handler(func=lambda call: call.data == 'admin_manage_subscriptions')
def admin_manage_subscriptions_callback(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return
    bot.answer_callback_query(call.id)
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, 
                          text="✅ <b>Управление обязательными подписками:</b>", # Используем HTML
                          parse_mode='HTML', reply_markup=manage_subscriptions_markup()) # Изменено на HTML

@bot.callback_query_handler(func=lambda call: call.data == 'admin_add_subscription')
def admin_add_subscription_callback(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return
    bot.answer_callback_query(call.id)
    user_data = get_user_data(user_id)
    user_data['status'] = 'admin_add_subscription_awaiting_id'
    save_data(BOT_DATA)
    bot.send_message(user_id, 
                     "✍️ <b>Введите ID канала/чата, его публичную ссылку (или ссылку-приглашение) и название через запятую.</b>\n\n" # Используем HTML
                     "Пример: <code>-1001234567890, https://t.me/my_channel_link, Мой Канал</code>\n\n" # Используем HTML
                     "<b>Важно:</b> Бот должен быть администратором в этом канале/чате, чтобы иметь возможность проверять подписку.", # Используем HTML
                     parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove()) # Изменено на HTML

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'admin_add_subscription_awaiting_id')
def admin_handle_add_subscription_data(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "❌ У вас нет прав.")
        return

    user_data = get_user_data(user_id)
    parts = [p.strip() for p in message.text.split(',')]

    if len(parts) < 3:
        bot.send_message(user_id, "❌ Неверный формат. Пожалуйста, введите ID, ссылку и название через запятую.", parse_mode='HTML') # Используем HTML
        return

    channel_id_str, channel_link, channel_name = parts[0], parts[1], parts[2]

    try:
        # Проверим, существует ли канал и является ли бот его админом
        chat_info = bot.get_chat(channel_id_str)
        if chat_info.type not in ['channel', 'supergroup']:
            bot.send_message(user_id, "❌ Это не канал или супергруппа. Пожалуйста, введите ID канала/чата.", parse_mode='HTML') # Используем HTML
            return

        BOT_DATA['required_subscriptions'][channel_id_str] = {
            'link': channel_link,
            'name': channel_name
        }
        save_data(BOT_DATA)
        bot.send_message(user_id, 
                         f"✅ Канал/чат <b><code>{escape_html(channel_name)}</code></b> (ID: <code>{channel_id_str}</code>) добавлен в список обязательных подписок.", # Используем HTML и escape_html
                         parse_mode='HTML', reply_markup=admin_panel_markup()) # Изменено на HTML
    except telebot.apihelper.ApiTelegramException as e:
        if "chat not found" in str(e) or "Bad Request: chat not found" in str(e) or "need to be a member of the supergroup chat" in str(e):
            bot.send_message(user_id, 
                             f"❌ Не удалось добавить канал. Убедитесь, что ID канала/чата верен, и бот добавлен в канал/чат как администратор.\nОшибка: <code>{escape_html(str(e))}</code>", # Используем HTML и escape_html
                             parse_mode='HTML') # Изменено на HTML
        else:
            bot.send_message(user_id, f"❌ Произошла ошибка при проверке канала: <code>{escape_html(str(e))}</code>", parse_mode='HTML') # Используем HTML и escape_html
        logging.error(f"Ошибка при добавлении обязательной подписки: {e}")
    except Exception as e:
        bot.send_message(user_id, f"❌ Произошла непредвиденная ошибка: <code>{escape_html(str(e))}</code>", parse_mode='HTML') # Используем HTML и escape_html
        logging.error(f"Непредвиденная ошибка при добавлении подписки: {e}")
    finally:
        user_data['status'] = 'main'
        save_data(BOT_DATA)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_list_subscriptions')
def admin_list_subscriptions_callback(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return
    bot.answer_callback_query(call.id)

    subscriptions = BOT_DATA.get('required_subscriptions', {})
    if not subscriptions:
        text = "🤷‍♀️ В настоящее время нет обязательных подписок."
    else:
        text = "✅ <b>Текущие обязательные подписки:</b>\n\n" # Используем HTML
        for channel_id, info in subscriptions.items():
            text += f"<b>Название:</b> {escape_html(info.get('name', 'N/A'))}\n" # Используем HTML и escape_html
            text += f"<b>ID:</b> <code>{channel_id}</code>\n" # Используем HTML
            text += f"<b>Ссылка:</b> <a href='{info['link']}'>{escape_html(info['link'])}</a>\n" # Используем HTML и escape_html
            text += "---\n"

    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, 
                          text=text, 
                          parse_mode='HTML', # Изменено на HTML
                          disable_web_page_preview=True, 
                          reply_markup=manage_subscriptions_markup())


@bot.callback_query_handler(func=lambda call: call.data == 'admin_remove_subscription')
def admin_remove_subscription_callback(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return
    bot.answer_callback_query(call.id)
    user_data = get_user_data(user_id)
    user_data['status'] = 'admin_remove_subscription_awaiting_id'
    save_data(BOT_DATA)
    bot.send_message(user_id, "✍️ <b>Введите ID канала/чата, который нужно удалить из обязательных подписок:</b>", parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove()) # Используем HTML

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'admin_remove_subscription_awaiting_id')
def admin_handle_remove_subscription_id(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "❌ У вас нет прав.")
        return

    user_data = get_user_data(user_id)
    channel_id_to_remove = message.text.strip()

    if channel_id_to_remove in BOT_DATA['required_subscriptions']:
        del BOT_DATA['required_subscriptions'][channel_id_to_remove]
        save_data(BOT_DATA)
        bot.send_message(user_id, 
                         f"✅ Канал/чат с ID <code>{channel_id_to_remove}</code> успешно удален из обязательных подписок.", # Используем HTML
                         parse_mode='HTML', reply_markup=admin_panel_markup()) # Изменено на HTML
    else:
        bot.send_message(user_id, 
                         f"❌ Канал/чат с ID <code>{channel_id_to_remove}</code> не найден в списке обязательных подписок.", # Используем HTML
                         parse_mode='HTML', reply_markup=admin_panel_markup()) # Изменено на HTML

    user_data['status'] = 'main'
    save_data(BOT_DATA)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_panel_back')
def admin_panel_back_callback(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return
    bot.answer_callback_query(call.id)
    bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, 
                          text="⚙️ Админ-панель", 
                          parse_mode='HTML', reply_markup=admin_panel_markup()) # Изменено на HTML

# --- НОВЫЕ ОБРАБОТЧИКИ ДЛЯ РАССЫЛКИ ---
@bot.callback_query_handler(func=lambda call: call.data == 'admin_start_broadcast')
def admin_start_broadcast_callback(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return
    bot.answer_callback_query(call.id)
    user_data = get_user_data(user_id)
    user_data['status'] = 'admin_broadcast_awaiting_message'
    save_data(BOT_DATA)
    bot.send_message(user_id, 
                     "✍️ <b>Введите текст сообщения для рассылки.</b>\n" # Используем HTML
                     "<i>(Поддерживается HTML: <b>жирный</b>, <i>курсив</i>, <code>моноширинный</code>, <a href='URL'>ссылка</a>)</i>\n\n" # Используем HTML
                     "Нажмите '🔙 В главное меню' если хотите отменить рассылку.",
                     parse_mode='HTML', # Изменено на HTML
                     reply_markup=back_to_main_menu_inline())

@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'admin_broadcast_awaiting_message')
def admin_handle_broadcast_message(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(user_id, "❌ У вас нет прав.")
        return

    user_data = get_user_data(user_id)
    broadcast_text = message.text

    sent_count = 0
    failed_count = 0
    total_users = len(BOT_DATA['users'])

    bot.send_message(user_id, f"Начинаю рассылку сообщения {total_users} пользователям. Это может занять некоторое время...", parse_mode='HTML') # Используем HTML

    for target_user_id_str in BOT_DATA['users'].keys():
        try:
            target_user_id = int(target_user_id_str)
            bot.send_message(target_user_id, broadcast_text, parse_mode='HTML', disable_web_page_preview=True) # Изменено на HTML
            sent_count += 1
            time.sleep(0.1) # Задержка для предотвращения ограничений Telegram API
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {target_user_id_str} в ходе рассылки: {e}")
            failed_count += 1

    bot.send_message(user_id, 
                     f"✅ <b>Рассылка завершена!</b>\n\n" # Используем HTML
                     f"Успешно отправлено: <b>{sent_count}</b>\n" # Используем HTML
                     f"Не удалось отправить: <b>{failed_count}</b>", # Используем HTML
                     parse_mode='HTML', # Изменено на HTML
                     reply_markup=main_menu_markup(user_id))

    user_data['status'] = 'main'
    save_data(BOT_DATA)

# --- ОБРАБОТЧИКИ CALLBACK-КНОПОК (InlineKeyboardMarkup) ---
@bot.callback_query_handler(func=lambda call: call.data == 'check_my_subscriptions')
def handle_check_my_subscriptions(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    if check_subscription(user_id):
        try:
            bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение с подписками: {e}")
        bot.send_message(user_id, "🎉 <b>Поздравляем! Вы подписаны на все обязательные каналы!</b>\n" # Используем HTML
                                  f"Теперь вы можете пользоваться ботом.", 
                                  parse_mode='HTML', reply_markup=main_menu_markup(user_id)) # Изменено на HTML
    else:
        bot.send_message(user_id, "🤔 Кажется, вы еще не подписались на все каналы. Пожалуйста, проверьте и попробуйте снова.", parse_mode='HTML', reply_markup=subscription_check_markup()) # Изменено на HTML

@bot.callback_query_handler(func=lambda call: call.data == 'personal_cabinet_deposit')
def handle_deposit_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    if user_data.get('is_processing_deposit', False):
        bot.send_message(user_id, "⏳ Пожалуйста, подождите, процесс пополнения уже запущен.")
        return

    user_data['is_processing_deposit'] = True
    user_data['status'] = 'set_deposit_amount'
    save_data(BOT_DATA)

    bot.send_message(user_id, "💰 <b>Введите сумму пополнения в USDT:</b>", parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove()) # Используем HTML

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_payment_cryptobot_'))
def handle_check_payment_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    invoice_id = call.data.replace('check_payment_cryptobot_', '')

    pending_deposit = BOT_DATA['users'][str(user_id)].get('pending_deposit')
    if not pending_deposit or str(pending_deposit['invoice_id']) != invoice_id:
        bot.send_message(user_id, "Счет не найден или уже обработан.")
        return

    status = check_invoice_status(invoice_id)

    if status == 'paid':
        mh_amount = pending_deposit['mh_amount']
        BOT_DATA['users'][str(user_id)]['balance'] += mh_amount
        BOT_DATA['admin_stats']['total_deposits'] += mh_amount
        BOT_DATA['users'][str(user_id)]['pending_deposit'] = None
        BOT_DATA['users'][str(user_id)]['is_processing_deposit'] = False
        save_data(BOT_DATA)
    # ✅ Добавляем лог пополнения
        BOT_DATA.setdefault('deposit_logs', [])
        BOT_DATA['deposit_logs'].append({
            "user_id": user_id,
            "username": call.from_user.username or f"ID:{user_id}",
            "amount": mh_amount,  # сумма в валюте бота (MH)
            "timestamp": int(time.time())
        })
        save_data(BOT_DATA)


        bot.send_message(user_id, f"🎉 <b>Баланс успешно пополнен!</b>\n" # Используем HTML
                                  f"На ваш счет зачислено {mh_amount:.2f} {BOT_DATA['currency']['name']}.\n"
                                  f"Текущий баланс: {BOT_DATA['users'][str(user_id)]['balance']:.2f} {BOT_DATA['currency']['name']}.",
                                  parse_mode='HTML', reply_markup=main_menu_markup(user_id)) # Изменено на HTML
        bot.answer_callback_query(call.id, "✅ Оплата подтверждена!")
    elif status == 'active':
        bot.answer_callback_query(call.id, "⏳ Счет ещё не оплачен.")
    else:
        bot.answer_callback_query(call.id, "❌ Счет истек, отменен или произошла ошибка. Если вы уверены в оплате, свяжитесь с поддержкой.", parse_mode='HTML') # Используем HTML
        BOT_DATA['users'][str(user_id)]['pending_deposit'] = None
        BOT_DATA['users'][str(user_id)]['is_processing_deposit'] = False
        save_data(BOT_DATA)


# --- MESSAGE: ВВОД СТАВКИ ---
@bot.message_handler(func=lambda m: get_user_data(m.from_user.id).get("status") == "set_bet")
def handle_set_bet(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    try:
        bet = float(message.text.replace(",", ".").strip())
    except ValueError:
        bot.send_message(user_id, "❌ Введите число для ставки.")
        return

    # --- Проверка минимальной ставки и баланса ---
    if bet < BOT_DATA['limits']['min_bet']:
        bot.send_message(user_id, f"❌ Минимальная ставка: {BOT_DATA['limits']['min_bet']} {BOT_DATA['currency']['name']}")
        return
    if bet > user_data['balance']:
        bot.send_message(user_id, f"❌ Недостаточно средств. Ваш баланс: {user_data['balance']:.2f} {BOT_DATA['currency']['name']}")
        return

    # --- Сохраняем ставку и меняем статус ---
    user_data["active_bet"] = bet
    user_data["is_processing_game"] = True
    user_data["status"] = "main"
    save_data(BOT_DATA)

    game_key = user_data.get("chosen_game")
    if not game_key:
        bot.send_message(user_id, "❌ Ошибка: игра не выбрана.")
        return

    emoji_map = {
        "game_cube": "🎲",
        "game_even": "🎲",
        "game_odd": "🎲",
        "game_more": "🎲",
        "game_less": "🎲",
        "game_duel": "🎲",
        "game_red": "🎯",
        "game_white": "🎯",
        "game_darts_center": "🎯",
        "game_basket_score": "🏀",
        "game_basket_miss": "🏀",
        "game_football_goal": "⚽",
        "game_football_miss": "⚽",
        "game_bowling": "🎳",
        "game_slots": "🎰"
    }

    if game_key not in emoji_map:
        bot.send_message(user_id, "❌ Игра не поддерживается.")
        return

    # --- Логика игры ---
    if game_key == "game_duel":
        # Дуель: кидаем два кубика
        user_dice = bot.send_dice(user_id, emoji="🎲")
        time.sleep(3)  # даем время на анимацию
        bot_dice = bot.send_dice(user_id, emoji="🎲")

        user_roll = user_dice.dice.value
        bot_roll = bot_dice.dice.value

        text, win_amount = play_duel(user_id, user_roll, bot_roll, bet)
        bot.send_message(user_id, text, parse_mode="HTML", reply_markup=game_after_roll_markup())

    else:
        # Другие игры: кидаем один кубик
        sent_dice = bot.send_dice(user_id, emoji=emoji_map[game_key])
        rolled_value = sent_dice.dice.value
        text, win_amount = play_game(user_id, game_key, rolled_value)
        
    bot.send_message(user_id, text, parse_mode="HTML", reply_markup=game_after_roll_markup())

    

    # --- Сбрасываем игру ---
    user_data["active_bet"] = None
    user_data["is_processing_game"] = False
    save_data(BOT_DATA)

def play_duel(user_id: int, user_roll: int, bot_roll: int, bet: float):
    user_data = get_user_data(user_id)
    coeffs = BOT_DATA["game_coeffs"]
    currency = BOT_DATA['currency']['name']
    win_amount = 0.0

    if user_roll > bot_roll:
        win_amount = bet * float(coeffs["duel"])
        user_data["balance"] += win_amount
        text = (f"⚔️ Дуэль!\n\n"
                f"Вы: 🎲 <b>{user_roll}</b>\n"
                f"Бот: 🎲 <b>{bot_roll}</b>\n\n"
                f"🏆 Победа! +{win_amount:.2f} {currency}")
    elif user_roll < bot_roll:
        user_data["balance"] -= bet
        text = (f"⚔️ Дуэль!\n\n"
                f"Вы: 🎲 <b>{user_roll}</b>\n"
                f"Бот: 🎲 <b>{bot_roll}</b>\n\n"
                f"❌ Поражение. -{bet:.2f} {currency}")
    else:
        text = (f"⚔️ Дуэль!\n\n"
                f"Вы: 🎲 <b>{user_roll}</b>\n"
                f"Бот: 🎲 <b>{bot_roll}</b>\n\n"
                f"🤝 Ничья. Ставка возвращена.")

    BOT_DATA['game_logs'].append({
        'user_id': user_id,
        'bet_amount': bet,
        'win': win_amount > 0,
        'winnings': win_amount if win_amount > 0 else (-bet if user_roll < bot_roll else 0),
        'timestamp': int(time.time())
    })

    save_data(BOT_DATA)
    return text, win_amount

# --- HANDLER: ВВОД СТАВКИ ---
@bot.message_handler(func=lambda message: get_user_data(message.from_user.id)['status'] == 'set_bet')
def handle_set_bet_amount(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    try:
        bet_amount = float(message.text.replace(',', '.'))

        if bet_amount < BOT_DATA['limits']['min_bet']:
            bot.send_message(user_id, f"❌ Минимальная ставка: {BOT_DATA['limits']['min_bet']} {BOT_DATA['currency']['name']}")
            return
        elif bet_amount > user_data['balance']:
            bot.send_message(user_id, "❌ Недостаточно средств на балансе.")
            return

        # Сохраняем ставку и меняем статус
        user_data['active_bet'] = bet_amount
        user_data['status'] = 'main'
        user_data['is_processing_game'] = True
        save_data(BOT_DATA)

        bot.send_message(
            user_id,
            f"🎲 Ваша ставка: <b>{bet_amount:.2f} {BOT_DATA['currency']['name']}</b>\n\nИгра начинается!",
            parse_mode="HTML"
        )

        # Запускаем игру с эмодзи
        game_key = user_data.get('chosen_game')

        # Эмодзи для игры
        if game_key == "game_cube":
            # Кидаємо анімацію кубика
            bot.send_dice(user_id, emoji="🎲")
        elif game_key == "game_even":
            bot.send_message(user_id, "🎲")
        elif game_key == "game_odd":
            bot.send_message(user_id, "🎲")
        elif game_key == "game_more":
            bot.send_message(user_id, "🎲")
        elif game_key == "game_less":
            bot.send_message(user_id, "🎲")
        elif game_key == "game_red":
            bot.send_message(user_id, "🎯")
        elif game_key == "game_white":
            bot.send_message(user_id, "🎯")
        elif game_key == "game_darts_center":
            bot.send_message(user_id, "🎯")
        elif game_key == "game_basket_score":
            bot.send_message(user_id, "🏀")
        elif game_key == "game_basket_miss":
            bot.send_message(user_id, "🏀")
        elif game_key == "game_football_goal":
            bot.send_message(user_id, "⚽️")
        elif game_key == "game_football_miss":
            bot.send_message(user_id, "⚽️")
        elif game_key == "game_bowling":
            bot.send_message(user_id, "🎳")
        elif game_key == "game_slots":
            bot.send_message(user_id, "🎰")

        # После 2 секунд мы считаем результат
        time.sleep(2)

        # Запускаем функцию игры
        text, win_amount = play_game(user_id, game_key)
        bot.send_message(user_id, text, parse_mode='HTML', reply_markup=game_after_roll_markup())

        # Очистка данных после игры
        user_data['active_bet'] = None
        user_data['is_processing_game'] = False
        save_data(BOT_DATA)

    except ValueError:
        bot.send_message(user_id, "❌ Пожалуйста, введите числовое значение для ставки.")

@bot.callback_query_handler(func=lambda call: call.data == 'play_game_again')
def handle_play_game_again(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)
    user_data['status'] = 'set_bet'
    save_data(BOT_DATA)

    try:
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение после игры: {e}")

    bot.send_message(
        user_id,
        "<pre>🔢 Введите сумму ставки:</pre>",
        parse_mode='HTML',
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.callback_query_handler(func=lambda call: call.data == 'personal_cabinet_withdraw')
def handle_withdraw_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    if not check_subscription(user_id):
        return

    user_data = get_user_data(user_id)

    # Проверяем доступный баланс
    if (user_data['balance'] - user_data['reserved_balance']) < BOT_DATA['limits'].get('min_withdraw', 10.0):
        bot.send_message(user_id, f"<pre>❌ Минимальная сумма для вывода: {BOT_DATA['limits']['min_withdraw']} {BOT_DATA['currency']['name']}. Ваш доступный баланс: {(user_data['balance'] - user_data['reserved_balance']):.2f} {BOT_DATA['currency']['name']}</pre>", parse_mode='HTML') # Используем HTML
        return
    commission_rate = BOT_DATA.get('withdraw_commission', 0.05)
    user_data['status'] = 'withdraw'
    save_data(BOT_DATA)
    bot.send_message(user_id, f"<pre>💵 Введите сумму для вывода и свой юзернейм Telegram через пробел.</pre>\n"
                               f"<b>Пример:</b> <code>100 @quyfa</code>\n" # Используем HTML
                               f"<b>Комиссия: {commission_rate*100:.1f}% от суммы вывода.</b>\n"
                               f"<pre>Заявка на вывод создана. Ожидайте проверки заявки от Администрации</pre>", # Используем HTML
                               parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove()) # Изменено на HTML

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main_menu_handler(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    user_data['status'] = 'main'
    save_data(BOT_DATA)

    try:
        # Пытаемся удалить сообщение с inline-кнопками, чтобы не было дублирования
        bot.delete_message(chat_id=user_id, message_id=call.message.message_id)
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение или его разметку: {e}")
        pass # Если не удалось, просто отправляем новое сообщение

    bot.send_message(user_id, "Главное меню:", reply_markup=main_menu_markup(user_id))

@bot.callback_query_handler(func=lambda call: call.data == "back_to_stats")
def back_to_stats(call):
    admin_tops_menu(call)  # просто викликаємо ту ж саму функцію меню статистики

# --- Главное меню админки с топами ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_tops_menu(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Нет доступа.")
        return

    stats = BOT_DATA['admin_stats']
    users_count = len(BOT_DATA['users'])

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👑 Топ Игроков", callback_data="top_users"))
    markup.add(types.InlineKeyboardButton("📥 Топ Пополнений", callback_data="top_deposits"),
               types.InlineKeyboardButton("📤 Топ Выводов", callback_data="top_withdraws"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel_back"))

    bot.edit_message_text(f"<pre>📊 Статистика Бота</pre>\n<b>├👥 Всего пользователей: {users_count}\n├💰 Всего пополнений: {stats['total_deposits']:.2f} {BOT_DATA['currency']['name']}\n├💸 Всего выводов: {stats['total_withdraws']:.2f} {BOT_DATA['currency']['name']}\n└💼 Общая комиссия: {stats['total_fees']:.2f} {BOT_DATA['currency']['name']}</b>\n━━━━━━━━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id, parse_mode='HTML',
                          reply_markup=markup)

# --- Подменю для топов ---
@bot.callback_query_handler(func=lambda call: call.data in ["top_users", "top_deposits", "top_withdraws"])
def top_submenu(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📅 За 24 часа", callback_data=f"{call.data}_24h"),
               types.InlineKeyboardButton("📆 За всё время", callback_data=f"{call.data}_all"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_stats"))

    bot.edit_message_text("<pre>📊 Выберите интересующий период:</pre>", call.message.chat.id, call.message.message_id,
                          reply_markup=markup, parse_mode='HTML')

# --- Общая функция для вывода топа ---
def send_top_list(chat_id, title, sorted_data, currency, limit=50):
    top_text = f"<pre>{title}</pre>\n"
    top_lines = []

    for i, (uid, amount) in enumerate(sorted_data[:limit]):
        try:
            user_info = bot.get_chat(int(uid))
            if user_info.username:
                display_name = f"@{escape_html(user_info.username)}"
            else:
                display_name = escape_html(user_info.first_name or "Без имени")
                if user_info.last_name:
                    display_name += f" {escape_html(user_info.last_name)}"
        except Exception:
            display_name = f"ID {uid}"

        line = f"{i+1}. {display_name} ({amount:.2f} {currency})"
        top_lines.append(line)

    # Делаем ├ и └
    for idx, line in enumerate(top_lines):
        if idx < len(top_lines) - 1:
            top_lines[idx] = f"├{line}"
        else:
            top_lines[idx] = f"└{line}"

    if top_lines:
        top_text += "\n".join(top_lines)
    else:
        top_text += "Нет данных."

    bot.send_message(chat_id, top_text, parse_mode="HTML")

# --- Хендлеры для топов ---
@bot.callback_query_handler(func=lambda call: call.data.endswith(("_24h", "_all")))
def handle_tops(call):
    now = datetime.now()
    cutoff_time = now - timedelta(hours=24)
    currency = BOT_DATA['currency']['name']

    # Сбор данных
    if call.data.startswith("top_users"):
        # Топ по выигрышам в играх
        player_stats = {}
        for log in BOT_DATA['game_logs']:
            if call.data.endswith("_24h") and datetime.fromtimestamp(log['timestamp']) < cutoff_time:
                continue
            player_stats[log['user_id']] = player_stats.get(log['user_id'], 0.0) + log['winnings']
        sorted_data = sorted(player_stats.items(), key=lambda x: x[1], reverse=True)
        send_top_list(call.message.chat.id, "🏆 Топ пользователей", sorted_data, currency)

    elif call.data.startswith("top_deposits"):
        deposits = {}
        for log in BOT_DATA['deposit_logs']:
            if call.data.endswith("_24h") and datetime.fromtimestamp(log['timestamp']) < cutoff_time:
                continue
            deposits[log['user_id']] = deposits.get(log['user_id'], 0.0) + log['amount']
        sorted_data = sorted(deposits.items(), key=lambda x: x[1], reverse=True)
        send_top_list(call.message.chat.id, "💰 Топ пополнений", sorted_data, currency)

    elif call.data.startswith("top_withdraws"):
        withdraws = {}
        for log in BOT_DATA['withdraw_logs']:
            if call.data.endswith("_24h") and datetime.fromtimestamp(log['timestamp']) < cutoff_time:
                continue
            withdraws[log['user_id']] = withdraws.get(log['user_id'], 0.0) + log['amount']
        sorted_data = sorted(withdraws.items(), key=lambda x: x[1], reverse=True)
        send_top_list(call.message.chat.id, "💸 Топ выводов", sorted_data, currency)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_create_check')
def admin_create_check_callback(call):
    user_id = call.from_user.id
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return

    bot.answer_callback_query(call.id)
    user_data = get_user_data(user_id)
    user_data['status'] = 'admin_set_check_amount'
    save_data(BOT_DATA)
    bot.send_message(user_id, "✍️ <b>Введите сумму чека для создания (админ):</b>", parse_mode='HTML') # Используем HTML

@bot.callback_query_handler(func=lambda call: call.data in ['admin_approve_withdraw', 'admin_reject_withdraw'])
def handle_admin_withdraw_action(call):
    admin_id = call.from_user.id
    if admin_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав.")
        return

    bot.answer_callback_query(call.id)
    message_id_from_admin = str(call.message.message_id) 

    withdrawal_info = BOT_DATA['pending_withdrawals'].get(message_id_from_admin)

    if not withdrawal_info:
        bot.edit_message_text(chat_id=admin_id, message_id=call.message.message_id, 
                              text="⚠️ Эта заявка на вывод уже была обработана или не найдена.", 
                              parse_mode='HTML') # Используем HTML
        return

    target_user_id = withdrawal_info['user_id']
    withdraw_amount = withdrawal_info['amount']
    telegram_username = withdrawal_info['telegram_username']
    commission = withdrawal_info['commission']
    amount_after_commission = withdrawal_info['amount_after_commission']

    user_data = get_user_data(target_user_id) 

    if call.data == 'admin_approve_withdraw':
        # Списываем средства с баланса пользователя и уменьшаем зарезервированный баланс
        if user_data['balance'] >= withdraw_amount and user_data['reserved_balance'] >= withdraw_amount:
            user_data['balance'] -= withdraw_amount
            user_data['reserved_balance'] -= withdraw_amount
            BOT_DATA['admin_stats']['total_withdraws'] += withdraw_amount 
            BOT_DATA['admin_stats']['total_fees'] += commission          

            # Безопасное формирование имени пользователя для админ-уведомления
            try:
                target_user_info = bot.get_chat_member(target_user_id, target_user_id).user
                target_user_name_escaped = escape_html(target_user_info.first_name)
                if target_user_info.last_name:
                    target_user_name_escaped += " " + escape_html(target_user_info.last_name)

                if target_user_info.username:
                    user_mention_admin = f"<a href='tg://user?id={target_user_id}'>@{escape_html(target_user_info.username)}</a>"
                else:
                    user_mention_admin = f"<a href='tg://user?id={target_user_id}'>{target_user_name_escaped}</a> (ID: <code>{target_user_id}</code>)"
            except Exception:
                user_mention_admin = f"Пользователь (ID: <code>{target_user_id}</code>)"

            bot.edit_message_text(chat_id=admin_id, message_id=call.message.message_id,
                                  text=f"<pre>✅ Вывод средств подтвержден!</pre>\n"
                                       f"<b>├Пользователь: {user_mention_admin}</b>\n" # Используем HTML
                                       f"<b>└К выплате: {amount_after_commission:.2f} {BOT_DATA['currency']['name']}</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━━━━\n"
                                       f"<pre>Не забудьте произвести перевод на {escape_html(telegram_username)}.</pre>", # Используем HTML и escape_html
                                  parse_mode='HTML') # Изменено на HTML

            try:
                bot.send_message(target_user_id, 
                                 f"<pre>🎉 Ваша заявка на вывод средств одобрена!</pre>\n" # Используем HTML
                                 f"<b>├Получено: {amount_after_commission:.2f} {BOT_DATA['currency']['name']}</b>.\n" # Используем HTML
                                 f"<b>└Tекущий баланс: {user_data['balance']:.2f} {BOT_DATA['currency']['name']}</b>\n" # Используем HTML
                                 f"━━━━━━━━━━━━━━━━━━━━━\n"
                                 f"<pre>Средства отправлены на ваш Telegram: {escape_html(telegram_username)}.</pre>",
                                 parse_mode='HTML', reply_markup=main_menu_markup(target_user_id)) # Изменено на HTML
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление пользователю {target_user_id} об одобрении вывода: {e}")
        else:
            bot.edit_message_text(chat_id=admin_id, message_id=call.message.message_id,
                                  text=f"⚠️ Ошибка: Недостаточно средств на балансе пользователя {target_user_id} для списания {withdraw_amount:.2f} {BOT_DATA['currency']['name']}, или зарезервировано недостаточно. Возможно, баланс изменился после создания заявки. Проверьте вручную.",
                                  parse_mode='HTML') # Используем HTML
            try:
                 bot.send_message(target_user_id, 
                                 f"<pre>⚠️ Ваша заявка на вывод средств была отменена из-за ошибки.</pre>\n",
                                 f"<i>Администратор не смог обработать заявку. Пожалуйста, проверьте свой баланс и свяжитесь с поддержкой, если проблема сохраняется.</b>",
                                 parse_mode='HTML', reply_markup=main_menu_markup(target_user_id)) # Используем HTML
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление пользователю {target_user_id} об ошибке вывода: {e}")
# Добавляем лог вывода
        BOT_DATA.setdefault('withdraw_logs', [])
        BOT_DATA['withdraw_logs'].append({
            "user_id": target_user_id,
            "username": telegram_username,
            "amount": amount_after_commission,
            "timestamp": int(time.time())
        })
        save_data(BOT_DATA)

    elif call.data == 'admin_reject_withdraw':
        # Возвращаем средства из зарезервированного баланса в обычный
        if user_data['reserved_balance'] >= withdraw_amount:
            user_data['reserved_balance'] -= withdraw_amount
        else:
            # Если почему-то зарезервировано меньше, чем в заявке (не должно быть, но на случай ошибок)
            logging.warning(f"Попытка отклонить вывод {withdraw_amount} {BOT_DATA['currency']['name']} для {target_user_id}, но зарезервировано только {user_data['reserved_balance']} {BOT_DATA['currency']['name']}.")
            user_data['reserved_balance'] = 0.0 # Обнуляем резерв на всякий случай

        # Безопасное формирование имени пользователя для админ-уведомления
        try:
            target_user_info = bot.get_chat_member(target_user_id, target_user_id).user
            target_user_name_escaped = escape_html(target_user_info.first_name)
            if target_user_info.last_name:
                target_user_name_escaped += " " + escape_html(target_user_info.last_name)

            if target_user_info.username:
                user_mention_admin = f"<a href='tg://user?id={target_user_id}'>@{escape_html(target_user_info.username)}</a>"
            else:
                user_mention_admin = f"<a href='tg://user?id={target_user_id}'>{target_user_name_escaped}</a> (ID: <code>{target_user_id}</code>)"
        except Exception:
            user_mention_admin = f"Пользователь (ID: <code>{target_user_id}</code>)"


        bot.edit_message_text(chat_id=admin_id, message_id=call.message.message_id, 
                              text=f"<pre>❌ Вывод средств отклонен.</pre>\n" # Используем HTML
                                   f"<b>├Пользователь: {user_mention_admin}</b>\n" # Используем HTML
                                   f"<b>└Сумма: {withdraw_amount:.2f} {BOT_DATA['currency']['name']}, средства возвращены.</b>", # Используем HTML
                              parse_mode='HTML') # Изменено на HTML

        try:
            bot.send_message(target_user_id, 
                             f"<pre>⛔️ Ваша заявка на вывод средств отклонена.</pre>\n" # Используем HTML
                             f"<b>├Сумма {withdraw_amount:.2f} {BOT_DATA['currency']['name']}, средства возвращены.</b>\n" # Используем HTML
                             f"<b>└</b><i>Причина: Свяжитесь с администратором для уточнения.</i>",
                             parse_mode='HTML', reply_markup=main_menu_markup(target_user_id)) # Изменено на HTML
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю {target_user_id} об отклонении вывода: {e}")

    save_data(BOT_DATA) 

    # Удаляем заявку после обработки
    if message_id_from_admin in BOT_DATA['pending_withdrawals']:
        del BOT_DATA['pending_withdrawals'][message_id_from_admin]
        save_data(BOT_DATA)

if __name__ == "__main__":
    load_data()
    bot.polling(none_stop=True)



