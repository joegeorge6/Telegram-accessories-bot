import os
import re
import asyncio
from datetime import datetime, timezone
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from flask import Flask
from threading import Thread

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

RETAIL_CHANNEL = "@girlsfashionesta"

def convert_to_arabic_numbers(text):
    if not text: return ""
    western = "0123456789"
    arabic = "٠١٢٣٤٥٦٧٨٩"
    table = str.maketrans(western, arabic)
    return str(text).translate(table)

def parse_date(date_str, default_date):
    # إذا كانت الخانة فارغة، يستخدم التاريخ الافتراضي (الذي جعلناه 'الآن' في السطر التالي)
    if not date_str or date_str.strip() == "": return default_date
    if len(date_str.split('-')) == 2:
        date_str += f"-{datetime.now().year}"
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try: return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except: continue
    return default_date

# التعديل الذكي: لو START_DATE فارغ، ابدأ من 'الآن' (لحظة تشغيل البوت)
START_DATE = parse_date(os.environ.get("START_DATE", ""), datetime.now(timezone.utc))

def get_current_end_date():
    raw_end = os.environ.get("END_DATE", "")
    if not raw_end: return datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
    return parse_date(raw_end, datetime.now(timezone.utc)).replace(hour=23, minute=59, second=59)

raw_channels = os.environ.get("SOURCE_CHANNELS", "").split()
SOURCE_CHANNELS = [int(ch) if ch.startswith("-") else ch for ch in raw_channels]

RETAIL_MAPPING = { 
    15: 45, 20: 50, 25: 55, 30: 60, 35: 65, 40: 70, 45: 75, 50: 80, 55: 85, 60: 90, 65: 95, 70: 100, 75: 105, 80: 115, 85: 120, 90: 130, 95: 135, 100: 140, 105: 150, 110: 155, 115: 165, 120: 170, 125: 175, 130: 185, 135: 190, 140: 200, 145: 205, 150: 210, 155: 220, 160: 225, 165: 235, 170: 240, 175: 245, 180: 255, 185: 260, 190: 270, 195: 275, 200: 280, 205: 290, 210: 295, 215: 305, 220: 310, 225: 315, 230: 325, 235: 330, 240: 340, 245: 345, 250: 350, 255: 360, 260: 365, 265: 375, 270: 380, 275: 385, 280: 395, 285: 400, 290: 410, 295: 415, 300: 420, 305: 430, 310: 435, 315: 445, 320: 450, 325: 455, 330: 465, 335: 470, 340: 480, 345: 485, 350: 490, 355: 500, 360: 505, 365: 515, 370: 520, 375: 525, 380: 535, 385: 540, 390: 550, 395: 555, 400: 560, 405: 570, 410: 575, 415: 585, 420: 590, 425: 595, 430: 605, 435: 610, 440: 620, 445: 625, 450: 630, 455: 640, 460: 645, 465: 655, 470: 660, 475: 665, 480: 675, 485: 680, 490: 690, 495: 695, 500: 700, 505: 710, 510: 715, 515: 725, 520: 730, 525: 735, 530: 745, 535: 750, 540: 760, 545: 765, 550: 770, 555: 780, 560: 785, 565: 795, 570: 800, 575: 805, 580: 815, 585: 820, 590: 830, 595: 835, 600: 840, 605: 850, 610: 855, 615: 865, 620: 870, 625: 875, 630: 885, 635: 890, 640: 900, 645: 905, 650: 910, 655: 920, 660: 925, 665: 935, 670: 940, 675: 945, 680: 955, 685: 960, 690: 970, 695: 975, 700: 980, 705: 990, 710: 995, 715: 1005, 720: 1010, 725: 1015, 730: 1025, 735: 1030, 740: 1040, 745: 1045, 750: 1050, 755: 1060, 760: 1065, 765: 1075, 770: 1080, 775: 1085, 780: 1095, 785: 1100, 790: 1110, 795: 1115, 800: 1120, 805: 1130, 810: 1135, 815: 1145, 820: 1150, 825: 1155, 830: 1165, 835: 1170, 840: 1180, 845: 1185, 850: 1190, 855: 1200, 860: 1205, 865: 1215, 870: 1220, 875: 1225, 880: 1235, 885: 1240, 890: 1250, 895: 1255, 900: 1260, 905: 1270, 910: 1275, 915: 1285, 920: 1290, 925: 1295, 930: 1305, 935: 1310, 940: 1320, 945: 1325, 950: 1330, 955: 1340, 960: 1345, 965: 1355, 970: 1360, 975: 1365, 980: 1375, 985: 1380, 990: 1390, 995: 1395, 1000: 1400 
}

