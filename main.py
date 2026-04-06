import math
import os
import base64
import requests
import telebot
import google.generativeai as genai
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# --- СОЗЛАМАЛАР (TOKEN VA KALITLAR) ---
TOKEN = "8644043557:AAEAGslHPCh6OQ6H6XmZdgS_nZhIwpyHUU8"
WEATHER_API_KEY = "80f124c130311f4422204c3527b140df"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

# Gemini API созламаси
GEMINI_API_KEY = "AIzaSyAUIlYbmhFDXeF0OB510Yz2nb-PvcHoryI"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TOKEN)

# Фойдаланувчи ҳолатлари
kasallik_mode = set()

# --- МАЖБУРИЙ ОБУНА ҚИСМИ ---
CHANNELS = ["@smart_dehqon_channel"]
CHANNEL_URL = "https://t.me/smart_dehqon_channel"

def check_sub(user_id):
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(chat_id=channel, user_id=user_id).status
            if status in ['member', 'administrator', 'creator']:
                return True
        except Exception:
            return False
    return False

# --- МЕНЮЛАР ---
def asosiy_menyu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🌤 Ob-havo"), KeyboardButton("🌱 Ekish tavsiyasi"))
    markup.add(KeyboardButton("🦠 Kasallik aniqlash"), KeyboardButton("📊 Bozor narxlari"))
    markup.add(KeyboardButton("📚 Kitoblar menyusi"), KeyboardButton("ℹ️ Yordam"))
    return markup

# --- БОТ БУЙРУҚЛАРИ (HANDLERS) ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.chat.id
    if check_sub(user_id):
        bot.send_message(user_id, f"Assalomu alaykum, {message.from_user.full_name}! SmartDehqon botiga xush kelibsiz.", reply_markup=asosiy_menyu())
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Kanalga a'zo bo'lish 📢", url=CHANNEL_URL))
        markup.add(InlineKeyboardButton("A'zo bo'ldim ✅", callback_data="check_sub"))
        bot.send_message(user_id, "Botdan foydalanish uchun kanalimizga a'zo bo'ling:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_callback(call):
    if check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Rahmat! A'zolik tasdiqlandi.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Xush kelibsiz!", reply_markup=asosiy_menyu())
    else:
        bot.answer_callback_query(call.id, "Siz hali kanalga a'zo bo'lmadingiz! ❌", show_alert=True)

# --- 🌱 AI EKISH TAVSIYALARI ---
@bot.message_handler(func=lambda message: message.text == "🌱 Ekish tavsiyasi")
def ekish_tavsiyalari(message):
    markup = InlineKeyboardMarkup(row_width=2)
    ekinlar = [("🍅 Pomidor", "ai_pomidor"), ("🥒 Bodring", "ai_bodring"), 
               ("🌽 Makkajo'xori", "ai_makkajo_xori"), ("🥔 Kartoshka", "ai_kartoshka"), ("🧅 Piyoz", "ai_piyoz")]
    for text, data in ekinlar:
        markup.add(InlineKeyboardButton(text, callback_data=data))
    bot.send_message(message.chat.id, "Qaysi ekin haqida AI dan batafsil ma'lumot olmoqchisiz?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ai_"))
def get_ai_info(call):
    ekin = call.data.replace("ai_", "").replace("_", " ")
    bot.answer_callback_query(call.id, "AI tahlil qilmoqda...")
    wait_msg = bot.send_message(call.message.chat.id, f"⌛ **{ekin.capitalize()}** haqida Gemini ma'lumot tayyorlamoqda...")

    try:
        prompt = f"O'zbekiston iqlimida {ekin} yetishtirish bo'yicha juda batafsil agronomik tavsiyalar ber. Ekish vaqti, parvarishlash va sirlarini yoz. Javobni o'zbek tilida, tushunarli va chiroyli formatda ber."
        response = gemini_model.generate_content(prompt)
        
        bot.delete_message(call.message.chat.id, wait_msg.message_id)
        bot.send_message(call.message.chat.id, response.text, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ Xatolik: {str(e)}", call.message.chat.id, wait_msg.message_id)

# --- 🦠 AI KASALLIK ANIQLASH (RASM TAHLILI) ---
@bot.message_handler(func=lambda message: message.text == "🦠 Kasallik aniqlash")
def kasallik_start(message):
    kasallik_mode.add(message.chat.id)
    bot.send_message(message.chat.id, "📸 O'simlikning kasallangan qismi rasmini yuboring. Gemini uni tahlil qiladi.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id not in kasallik_mode:
        return
    
    wait_msg = bot.send_message(message.chat.id, "⌛ Rasm tahlil qilinmoqda, iltimos kuting...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Gemini-ga rasmni yuborish
        img = {'mime_type': 'image/jpeg', 'data': downloaded_file}
        prompt = "Siz agronom mutaxassissiz. Ushbu o'simlik rasmini tahlil qiling. Kasallik bormi? Bo'lsa nomi va davolash choralarini o'zbek tilida yozing."
        
        response = gemini_model.generate_content([prompt, img])
        
        bot.delete_message(message.chat.id, wait_msg.message_id)
        bot.send_message(message.chat.id, response.text, parse_mode="Markdown")
        kasallik_mode.discard(message.chat.id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

# --- 🌤 OB-HAVO ---
@bot.message_handler(func=lambda message: message.text == "🌤 Ob-havo")
def weather_handler(message):
    city = "Tashkent"
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric", "lang": "uz"}
    res = requests.get(WEATHER_URL, params=params).json()
    
    if res.get("main"):
        temp = res["main"]["temp"]
        desc = res["weather"][0]["description"]
        bot.send_message(message.chat.id, f"🌤 {city}da harorat: {temp}°C\nHolat: {desc.capitalize()}")
    else:
        bot.send_message(message.chat.id, "❌ Ob-havo ma'lumotini olib bo'lmadi.")

# --- BOSHQA MATNLAR ---
@bot.message_handler(func=lambda message: True)
def text_handler(message):
    if message.text == "📊 Bozor narxlari":
        bot.send_message(message.chat.id, "📊 *Bozor narxlari (o'rtacha):*\n🍅 Pomidor: 12,000\n🥒 Bodring: 8,000\n🥔 Kartoshka: 5,000", parse_mode="Markdown")
    elif message.text == "ℹ️ Yordam":
        bot.send_message(message.chat.id, "Savollar bo'lsa @Hasanboy_Obidjonov ga yozing.")

if __name__ == "__main__":
    bot.polling(none_stop=True)
