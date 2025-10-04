import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from config import BOT_TOKEN, MAX_PLAYLISTS_TO_SHOW
from vk_parser import VKParser

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VKPlaylistBot:
    def __init__(self):
        self.parser = VKParser()
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрация обработчиков
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start"""
        welcome_text = """
🎵 Привет! Я бот для поиска плейлистов ВКонтакте.

Я могу помочь найти плейлисты, в которых есть определенный трек.

📌 Как использовать:
1. Отправь мне название трека (например: "Саша Выше, Postskriptum v.l.g. - Сердце Героя")
2. Или отправь ссылку на трек ВКонтакте

Я найду все плейлисты с этим треком, где больше 200 прослушиваний, и отсортирую их по популярности.
        """
        await update.message.reply_text(welcome_text)
    
    async def help(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /help"""
        help_text = """
🔍 Поиск плейлистов ВКонтакте

Просто отправь мне:
• Название трека и артиста
• Или ссылку на аудио ВКонтакте

Примеры:
"Саша Выше, Postskriptum v.l.g. - Сердце Героя"
"https://vk.com/audio123456789_123456789"

📊 Бот покажет только плейлисты с 200+ прослушиваний
        """
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Обработчик текстовых сообщений"""
        user_input = update.message.text
        
        await update.message.reply_text("🔍 Ищу плейлисты... Это может занять некоторое время.")
        
        try:
            results = []
            
            # Проверяем, является ли ввод ссылкой
            if 'vk.com' in user_input or 'audio' in user_input:
                audio_info = self.parser.extract_audio_info(user_input)
                if audio_info and 'owner_id' in audio_info:
                    results = self.parser.search_audio_in_playlists(
                        int(audio_info['owner_id']), 
                        int(audio_info['audio_id'])
                    )
                else:
                    await update.message.reply_text("❌ Не удалось распознать ссылку на аудио")
                    return
            else:
                # Поиск по названию
                results = self.parser.search_by_query_in_playlists(user_input)
            
            if not results:
                await update.message.reply_text("❌ Не найдено плейлистов с этим треком (или прослушиваний меньше 200)")
                return
            
            # Формируем ответ
            response = f"🎵 Найдено плейлистов: {len(results)}\n\n"
            
            for i, result in enumerate(results[:MAX_PLAYLISTS_TO_SHOW], 1):
                playlist = result['playlist']
                response += f"{i}. {playlist['title']}\n"
                response += f"   👥 Прослушиваний: {result['listens']}\n"
                response += f"   🔗 {result['playlist_url']}\n\n"
            
            if len(results) > MAX_PLAYLISTS_TO_SHOW:
                response += f"🤏 Показано {MAX_PLAYLISTS_TO_SHOW} из {len(results)} плейлистов"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text("❌ Произошла ошибка при поиске. Попробуйте позже.")

    def run(self):
        """Запуск бота"""
        self.application.run_polling()

if __name__ == '__main__':
    bot = VKPlaylistBot()
    bot.run()
