import os
import re
import asyncio
import sqlite3
from datetime import datetime, timezone
from pyrogram import Client, filters, idle
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from flask import Flask
from threading import Thread

# ==========================================
# 1. الإعدادات وقاعدة البيانات
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

RETAIL_CHANNEL = "@girlsfashionesta"
WHOLESALE_CHANNEL = "@Far_sha1"

# قاعدة بيانات للربط بين رسائل القناتين (للتعديل والحذف التلقائي)
db = sqlite3.connect("msg_map.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS mapping (retail_id INTEGER PRIMARY KEY, wholesale_id INTEGER)")
db.commit()

raw_channels = os.environ.get("SOURCE_CHANNELS", "").split()
SOURCE_CHANNELS = [int(ch) if ch.startswith("-") else ch for ch in raw_channels]

# ==========================================
# 2. جداول الأسعار (حرفياً كما أرسلتها)
# ==========================================
RETAIL_MAPPING = {
    25: 55, 30: 60, 35: 65, 40: 70, 45: 75, 50: 80, 55: 85, 60: 90, 65: 95, 70: 100,
    75: 105, 80: 115, 85: 120, 90: 130, 95: 135, 100: 140, 105: 150, 110: 155, 115: 165, 120: 170,
    125: 175, 130: 185, 135: 190, 140: 200, 145: 205, 150: 210, 155: 220, 160: 225, 165: 235, 170: 240,
    175: 245, 180: 255, 185: 260, 190: 270, 195: 275, 200: 280, 205: 290, 210: 295, 215: 305, 220: 310,
    225: 315, 230: 325, 235: 330, 240: 340, 245: 345, 250: 350, 255: 360, 260: 365, 265: 375, 270: 380,
    275: 385, 280: 395, 285: 400, 290: 410, 295: 415, 300: 420, 305: 430, 310: 435, 315: 445, 320: 450,
    325: 455, 330: 465, 335: 470, 340: 480, 345: 485, 350: 490, 355: 500, 360: 505, 365: 515, 370: 520,
    375: 525, 380: 535, 385: 540, 390: 550, 395: 555, 400: 560, 405: 570, 410: 575, 415: 585, 420: 590,
    425: 595, 430: 605, 435: 610, 440: 620, 445: 625, 450: 630, 455: 640, 460: 645, 465: 655, 470: 660,
    475: 665, 480: 675, 485: 680, 490: 690, 495: 695, 500: 700, 505: 710, 510: 715, 515: 725, 520: 730,
    525: 735, 530: 745, 535: 750, 540: 760, 545: 765, 550: 770, 555: 780, 560: 785, 565: 795, 570: 800,
    575: 805, 580: 815, 585: 820, 590: 830, 595: 835, 600: 840, 605: 850, 610: 855, 615: 865, 620: 870,
    625: 875, 630: 885, 635: 890, 640: 900, 645: 905, 650: 910, 655: 920, 660: 925, 665: 935, 670: 940,
    675: 945, 680: 955, 685: 960, 690: 970, 695: 975, 700: 980, 705: 990, 710: 995, 715: 1005, 720: 1010,
    725: 1015, 730: 1025, 735: 1030, 740: 1040, 745: 1045, 750: 1050, 755: 1060, 760: 1065, 765: 1075, 770: 1080,
    775: 1085, 780: 1095, 785: 1100, 790: 1110, 795: 1115, 800: 1120, 805: 1130, 810: 1135, 815: 1145, 820: 1150,
    825: 1155, 830: 1165, 835: 1170, 840: 1180, 845: 1185, 850: 1190, 855: 1200, 860: 1205, 865: 1215, 870: 1220,
    875: 1225, 880: 1235, 885: 1240, 890: 1250, 895: 1255, 900: 1260, 905: 1270, 910: 1275, 915: 1285, 920: 1290,
    925: 1295, 930: 1305, 935: 1310, 940: 1320, 945: 1325, 950: 1330, 955: 1340, 960: 1345, 965: 1355, 970: 1360,
    975: 1365, 980: 1375, 985: 1380, 990: 1390, 995: 1395, 1000: 1400,
}

