import os
import re
import asyncio 
from datetime import datetime, timezone
from pyrogram import Client, filters
from flask import Flask
from threading import Thread

# ==========================================
# إعدادات المتغيرات البيئية
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "")

# إعداد تاريخ البدء (تنسيق: YYYY-MM-DD)
START_DATE_STR = os.environ.get("START_DATE", "2024-01-01")
try:
    START_DATE = datetime.strptime(START_DATE_STR, "%Y-%m-%d").replace(tzinfo=timezone.utc)
except:
    START_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)

# تحويل القنوات بطريقة آمنة
raw_channels = os.environ.get("SOURCE_CHANNELS", "").split()
SOURCE_CHANNELS = []
for ch in raw_channels:
    try:
        SOURCE_CHANNELS.append(int(ch))
    except ValueError:
        SOURCE_CHANNELS.append(ch)

# ==========================================
# 1. جدول الأسعار
# ==========================================
PRICE_MAPPING = {
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

# ==========================================
# 2. نظام الترقيم
# ==========================================
last_saved_date = None
daily_post_counter = 0

SUPPLIER_PREFIX_MAP = {
    "aymanelawamy123": "A",
    "sasaaccessories": "S",
    "ayselstore55": "AS",
    "miyokowatches22": "M",
    -1001132261086: "P",  
    -1001448553593: "I",  
    -1001682055192: "H",  
}

def generate_my_code(source_channel_id):
    global last_saved_date, daily_post_counter
    now = datetime.now()
    today_day = now.strftime("%d")
    today_month = now.strftime("%m")
    today_str = f"{today_day}{today_month}"
    
    if last_saved_date != today_str:
        last_saved_date = today_str
        daily_post_counter = 1  
    else:
        daily_post_counter += 1 
        
    prefix = SUPPLIER_PREFIX_MAP.get(source_channel_id, "UN")
    return f"{prefix}{daily_post_counter:02d}{today_day}{today_month}"

# ==========================================
# 3. المعالجة
# ==========================================
def normalize_numbers(text):
    arabic_numbers = "٠١٢٣٤٥٦٧٨٩"
    english_numbers = "0123456789"
    translation_table = str.maketrans(arabic_numbers, english_numbers)
    return text.translate(translation_table)

def extract_product_type(text, source_name):
    if not text: return "قطعة"
    text_lower = text.lower()
    if source_name == -1001132261086:
        p_match = re.search(r'\b(A|K|N|CP|E|R|B)\b', text, re.IGNORECASE)
        if p_match:
            p_map = {"A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه", "E": "حلق", "R": "خاتم", "B": "اسورة"}
            return p_map.get(p_match.group(1).upper(), "قطعة")
    keywords = ["طقم", "سلسلة", "اسورة", "اسوره", "خاتم", "خواتم", "حلق", "حلقان", "كوليه", "خلخال", "بيرسينج", "بروش", "انسيال"]
    for word in keywords:
        if word in text_lower: return word
    return "قطعة"

def get_ring_size_info(text):
    size_match = re.search(r'(مقاس(?:ات)?(?:\s+من)?\s+\d+\s*ل(?:ـ)?\s*\d+)', text)
    if size_match: return size_match.group(1) 
    if any(x in text for x in ["فري", "سايز", "مقاس واحد"]): return "فري سايز"
    return ""

def extract_and_modify_price(text, source_name):
    if not text: return "حددنا لك"
    clean_text = normalize_numbers(text)
    online_price_channels = ["sasaaccessories", -1001682055192, "miyokowatches22"]
    found_price = None
    if source_name in online_price_channels:
        online_match = re.search(r'(?:اونلاين|الاون لاين)[^\d]*(\d+)', clean_text)
        if online_match: found_price = int(online_match.group(1))
    if found_price is None:
        normal_match = re.search(r'(\d+)(\s*جنيه|\s*ج\.?|\s*ج)', clean_text)
        if normal_match: found_price = int(normal_match.group(1))
    if found_price:
        new_price = PRICE_MAPPING.get(found_price)
        return str(new_price) if new_price else str(found_price + 30)
    return "حددنا لك"

def build_final_text(original_text, source_channel_id):
    if not original_text: original_text = ""
    processed_text = normalize_numbers(original_text)
    text_lower = processed_text.lower()
    product_name = extract_product_type(processed_text, source_channel_id)
    size_info = get_ring_size_info(processed_text) if product_name in ["خاتم", "خواتم"] else ""
    product_size = f"{product_name} {size_info}" if size_info else product_name
    my_new_code = generate_my_code(source_channel_id)
    new_price = extract_and_modify_price(processed_text, source_channel_id)

    if "بيرسينج بول باك" in text_lower:
        final_text = f"بيرسينج بول باك شيك قوي💕💕\nعمود استانلس بيور عيار ٣١٦ 💎💯\nالكود : 🔖  {my_new_code}\nبسعر : 💰   {new_price}   ج  🔥"
    elif "استانلس" in text_lower or "استالنس" in text_lower:
        final_text = f"{product_size} قمر قوي💕\nاستانلس بيور عيار ٣١٦ 💎💯\nالكود : 🔖  {my_new_code}\nبسعر : 💰   {new_price}   ج  🔥"
    else:
        final_text = f"{product_size} مميز جداً ✨\nلو عايز تتميز دوس على الطلب 💎\nالكود : 🔖  {my_new_code}\nبسعر : 💰   {new_price}   ج  🔥"
    return final_text, my_new_code

# ==========================================
# 4. سيرفر الويب الوهمي
# ==========================================
web_app = Flask(__name__)
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) # تقليل رسائل السيرفر

@web_app.route('/')
def home(): return "Bot is running!"

def run_web():
    web_app.run(host="0.0.0.0", port=8000)

# ==========================================
# 5. تشغيل البوت
# ==========================================
# ملاحظة: تم تغيير المسار ليكون في الذاكرة تماماً لتجنب قفل القاعدة
app = Client(
    "auto_poster_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

async def forward_post(client, message):
    try:
        if message.date < START_DATE:
            return

        orig = message.caption or message.text or ""
        source_name = message.chat.username or message.chat.id
        final_text, code = build_final_text(orig, source_name)
        
        if message.photo:
            path = await message.download()
            await client.send_photo(TARGET_CHANNEL, path, caption=final_text)
            if os.path.exists(path): os.remove(path)
        elif message.video:
            path = await message.download()
            await client.send_video(TARGET_CHANNEL, path, caption=final_text)
            if os.path.exists(path): os.remove(path)
        elif message.text:
            await client.send_message(TARGET_CHANNEL, final_text)
        
        print(f"✅ تم النقل بنجاح | الكود: {code}")
            
    except Exception as e: 
        print(f"❌ خطأ أثناء النقل: {e}")

@app.on_message(filters.chat(SOURCE_CHANNELS))
async def new_post(client, message):
    source = message.chat.username or message.chat.id
    if message.forward_from_chat or message.forward_from:
         return
    print(f"📩 وصلت رسالة جديدة من: {source}")
    await asyncio.sleep(2)
    await forward_post(client, message)

if __name__ == "__main__":
    Thread(target=run_web).start()
    print("🚀 البوت يعمل الآن ويراقب القنوات...")
    print(f"📅 تاريخ البدء المعتمد: {START_DATE}")
    app.run()
