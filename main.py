import os
import re
import asyncio
from datetime import datetime, timezone
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from flask import Flask
from threading import Thread

# ==========================================
# 1. الإعدادات الأساسية والذاكرة
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

RETAIL_CHANNEL = "@girlsfashionesta"
DB_FILE = "processed_msgs.txt"

P_CODE_TRANSLATION = {
    "A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه", 
    "C": "كوليه", "E": "حلق", "R": "خاتم", "B": "اسورة"
}

# لتتبع المجموعات التي قيد المعالجة حالياً لمنع التكرار والقفز في العداد
processed_media_groups = set()

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

def convert_to_arabic_numbers(text):
    if not text: return ""
    western, arabic = "0123456789", "٠١٢٣٤٥٦٧٨٩"
    return str(text).translate(str.maketrans(western, arabic))

def normalize_numbers(text):
    if not text: return ""
    return text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

def parse_date(date_str, default_date, is_end=False):
    if not date_str or date_str.strip() == "": return default_date
    if len(date_str.split('-')) == 2: date_str += f"-{datetime.now().year}"
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if is_end: return dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            return dt.replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
        except: continue
    return default_date

START_DATE = parse_date(os.environ.get("START_DATE", ""), datetime.now(timezone.utc))
END_DATE_LIMIT = parse_date(os.environ.get("END_DATE", ""), None, is_end=True)

raw_channels = os.environ.get("SOURCE_CHANNELS", "").split()
SOURCE_CHANNELS = [int(ch) if ch.startswith("-") else ch for ch in raw_channels]

RETAIL_MAPPING = { 15: 45, 20: 50, 25: 55, 30: 60, 35: 65, 40: 70, 45: 75, 50: 80, 55: 85, 60: 90, 65: 95, 70: 100, 75: 105, 80: 115, 85: 120, 90: 130, 95: 135, 100: 140, 105: 150, 110: 155, 115: 165, 120: 170, 125: 175, 130: 185, 135: 190, 140: 200, 145: 205, 150: 210, 155: 220, 160: 225, 165: 235, 170: 240, 175: 245, 180: 255, 185: 260, 190: 270, 195: 275, 200: 280, 205: 290, 210: 295, 215: 305, 220: 310, 225: 315, 230: 325, 235: 330, 240: 340, 245: 345, 250: 350, 255: 360, 260: 365, 265: 375, 270: 380, 275: 385, 280: 395, 285: 400, 290: 410, 295: 415, 300: 420, 305: 430, 310: 435, 315: 445, 320: 450, 325: 455, 330: 465, 335: 470, 340: 480, 345: 485, 350: 490, 355: 500, 360: 505, 365: 515, 370: 520, 375: 525, 380: 535, 385: 540, 390: 550, 395: 555, 400: 560, 405: 570, 410: 575, 415: 585, 420: 590, 425: 595, 430: 605, 435: 610, 440: 620, 445: 625, 450: 630, 455: 640, 460: 645, 465: 655, 470: 660, 475: 665, 480: 675, 485: 680, 490: 690, 495: 695, 500: 700, 505: 710, 510: 715, 515: 725, 520: 730, 525: 735, 530: 745, 535: 750, 540: 760, 545: 765, 550: 770, 555: 780, 560: 785, 565: 795, 570: 800, 575: 805, 580: 815, 585: 820, 590: 830, 595: 835, 600: 840, 605: 850, 610: 855, 615: 865, 620: 870, 625: 875, 630: 885, 635: 890, 640: 900, 645: 905, 650: 910, 655: 920, 660: 925, 665: 935, 670: 940, 675: 945, 680: 955, 685: 960, 690: 970, 695: 975, 700: 980, 705: 990, 710: 995, 715: 1005, 720: 1010, 725: 1015, 730: 1025, 735: 1030, 740: 1040, 745: 1045, 750: 1050, 755: 1060, 760: 1065, 765: 1075, 770: 1080, 775: 1085, 780: 1095, 785: 1100, 790: 1110, 795: 1115, 800: 1120, 805: 1130, 810: 1135, 815: 1145, 820: 1150, 825: 1155, 830: 1165, 835: 1170, 840: 1180, 845: 1185, 850: 1190, 855: 1200, 860: 1205, 865: 1215, 870: 1220, 875: 1225, 880: 1235, 885: 1240, 890: 1250, 895: 1255, 900: 1260, 905: 1270, 910: 1275, 915: 1285, 920: 1290, 925: 1295, 930: 1305, 935: 1310, 940: 1320, 945: 1325, 950: 1330, 955: 1340, 960: 1345, 965: 1355, 970: 1360, 975: 1365, 980: 1375, 985: 1380, 990: 1390, 995: 1395, 1000: 1400 }

