import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    CallbackContext, ConversationHandler
)
from config import BOT_TOKEN, MAX_PLAYLISTS_TO_SHOW
from vk_parser import VKParser

# Состояния диалога
SETTING_TOKEN, SEARCHING = range(2)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VKPlaylistBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Хранилище парсеров для каждого пользователя
        self.user_parsers = {}
        
        # Настройка ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                SETTING_TOKEN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_token)
                ],
                SEARCHING: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search)
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler('help', self.help))
        self.application.add_handler(CommandHandler('token', self.token_command))
        self.application.add_handler(CommandHandler('status', self.status))
    
    def get_parser(self, user_id: int) -> VKParser:
        """Получает парсер для пользователя"""
        if user_id not in self.user_parsers:
            self.user_parsers[user_id] = VKParser()
        return self.user_parsers[user_id]
    
    async def start(self, update: Update, context: CallbackContext) -> int:
        """Начало диалога"""
        user_id = update.message.from_user.id
        parser = self.get_parser(user_id)
        
        if parser.token:
            await update.message.reply_text(
                "🔍 Бот готов к поиску! Отправьте название трека или ссылку ВК.\n\n"
                "Команды:\n"
                "/token - изменить токен\n"
                "/status - проверить статус\n"
                "/help - помощь",
                reply_markup=ReplyKeyboardRemove()
            )
            return SEARCHING
        else:
            await update.message.reply_text(
                "🔑 Для работы бота нужен токен ВКонтакте.\n\n"
                "📋 Как получить токен:\n"
                "1. Откройте ссылку в браузере:\n"
                "https://oauth.vk.com/authorize?client_id=6121396&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=audio&response_type=token&v=5.199\n\n"
                "2. Авторизуйтесь и разрешите доступ\n"
                "3. Скопируйте токен из адресной строки\n"
                "4. Пришлите его сюда\n\n"
                "❓ Токен выглядит так: vk1.a.abc123...\n\n"
                "Для отмены введите /cancel",
                reply_markup=ReplyKeyboardRemove()
            )
            return SETTING_TOKEN
    
    async def set_token(self, update: Update, context: CallbackContext) -> int:
        """Установка токена пользователя"""
        user_id = update.message.from_user.id
        token = update.message.text.strip()
        
        parser = self.get_parser(user_id)
        success, message = parser.set_token(token)
        
        await update.message.reply_text(message)
        
        if success:
            await update.message.reply_text(
                "🎉 Отлично! Теперь вы можете искать плейлисты.\n\n"
                "Отправьте:\n"
                "• Название трека (например: 'Lil Nas X - Old Town Road')\n"
                "• Или ссылку на аудио ВК\n\n"
                "Команды:\n"
                "/token - изменить токен\n"
                "/status - проверить статус\n"
                "/help - помощь"
            )
            return SEARCHING
        else:
            await update.message.reply_text(
                "❌ Не удалось установить токен. Попробуйте еще раз или введите /cancel"
            )
            return SETTING_TOKEN
    
    async def handle_search(self, update: Update, context: CallbackContext) -> int:
        """Обработка поисковых запросов"""
        user_id = update.message.from_user.id
        user_input = update.message.text.strip()
        
        parser = self.get_parser(user_id)
        
        if not parser.token:
            await update.message.reply_text(
                "❌ Токен не установлен. Введите /token для настройки"
            )
            return SETTING_TOKEN
        
        try:
            status_msg = await update.message.reply_text("🔍 Ищу плейлисты...")
            
            results = parser.search(user_input)
            
            if not results:
                await status_msg.edit_text(
                    "❌ Плейлисты не найдены\n\n"
                    "Возможные причины:\n"
                    "• Трек не найден\n"
                    "• Нет плейлистов с 200+ прослушиваниями\n"
                    "• Попробуйте другой запрос"
                )
                return SEARCHING
            
            response = f"🎵 Найдено плейлистов: {len(results)}\n\n"
            
            for i, playlist in enumerate(results[:MAX_PLAYLISTS_TO_SHOW], 1):
                response += f"{i}. **{playlist['title']}**\n"
                response += f"   🔊 {playlist['listens']} прослушиваний\n"
                response += f"   🔗 {playlist['url']}\n\n"
            
            if len(results) > MAX_PLAYLISTS_TO_SHOW:
                response += f"🤏 Показано {MAX_PLAYLISTS_TO_SHOW} из {len(results)}"
            
            await status_msg.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await update.message.reply_text("❌ Ошибка при поиске")
        
        return SEARCHING
    
    async def token_command(self, update: Update, context: CallbackContext) -> int:
        """Команда для смены токена"""
        await update.message.reply_text(
            "🔄 Введите новый токен ВКонтакте:\n\n"
            "Ссылка для получения:\n"
            "https://oauth.vk.com/authorize?client_id=6121396&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=audio&response_type=token&v=5.199\n\n"
            "Для отмены введите /cancel"
        )
        return SETTING_TOKEN
    
    async def status(self, update: Update, context: CallbackContext):
        """Проверка статуса"""
        user_id = update.message.from_user.id
        parser = self.get_parser(user_id)
        
        if parser.token:
            success, message = parser.check_token(parser.token)
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ Токен не установлен")
    
    async def help(self, update: Update, context: CallbackContext):
        """Справка"""
        help_text = """
🎵 Бот для поиска плейлистов ВКонтакте

📋 Команды:
/start - начать работу
/token - установить/изменить токен
/status - проверить статус
/help - эта справка

🔍 Поиск:
• Название трека: "Lil Nas X - Old Town Road"
• Ссылка ВК: https://vk.com/audio123456789_123456789
• Ссылка ВК: audio-123456789_123456789

🔐 Безопасность:
• Токен хранится только во время сессии
• Никто не имеет доступа к вашему токену
• Для выхода - просто перезапустите бота
        """
        await update.message.reply_text(help_text)
    
    async def cancel(self, update: Update, context: CallbackContext) -> int:
        """Отмена диалога"""
        await update.message.reply_text(
            "❌ Действие отменено",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    def run(self):
        logger.info("Bot started with user token system")
        self.application.run_polling()

if __name__ == '__main__':
    bot = VKPlaylistBot()
    bot.run()