# ==========================================
# 2. الدوال المساعدة
# ==========================================
SUPPLIER_PREFIX_MAP = {"aymanelawamy123": "A", "sasaaccessories": "S", "ayselstore55": "AS", "miyokowatches22": "M", -1001132261086: "P", -1001448553593: "I", -1001682055192: "H"}
P_CHANNEL_TYPES = {"A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه", "C": "كوليه", "E": "حلق", "R": "خاتم", "B": "اسورة"}
REVIEW_KEYWORDS = ["ريفيو", "ريفيوهات", "آراء", "اراء", "رأي", "راي", "وصلنا", "تجربة", "تجربه", "تسلم", "شكرا", "شكرًا"]

last_saved_date = None
daily_post_counter = 0

def generate_my_code(source_channel_id, msg_date):
    global last_saved_date, daily_post_counter
    today_str = msg_date.strftime("%d%m")
    if last_saved_date != today_str:
        last_saved_date, daily_post_counter = today_str, 1
    else: daily_post_counter += 1
    prefix = SUPPLIER_PREFIX_MAP.get(source_channel_id, "UN")
    return f"{prefix}{daily_post_counter:02d}{today_str}"

def normalize_numbers(text):
    if not text: return ""
    return text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

def build_text(original_text, source_id, msg_date):
    prefix = SUPPLIER_PREFIX_MAP.get(source_id, "")
    my_code = generate_my_code(source_id, msg_date)
    if not original_text or original_text.strip() == "":
        if prefix == "P": return f"الكود : 🔖 {my_code}\nالسعر : 💰 ج 🔥"
        return None
    if any(word in original_text for word in REVIEW_KEYWORDS): return None
    processed_text = normalize_numbers(original_text)
    piece_type_name = ""
    if prefix == "P":
        type_match = re.search(r'([A-Z]+)\d+', processed_text, re.IGNORECASE)
        if type_match:
            code_letters = type_match.group(1).upper()
            piece_type_name = P_CHANNEL_TYPES.get(code_letters, "")
    norm_orig = normalize_numbers(original_text)
    found_price_val = None
    p_price_match = re.search(r'price\s*(\d+)', norm_orig, re.IGNORECASE)
    if p_price_match: found_price_val = int(p_price_match.group(1))
    if not found_price_val:
        nums = [int(n) for n in re.findall(r'(\d+)', norm_orig) if 10 <= int(n) <= 2000]
        if any(kw in processed_text for kw in ["بدل", "بكام", "بس", "عرض"]):
            if nums: found_price_val = min(nums)
        else:
            online_m = re.search(r'(?:اونلاين|online)\s*(\d+)', processed_text, re.IGNORECASE)
            if online_m: found_price_val = int(online_m.group(1))
            elif nums: found_price_val = nums[0]
    final_price_val = RETAIL_MAPPING.get(found_price_val, "")
    price_str_ar = convert_to_arabic_numbers(final_price_val)
    patterns = [r'.*(?:اونلاين|online).*', r'.*(?:سعر القطعه|القطعه بـ|price|بسعر|جمله|جملة).*', r'.*(?:بدل|بكام|عرض خاص|عرض|بس).*', r'.*(?:الكود|السعر|بسعر).*[:：].*', r'^[A-Z]+\d+.*', r'^[\W\s]*\d+[\W\s]*$']
    if prefix == "I": processed_text = re.sub(r'infinity', 'فاشونيستا', processed_text, flags=re.IGNORECASE)
    if prefix == "AS": processed_text = re.sub(r'ختم\s*AS', '', processed_text, flags=re.IGNORECASE)
    clean_lines = []
    for line in processed_text.split('\n'):
        line = line.strip()
        if not any(re.search(p, line, re.IGNORECASE) for p in patterns) and line: clean_lines.append(line)
    description = "\n".join(clean_lines)
    if prefix == "P":
        first_line = clean_lines[0] if clean_lines else ""
        if piece_type_name and piece_type_name in first_line: final_desc = description
        elif piece_type_name:
            if not description: final_desc = f"{piece_type_name} شيك قوي💕💕\nاستانلس بيور عيار ٣١٦ 💎💯\nلمسة شيك وجودة باينة من أول نظرة ✨️"
            else: final_desc = f"{piece_type_name}\n{description}"
        else: final_desc = description
        return f"{final_desc}\n\nالكود : 🔖 {my_code}\nبسعر : 💰 {price_str_ar} ج 🔥"
    return f"{description}\n\nالكود : 🔖 {my_code}\nالسعر : 💰 {price_str_ar} ج 🔥"

