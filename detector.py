import telebot
import opennsfw2 as n2
from PIL import Image
import requests
import tempfile
import os
import time
import json
import threading
from datetime import datetime, date
from queue import Queue

TOKEN = 'توكن بوتك هنا'
CHANNEL_USERNAME = 'يوزر قناة الاجباري هنا بدون @'
CHANNEL_URL = 'https://t.me/SYR_SB'
PROGRAMMER_URL = 'https://t.me/SB_SAHAR'
DEVELOPER_ID = '6789179634' 
NSFW_THRESHOLD = 0.7  
bot = telebot.TeleBot(TOKEN)
VIOLATIONS_FILE = "user_violations.json"
REPORTS_FILE = "daily_reports.json"
user_violations = {}
daily_reports = {}
current_date = date.today().isoformat()
processed_messages = set() 
media_queue = Queue() 
def load_violations():
    global user_violations
    try:
        with open(VIOLATIONS_FILE, 'r', encoding='utf-8') as f:
            user_violations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        user_violations = {}
def save_violations():
    with open(VIOLATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_violations, f, ensure_ascii=False, indent=4)
def load_reports():
    global daily_reports
    try:
        with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
            daily_reports = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        daily_reports = {}
def save_reports():
    with open(REPORTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(daily_reports, f, ensure_ascii=False, indent=4)
def check_image_safety(image_path):
    try:
        image = Image.open(image_path)
        nsfw_probability = n2.predict_image(image)
        print(f"NSFW Probability for image: {nsfw_probability}")
        return 'nude' if nsfw_probability > NSFW_THRESHOLD else 'ok'
    except Exception as e:
        print(f"حدث خطأ أثناء تحليل الصورة: {e}")
        return 'error'
def process_media_worker():
    while True:
        content, file_extension, message, media_type = media_queue.get()
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_file_path)
            print(f"NSFW Probabilities for video {message.message_id}: {nsfw_probabilities}")
            os.unlink(temp_file_path)
            
            if any(prob >= NSFW_THRESHOLD for prob in nsfw_probabilities):
                handle_violation(message, media_type)
        except Exception as e:
            print(f"خطأ في معالجة الميديا للرسالة {message.message_id}: {e}")
        finally:
            media_queue.task_done()
def handle_violation(message, content_type):
    global current_date
    try:
        bot.delete_message(message.chat.id, message.message_id)
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        user_violations[user_id] = user_violations.get(user_id, 0) + 1
        violation_count = user_violations[user_id]
        
        warning_msg = (
            f"⚠️ <b>تنبيه فوري!</b>\n"
            f"👤 <b>العضو:</b> <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
            f"🚫 <b>نوع المخالفة:</b> {content_type} غير لائق\n"
            f"🔢 <b>عدد المخالفات:</b> {violation_count}/10\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        if is_user_admin(chat_id, user_id):
            warning_msg += (
                "🛡️ <b>ملاحظة:</b> المستخدم مشرف لايمكن تقيده تجاوز الحد المسموح!\n"
                "📢 <b>يرجى التعامل معه من قبل مالك المجموعة.</b>"
            )
        else:
            warning_msg += (
                "⚠️ <b>تحذير:</b> إذا تجاوزت 10 مخالفات، سيتم تقييدك تلقائيًا لمدة 24 ساعة!"
            )
        bot.send_message(chat_id, warning_msg, parse_mode="HTML")
        
        today = date.today().isoformat()
        if today != current_date:
            reset_daily_reports()
            current_date = today
        
        if chat_id not in daily_reports:
            daily_reports[chat_id] = []
        
        violation_entry = {
            "user_name": message.from_user.first_name,
            "username": f"@{message.from_user.username}" if message.from_user.username else "غير متوفر",
            "user_id": user_id,
            "violation_type": content_type,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_violations": violation_count
        }
        daily_reports[chat_id].append(violation_entry)
        save_reports()
        
        if violation_count >= 10 and not is_user_admin(chat_id, user_id):
            bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + 86400, can_send_messages=False)
            bot.send_message(chat_id, (
                f"🚫 <b>تم تقييد العضو!</b>\n"
                f"👤 <b>العضو:</b> <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
                f"⏳ <b>المدة:</b> 24 ساعة\n"
                "📢 <b>السبب:</b> تجاوز 10 مخالفات!"
            ), parse_mode="HTML")
            user_violations[user_id] = 0
        
        save_violations()
    except Exception as e:
        print(f"خطأ في معالجة المخالفة: {e}")
