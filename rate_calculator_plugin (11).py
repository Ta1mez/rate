from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cardinal import Cardinal

import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import json
import os

# Метаданные плагина
NAME = "Rate Calculator Plugin"
VERSION = "3.0.8"
DESCRIPTION = "Плагин для обновления курсов валют и расчёта чистой выгоды."
CREDITS = "@ta1mez"
UUID = "c76d42ea-5128-4f67-8a13-7d8c9a0bfa33"
SETTINGS_PAGE = False

# Имя файла для хранения курсов
RATES_FILE = "exchange_rates.json"

def save_exchange_rates():
    """Сохраняет текущие курсы валют в файл."""
    try:
        with open(RATES_FILE, "w", encoding="utf-8") as f:
            json.dump(exchange_rates, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка при сохранении курсов: {e}")

def load_exchange_rates():
    """Загружает курсы валют из файла."""
    if os.path.exists(RATES_FILE):
        try:
            with open(RATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка при загрузке курсов: {e}")
    return {
        "RUB": 5.5289,
        "UAH": 0.4380,
        "BRL": 3.5000,  # Добавлены бразильские реалы с 4 цифрами после точки
        "USD": 18.65
    }  # Возвращаем исходные значения, если файл не найден или поврежден

exchange_rates = load_exchange_rates()

# Словарь для хранения последних запросов
last_requests = {}
alternate_commission_states = {}

# Генерация стартового сообщения
def generate_main_message():
    return (
        f"<b>💳 Актуальные курсы валют:</b>\n"
        f"• 🇷🇺 <b>MDL - RUB:</b> <code>{exchange_rates['RUB']:.4f}</code> RUB\n"
        f"• 🇺🇦 <b>UAH - MDL:</b> <code>{exchange_rates['UAH']:.4f}</code> MDL\n"
        f"• 🇧🇷 <b>BRL - MDL:</b> <code>{exchange_rates['BRL']:.4f}</code> MDL\n"  # Добавлены реалы
        f"• 🇺🇸 <b>USD - MDL:</b> <code>{exchange_rates['USD']:.2f}</code> MDL\n\n"
        f"⚙️ Выберите функцию:"
    )

def main(cardinal: Cardinal, *args):
    if not cardinal.telegram:
        return
    tg = cardinal.telegram
    bot = tg.bot

    def start_rate(message: Message, edit_message_id: int = None):
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("💳 Обновить курсы", callback_data="update_rates"),
            InlineKeyboardButton("💰 Рассчитать выгоду", callback_data="calculate_profit")
        )
        if edit_message_id:
            bot.edit_message_text(generate_main_message(), message.chat.id, edit_message_id, reply_markup=markup, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, generate_main_message(), reply_markup=markup, parse_mode="HTML")

    def handle_callback(call):
        user_id = call.from_user.id
        last_requests.pop(user_id, None)  # Сброс предыдущих запросов
        if call.data == "update_rates":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("🇷🇺 MDL - RUB", callback_data="update_rub"),
                InlineKeyboardButton("🇺🇦 UAH - MDL", callback_data="update_uah"),
                InlineKeyboardButton("🇧🇷 BRL - MDL", callback_data="update_brl"),  # Добавлены реалы
                InlineKeyboardButton("🇺🇲 USD - MDL", callback_data="update_usd"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            )
            bot.edit_message_text(
                "⚙️ Выберите обновляемый курс:",
                call.message.chat.id,
                call.message.id,
                reply_markup=markup
            )
        elif call.data.startswith("update_"):
            currency = call.data.split("_")[1]
            if currency == "rub":
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_update_rates"))
                bot.edit_message_text(
                    "🟢 По какому курсу куплены USDT?",
                    call.message.chat.id,
                    call.message.id,
                    reply_markup=markup
                )
                last_requests[user_id] = "update_rub"
                bot.register_next_step_handler(call.message, lambda msg: update_rub_rate(msg, call.message.id))
            elif currency == "uah":
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_update_rates"))
                bot.edit_message_text(
                    "🇲🇩 Какая сумма последней транзакции в леях?",
                    call.message.chat.id,
                    call.message.id,
                    reply_markup=markup
                )
                last_requests[user_id] = "update_uah"
                bot.register_next_step_handler(call.message, lambda msg: update_uah_rate(msg, call.message.id))
            elif currency == "brl":  # Добавлено обновление курса BRL
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_update_rates"))
                bot.edit_message_text(
                    "🇲🇩 Какая сумма последней транзакции в леях?",
                    call.message.chat.id,
                    call.message.id,
                    reply_markup=markup
                )
                last_requests[user_id] = "update_brl"
                bot.register_next_step_handler(call.message, lambda msg: update_brl_rate(msg, call.message.id))
            elif currency == "usd":
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_update_rates"))
                bot.edit_message_text(
                    "🇺🇲 Какой курс <b>USD - MDL</b>?",
                    call.message.chat.id,
                    call.message.id,
                    parse_mode="HTML",
                    reply_markup=markup
                )
                last_requests[user_id] = "update_usd"
                bot.register_next_step_handler(call.message, lambda msg: update_usd_rate(msg, call.message.id))

        elif call.data == "calculate_profit":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("🟡 Brawl Stars", callback_data="brawl_stars"),
                InlineKeyboardButton("🔴 Clash Royale", callback_data="clash_royale"),
                InlineKeyboardButton("🔵 Telegram", callback_data="telegram"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            )
        
            # Проверяем, откуда нажата кнопка
            if call.message.text and "💰 Чистая выгода" in call.message.text:
                # Если кнопка нажата после расчёта (чистая выгода уже была показана)
                bot.send_message(call.message.chat.id, "🎮 Выберите категорию:", reply_markup=markup)
            else:
                # Если кнопка нажата из главного меню, редактируем сообщение
                bot.edit_message_text("🎮 Выберите категорию:", call.message.chat.id, call.message.id, reply_markup=markup)
        
            bot.answer_callback_query(call.id)

        elif call.data == "brawl_stars":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
            bot.edit_message_text(
                "💸 Введите цену лота (для покупателя) в рублях:",
                call.message.chat.id,
                call.message.id,
                reply_markup=markup
            )
            last_requests[user_id] = "brawl_stars"
            bot.register_next_step_handler(call.message, lambda msg: get_brawl_stars_lot_price(msg, call.message.id))

        elif call.data == "clash_royale":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
            bot.edit_message_text(
                "💸 Введите цену лота (для покупателя) в рублях:",
                call.message.chat.id,
                call.message.id,
                reply_markup=markup
            )
            last_requests[user_id] = "clash_royale"
            bot.register_next_step_handler(call.message, lambda msg: get_clash_royale_lot_price(msg, call.message.id))

        elif call.data == "telegram":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
            bot.edit_message_text(
                "💸 Введите цену товара в рублях:",
                call.message.chat.id,
                call.message.id,
                reply_markup=markup
            )
            last_requests[user_id] = "telegram"
            bot.register_next_step_handler(call.message, lambda msg: get_telegram_lot_price(msg, call.message.id))

        elif call.data == "back_to_main":
            start_rate(call.message, call.message.id)
        elif call.data == "back_to_update_rates":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("🇷🇺 MDL - RUB", callback_data="update_rub"),
                InlineKeyboardButton("🇺🇦 UAH - MDL", callback_data="update_uah"),
                InlineKeyboardButton("🇧🇷 BRL - MDL", callback_data="update_brl"),  # Добавлены реалы
                InlineKeyboardButton("🇺🇲 USD - MDL", callback_data="update_usd"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            )
            bot.edit_message_text(
                "⚙️ Выберите обновляемый курс:",
                call.message.chat.id,
                call.message.id,
                reply_markup=markup
            )
        elif call.data == "back_to_game_selection":
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(
                InlineKeyboardButton("🟡 Brawl Stars", callback_data="brawl_stars"),
                InlineKeyboardButton("🔴 Clash Royale", callback_data="clash_royale"),
                InlineKeyboardButton("🔵 Telegram", callback_data="telegram"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
            )
            bot.edit_message_text(
                "🎮 Выберите категорию:",
                call.message.chat.id,
                call.message.id,
                reply_markup=markup
            )

    def update_rub_rate(message: Message, edit_message_id: int):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "update_rub":
            try:
                buy_rate = float(message.text)
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_update_rates"))
                bot.send_message(message.chat.id, "🔴 По какому курсу проданы USDT?", reply_markup=markup)
                last_requests[user_id] = "finalize_rub"
                bot.register_next_step_handler(message, lambda msg: finalize_update_rub_rate(msg, buy_rate))
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректный курс покупки USDT.")
                bot.register_next_step_handler(message, lambda msg: update_rub_rate(msg, edit_message_id))

    def finalize_update_rub_rate(message: Message, buy_rate: float):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "finalize_rub":
            try:
                sell_rate = float(message.text)
                exchange_rates["RUB"] = buy_rate / sell_rate
                save_exchange_rates()  # Сохраняем обновленные курсы
                bot.send_message(message.chat.id, "✅ Курс <b>🇷🇺 MDL - RUB</b> успешно обновлён!", parse_mode="HTML")
                start_rate(message)
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректный курс продажи USDT.")
                bot.register_next_step_handler(message, lambda msg: finalize_update_rub_rate(msg, buy_rate))

    def update_uah_rate(message: Message, edit_message_id: int):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "update_uah":
            try:
                mdl_amount = float(message.text)
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_update_rates"))
                bot.send_message(message.chat.id, "🇺🇦 Какая сумма этой транзакции в гривнах?", reply_markup=markup)
                last_requests[user_id] = "finalize_uah"
                bot.register_next_step_handler(message, lambda msg: finalize_update_uah_rate(msg, mdl_amount))
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную сумму в леях.")
                bot.register_next_step_handler(message, lambda msg: update_uah_rate(msg, edit_message_id))

    def finalize_update_uah_rate(message: Message, mdl_amount: float):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "finalize_uah":
            try:
                uah_amount = float(message.text)
                exchange_rates["UAH"] = mdl_amount / uah_amount
                save_exchange_rates()  # Сохраняем обновленные курсы
                bot.send_message(message.chat.id, "✅ Курс <b>🇺🇦 UAH - MDL</b> успешно обновлён!", parse_mode="HTML")
                start_rate(message)
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную сумму в гривнах.")
                bot.register_next_step_handler(message, lambda msg: finalize_update_uah_rate(msg, mdl_amount))

    def update_brl_rate(message: Message, edit_message_id: int):  # Добавлена функция для BRL
        user_id = message.from_user.id
        if last_requests.get(user_id) == "update_brl":
            try:
                mdl_amount = float(message.text)
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_update_rates"))
                bot.send_message(message.chat.id, "🇧🇷 Какая сумма этой транзакции в реалах?", reply_markup=markup)
                last_requests[user_id] = "finalize_brl"
                bot.register_next_step_handler(message, lambda msg: finalize_update_brl_rate(msg, mdl_amount))
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную сумму в леях.")
                bot.register_next_step_handler(message, lambda msg: update_brl_rate(msg, edit_message_id))

    def finalize_update_brl_rate(message: Message, mdl_amount: float):  # Добавлена функция для BRL
        user_id = message.from_user.id
        if last_requests.get(user_id) == "finalize_brl":
            try:
                brl_amount = float(message.text)
                exchange_rates["BRL"] = mdl_amount / brl_amount
                save_exchange_rates()  # Сохраняем обновленные курсы
                bot.send_message(message.chat.id, "✅ Курс <b>🇧🇷 BRL - MDL</b> успешно обновлён!", parse_mode="HTML")
                start_rate(message)
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную сумму в реалах.")
                bot.register_next_step_handler(message, lambda msg: finalize_update_brl_rate(msg, mdl_amount))

    def update_usd_rate(message: Message, edit_message_id: int):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "update_usd":
            try:
                exchange_rates["USD"] = float(message.text)
                save_exchange_rates()  # Сохраняем обновленные курсы
                bot.send_message(message.chat.id, "✅ Курс <b>🇺🇲 USD - MDL</b> успешно обновлён!", parse_mode="HTML")
                start_rate(message)
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректный курс USD - MDL.")
                bot.register_next_step_handler(message, lambda msg: update_usd_rate(msg, edit_message_id))

    def get_brawl_stars_lot_price(message: Message, edit_message_id: int):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "brawl_stars":
            try:
                lot_price_buyer = float(message.text)
                lot_price = lot_price_buyer * (1 - 0.16068374059755964)  # Вычитаем 16.068374059755964%
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton("🇺🇦 Гривны", callback_data=f"brawl_profit_uah_{lot_price}_{lot_price_buyer}"),
                    InlineKeyboardButton("🇧🇷 Реалы", callback_data=f"brawl_profit_brl_{lot_price}_{lot_price_buyer}"),  # Добавлены реалы
                    InlineKeyboardButton("🇺🇲 Доллары", callback_data=f"brawl_profit_usd_{lot_price}_{lot_price_buyer}"),
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection")
                )
                bot.send_message(message.chat.id, "⚙️ Выберите валюту акции:", reply_markup=markup)
                last_requests[user_id] = f"brawl_select_currency_{lot_price}_{lot_price_buyer}"
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную цену лота.")
                bot.register_next_step_handler(message, lambda msg: get_brawl_stars_lot_price(msg, edit_message_id))

    def get_clash_royale_lot_price(message: Message, edit_message_id: int):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "clash_royale":
            try:
                lot_price_buyer = float(message.text)
                lot_price = lot_price_buyer * (1 - 0.123214261446109)  # Вычитаем 12.3214261446109%
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton("🇺🇦 Гривны", callback_data=f"clash_profit_uah_{lot_price}_{lot_price_buyer}"),
                    InlineKeyboardButton("🇧🇷 Реалы", callback_data=f"clash_profit_brl_{lot_price}_{lot_price_buyer}"),  # Добавлены реалы
                    InlineKeyboardButton("🇺🇲 Доллары", callback_data=f"clash_profit_usd_{lot_price}_{lot_price_buyer}"),
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection")
                )
                bot.send_message(message.chat.id, "⚙️ Выберите валюту акции:", reply_markup=markup)
                last_requests[user_id] = f"clash_select_currency_{lot_price}_{lot_price_buyer}"
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную цену лота.")
                bot.register_next_step_handler(message, lambda msg: get_clash_royale_lot_price(msg, edit_message_id))

    def get_telegram_lot_price(message: Message, edit_message_id: int):
        user_id = message.from_user.id
        if last_requests.get(user_id) == "telegram":
            try:
                lot_price_buyer = float(message.text)
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton("🇺🇦 Гривны", callback_data=f"telegram_profit_uah_{lot_price_buyer}"),
                    InlineKeyboardButton("🇧🇷 Реалы", callback_data=f"telegram_profit_brl_{lot_price_buyer}"),  # Добавлены реалы
                    InlineKeyboardButton("🇺🇲 Доллары", callback_data=f"telegram_profit_usd_{lot_price_buyer}"),
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection")
                )
                bot.send_message(message.chat.id, "⚙️ Выберите валюту акции:", reply_markup=markup)
                last_requests[user_id] = f"telegram_select_currency_{lot_price_buyer}"
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную цену товара.")
                bot.register_next_step_handler(message, lambda msg: get_telegram_lot_price(msg, edit_message_id))

    def handle_brawl_stars_currency(call):
        user_id = call.from_user.id
        data = call.data.split("_")
        currency = data[2]
        lot_price = float(data[3])
        lot_price_buyer = float(data[4])
    
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
        
        # Сообщение о вводе цены акции
        bot.edit_message_text(
            f"⚙️ Введите цену акции в {currency.upper()}:",
            call.message.chat.id,
            call.message.id,
            reply_markup=markup
        )
        
        # Сохраняем состояние для пользователя
        last_requests[user_id] = f"brawl_profit_{currency}_{lot_price}_{lot_price_buyer}"
        
        # Регистрируем обработчик для следующего шага
        bot.register_next_step_handler(call.message, lambda msg: calculate_brawl_profit(msg, currency, lot_price, lot_price_buyer))
        
    def toggle_quests(call):
        data = call.data.split("_")
        currency, lot_price, lot_price_buyer, action_price = data[2], float(data[3]), float(data[4]), float(data[5])
        message_id = call.message.id
        user_id = call.from_user.id
    
        # Получаем текущее состояние (инициализируем, если его еще нет)
        current_state = alternate_commission_states.get(
            message_id,
            {"state": False, "profit_rub_off": None, "profit_mdl_off": None}
        )
        new_state = not current_state["state"]  # Переключаем состояние (включено/выключено)
    
        # Пересчитываем себестоимость и чистую выгоду
        mdl_price = action_price * exchange_rates[currency.upper()]
        rub_price = mdl_price * exchange_rates["RUB"]
        commission_rate = 0.08224296149183244 if new_state else 0.16068374059755964
        lot_price_with_commission = lot_price_buyer * (1 - commission_rate)
        net_profit = lot_price_with_commission * 0.97 - rub_price
        net_profit_mdl = net_profit / exchange_rates["RUB"]
        currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Обновлен выбор флага с учетом BRL
    
        # Сохраняем выгоду "выключенного" состояния при первом вызове
        if current_state["profit_rub_off"] is None:
            current_state["profit_rub_off"] = lot_price_buyer * (1 - 0.16068374059755964) * 0.97 - rub_price
            current_state["profit_mdl_off"] = current_state["profit_rub_off"] / exchange_rates["RUB"]
    
        # Вычисляем прирост (разница между состояниями)
        profit_diff_rub = net_profit - current_state["profit_rub_off"]
        profit_diff_mdl = net_profit_mdl - current_state["profit_mdl_off"]
    
        # Обновляем состояние
        current_state["state"] = new_state
        alternate_commission_states[message_id] = current_state
    
        # Формируем сообщение
        profit_message = (
            f"🇷🇺 Цена лота: <code>{lot_price_buyer:.2f}</code> RUB\n"
            f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
            f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
        )
    
        if net_profit < 0:
            profit_message += (
                f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
            )
        else:
            profit_message += f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB"
            if new_state:  # Показываем прирост только при включенной функции
                profit_message += f" (<b>+{profit_diff_rub:.2f}</b>)"
            profit_message += f"\n └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
            if new_state:
                profit_message += f" (<b>+{profit_diff_mdl:.2f}</b>)"
    
        # Обновляем кнопки
        alternate_commission_text = "🟢 Квесты" if new_state else "🔴 Квесты"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(alternate_commission_text, callback_data=f"toggle_quests_{currency}_{lot_price}_{lot_price_buyer}_{action_price}"),
            InlineKeyboardButton("⚙️ Рассчитать с другой ценой лота", callback_data=f"recalculate_brawl_{currency}_{action_price}_{lot_price_buyer}"),
            InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
        )
    
        # Обновляем сообщение
        bot.edit_message_text(
            profit_message,
            chat_id=call.message.chat.id,
            message_id=message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )
        
    def handle_clash_royale_currency(call):
        user_id = call.from_user.id
        data = call.data.split("_")
        currency = data[2]
        lot_price = float(data[3])
        lot_price_buyer = float(data[4])
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
        bot.edit_message_text(
            f"⚙️ Введите цену акции в {currency.upper()}:",
            call.message.chat.id,
            call.message.id,
            reply_markup=markup
        )
        last_requests[user_id] = f"clash_profit_{currency}_{lot_price}_{lot_price_buyer}"
        bot.register_next_step_handler(call.message, lambda msg: calculate_clash_profit(msg, currency, lot_price, lot_price_buyer))
        
    def toggle_items(call):
        data = call.data.split("_")
        currency, lot_price, lot_price_buyer, action_price = data[2], float(data[3]), float(data[4]), float(data[5])
        message_id = call.message.id
        user_id = call.from_user.id
    
        # Получаем текущее состояние (инициализируем, если его еще нет)
        current_state = alternate_commission_states.get(
            message_id,
            {"state": False, "profit_rub_off": None, "profit_mdl_off": None}
        )
        new_state = not current_state["state"]  # Переключаем состояние (включено/выключено)
    
        # Пересчитываем себестоимость и чистую выгоду
        mdl_price = action_price * exchange_rates[currency.upper()]
        rub_price = mdl_price * exchange_rates["RUB"]
        commission_rate = 0.05576919826590123 if new_state else 0.123214261446109
        lot_price_with_commission = lot_price_buyer * (1 - commission_rate)
        net_profit = lot_price_with_commission * 0.97 - rub_price
        net_profit_mdl = net_profit / exchange_rates["RUB"]
        currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Обновлен выбор флага с учетом BRL
    
        # Сохраняем выгоду "выключенного" состояния при первом вызове
        if current_state["profit_rub_off"] is None:
            current_state["profit_rub_off"] = lot_price_buyer * (1 - 0.123214261446109) * 0.97 - rub_price
            current_state["profit_mdl_off"] = current_state["profit_rub_off"] / exchange_rates["RUB"]
    
        # Вычисляем прирост (разница между состояниями)
        profit_diff_rub = net_profit - current_state["profit_rub_off"]
        profit_diff_mdl = net_profit_mdl - current_state["profit_mdl_off"]
    
        # Обновляем состояние
        current_state["state"] = new_state
        alternate_commission_states[message_id] = current_state
    
        # Формируем сообщение
        profit_message = (
            f"🇷🇺 Цена лота: <code>{lot_price_buyer:.2f}</code> RUB\n"
            f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
            f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
        )
    
        if net_profit < 0:
            profit_message += (
                f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
            )
        else:
            profit_message += f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB"
            if new_state:  # Показываем прирост только при включенной функции
                profit_message += f" (<b>+{profit_diff_rub:.2f}</b>)"
            profit_message += f"\n └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
            if new_state:
                profit_message += f" (<b>+{profit_diff_mdl:.2f}</b>)"
    
        # Обновляем кнопки
        alternate_items_text = "🟢 Предметы" if new_state else "🔴 Предметы"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(alternate_items_text, callback_data=f"toggle_items_{currency}_{lot_price}_{lot_price_buyer}_{action_price}"),
            InlineKeyboardButton("⚙️ Рассчитать с другой ценой лота", callback_data=f"recalculate_clash_{currency}_{action_price}_{lot_price_buyer}"),
            InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
            InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
        )
    
        # Обновляем сообщение
        bot.edit_message_text(
            profit_message,
            chat_id=call.message.chat.id,
            message_id=message_id,
            reply_markup=markup,
            parse_mode="HTML"
        )

    def handle_telegram_currency(call):
        user_id = call.from_user.id
        data = call.data.split("_")
        currency = data[2]
        lot_price_buyer = float(data[3])
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
        bot.edit_message_text(
            f"⚙️ Введите цену акции в {currency.upper()}:",
            call.message.chat.id,
            call.message.id,
            reply_markup=markup
        )
        last_requests[user_id] = f"telegram_profit_{currency}_{lot_price_buyer}"
        bot.register_next_step_handler(call.message, lambda msg: calculate_telegram_profit(msg, currency, lot_price_buyer))

    def calculate_brawl_profit(message: Message, currency: str, lot_price: float, lot_price_buyer: float, use_alternate_commission: bool = False):
        user_id = message.from_user.id
        if last_requests.get(user_id) == f"brawl_profit_{currency}_{lot_price}_{lot_price_buyer}":
            try:
                # Проверяем ввод и обрабатываем выражения
                user_input = message.text.replace(",", ".").replace(" ", "")
                if not all(char.isdigit() or char in "+-*/." for char in user_input):
                    raise ValueError("Некорректное выражение")
        
                action_price = eval(user_input)  # Вычисляем значение выражения
                mdl_price = action_price * exchange_rates[currency.upper()]
                rub_price = mdl_price * exchange_rates["RUB"]
        
                # Выбор комиссии
                commission_rate = 0.08224296149183244 if use_alternate_commission else 0.16068374059755964
                lot_price_with_commission = lot_price_buyer * (1 - commission_rate)
                net_profit = lot_price_with_commission * 0.97 - rub_price
                net_profit_mdl = net_profit / exchange_rates["RUB"]
                currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Обновлен выбор флага с учетом BRL
        
                profit_message = (
                    f"🇷🇺 Цена лота: <code>{lot_price_buyer:.2f}</code> RUB\n"
                    f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
                    f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
                )
        
                if net_profit < 0:
                    profit_message += (
                        f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
                else:
                    profit_message += (
                        f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
        
                # Кнопки
                alternate_commission_text = "🟢 Квесты" if use_alternate_commission else "🔴 Квесты"
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton(alternate_commission_text, callback_data=f"toggle_quests_{currency}_{lot_price}_{lot_price_buyer}_{action_price}"),
                    InlineKeyboardButton("⚙️ Рассчитать с другой ценой лота", callback_data=f"recalculate_brawl_{currency}_{action_price}_{lot_price_buyer}"),
                    InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                )
        
                bot.send_message(message.chat.id, profit_message, reply_markup=markup, parse_mode="HTML")
        
            except (ValueError, SyntaxError):
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректное выражение цены акции.")
                bot.register_next_step_handler(message, lambda msg: calculate_brawl_profit(msg, currency, lot_price, lot_price_buyer, use_alternate_commission))

    def calculate_clash_profit(message: Message, currency: str, lot_price: float, lot_price_buyer: float, use_items: bool = False):
        user_id = message.from_user.id
        if last_requests.get(user_id) == f"clash_profit_{currency}_{lot_price}_{lot_price_buyer}":
            try:
                # Проверяем ввод и обрабатываем выражения
                user_input = message.text.replace(",", ".").replace(" ", "")
                if not all(char.isdigit() or char in "+-*/." for char in user_input):
                    raise ValueError("Некорректное выражение")
    
                action_price = eval(user_input)  # Вычисляем значение выражения
                mdl_price = action_price * exchange_rates[currency.upper()]
                rub_price = mdl_price * exchange_rates["RUB"]
    
                # Выбор комиссии
                commission_rate = 0.05576919826590123 if use_items else 0.123214261446109
                lot_price_with_commission = lot_price_buyer * (1 - commission_rate)
                net_profit = lot_price_with_commission * 0.97 - rub_price
                net_profit_mdl = net_profit / exchange_rates["RUB"]
                currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Обновлен выбор флага с учетом BRL
    
                profit_message = (
                    f"🇷🇺 Цена лота: <code>{lot_price_buyer:.2f}</code> RUB\n"
                    f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
                    f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
                )
    
                if net_profit < 0:
                    profit_message += (
                        f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
                else:
                    profit_message += (
                        f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
    
                # Кнопки
                alternate_items_text = "🔴 Предметы"
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton(alternate_items_text, callback_data=f"toggle_items_{currency}_{lot_price}_{lot_price_buyer}_{action_price}"),
                    InlineKeyboardButton("⚙️ Рассчитать с другой ценой лота", callback_data=f"recalculate_clash_{currency}_{action_price}_{lot_price_buyer}"),
                    InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                )
    
                bot.send_message(message.chat.id, profit_message, reply_markup=markup, parse_mode="HTML")
    
            except (ValueError, SyntaxError):
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректное выражение цены акции.")
                bot.register_next_step_handler(message, lambda msg: calculate_clash_profit(msg, currency, lot_price, lot_price_buyer, use_items))

    def calculate_telegram_profit(message: Message, currency: str, lot_price_buyer: float):
        user_id = message.from_user.id
        if last_requests.get(user_id) == f"telegram_profit_{currency}_{lot_price_buyer}":
            try:
                action_price = eval(message.text.replace(',', '+'))
                mdl_price = action_price * exchange_rates[currency.upper()]
                rub_price = mdl_price * exchange_rates["RUB"]
                net_profit = lot_price_buyer - rub_price
                currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Обновлен выбор флага с учетом BRL
                net_profit_mdl = net_profit / exchange_rates["RUB"]

                profit_message = (
                    f"🇷🇺 Цена товара: <code>{lot_price_buyer:.2f}</code> RUB\n"
                    f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
                    f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
                )

                if net_profit < 0:
                    profit_message += (
                        f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
                else:
                    profit_message += (
                        f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )

                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton("⚙️ Рассчитать с другой ценой товара", callback_data=f"recalculate_telegram_{currency}_{action_price}_{lot_price_buyer}"),
                    InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                )
                bot.send_message(message.chat.id, profit_message, reply_markup=markup, parse_mode="HTML")
            except (ValueError, SyntaxError):
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректное выражение цены акции.")
                bot.register_next_step_handler(message, lambda msg: calculate_telegram_profit(msg, currency, lot_price_buyer))

    def recalculate_with_different_brawl_lot(call):
        user_id = call.from_user.id
        data = call.data.split("_")
        currency = data[2]
        action_price = float(data[3])
        lot_price_buyer = float(data[4])
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
        
        bot.edit_message_text(
            "💸 Введите *другую* цену лота в рублях:",
            call.message.chat.id,
            call.message.id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        last_requests[user_id] = f"recalculate_brawl_{currency}_{action_price}_{lot_price_buyer}"
        bot.register_next_step_handler(
            call.message, 
            lambda msg: calculate_with_different_brawl_lot(msg, currency, action_price, lot_price_buyer)
        )

    def recalculate_with_different_clash_lot(call):
        user_id = call.from_user.id
        data = call.data.split("_")
        currency = data[2]
        action_price = float(data[3])
        lot_price_buyer = float(data[4])
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
        bot.edit_message_text(
            "💸 Введите *другую* цену лота в рублях:",
            call.message.chat.id,
            call.message.id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        last_requests[user_id] = f"recalculate_clash_{currency}_{action_price}_{lot_price_buyer}"
        bot.register_next_step_handler(call.message, lambda msg: calculate_with_different_clash_lot(msg, currency, action_price, lot_price_buyer))

    def recalculate_with_different_telegram_lot(call):
        user_id = call.from_user.id
        data = call.data.split("_")
        currency = data[2]
        action_price = float(data[3])
        lot_price_buyer = float(data[4])
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_game_selection"))
        bot.edit_message_text(
            "💸 Введите *другую* цену товара в рублях:",
            call.message.chat.id,
            call.message.id,
            parse_mode="Markdown",
            reply_markup=markup
        )
        last_requests[user_id] = f"recalculate_telegram_{currency}_{action_price}_{lot_price_buyer}"
        bot.register_next_step_handler(call.message, lambda msg: calculate_with_different_telegram_lot(msg, currency, action_price, lot_price_buyer))

    def calculate_with_different_brawl_lot(message: Message, currency: str, action_price: float, original_lot_price_buyer: float):
        user_id = message.from_user.id
        
        if last_requests.get(user_id) == f"recalculate_brawl_{currency}_{action_price}_{original_lot_price_buyer}":
            try:
                # Ввод новой цены лота
                new_lot_price_buyer = float(message.text)
                lot_price = new_lot_price_buyer * (1 - 0.16068374059755964)
                mdl_price = action_price * exchange_rates[currency.upper()]
                rub_price = mdl_price * exchange_rates["RUB"]
                
                # Рассчитываем чистую выгоду
                net_profit = lot_price * 0.97 - rub_price
                net_profit_mdl = net_profit / exchange_rates["RUB"]
                currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Исправлен выбор флага
                
                # Сохраняем для "Другая комиссия", инициализируя как выключенное состояние
                alternate_commission_states[message.id] = {
                    "state": False,  # По умолчанию выключено
                    "profit_rub_off": net_profit,
                    "profit_mdl_off": net_profit_mdl
                }
    
                # Формируем сообщение
                profit_message = (
                    f"🇷🇺 Цена лота: <code>{new_lot_price_buyer:.2f}</code> RUB\n"
                    f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
                    f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
                )
                if net_profit < 0:
                    profit_message += (
                        f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
                else:
                    profit_message += (
                        f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
    
                # Кнопки
                alternate_commission_text = "🔴 Квесты"  # По умолчанию выключено
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton(alternate_commission_text, callback_data=f"toggle_quests_{currency}_{lot_price}_{new_lot_price_buyer}_{action_price}"),
                    InlineKeyboardButton("⚙️ Рассчитать с другой ценой лота", callback_data=f"recalculate_brawl_{currency}_{action_price}_{new_lot_price_buyer}"),
                    InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                )
    
                # Отправляем сообщение
                bot.send_message(message.chat.id, profit_message, reply_markup=markup, parse_mode="HTML")
    
            except ValueError:
                # Обрабатываем ошибки ввода
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректную цену лота.")
                bot.register_next_step_handler(
                    message, 
                    lambda msg: calculate_with_different_brawl_lot(msg, currency, action_price, original_lot_price_buyer)
                )
                
    def calculate_with_different_clash_lot(message: Message, currency: str, action_price: float, original_lot_price_buyer: float):
        user_id = message.from_user.id
        if last_requests.get(user_id) == f"recalculate_clash_{currency}_{action_price}_{original_lot_price_buyer}":
            try:
                new_lot_price_buyer = float(message.text)
                lot_price = new_lot_price_buyer * (1 - 0.123214261446109)
                mdl_price = action_price * exchange_rates[currency.upper()]
                rub_price = mdl_price * exchange_rates["RUB"]
    
                net_profit = lot_price * 0.97 - rub_price
                net_profit_mdl = net_profit / exchange_rates["RUB"]
                currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Исправлен выбор флага
    
                # Сохраняем состояние "Предметы"
                alternate_commission_states[message.id] = {
                    "state": False,  # По умолчанию выключено
                    "profit_rub_off": net_profit,
                    "profit_mdl_off": net_profit_mdl
                }
    
                # Формируем сообщение
                profit_message = (
                    f"🇷🇺 Цена лота: <code>{new_lot_price_buyer:.2f}</code> RUB\n"
                    f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
                    f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
                )
    
                if net_profit < 0:
                    profit_message += (
                        f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
                else:
                    profit_message += (
                        f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
    
                # Кнопки
                alternate_items_text = "🔴 Предметы"  # По умолчанию выключено
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton(alternate_items_text, callback_data=f"toggle_items_{currency}_{lot_price}_{new_lot_price_buyer}_{action_price}"),
                    InlineKeyboardButton("⚙️ Рассчитать с другой ценой лота", callback_data=f"recalculate_clash_{currency}_{action_price}_{new_lot_price_buyer}"),
                    InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                )
    
                bot.send_message(message.chat.id, profit_message, reply_markup=markup, parse_mode="HTML")
            except ValueError:
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректное значение.")
                bot.register_next_step_handler(message, lambda msg: calculate_with_different_clash_lot(msg, currency, action_price, original_lot_price_buyer))
                
    def calculate_with_different_telegram_lot(message: Message, currency: str, action_price: float, original_lot_price_buyer: float):
        user_id = message.from_user.id
        if last_requests.get(user_id) == f"recalculate_telegram_{currency}_{action_price}_{original_lot_price_buyer}":
            try:
                new_lot_price_buyer = float(message.text)
                mdl_price = action_price * exchange_rates[currency.upper()]
                rub_price = mdl_price * exchange_rates["RUB"]
                net_profit = new_lot_price_buyer - rub_price
                net_profit_mdl = net_profit / exchange_rates["RUB"]
                currency_flag = "🇺🇦" if currency == "uah" else "🇧🇷" if currency == "brl" else "🇺🇲"  # Исправлен выбор флага

                profit_message = (
                    f"🇷🇺 Цена товара: <code>{new_lot_price_buyer:.2f}</code> RUB\n"
                    f"{currency_flag} Цена акции: <code>{action_price:.2f}</code> {currency.upper()}\n"
                    f"🇲🇩 Себестоимость: <code>{mdl_price:.2f}</code> MDL\n\n"
                )

                if net_profit < 0:
                    profit_message += (
                        f"<b>❗ Убыток:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )
                else:
                    profit_message += (
                        f"<b>💰 Чистая выгода:</b> <code>{net_profit:.2f}</code> RUB\n"
                        f" └ 🇲🇩: ~<code>{net_profit_mdl:.2f}</code> MDL"
                    )

                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(
                    InlineKeyboardButton("⚙️ Рассчитать с другой ценой товара", callback_data=f"recalculate_telegram_{currency}_{action_price}_{new_lot_price_buyer}"),
                    InlineKeyboardButton("🔁 Рассчитать ещё раз", callback_data="calculate_profit"),
                    InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")
                )
                bot.send_message(message.chat.id, profit_message, reply_markup=markup, parse_mode="HTML")
            except (ValueError, SyntaxError):
                bot.send_message(message.chat.id, "❌ Ошибка: введите корректное выражение цены товара.")
                bot.register_next_step_handler(message, lambda msg: calculate_with_different_telegram_lot(msg, currency, action_price, original_lot_price_buyer))
                
    # Регистрация команды /rate
    cardinal.add_telegram_commands(UUID, [
        ("rate", "Обновить курсы и рассчитать выгоду.", True)
    ])
    bot.register_message_handler(start_rate, commands=["rate"])
    bot.register_callback_query_handler(handle_callback, func=lambda call: call.data.startswith("update_") or call.data == "calculate_profit" or call.data == "back_to_main" or call.data == "back_to_update_rates" or call.data == "brawl_stars" or call.data == "clash_royale" or call.data == "telegram" or call.data == "back_to_game_selection")
    bot.register_callback_query_handler(handle_brawl_stars_currency, func=lambda call: call.data.startswith("brawl_profit_"))
    bot.register_callback_query_handler(toggle_quests, func=lambda call: call.data.startswith("toggle_quests_"))
    bot.register_callback_query_handler(handle_clash_royale_currency, func=lambda call: call.data.startswith("clash_profit_"))
    bot.register_callback_query_handler(toggle_items, func=lambda call: call.data.startswith("toggle_items_"))
    bot.register_callback_query_handler(handle_telegram_currency, func=lambda call: call.data.startswith("telegram_profit_"))
    bot.register_callback_query_handler(recalculate_with_different_brawl_lot, func=lambda call: call.data.startswith("recalculate_brawl_"))
    bot.register_callback_query_handler(recalculate_with_different_clash_lot, func=lambda call: call.data.startswith("recalculate_clash_"))
    bot.register_callback_query_handler(recalculate_with_different_telegram_lot, func=lambda call: call.data.startswith("recalculate_telegram_"))

BIND_TO_PRE_INIT = [main]
BIND_TO_DELETE = None