# ==========================================
# 3. نظام النشر المتطور واللحظي
# ==========================================
media_groups = {}
async def safe_send(func, *args, **kwargs):
    while True:
        try: return await func(*args, **kwargs)
        except FloodWait as e:
            print(f"⚠️ انتظار {e.value} ثانية...")
            await asyncio.sleep(e.value)
        except: break

async def send_to_targets(client, messages, source_id):
    main_msg = next((m for m in messages if (m.caption or m.text)), messages[0])
    msg_date = main_msg.date.replace(tzinfo=timezone.utc)
    retail_text = build_text(main_msg.caption or main_msg.text, source_id, msg_date)
    if not retail_text and SUPPLIER_PREFIX_MAP.get(source_id) != "P": return
    try:
        for m in messages:
            if m.photo: await safe_send(client.send_photo, RETAIL_CHANNEL, m.photo.file_id)
            elif m.video: await safe_send(client.send_video, RETAIL_CHANNEL, m.video.file_id)
            await asyncio.sleep(3) 
        if retail_text:
            await safe_send(client.send_message, RETAIL_CHANNEL, retail_text)
            await asyncio.sleep(4)
    except: pass

async def fetch_history(client):
    print(f"🔎 سحب الشغل من {START_DATE}...")
    current_limit = get_current_end_date()
    for channel in SOURCE_CHANNELS:
        all_messages = []
        async for msg in client.get_chat_history(channel):
            m_date = msg.date.replace(tzinfo=timezone.utc)
            if m_date < START_DATE: break
            if m_date > current_limit: continue
            all_messages.append(msg)
        all_messages.reverse()
        curr_gid, g_msgs = None, []
        for msg in all_messages:
            if msg.media_group_id:
                if msg.media_group_id == curr_gid: g_msgs.append(msg)
                else:
                    if g_msgs: await send_to_targets(client, g_msgs, channel)
                    g_msgs, curr_gid = [msg], msg.media_group_id
            else:
                if g_msgs: await send_to_targets(client, g_msgs, channel)
                g_msgs, curr_gid = [], None
                await send_to_targets(client, [msg], channel)
        if g_msgs: await send_to_targets(client, g_msgs, channel)

# ==========================================
# 4. تشغيل البوت
# ==========================================
app = Client("retail_v15", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message(filters.chat(SOURCE_CHANNELS) & ~filters.forwarded)
async def main_handler(client, message):
    if message.media_group_id:
        gid = message.media_group_id
        if gid not in media_groups:
            media_groups[gid] = []
            await asyncio.sleep(10)
            await send_to_targets(client, media_groups[gid], message.chat.id)
            del media_groups[gid]
        media_groups[gid].append(message)
    else:
        await send_to_targets(client, [message], message.chat.id)

web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Retail Pro Bot v15.0 Active!"

async def start_bot():
    await app.start()
    asyncio.create_task(fetch_history(app))
    await idle()

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host="0.0.0.0", port=8000)).start()
    app.run(start_bot())
