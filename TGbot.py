#импорт библиотек для работы
import logging
import requests
import telebot
from telebot import types

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота телеграмма
TOKEN = '8046616176:AAFpqPHYmQ20j0o2q2UqaIcjWrMg_rfYlVg'

# Константы для доступа к API Яндекса
OAUTH_TOKEN = 'y0_AgAAAABkPR7rAATuwQAAAAEVj9mAAAC-u4PaUR9NOZyxg5y3p_bSOsC6ag'
FOLDER_ID = 'b1gihcr2c5thnjujvrjm'
API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Переменные для хранения данных
messages_history = {}
user_data = {}
is_authorized = {}
user_state = {} # чтобы хранить состояние пользователя

# Создаем объект бота
bot = telebot.TeleBot(TOKEN)

# Состояния для ConversationHandler
AUTH, COURSE, CHAT_WITH_GPT = range(3)

# Функция для получения IAM-токена
def get_iam_token():
    response = requests.post(
        'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        json={'yandexPassportOauthToken': OAUTH_TOKEN}
    )
    response.raise_for_status()
    return response.json()['iamToken']

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет, я обучающий StroyDvor бот! Для того чтобы начать, вам нужно авторизоваться.\n'
                                      'Пожалуйста, введите ваше ФИО и ID пользователя.')
    bot.register_next_step_handler(message, get_user_info)

# Обработчик ввода ФИО и ID пользователя
def get_user_info(message):
    user_input = message.text.strip()

    # Сохраняем ФИО и ID
    user_data[message.from_user.id] = user_input
    is_authorized[message.from_user.id] = True  # Устанавливаем флаг авторизации
    user_state[message.from_user.id] = COURSE  # Устанавливаем начальное состояние
    logger.info(f'Получено ФИО и ID пользователя: {user_input}')

    # Отправляем меню с командами
    send_menu(message)

# Функция отправки меню
def send_menu(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("📚 Перейти к курсу", "⭐️ Общий рейтинг")
    keyboard.row("ℹ️ Справка")
    bot.send_message(message.chat.id, 'Вы вернулись в меню:', reply_markup=keyboard)

# Обработчик команд из меню
@bot.message_handler(func=lambda message: is_authorized.get(message.from_user.id, False)
                                          and user_state.get(message.from_user.id) == COURSE)
def handle_command(message):
    user_text = message.text
    logger.info(f'Получено сообщение от пользователя {user_data}: {user_text}')

    if user_text == "📚 Перейти к курсу":
        course_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        course_keyboard.row("Курс 1", "Курс 2")
        course_keyboard.row("Курс 3", "🔙 Назад")
        bot.send_message(message.chat.id, 'Выберите курс:', reply_markup=course_keyboard)
        user_state[message.from_user.id] = COURSE  # Обновляем состояние
    elif user_text in ["Курс 1", "Курс 2", "Курс 3"]:
        bot.send_message(message.chat.id, '🚧 Курс еще не готов. Пожалуйста, подождите немного! ⏳\nА пока пообщайтесь с Яндекс GPT.')

        # оставляем только кнопку "Назад"
        back_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_keyboard.add("🔙 Назад")
        bot.send_message(message.chat.id, 'Вы можете пообщаться с Яндекс GPT. Для этого напишите ваш вопрос.', reply_markup=back_keyboard)
        user_state[message.from_user.id] = CHAT_WITH_GPT  # Обновляем состояние
    elif user_text == "⭐️ Общий рейтинг":
        ranking_text = (
            "Общий рейтинг ⭐️:\n"
            "1. Григорий - 9800 очков\n"
            "2. Анна - 9500 очков\n"
            "3. Алексей - 9200 очков\n"
            "4. Мария - 8900 очков\n"
            "5. Дмитрий - 8700 очков\n"
        )
        bot.send_message(message.chat.id, ranking_text)
    elif user_text == "ℹ️ Справка":
        bot.send_message(message.chat.id, 'Справочная информация будет дополняться.')
    elif user_text == "🔙 Назад":
        send_menu(message)
        user_state[message.from_user.id] = COURSE  # Обновляем состояние
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, выберите команду из меню.')

# Обработчик сообщений для общения с Яндекс GPT
@bot.message_handler(func=lambda message: is_authorized.get(message.from_user.id, False)
                                          and user_state.get(message.from_user.id) == CHAT_WITH_GPT)
def process_message(message):
    user_text = message.text
    logger.info(f'Получено сообщение от пользователя: {user_text}')

    if user_text == "🔙 Назад":
        send_menu(message)
        user_state[message.from_user.id] = COURSE  # Обновляем состояние
        return

    # Добавляем сообщение в историю
    if message.from_user.id not in messages_history:
        messages_history[message.from_user.id] = []
    messages_history[message.from_user.id].append({"role": "user", "text": user_text})

    try:
        iam_token = get_iam_token()
        logger.info(f'Получен IAM-токен: {iam_token}')
    except requests.RequestException as e:
        logger.error(f'Ошибка при получении IAM-токена: {e}')
        bot.send_message(message.chat.id, 'Произошла ошибка при получении токена.')
        return

    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt",
        "completionOptions": {"temperature": 0.3, "maxTokens": 1000},
        "messages": [
            {"role": "system", "text": "отвечу на любые ваши вопросы!"}
        ] + messages_history[message.from_user.id]  # Добавляем историю сообщений пользователя
    }

    try:
        response = requests.post(
            API_URL,
            headers={"Accept": "application/json", "Authorization": f"Bearer {iam_token}"},
            json=data
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f'Полный ответ от Yandex GPT: {result}')

        answer = result.get('result', {}).get('alternatives', [{}])[0].get('message', {}).get('text', 'Ошибка получения ответа.')

        # Добавляем ответ бота в историю
        messages_history[message.from_user.id].append({"role": "assistant", "text": answer})
    except requests.RequestException as e:
        logger.error(f'Ошибка при запросе к Yandex GPT: {e}')
        answer = 'Произошла ошибка при запросе к Yandex GPT.'

    bot.send_message(message.chat.id, answer)

# Запускаем бота
bot.polling()

