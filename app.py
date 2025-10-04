import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from config import BOT_TOKEN, MAX_PLAYLISTS_TO_SHOW, MIN_LISTENS
from vk_parser import VKParser

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VKPlaylistBot:
    def __init__(self):
        try:
            self.parser = VKParser()
            self.application = Application.builder().token(BOT_TOKEN).build()
            self.min_listens = MIN_LISTENS
            
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("status", self.status))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            logger.info("✅ Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Bot initialization failed: {e}")
            raise
    
    async def start(self, update: Update, context: CallbackContext) -> None:
        welcome_text = f"""
🎵 Бот для поиска плейлистов ВКонтакте

Отправьте мне:
• Название трека
• Или ссылку на аудио ВК

Я найду плейлисты с этим треком (от {self.min_listens}+ прослушиваний)
        """
        await update.message.reply_text(welcome_text)
    
    async def help(self, update: Update, context: CallbackContext) -> None:
        help_text = f"""
Примеры запросов:
"Саша Выше - Сердце Героя"
"https://vk.com/audio123456789_123456789"
"audio-123456789_123456789"

Показываю плейлисты от {self.min_listens}+ прослушиваний
        """
        await update.message.reply_text(help_text)

    async def status(self, update: Update, context: CallbackContext) -> None:
        """Проверка статуса бота"""
        try:
            await update.message.reply_text("✅ Бот работает исправно!")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        user_input = update.message.text.strip()
        
        search_message = await update.message.reply_text("🔍 Начинаю поиск...")
        
        try:
            results = []
            
            if any(x in user_input for x in ['vk.com', 'audio', 'http']):
                audio_info = self.parser.extract_audio_info(user_input)
                
                if audio_info and 'owner_id' in audio_info:
                    await search_message.edit_text("🔍 Ищу плейлисты по ссылке...")
                    results = self.parser.search_playlists_global_by_audio(
                        audio_info['owner_id'], 
                        audio_info['audio_id']
                    )
                else:
                    await search_message.edit_text("❌ Не удалось распознать ссылку.")
                    return
            else:
                await search_message.edit_text(f"🔍 Ищу трек '{user_input}'...")
                results = self.parser.search_playlists_global_by_query(user_input)
            
            if not results:
                await search_message.edit_text(
                    f"❌ Не найдено плейлистов\n"
                    f"• Проверьте название трека\n"
                    f"• Или плейлисты имеют < {self.min_listens} прослушиваний"
                )
                return
            
            response = f"🎵 Найдено: {len(results)} плейлистов\n\n"
            
            for i, result in enumerate(results[:MAX_PLAYLISTS_TO_SHOW], 1):
                playlist = result['playlist']
                owner_info = result.get('owner_info', {})
                
                response += f"{i}. **{playlist['title']}**\n"
                response += f"   👤 {owner_info.get('name', 'Автор')}\n"
                response += f"   🔊 {result['listens']} прослушиваний\n"
                response += f"   🔗 {result['playlist_url']}\n\n"
            
            if len(results) > MAX_PLAYLISTS_TO_SHOW:
                response += f"Показано {MAX_PLAYLISTS_TO_SHOW} из {len(results)}\n"
            
            await search_message.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await search_message.edit_text("❌ Ошибка поиска. Попробуйте позже.")

    def run(self):
        logger.info("Бот запущен!")
        self.application.run_polling()

if __name__ == '__main__':
    try:
        bot = VKPlaylistBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start: {e}")
