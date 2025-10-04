import logging
import asyncio
from telegram import Update
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
        self.application.add_handler(CommandHandler("debug", self.debug))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start"""
        welcome_text = """
🎵 Привет! Я бот для поиска плейлистов ВКонтакте.

Я могу помочь найти плейлисты по всему ВКонтакте, в которых есть определенный трек.

📌 Как использовать:
1. Отправь мне название трека (например: "Саша Выше, Postskriptum v.l.g. - Сердце Героя")
2. Или отправь ссылку на трек ВКонтакте

🔍 Я найду все плейлисты с этим треком (где больше 200 прослушиваний) и отсортирую их по популярности.

💡 Отличный инструмент для продвижения музыки!
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
"audio-123456789_123456789"

📊 Бот покажет только плейлисты с 200+ прослушиваний
🎯 Сортировка по популярности
👥 Показывает авторов плейлистов
        """
        await update.message.reply_text(help_text)

    async def debug(self, update: Update, context: CallbackContext) -> None:
        """Отладочная информация"""
        try:
            user_info = self.parser.get_current_user()
            debug_text = f"🔧 Отладочная информация:\n\n"
            debug_text += f"Токен: {'✅' if self.parser.access_token else '❌'}\n"
            debug_text += f"User ID: {self.parser.user_id}\n"
            debug_text += f"Инфо о пользователе: {user_info}\n"
            await update.message.reply_text(debug_text)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка отладки: {e}")
    
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Обработчик текстовых сообщений"""
        user_input = update.message.text.strip()
        
        # Показываем что бот начал поиск
        search_message = await update.message.reply_text("🔍 Начинаю поиск... Это может занять до 30 секунд.")
        
        try:
            results = []
            search_type = ""
            
            # Проверяем, является ли ввод ссылкой
            if any(x in user_input for x in ['vk.com', 'audio', 'http']):
                search_type = "по ссылке"
                audio_info = self.parser.extract_audio_info(user_input)
                
                if audio_info and 'owner_id' in audio_info:
                    await search_message.edit_text("🔍 Ищу плейлисты по ссылке на аудио...")
                    results = self.parser.search_playlists_global_by_audio(
                        audio_info['owner_id'], 
                        audio_info['audio_id']
                    )
                else:
                    await search_message.edit_text("❌ Не удалось распознать ссылку на аудио. Попробуйте другой формат.")
                    return
            else:
                # Поиск по названию
                search_type = "по названию"
                await search_message.edit_text(f"🔍 Ищу трек '{user_input}'...")
                results = self.parser.search_playlists_global_by_query(user_input)
            
            if not results:
                await search_message.edit_text(
                    f"❌ Не найдено плейлистов с этим треком\n\n"
                    f"Возможные причины:\n"
                    f"• Трек не найден в ВКонтакте\n"
                    f"• Плейлисты с треком имеют меньше {MIN_LISTENS} прослушиваний\n"
                    f"• Трек не добавлен в публичные плейлисты"
                )
                return
            
            # Формируем ответ
            response = f"🎵 Найдено плейлистов: {len(results)}\n"
            response += f"🔍 Поиск {search_type}\n\n"
            
            for i, result in enumerate(results[:MAX_PLAYLISTS_TO_SHOW], 1):
                playlist = result['playlist']
                owner_info = result.get('owner_info', {})
                
                response += f"**{i}. {playlist['title']}**\n"
                
                # Информация о владельце
                if owner_info:
                    if owner_info.get('is_group'):
                        response += f"   👥 Группа: {owner_info['first_name']}\n"
                    else:
                        response += f"   👤 Автор: {owner_info['first_name']} {owner_info['last_name']}\n"
                
                response += f"   🔊 Прослушиваний: {result['listens']}\n"
                response += f"   🔗 {result['playlist_url']}\n\n"
            
            if len(results) > MAX_PLAYLISTS_TO_SHOW:
                response += f"🤏 Показано {MAX_PLAYLISTS_TO_SHOW} из {len(results)} плейлистов\n\n"
            
            response += "💡 *Для связи с авторами плейлистов используйте ссылки на их профили*"
            
            await search_message.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await search_message.edit_text("❌ Произошла ошибка при поиске. Попробуйте позже или проверьте формат запроса.")

    def run(self):
        """Запуск бота"""
        logger.info("Бот запущен!")
        self.application.run_polling()

if __name__ == '__main__':
    bot = VKPlaylistBot()
    bot.run()