WHOLESALE_MAPPING = {
    25: 45, 30: 50, 35: 55, 40: 60, 45: 65, 50: 70, 55: 75, 60: 80, 65: 85, 70: 90,
    75: 95, 80: 100, 85: 105, 90: 110, 95: 115, 100: 120, 105: 130, 110: 135, 115: 140, 120: 145,
    125: 150, 130: 160, 135: 165, 140: 170, 145: 175, 150: 180, 155: 190, 160: 195, 165: 200, 170: 205,
    175: 210, 180: 220, 185: 225, 190: 230, 195: 235, 200: 240, 205: 250, 210: 255, 215: 260, 220: 265,
    225: 275, 230: 280, 235: 285, 240: 290, 245: 295, 250: 300, 255: 310, 260: 315, 265: 320, 270: 325,
    275: 330, 280: 340, 285: 345, 290: 350, 295: 355, 300: 360, 305: 370, 310: 375, 315: 380, 320: 385,
    325: 390, 330: 400, 335: 405, 340: 410, 345: 415, 350: 420, 355: 430, 360: 435, 365: 440, 370: 445,
    375: 450, 380: 460, 385: 465, 390: 470, 395: 475, 400: 480, 405: 490, 410: 495, 415: 500, 420: 505,
    425: 510, 430: 520, 435: 535, 440: 530, 445: 535, 450: 540, 455: 550, 460: 555, 465: 560, 470: 565,
    475: 570, 480: 580, 485: 585, 490: 590, 495: 595, 500: 600, 505: 610, 510: 615, 515: 620, 520: 625,
    525: 630, 530: 640, 535: 645, 540: 650, 545: 655, 550: 660, 555: 670, 560: 675, 565: 680, 570: 685,
    575: 690, 580: 700, 585: 705, 590: 710, 595: 715, 600: 720, 605: 730, 610: 735, 615: 740, 620: 745,
    625: 750, 630: 760, 635: 765, 640: 770, 645: 775, 650: 780, 655: 790, 660: 795, 665: 800, 670: 805,
    675: 810, 680: 820, 685: 825, 690: 830, 695: 835, 700: 840, 705: 850, 710: 855, 715: 860, 720: 865,
    725: 870, 730: 880, 735: 885, 740: 890, 745: 895, 750: 900, 755: 910, 760: 915, 765: 920, 770: 925,
    775: 930, 780: 940, 785: 945, 790: 950, 795: 955, 800: 960, 805: 970, 810: 975, 815: 980, 820: 985,
    825: 990, 830: 1000, 835: 1005, 840: 1010, 845: 1015, 850: 1020, 855: 1030, 860: 1035, 865: 1040, 870: 1045,
    875: 1050, 880: 1060, 885: 1065, 890: 1070, 895: 1075, 900: 1080, 905: 1090, 910: 1095, 915: 1100, 920: 1105,
    925: 1110, 930: 1120, 935: 1125, 940: 1130, 945: 1135, 950: 1140, 955: 1150, 960: 1155, 965: 1160, 970: 1165,
    975: 1170, 980: 1180, 985: 1185, 990: 1190, 995: 1195, 1000: 1200,
}

# ==========================================
# 3. الدوال المساعدة ونظام الترقيم
# ==========================================
SUPPLIER_PREFIX_MAP = {"aymanelawamy123": "A", "sasaaccessories": "S", "ayselstore55": "AS", "miyokowatches22": "M", -1001132261086: "P", -1001448553593: "I", -1001682055192: "H"}
P_CHANNEL_TYPES = {"A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه", "E": "حلق", "R": "خاتم", "B": "اسورة"}
REVIEW_KEYWORDS = ["ريفيو", "ريفيوهات", "آراء", "اراء", "رأي", "راي", "وصلنا", "تجربة", "تجربه", "تسلم", "شكرا", "شكرًا"]

