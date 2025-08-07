import telebot
import requests

TOKEN = "8347050926:AAFOGdrN1kCyQDxpgG5orEVUXpshcPiqEyI"
bot = telebot.TeleBot(TOKEN)

CHANNEL_ID = "@Luck111AvirajBhai_Bot"

@bot.channel_post_handler(content_types=['new_chat_members'])
def approve_join_request(message):
    for user in message.new_chat_members:
        try:
            bot.approve_chat_join_request(CHANNEL_ID, user.id)
            print(f"Approved: {user.first_name}")
        except Exception as e:
            print(f"Error: {e}")

bot.polling()
