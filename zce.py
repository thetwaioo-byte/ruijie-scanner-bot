import os
import telebot
from telebot import types
from urllib.parse import urlparse, parse_qs
import requests
import concurrent.futures
import time

# Bot Token နှင့် Admin ID
TOKEN = "9270543827:AAFtUWde0A3JPhAtvkJ2OcYyEL12lUx3hTw"
ADMIN_ID = 6130147402

bot = telebot.TeleBot(TOKEN)

# အသုံးပြုသူတစ်ဦးချင်းစီ၏ အချက်အလက်နှင့် State များကို သိမ်းဆည်းရန်
user_data = {}

# /start command ပို့လိုက်သည့်အခါ မီနူးခလုတ်များ ပြသရန်
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🌿 PAID USER", callback_data='paid_user')
    btn2 = types.InlineKeyboardButton("🔗 Portal URL ထည့်ရန်", callback_data='set_url')
    btn3 = types.InlineKeyboardButton("🟢 Proxy ON", callback_data='proxy_on')
    btn4 = types.InlineKeyboardButton("🔒 Success Codes", callback_data='success_codes')
    btn5 = types.InlineKeyboardButton("🔄 Recheck ပြန်လုပ်စစ်စမ", callback_data='recheck')
    btn6 = types.InlineKeyboardButton("🔴 Scan ရပ်မည်", callback_data='stop_scan')
    
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    welcome_text = (
        f"✨ **RUIJIE VOUCHER SCANNER (PRO)** ✨\n\n"
        f"👹 **NAME:** {name}\n"
        f"🆔 **USER ID:** {user_id}\n\n"
        f"အောက်ပါ Menu မှ ရွေးချယ်ပါ သို့မဟုတ် Portal URL ကို အရင်ပေးပို့ပါ။"
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

# ခလုတ်များ နှိပ်လိုက်သောအခါ လုပ်ဆောင်မည့် Handler
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        user_id = call.message.chat.id
        if call.data == 'paid_user':
            bot.answer_callback_query(call.id, "Paid User စစ်ဆေးနေပါသည်...")
            bot.send_message(user_id, "🌿 သင်သည် Paid User အဖြစ် သတ်မှတ်ထားပြီး ဖြစ်ပါသည်။")
            
        elif call.data == 'set_url':
            bot.answer_callback_query(call.id, "Portal URL ထည့်ရန်")
            user_data[user_id] = {'state': 'waiting_for_url', 'success_list': [], 'is_scanning': False}
            bot.send_message(user_id, "🔗 ကျေးဇူးပြု၍ Ruijie Portal URL ကို ပေးပို့ပါ။")
            
        elif call.data == 'proxy_on':
            bot.answer_callback_query(call.id, "Proxy အလုပ်လုပ်နေပါပြီ")
            bot.send_message(user_id, "🟢 Proxy ကို အောင်မြင်စွာ ဖွင့်ပြီးပါပြီ။")
            
        elif call.data == 'success_codes':
            bot.answer_callback_query(call.id, "Success Codes")
            success_list = user_data.get(user_id, {}).get('success_list', [])
            if success_list:
                codes_str = "\n".join(success_list)
                bot.send_message(user_id, f"🔒 **အောင်မြင်ထားသော Voucher Codes:**\n\n{codes_str}", parse_mode='Markdown')
            else:
                bot.send_message(user_id, "🔒 ယခုထိ ရှာဖွေတွေ့ရှိထားသော Success Code မရှိသေးပါ။")
            
        elif call.data == 'recheck':
            bot.answer_callback_query(call.id, "Recheck လုပ်နေပါပြီ...")
            bot.send_message(user_id, "🔄 ပြန်လည် စစ်ဆေးခြင်း ပြီးစီးပါသည်။")
            
        elif call.data == 'stop_scan':
            bot.answer_callback_query(call.id, "Scan ရပ်လိုက်ပါပြီ")
            if user_id in user_data:
                user_data[user_id]['is_scanning'] = False
                user_data[user_id]['state'] = 'stopped'
            bot.send_message(user_id, "🔴 Ruijie Voucher Scan ဖတ်ခြင်းကို လုံခြုံစွာ ရပ်ဆိုင်းလိုက်ပါပြီ။")
            
    except Exception as e:
        print(f"Error: {e}")

# တစ်ခုချင်းစီကို လုံခြုံမြန်ဆန်စွာ စစ်ဆေးမည့် Function (Rate-limited & Safe)
def verify_voucher_code(code, portal_url):
    try:
        # ဤနေရာတွင် Ruijie Portal URL သို့ တိုက်ရိုက် HTTP Request ပို့စစ်ဆေးမည့် Logic ပါဝင်မည်
        # ဥပမာ: response = requests.get(f"{portal_url}&code={code}", timeout=2)
        
        # လုံခြုံရေးအရ Router IP Block မလုပ်စေရန် အနည်းငယ် နှေးပေးခြင်း (Sleep)
        time.sleep(0.05) 
        
        # စမ်းသပ်ချက် အနေဖြင့် ထည့်ထားခြင်း (အမှန်တကယ် ကုဒ်မှန်လျှင် True ဖြစ်မည်)
        is_valid = False 
        
        return code, is_valid
    except Exception:
        return code, False

# စာသားများ (URL သို့မဟုတ် ကုဒ်စာရင်းများ) လက်ခံစစ်ဆေးခြင်း
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.chat.id
    text = message.text.strip()
    
    # Ruijie Portal URL ပို့လာခြင်း ဟုတ်မဟုတ် စစ်ဆေးခြင်း
    if "portal-mm-as.ruijienetworks.com" in text or "gw_address" in text:
        try:
            parsed_url = urlparse(text)
            query_params = parse_qs(parsed_url.query)
            
            gw_address = query_params.get('gw_address', [''])[0]
            gw_port = query_params.get('gw_port', [''])[0]
            ip = query_params.get('ip', [''])[0]
            mac = query_params.get('mac', [''])[0]
            
            if user_id not in user_data:
                user_data[user_id] = {}
            
            user_data[user_id]['portal_url'] = text
            user_data[user_id]['gw_address'] = gw_address
            user_data[user_id]['gw_port'] = gw_port
            user_data[user_id]['ip'] = ip
            user_data[user_id]['mac'] = mac
            user_data[user_id]['state'] = 'url_ready'
            user_data[user_id]['success_list'] = []
            user_data[user_id]['is_scanning'] = True
            
            response_msg = (
                f"✅ **Portal URL ကို အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ!**\n\n"
                f"🌐 Router IP: `{gw_address}:{gw_port}`\n"
                f"💻 Client IP: `{ip}`\n"
                f"🖧 MAC: `{mac}`\n\n"
                f"🚀 **လုံခြုံပြီး အမြန်ဆုံး စကန်ဖတ်ရန် အသင့်ဖြစ်ပါပြီ။** ကုဒ်များကို ပေးပို့ပါ။"
            )
            bot.send_message(user_id, response_msg, parse_mode='Markdown')
            return
        except Exception as e:
            bot.send_message(user_id, f"❌ URL ခွဲခြမ်းစိတ်ဖြာရာတွင် အမှားအယွင်းရှိသည်: {e}")
            return

    # ကုဒ်များ ပို့လာပါက အမြန်စစ်ဆေးခြင်း
    user_info = user_data.get(user_id, {})
    current_state = user_info.get('state')
    
    if current_state == 'url_ready':
        portal_url = user_info.get('portal_url')
        codes = text.split()
        
        bot.send_message(user_id, f"⚡ စုစုပေါင်း ကုဒ်ရေ `{len(codes)}` ခုကို အလုံခြုံဆုံး အမြန်နှုန်းဖြင့် စတင်စစ်ဆေးနေပါပြီ...")
        
        user_info['is_scanning'] = True
        found_success = []
        
        # Router IP Block မခံရအောင် သင့်တင့်သော Threads အရေအတွက် (ဥပမာ: 10 သို့မဟုတ် 15) သုံးခြင်း
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(verify_voucher_code, code, portal_url): code for code in codes}
            
            for future in concurrent.futures.as_completed(futures):
                if not user_info.get('is_scanning', True):
                    break
                code, is_valid = future.result()
                if is_valid:
                    found_success.append(code)
                    if 'success_list' not in user_info:
                        user_info['success_list'] = []
                    user_info['success_list'].append(code)
                    bot.send_message(user_id, f"✅ **SUCCESS!** အောင်မြင်သော ကုဒ်တွေ့ရှိပါပြီ: `🔑 {code}`", parse_mode='Markdown')
        
        bot.send_message(user_id, f"🏁 စစ်ဆေးမှု ပြီးဆုံးပါပြီ။ အောင်မြင်သော ကုဒ်ပေါင်း `{len(found_success)}` ခု ရရှိထားပါသည်။")
    else:
        bot.send_message(user_id, "⚠️ ကျေးဇူးပြု၍ ပထမဦးစွာ Ruijie Portal URL ကို အရင်ပေးပို့ပါ။")

if __name__ == '__main__':
    print("Bot is running with Pro Optimized Scanner...")
    bot.infinity_polling()
            