def is_user_admin(chat_id, user_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(str(admin.user.id) == str(user_id) for admin in admins)
    except Exception as e:
        print(f"خطأ في التحقق من الصلاحيات: {e}")
        return False
def is_user_subscribed(user_id):
    try:
        if str(user_id) == DEVELOPER_ID:
            print(f"User {user_id} is the developer, bypassing subscription check.")
            return True
        
        chat_member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        status = chat_member.status
        print(f"User {user_id} status in channel @{CHANNEL_USERNAME}: {status}")
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription for user {user_id}: {e}")
        return False
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.message_id in processed_messages:
        print(f"الرسالة {message.message_id} تم فحصها مسبقًا، يتم تجاهلها.")
        return
    
    processed_messages.add(message.message_id)
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_link = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        response = requests.get(file_link)
        tmp_file.write(response.content)
        temp_path = tmp_file.name

    res = check_image_safety(temp_path)
    os.remove(temp_path)

    if res == 'nude':
        handle_violation(message, 'صورة')
@bot.message_handler(content_types=['sticker'])
def handle_sticker(message, is_edited=False):
    if not is_edited and message.message_id in processed_messages:
        print(f"الرسالة {message.message_id} تم فحصها مسبقًا، يتم تجاهلها.")
        return
    
    if not is_edited:
        processed_messages.add(message.message_id)
    
    if message.sticker.thumb:
        file_info = bot.get_file(message.sticker.thumb.file_id)
        sticker_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            response = requests.get(sticker_url)
            tmp_file.write(response.content)
            temp_path = tmp_file.name

        res = check_image_safety(temp_path)
        os.remove(temp_path)

        if res == 'nude':
            handle_violation(message, 'ملصق')
@bot.message_handler(content_types=['video'])
def handle_video(message, is_edited=False):
    if not is_edited and message.message_id in processed_messages:
        print(f"الرسالة {message.message_id} تم فحصها مسبقًا، يتم تجاهلها.")
        return
    
    if not is_edited:
        processed_messages.add(message.message_id)
    
    file_info = bot.get_file(message.video.file_id)
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
    response = requests.get(file_url)
    if response.status_code == 200:
        media_queue.put((response.content, '.mp4', message, 'فيديو'))
        
@bot.message_handler(content_types=['animation'])
def handle_gif(message, is_edited=False):
    if not is_edited and message.message_id in processed_messages:
        print(f"الرسالة {message.message_id} تم فحصها مسبقًا، يتم تجاهلها.")
        return
    
    if not is_edited:
        processed_messages.add(message.message_id)
    
    file_info = bot.get_file(message.animation.file_id)
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
    response = requests.get(file_url)
    if response.status_code == 200:
        media_queue.put((response.content, '.gif', message, 'صورة متحركة'))
        
@bot.message_handler(func=lambda message: message.entities and any(entity.type == 'custom_emoji' for entity in message.entities))
def handle_custom_emoji(message):
    if message.message_id in processed_messages:
        print(f"الرسالة {message.message_id} تم فحصها مسبقًا، يتم تجاهلها.")
        return
    
    processed_messages.add(message.message_id)
    custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
    sticker_links = get_premium_sticker_info(custom_emoji_ids)
    for link in sticker_links:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            response = requests.get(link)
            tmp_file.write(response.content)
            temp_path = tmp_file.name

        res = check_image_safety(temp_path)
        os.remove(temp_path)

        if res == 'nude':
            handle_violation(message, 'رمز تعبيري مميز')

def get_premium_sticker_info(custom_emoji_ids):
    try:
        sticker_set = bot.get_custom_emoji_stickers(custom_emoji_ids)
        return [f'https://api.telegram.org/file/bot{TOKEN}/{bot.get_file(sticker.thumb.file_id).file_path}' for sticker in sticker_set if sticker.thumb]
    except Exception as e:
        print(f"Error retrieving sticker info: {e}")
        return []

@bot.edited_message_handler(content_types=['text'])
def handle_edited_custom_emoji_message(message):
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else f"({user_id})"

    if message.entities:
        custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
        if custom_emoji_ids:
            sticker_links = get_premium_sticker_info(custom_emoji_ids)
            for link in sticker_links:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    response = requests.get(link)
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name

                res = check_image_safety(temp_path)
                os.remove(temp_path)

                if res == 'nude':
                    bot.delete_message(message.chat.id, message.message_id)
                    alert_message = (
                        f"🚨 <b>تنبيه فوري!</b>\n"
                        f"🔗 <b>المستخدم:</b> {user_name} <b>عدّل رسالة وأضاف رمز تعبيري مميز غير لائق!</b>\n"
                        "📢 <b>يرجى اتخاذ الإجراء اللازم.</b>"
                    )
                    bot.send_message(message.chat.id, alert_message, parse_mode="HTML")
                    handle_violation(message, 'رمز تعبيري مميز معدل')
                    
@bot.edited_message_handler(content_types=['photo', 'video', 'animation', 'sticker'])
def handle_edited_media(message):
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else f"({user_id})"

    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_link = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            response = requests.get(file_link)
            tmp_file.write(response.content)
            temp_path = tmp_file.name

        res = check_image_safety(temp_path)
        os.remove(temp_path)

        if res == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            alert_message = (
                f"🚨 <b>تنبيه فوري!</b>\n"
                f"🔗 <b>المستخدم:</b> {user_name} <b>عدّل رسالة إلى صورة غير لائقة!</b>\n"
                "📢 <b>يرجى اتخاذ الإجراء اللازم.</b>"
            )
            bot.send_message(message.chat.id, alert_message, parse_mode="HTML")
            handle_violation(message, 'صورة معدلة')

    elif message.content_type == 'video':
        handle_video(message, is_edited=True)
    elif message.content_type == 'animation':
        handle_gif(message, is_edited=True)
    elif message.content_type == 'sticker':
        handle_sticker(message, is_edited=True)
        
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if not is_user_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        subscribe_button = telebot.types.InlineKeyboardButton("اشترك الآن", url=CHANNEL_URL)
        check_button = telebot.types.InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")
        markup.add(subscribe_button, check_button)
        
        bot.send_message(
            message.chat.id,
            f"⚠️ <b>تنبيه:</b> يجب عليك الاشتراك في القناة أولاً لاستخدام البوت!\n\n"
            f"👉 <a href='{CHANNEL_URL}'>اضغط هنا للاشتراك</a>",
            parse_mode="HTML",
            reply_markup=markup
        )
        return

    markup = telebot.types.InlineKeyboardMarkup()
    programmer_button = telebot.types.InlineKeyboardButton("المطور", url=PROGRAMMER_URL)
    add_to_group_button = telebot.types.InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true")
    markup.add(programmer_button, add_to_group_button)

    bot.send_message(
        message.chat.id,
        (
            "🛡️ <b>مرحبًا بك في بوت الحماية الذكي!</b>\n"
            "أنا هنا لحماية مجموعاتك من المحتوى غير اللائق تلقائيًا.\n"
            "📊 <b>للمشرفين:</b> استخدم /stats لعرض التقرير اليومي.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <b>أضفني الآن واستمتع بالأمان!</b>"
        ),
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    user_id = call.from_user.id
    if is_user_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        programmer_button = telebot.types.InlineKeyboardButton("المطور", url=PROGRAMMER_URL)
        add_to_group_button = telebot.types.InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true")
        markup.add(programmer_button, add_to_group_button)

        bot.edit_message_text(
            (
                "🛡️ <b>مرحبًا بك في بوت الحماية الذكي!</b>\n"
                "أنا هنا لحماية مجموعاتك من المحتوى غير اللائق تلقائيًا.\n"
                "📊 <b>للمشرفين:</b> استخدم /stats لعرض التقرير اليومي.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡ <b>أضفني الآن واستمتع بالأمان!</b>"
            ),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "⚠️ لم تشترك بعد! الرجاء الاشتراك في القناة أولاً.", show_alert=True)

@bot.message_handler(content_types=['new_chat_members'])
def on_user_joins(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            chat_id = str(message.chat.id)
            bot.send_message(
                message.chat.id,
                (
                    "🦅 <b>تم تفعيل بوت الحماية بنجاح!</b>\n"
                    "سأقوم تلقائيًا بمراقبة الصور، الفيديوهات، الملصقات، والرموز التعبيرية.\n"
                    "📊 <b>للمشرفين:</b> استخدم /stats لعرض الإحصائيات اليومية.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚡ <b>مجموعتك الآن تحت الحماية الكاملة!</b>"
                ),
                parse_mode="HTML"
            )
@bot.message_handler(commands=['stats'])
def show_stats(message):
    chat_id = str(message.chat.id)
    user_id = message.from_user.id
    
    if not is_user_admin(chat_id, user_id):
        bot.reply_to(message, "❌ <b>عذرًا!</b> هذا الأمر مخصص للمشرفين فقط.", parse_mode="HTML")
        return
    
    send_daily_report(chat_id)

def send_daily_report(chat_id):
    chat_id = str(chat_id)
    if chat_id in daily_reports and daily_reports[chat_id]:
        report_msg = (
            "📊 <b>التقرير اليومي للمجموعة</b>\n"
            f"🕒 <b>تاريخ التقرير:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        violations = daily_reports[chat_id]
        report_msg += f"📈 <b>إجمالي المخالفات:</b> {len(violations)}\n\n"
        for idx, violation in enumerate(violations, 1):
            report_msg += (
                f"#{idx} <b>المستخدم:</b> {violation['user_name']} ({violation['username']})\n"
                f"🆔 <b>المعرف:</b> <code>{violation['user_id']}</code>\n"
                f"⚠️ <b>نوع المخالفة:</b> {violation['violation_type']}\n"
                f"⏰ <b>الوقت:</b> {violation['time']}\n"
                f"🔢 <b>عدد المخالفات الكلي:</b> {violation['total_violations']}\n"
                "───────────────────\n"
            )
        report_msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📢 <b>البوت يعمل بكفاءة لحماية المجموعة!</b>"
        
        if len(report_msg) > 4096:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tmp_file:
                tmp_file.write(report_msg.replace('<b>', '').replace('</b>', '').replace('<a href="tg://user?id=', '').replace('">', ' - ').replace('</a>', '').replace('<code>', '`').replace('</code>', '`'))
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, 'rb') as file:
                bot.send_document(chat_id, file, caption=(
                    "📈 <b>تنبيه:</b> المخالفات كثيرة جدًا لإرسالها في رسالة واحدة!\n"
                    "📎 <b>الملف المرفق يحتوي على التقرير اليومي الكامل.</b>"
                ), parse_mode="HTML")
            os.unlink(tmp_file_path)
        else:
            bot.send_message(chat_id, report_msg, parse_mode="HTML")
    else:
        bot.send_message(chat_id, "✅ <b>لا توجد مخالفات مسجلة اليوم!</b>\n📢 <b>المجموعة نظيفة وآمنة!</b>", parse_mode="HTML")

def reset_daily_reports():
    global daily_reports
    daily_reports = {}
    save_reports()
    print("✅ تم تصفير التقارير اليومية.")
def check_day_change():
    global current_date
    while True:
        today = date.today().isoformat()
        if today != current_date:
            reset_daily_reports()
            current_date = today
        time.sleep(3600)
def run_bot_with_restart():
    while True:
        try:
            print("تشغيل البوت...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"حدث خطأ أثناء تشغيل البوت: {e}")
            print("rest")
            time.sleep(5)

load_violations()
load_reports()
threading.Thread(target=process_media_worker, daemon=True).start()

if __name__ == "__main__":
    threading.Thread(target=check_day_change, daemon=True).start()
    print("ok")
    run_bot_with_restart()