# ==========================================
# 2. المنطق والذاكرة
# ==========================================
SUPPLIER_PREFIX_MAP = {"aymanelawamy123": "A", "sasaaccessories": "S", "ayselstore55": "AS", "miyokowatches22": "M", -1001132261086: "P", -1001448553593: "I", -1001682055192: "H"}
AD_KEYWORDS = ["شركه PR", "شركة PR", "النزهه الجديده", "رقم الحجز", "pribore", "بيجامتك", "01012050836", "للتواصل لطلبات الجمله", "عبدالرحمن", "01505530190"]
REVIEW_KEYWORDS = ["ريفيو", "ريفيوهات", "آراء", "اراء", "رأي", "راي", "وصلنا", "تجربة", "تسلم", "شكرا"]

channel_counters = {}

def is_msg_processed(msg_id):
    if not os.path.exists(DB_FILE): return False
    with open(DB_FILE, "r") as f: return str(msg_id) in f.read().splitlines()

def mark_msg_as_processed(msg_id):
    with open(DB_FILE, "a") as f: f.write(str(msg_id) + "\n")

def increment_counter(source_id, today_str):
    global channel_counters
    counter_key = f"{source_id}_{today_str}"
    channel_counters[counter_key] = channel_counters.get(counter_key, 0) + 1

def generate_my_code(source_channel_id, msg_date):
    today_str = msg_date.strftime("%d%m")
    counter_key = f"{source_channel_id}_{today_str}"
    current_num = channel_counters.get(counter_key, 0) + 1
    prefix = SUPPLIER_PREFIX_MAP.get(source_channel_id, "UN")
    return f"{prefix}{current_num:02d}{today_str}"

def extract_real_price(text):
    if not text: return None
    norm_text = normalize_numbers(text)
    clean_for_search = re.sub(r'\d+\s*(?:سم|س|M|CM|ملي|متر|شكل|لون|ق)', '', norm_text, flags=re.IGNORECASE)
    price_match = re.search(r'(?:أونلاين|اونلاين|online|سعر القطعه|سعر القطعة|قطعه|قطعة|اقل من دسته|اقل من دستة|بسعر|السعر|سعر|price|L\.E|LE)\s*[:：]?\s*(\d+)', clean_for_search, re.IGNORECASE)
    if price_match: return int(price_match.group(1))
    wholesale_match = re.search(r'(?:الجمله|الجملة|جمله|جملة)\s*[:：]?\s*(\d+)', clean_for_search, re.IGNORECASE)
    if wholesale_match: return int(wholesale_match.group(1))
    price_match_rev = re.search(r'(\d+)\s*[:：]?\s*(?:ج|L\.E|LE|egp|جنيه)', clean_for_search, re.IGNORECASE)
    if price_match_rev: return int(price_match_rev.group(1))
    nums = [int(n) for n in re.findall(r'(\d+)', clean_for_search) if 15 <= int(n) <= 2000]
    return nums[-1] if nums else None

