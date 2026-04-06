import os
import random
import logging
import re
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

# --- Конфигурация ---
MAX_DICE_SIDES = 100 # Глобальное ограничение

# --- Логирование ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Вспомогательные функции ---
def roll_dice(sides: int, modifier: int = 0) -> int:
    """Бросает кубик с заданным количеством граней и добавляет модификатор."""
    return random.randint(1, sides) + modifier

def parse_modifier(text: str, command_len: int) -> int:
    """Извлекает модификатор из текста сообщения."""
    mod_str = text[command_len:].strip()
    if not mod_str:
        return 0
    try:
        if mod_str[0] in ('+', '-'):
            return int(mod_str)
        else:
            return int(mod_str)
    except ValueError:
        raise ValueError("❌ Неверный формат модификатора. Используйте +N или -N (например, /d20+5)")

def parse_dice_command(text: str):
    """Парсит команду вида /d20+5, /к-2 или /d100. Возвращает (количество_граней, модификатор)."""
    # Убираем слеш в начале и приводим к нижнему регистру
    text = text.lower().strip()
    if not text.startswith('/'):
        return None, None

    # Убираем слеш
    text = text[1:]

    # Проверяем русскую команду "к"
    if text.startswith('к'):
        dice_part = 'к'
        rest = text[1:]
    else:
        # Ищем цифры в начале для английских команд
        match = re.match(r'd(\d+)(.*)', text)
        if not match:
            return None, None
        dice_part = match.group(1)
        rest = match.group(2)

    # Извлекаем модификатор
    modifier = 0
    if rest:
        try:
            modifier = int(rest)
        except ValueError:
            raise ValueError("❌ Неверный формат команды. Пример: /d20+5 или /к-2")

    # Определяем количество граней
    if dice_part == 'к':
        sides = 20  # По умолчанию для /к
    else:
        try:
            sides = int(dice_part)
        except ValueError:
            return None, None

    return sides, modifier

def send_message(vk, peer_id, text):
    """Отправляет сообщение."""
    vk.messages.send(peer_id=peer_id, message=text, random_id=get_random_id())

def send_dice_result(vk, peer_id, sides: int, modifier: int):
    """Формирует и отправляет результат броска."""
    if sides > MAX_DICE_SIDES:
        send_message(vk, peer_id, f"❌ Ошибка: Максимальное количество граней — {MAX_DICE_SIDES}. Вы запросили d{sides}.")
        return

    if sides < 1:
        send_message(vk, peer_id, f"❌ Ошибок: Количество граней должно быть больше 0. Вы запросили d{sides}.")
        return

    result = roll_dice(sides, modifier)
    mod_text = f"{modifier:+d}" if modifier != 0 else ""
    answer = f"🎲 d{sides}{mod_text} = {result}"
    send_message(vk, peer_id, answer)

# --- Главная функция бота ---
def main():
    # 1. Получаем токен и ID сообщества из переменных окружения
    token = os.environ.get("VK_TOKEN")
    group_id = os.environ.get("VK_GROUP_ID")
    if not token or not group_id:
        raise ValueError("❌ Ошибка: Не заданы переменные окружения VK_TOKEN или VK_GROUP_ID")

    # 2. Авторизация VK API
    vk_session = VkApi(token=token)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, group_id)
    logging.info("✅ Бот успешно запущен и слушает сообщения ВКонтакте!")

    # 3. Главный цикл обработки событий
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            # Определяем, откуда пришло сообщение
            if event.from_chat:
                peer_id = 2000000000 + event.chat_id
            elif event.from_user:
                peer_id = event.message.peer_id
            else:
                continue

            message_text = event.message.text.strip()
            if not message_text:
                continue

            # --- Обработка команд с кубами ---
            if message_text.startswith('/d') or message_text.startswith('/к'):
                try:
                    sides, modifier = parse_dice_command(message_text)
                    if sides is None:
                        send_message(vk, peer_id, "❌ Неизвестная команда. Используйте /help.")
                        continue
                    send_dice_result(vk, peer_id, sides, modifier)
                except ValueError as e:
                    send_message(vk, peer_id, str(e))
                continue

            # --- Специальные команды ---
            lower_msg = message_text.lower()
            if lower_msg == '/attack':
                roll = random.randint(1, 20)
                if roll == 1:
                    result = "💥 КРИТИЧЕСКИЙ ПРОМАХ! (1)"
                elif roll == 20:
                    result = "✨ КРИТИЧЕСКОЕ ПОПАДАНИЕ! (20)"
                elif 2 <= roll <= 9:
                    result = "❌ ПРОМАХ"
                else:
                    result = "✅ ПОПАДАНИЕ"
                answer = f"🎯 **Атака** (d20 = {roll}): {result}"
                send_message(vk, peer_id, answer)
                continue

            if lower_msg == '/defense':
                roll = random.randint(1, 20)
                if roll == 1:
                    result = "💀 КРИТИЧЕСКИЙ ПРОВАЛ! (1)"
                elif roll == 20:
                    result = "🛡️ КРИТИЧЕСКИЙ УСПЕХ! (20)"
                elif 2 <= roll <= 9:
                    result = "❌ ПРОВАЛ"
                else:
                    result = "✅ УСПЕХ"
                answer = f"🛡️ **Защита** (d20 = {roll}): {result}"
                send_message(vk, peer_id, answer)
                continue

            if lower_msg == '/double':
                roll = random.randint(1, 6)
                if roll <= 3:
                    result = "Пусто"
                else:
                    result = "×2"
                answer = f"🎲 **Куб удвоения** (d6 = {roll}): {result}"
                send_message(vk, peer_id, answer)
                continue

            if lower_msg == '/help':
                help_text = (
                    "🤖 **Доступные команды:**\n\n"
                    "**Броски кубов (с модификаторами):**\n"
                    "/d4+2, /d4-1, /d4 – куб d4\n"
                    "/d6+5, /d6 – куб d6\n"
                    "/d8, /d10, /d12, /d20, /d100 – аналогично\n"
                    "/к+3, /к – русская команда (по умолчанию d20)\n\n"
                    "**Специальные команды:**\n"
                    "/attack – куб атаки (промах/попадание/крит)\n"
                    "/defense – куб защиты (провал/успех/крит)\n"
                    "/double – куб удвоения (пусто/×2)\n\n"
                    f"⚠️ **Важно:** Максимальное количество граней — {MAX_DICE_SIDES}.\n\n"
                    "/help – это сообщение"
                )
                send_message(vk, peer_id, help_text)
                continue

if __name__ == "__main__":
    main()