last_saved_date = None
daily_post_counter = 0

def generate_my_code(source_channel_id):
    global last_saved_date, daily_post_counter
    now = datetime.now()
    today_str = now.strftime("%d%m")
    if last_saved_date != today_str:
        last_saved_date = today_str
        daily_post_counter = 1
    else: daily_post_counter += 1
    prefix = SUPPLIER_PREFIX_MAP.get(source_channel_id, "UN")
    return f"{prefix}{daily_post_counter:02d}{today_str}"

def normalize_numbers(text):
    return text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

def build_text(original_text, source_id, is_wholesale=False):
    if not original_text: return ""
    if any(word in original_text for word in REVIEW_KEYWORDS): return None
    processed_text = normalize_numbers(original_text)
    prefix = SUPPLIER_PREFIX_MAP.get(source_id, "")
    
    # القناة P
    if prefix == "P":
        p_match = re.search(r'^([A-Z]+)\d+\s+price\s+\d+', processed_text, re.IGNORECASE)
        if p_match:
            code_letter = p_match.group(1).upper()
            product_from_code = P_CHANNEL_TYPES.get(code_letter, "قطعة")
            processed_text = re.sub(r'^[A-Z]+\d+\s+price\s+\d+', '', processed_text, flags=re.IGNORECASE).strip()
            if not processed_text:
                processed_text = f"{product_from_code} قمر قوي💕\nاستانلس بيور عيار ٣١٦ 💎💯\nلمسة شيك وجودة باينة من أول نظرة ✨"

    if prefix == "I": processed_text = re.sub(r'infinity', 'فاشونيستا', processed_text, flags=re.IGNORECASE)
    if prefix == "AS": processed_text = re.sub(r'ختم\s*AS', '', processed_text, flags=re.IGNORECASE)

    # استخراج السعر الجديد
    mapping = WHOLESALE_MAPPING if is_wholesale else RETAIL_MAPPING
    found_numbers = [int(n) for n in re.findall(r'(\d+)', original_text) if 10 <= int(n) <= 2000]
    found_price_val = None
    online_match = re.search(r'(?:اونلاين|online)\s*(\d+)', processed_text, re.IGNORECASE)
    offer_match = re.search(r'عرض\s*(\d+)', processed_text, re.IGNORECASE)
    
    if online_match: found_price_val = int(online_match.group(1))
    elif offer_match: found_price_val = int(offer_match.group(1))
    elif any(x in processed_text for x in ["بدل", "عرض خاص", "بس"]):
        if found_numbers: found_price_val = min(found_numbers)
    else:
        any_p_match = re.search(r'(\d+)\s*(?:جنيه|ج)', processed_text)
        if any_p_match: found_price_val = int(any_p_match.group(1))
        elif found_numbers: found_price_val = found_numbers[0]

    new_price = str(mapping.get(found_price_val, "سعر غير مسجل"))
    
    # تنظيف النص
    patterns = [r'.*(?:اونلاين|online).*', r'.*(?:سعر القطعه|القطعه بـ|price|بسعر|جمله).*', r'.*(?:بدل|عرض خاص|عرض).*', r'^\d+\s*(?:ج|جنيه)?\s*$']
    clean_lines = [l.strip() for l in processed_text.split('\n') if not any(re.search(p, l, re.IGNORECASE) for p in patterns) and l.strip()]
    
    final_clean_text = "\n".join(clean_lines)
    code = generate_my_code(source_id)
    return f"{final_clean_text}\n\nالكود : 🔖 {code}\nالسعر ({'جملة' if is_wholesale else 'قطاعي'}) : 💰 {new_price} ج 🔥"