def build_text(original_text, source_id, msg_date):
    if not original_text: return ""
    norm_text = normalize_numbers(original_text)
    if any(word in norm_text for word in AD_KEYWORDS): return None
    if any(word in norm_text for word in REVIEW_KEYWORDS): return None
    
    found_price_val = extract_real_price(original_text)
    final_price_val = RETAIL_MAPPING.get(found_price_val, "")
    price_str_ar = convert_to_arabic_numbers(final_price_val)
    
    original_code_prefix = ""
    code_match = re.search(r'([A-Z]+)\d+', norm_text, re.IGNORECASE)
    if code_match: original_code_prefix = code_match.group(1).upper()

    cleaned_lines = []
    for line in norm_text.split('\n'):
        line = line.strip()
        if not line: continue
        if re.match(r'^[A-Z]+\d+.*$', line, re.IGNORECASE) or re.match(r'^\d+\s*[:：]?\s*(?:ج|LE|L\.E|السعر).*$', line, re.IGNORECASE):
            continue
        patterns_to_delete = [r'.*(?:جمله|جملة|دسته|دستة).*', r'.*(?:سعر العلبه|سعر العلبة).*', r'.*(?:اختيار).*']
        if any(re.search(p, line, re.IGNORECASE) for p in patterns_to_delete): continue
        line = re.sub(r'(?:السعر|سعر|price|بسعر|قطعه|قطعة|أونلاين|اونلاين|online|اقل من).*', '', line, flags=re.IGNORECASE).strip()
        line = re.sub(r'[:：]?\s*\d+\s*(?:ج|LE|L\.E|egp|جنيه).*', '', line, flags=re.IGNORECASE).strip()
        if line: cleaned_lines.append(line)

    description = "\n".join(cleaned_lines)
    has_description = any(c.isalpha() or '\u0600' <= c <= '\u06FF' for c in description)

    if not has_description and original_code_prefix in P_CODE_TRANSLATION:
        item_name = P_CODE_TRANSLATION[original_code_prefix]
        description = f"{item_name} شيك قوي💕💕\nاستانلس بيور عيار ٣١٦ 💎💯\nلمسة شيك وجودة باينة من أول نظرة ✨️"

    my_code = generate_my_code(source_id, msg_date)
    return f"{description}\n\nالكود : 🔖 {my_code}\nالسعر : 💰 {price_str_ar} ج 🔥"

# ==========================================
# 3. نظام النشر المتطور
# ==========================================
async def safe_send(client, messages, source_id):
    if not messages or is_msg_processed(messages[0].id): return
    valid_messages = [m for m in messages if not m.poll]
    if not valid_messages: return
    
    main_msg = next((m for m in valid_messages if (m.caption or m.text)), valid_messages[0])
    msg_date = main_msg.date.replace(tzinfo=timezone.utc)
    if END_DATE_LIMIT and msg_date > END_DATE_LIMIT: return

    raw_caption = main_msg.caption or main_msg.text
    retail_text = build_text(raw_caption, source_id, msg_date)
    if retail_text is None: return
    
    try:
        for m in valid_messages:
            if m.photo: await client.send_photo(RETAIL_CHANNEL, m.photo.file_id)
            elif m.video: await client.send_video(RETAIL_CHANNEL, m.video.file_id)
            elif m.animation: await client.send_animation(RETAIL_CHANNEL, m.animation.file_id)
            await asyncio.sleep(2) 
        
        if retail_text != "": 
            await client.send_message(RETAIL_CHANNEL, retail_text)
            # الزيادة الحقيقية للعداد تحدث هنا فقط بعد نجاح الإرسال
            if raw_caption:
                increment_counter(source_id, msg_date.strftime("%d%m"))
        
        mark_msg_as_processed(messages[0].id)
        await asyncio.sleep(3)
    except FloodWait as e: await asyncio.sleep(e.value)
    except: pass

async def fetch_history(client):
    for channel in SOURCE_CHANNELS:
        all_items, group_processed = [], set()
        async for msg in client.get_chat_history(channel, limit=300):
            m_date = msg.date.replace(tzinfo=timezone.utc)
            if m_date < START_DATE: break
            if (END_DATE_LIMIT and m_date > END_DATE_LIMIT) or is_msg_processed(msg.id): continue
            
            if msg.media_group_id:
                if msg.media_group_id in group_processed: continue
                group_processed.add(msg.media_group_id)
                all_items.append(await client.get_media_group(channel, msg.id))
            else: all_items.append([msg])

        all_items.reverse()
        for item in all_items: await safe_send(client, item, channel)

# ==========================================
# 4. تشغيل البوت
# ==========================================
app = Client("retail_v21", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message(filters.chat(SOURCE_CHANNELS))
async def main_handler(client, message):
    if message.poll or is_msg_processed(message.id): return 
    
    # حماية الألبومات من التكرار اللحظي
    if message.media_group_id:
        if message.media_group_id in processed_media_groups: return
        processed_media_groups.add(message.media_group_id)
        try:
            msgs = await client.get_media_group(message.chat.id, message.id)
            await safe_send(client, msgs, message.chat.id)
        except: pass
    else: await safe_send(client, [message], message.chat.id)

web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Retail Pro Bot v21.9 Active!"

async def start_bot():
    await app.start()
    asyncio.create_task(fetch_history(app))
    await idle()

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host="0.0.0.0", port=8000)).start()
    app.run(start_bot())
