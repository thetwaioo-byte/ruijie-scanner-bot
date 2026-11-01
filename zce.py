import os
import telebot
from telebot import types

# ပေးပို့ထားသော Token ကို တိုက်ရိုက်ထည့်သွင်းထားသည် (သို့မဟုတ် Render Environment Variable မှ ယူမည်)
TOKEN = "9270543827:AAFtUWde0A3JPhAtvkJ2OcYyEL12lUx3hTw"
ADMIN_ID = 6130147402

bot = telebot.TeleBot(TOKEN)

# /start command ပို့လိုက်သည့်အခါ မီနူးခလုတ်များ ပြသရန်
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    # Inline Keyboard ဖန်တီးခြင်း
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🌿 PAID USER", callback_data='paid_user')
    btn2 = types.InlineKeyboardButton("🔗 Portal URL ထည့်ရန်", callback_data='set_url')
    btn3 = types.InlineKeyboardButton("🟢 Proxy ON", callback_data='proxy_on')
    btn4 = types.InlineKeyboardButton("🔒 Success Codes", callback_data='success_codes')
    btn5 = types.InlineKeyboardButton("🔄 Recheck ပြန်လုပ်စစ်စမ", callback_data='recheck')
    btn6 = types.InlineKeyboardButton("🔴 Scan ရပ်မည်", callback_data='stop_scan')
    
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    welcome_text = (
        f"✨ **RUIJIE VOUCHER SCANNER** ✨\n\n"
        f"👹 **NAME:** {name}\n"
        f"🆔 **USER ID:** {user_id}\n\n"
        f"အောက်ပါ Menu မှ ရွေးချယ်ပါ။"
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

# ခလုတ်များ (Inline Buttons) နှိပ်လိုက်သောအခါ ဖမ်းယူ၍ အလုပ်လုပ်မည့် Handler
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.data == 'paid_user':
            bot.answer_callback_query(call.id, "Paid User စစ်ဆေးနေပါသည်...")
            bot.send_message(call.message.chat.id, "🌿 သင်သည် Paid User အဖြစ် သတ်မှတ်ထားပြီး ဖြစ်ပါသည်။")
            
        elif call.data == 'set_url':
            bot.answer_callback_query(call.id, "Portal URL ထည့်ရန်")
            bot.send_message(call.message.chat.id, "🔗 ကျေးဇူးပြု၍ Portal URL ကို ပေးပို့ပါ။")
            
        elif call.data == 'proxy_on':
            bot.answer_callback_query(call.id, "Proxy အလုပ်လုပ်နေပါပြီ")
            bot.send_message(call.message.chat.id, "🟢 Proxy ကို အောင်မြင်စွာ ဖွင့်ပြီးပါပြီ။")
            
        elif call.data == 'success_codes':
            bot.answer_callback_query(call.id, "Success Codes")
            bot.send_message(call.message.chat.id, "🔒 အောင်မြင်ထားသော Code စာရင်းများမှာ ဘာမှမရှိသေးပါ။")
            
        elif call.data == 'recheck':
            bot.answer_callback_query(call.id, "Recheck လုပ်နေပါပြီ...")
            bot.send_message(call.message.chat.id, "🔄 ပြန်လည် စစ်ဆေးခြင်း ပြီးစီးပါသည်။")
            
        elif call.data == 'stop_scan':
            bot.answer_callback_query(call.id, "Scan ရပ်လိုက်ပါပြီ")
            bot.send_message(call.message.chat.id, "🔴 Scan ဖတ်ခြင်းကို ရပ်ဆိုင်းလိုက်ပါပြီ။")
            
    except Exception as e:
        print(f"Error: {e}")

# Bot ကို စတင်လည်ပတ်ခြင်း (Polling)
if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
    
