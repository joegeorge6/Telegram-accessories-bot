import os
import re
import asyncio 
from datetime import datetime, timezone
from pyrogram import Client, filters, idle
from flask import Flask
from threading import Thread

# ==========================================
# إعدادات المتغيرات البيئية
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "")

START_DATE_STR = os.environ.get("START_DATE", "2024-01-01")
def parse_date(date_str):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime(2024, 1, 1, tzinfo=timezone.utc)

START_DATE = parse_date(START_DATE_STR)

raw_channels = os.environ.get("SOURCE_CHANNELS", "").split()
SOURCE_CHANNELS = []
for ch in raw_channels:
    if ch.startswith("-"):
        try: SOURCE_CHANNELS.append(int(ch))
        except: SOURCE_CHANNELS.append(ch)
    else: SOURCE_CHANNELS.append(ch)

# ==========================================
# 1. جدول الأسعار (كامل)
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
# 2. نظام الترقيم والدوال
# ==========================================
last_saved_date = None
daily_post_counter = 0

SUPPLIER_PREFIX_MAP = {
    "aymanelawamy123": "A", "sasaaccessories": "S", "ayselstore55": "AS",
    "miyokowatches22": "M", -1001132261086: "P", -1001448553593: "I", -1001682055192: "H",
}

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

def build_final_text(original_text, source_channel_id):
    processed_text = normalize_numbers(original_text or "")
    text_lower = processed_text.lower()
    
    # استخراج النوع
    product_name = "قطعة"
    keywords = ["طقم", "سلسلة", "اسورة", "اسوره", "خاتم", "خواتم", "حلق", "حلقان", "كوليه", "خلخال", "بيرسينج", "بروش", "انسيال"]
    for word in keywords:
        if word in text_lower: product_name = word; break
    
    # السعر
    new_price = "حددنا لك"
    normal_match = re.search(r'(\d+)(\s*جنيه|\s*ج\.?|\s*ج)', processed_text)
    if normal_match:
        p = int(normal_match.group(1))
        new_price = str(PRICE_MAPPING.get(p, p + 30))

    my_new_code = generate_my_code(source_channel_id)
    
    return f"{product_name} قمر قوي💕\nاستانلس بيور عيار ٣١٦ 💎💯\nالكود : 🔖 {my_new_code}\nبسعر : 💰 {new_price} ج 🔥", my_new_code

# ==========================================
# 3. البوت والسحب
# ==========================================
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Bot is running!"

app = Client("session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

async def process_and_send(message):
    try:
        orig = message.caption or message.text or ""
        source = message.chat.username or message.chat.id
        final_text, code = build_final_text(orig, source)
        if message.photo:
            path = await message.download()
            await app.send_photo(TARGET_CHANNEL, path, caption=final_text)
            if os.path.exists(path): os.remove(path)
        elif message.text:
            await app.send_message(TARGET_CHANNEL, final_text)
        print(f"✅ تم النقل من {source} | الكود: {code}")
    except Exception as e: print(f"❌ خطأ نقل: {e}")

async def run_bot():
    await app.start()
    print(f"⏳ جاري سحب الشغل القديم من تاريخ {START_DATE}...")
    for chat_id in SOURCE_CHANNELS:
        print(f"📂 فحص القناة: {chat_id}")
        async for message in app.get_chat_history(chat_id, limit=30):
            if message.date >= START_DATE and not (message.forward_from_chat or message.forward_from):
                await process_and_send(message)
                await asyncio.sleep(1)
    print("✨ انتهى السحب القديم. البوت الآن يراقب الجديد.")
    
    @app.on_message(filters.chat(SOURCE_CHANNELS) & ~filters.forwarded)
    async def live_updates(client, message):
        print(f"📩 رسالة جديدة من {message.chat.id}")
        await process_and_send(message)
    
    await idle()

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host="0.0.0.0", port=8000)).start()
    asyncio.get_event_loop().run_until_complete(run_bot())