# ==========================================
# 4. نظام الميديا والنشر (المزامنة)
# ==========================================
media_groups = {} 

async def process_album(client, media_group_id):
    await asyncio.sleep(2)
    if media_group_id not in media_groups: return
    messages = media_groups.pop(media_group_id)
    main_msg = next((m for m in messages if m.caption), messages[0])
    source = main_msg.chat.username or main_msg.chat.id
    
    r_text = build_text(main_msg.caption, source, False)
    if r_text is None: return
    w_text = build_text(main_msg.caption, source, True)
    
    retail_media = [InputMediaPhoto(m.photo.file_id) if m.photo else InputMediaVideo(m.video.file_id) for m in messages]
    wholesale_media = [InputMediaPhoto(m.photo.file_id) if m.photo else InputMediaVideo(m.video.file_id) for m in messages]
    
    try:
        await client.send_media_group(RETAIL_CHANNEL, retail_media)
        await client.send_media_group(WHOLESALE_CHANNEL, wholesale_media)
        r_msg = await client.send_message(RETAIL_CHANNEL, r_text)
        w_msg = await client.send_message(WHOLESALE_CHANNEL, w_text)
        cursor.execute("INSERT INTO mapping VALUES (?, ?)", (r_msg.id, w_msg.id))
        db.commit()
    except Exception as e: print(f"Error: {e}")

# ==========================================
# 5. تشغيل البوت ومعالجة الرسائل
# ==========================================
app = Client("session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message(filters.chat(SOURCE_CHANNELS) & ~filters.forwarded)
async def main_handler(client, message):
    if message.media_group_id:
        if message.media_group_id not in media_groups:
            media_groups[message.media_group_id] = [message]
            asyncio.create_task(process_album(client, message.media_group_id))
        else: media_groups[message.media_group_id].append(message)
    else:
        try:
            source = message.chat.username or message.chat.id
            r_text = build_text(message.caption or message.text, source, False)
            if r_text is None: return
            w_text = build_text(message.caption or message.text, source, True)
            
            if message.photo:
                await client.send_photo(RETAIL_CHANNEL, message.photo.file_id)
                await client.send_photo(WHOLESALE_CHANNEL, message.photo.file_id)
            elif message.video:
                await client.send_video(RETAIL_CHANNEL, message.video.file_id)
                await client.send_video(WHOLESALE_CHANNEL, message.video.file_id)
            elif message.animation:
                await client.send_animation(RETAIL_CHANNEL, message.animation.file_id)
                await client.send_animation(WHOLESALE_CHANNEL, message.animation.file_id)
            
            r_msg = await client.send_message(RETAIL_CHANNEL, r_text)
            w_msg = await client.send_message(WHOLESALE_CHANNEL, w_text)
            cursor.execute("INSERT INTO mapping VALUES (?, ?)", (r_msg.id, w_msg.id))
            db.commit()
        except: pass

@app.on_edited_message(filters.chat(RETAIL_CHANNEL))
async def edit_handler(client, message):
    cursor.execute("SELECT wholesale_id FROM mapping WHERE retail_id = ?", (message.id,))
    res = cursor.fetchone()
    if res:
        new_w_text = message.text.replace("قطاعي", "جملة").replace("(قطاعي)", "(جملة)")
        await client.edit_message_text(WHOLESALE_CHANNEL, res[0], new_w_text)

@app.on_deleted_messages(filters.chat(RETAIL_CHANNEL))
async def delete_handler(client, messages):
    for msg in messages:
        cursor.execute("SELECT wholesale_id FROM mapping WHERE retail_id = ?", (msg.id,))
        res = cursor.fetchone()
        if res:
            await client.delete_messages(WHOLESALE_CHANNEL, res[0])
            cursor.execute("DELETE FROM mapping WHERE retail_id = ?", (msg.id,))
    db.commit()

web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Final Pro Bot is Live!"

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host="0.0.0.0", port=8000)).start()
    app.run()
