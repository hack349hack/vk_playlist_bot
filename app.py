import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from config import BOT_TOKEN, MAX_PLAYLISTS_TO_SHOW, MIN_LISTENS
from vk_parser import VKParser

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class VKPlaylistBot:
    def __init__(self):
        self.parser = VKParser()
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update: Update, context: CallbackContext) -> None:
        text = """
🎵 Бот для поиска плейлистов ВК

Отправьте:
• Название трека
• Или ссылку на аудио ВК

Пример: "Lil Nas X - Old Town Road"
        """
        await update.message.reply_text(text)
    
    async def help(self, update: Update, context: CallbackContext) -> None:
        text = """
📝 Форматы ссылок:
• https://vk.com/audio123456789_123456789
• audio-123456789_123456789
• audios123456789_123456789

🎯 Показываю плейлисты от 200+ прослушиваний
        """
        await update.message.reply_text(text)
    
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        user_input = update.message.text.strip()
        
        msg = await update.message.reply_text("🔍 Поиск...")
        
        try:
            if any(x in user_input for x in ['vk.com', 'audio', 'http']):
                # Поиск по ссылке
                audio_info = self.parser.extract_audio_info(user_input)
                if audio_info and 'owner_id' in audio_info:
                    await msg.edit_text("🔍 Ищу по ссылке...")
                    results = self.parser.search_playlists_by_audio(
                        audio_info['owner_id'], 
                        audio_info['audio_id']
                    )
                else:
                    await msg.edit_text("❌ Не распознана ссылка")
                    return
            else:
                # Поиск по названию
                await msg.edit_text(f"🔍 Ищу '{user_input}'...")
                results = self.parser.search_by_query(user_input)
            
            if not results:
                await msg.edit_text("❌ Не найдено плейлистов")
                return
            
            response = f"🎵 Найдено: {len(results)}\n\n"
            
            for i, result in enumerate(results[:MAX_PLAYLISTS_TO_SHOW], 1):
                response += f"{i}. {result['title']}\n"
                response += f"   🔊 {result['listens']} прослушиваний\n"
                response += f"   🔗 {result['url']}\n\n"
            
            await msg.edit_text(response)
            
        except Exception as e:
            await msg.edit_text("❌ Ошибка поиска")

    def run(self):
        self.application.run_polling()

if __name__ == '__main__':
    bot = VKPlaylistBot()
    bot.run()
