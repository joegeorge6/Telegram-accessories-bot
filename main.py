import os
import re
import asyncio
from datetime import datetime, timezone
from pyrogram import Client, filters, idle
from flask import Flask
from threading import Thread

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

RETAIL_CHANNEL = "@girlsfashionesta"

def parse_date(date_str, default_date):
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try: return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except: continue
    return default_date

START_DATE = parse_date(os.environ.get("START_DATE", ""), datetime(2026, 4, 10, tzinfo=timezone.utc))
raw_end_date = parse_date(os.environ.get("END_DATE", ""), datetime.now(timezone.utc))
END_DATE = raw_end_date.replace(hour=23, minute=59, second=59)

raw_channels = os.environ.get("SOURCE_CHANNELS", "").split()
SOURCE_CHANNELS = [int(ch) if ch.startswith("-") else ch for ch in raw_channels]

RETAIL_MAPPING = { 25: 55, 30: 60, 35: 65, 40: 70, 45: 75, 50: 80, 55: 85, 60: 90, 65: 95, 70: 100, 75: 105, 80: 115, 85: 120, 90: 130, 95: 135, 100: 140, 105: 150, 110: 155, 115: 165, 120: 170, 125: 175, 130: 185, 135: 190, 140: 200, 145: 205, 150: 210, 155: 220, 160: 225, 165: 235, 170: 240, 175: 245, 180: 255, 185: 260, 190: 270, 195: 275, 200: 280, 205: 290, 210: 295, 215: 305, 220: 310, 225: 315, 230: 325, 235: 330, 240: 340, 245: 345, 250: 350, 255: 360, 260: 365, 265: 375, 270: 380, 275: 385, 280: 395, 285: 400, 290: 410, 295: 415, 300: 420, 305: 430, 310: 435, 315: 445, 320: 450, 325: 455, 330: 465, 335: 470, 340: 480, 345: 485, 350: 490, 355: 500, 360: 505, 365: 515, 370: 520, 375: 525, 380: 535, 385: 540, 390: 550, 395: 555, 400: 560, 405: 570, 410: 575, 415: 585, 420: 590, 425: 595, 430: 605, 435: 610, 440: 620, 445: 625, 450: 630, 455: 640, 460: 645, 465: 655, 470: 660, 475: 665, 480: 675, 485: 680, 490: 690, 495: 695, 500: 700, 505: 710, 510: 715, 515: 725, 520: 730, 525: 735, 530: 745, 535: 750, 540: 760, 545: 765, 550: 770, 555: 780, 560: 785, 565: 795, 570: 800, 575: 805, 580: 815, 585: 820, 590: 830, 595: 835, 600: 840, 605: 850, 610: 855, 615: 865, 620: 870, 625: 875, 630: 885, 635: 890, 640: 900, 645: 905, 650: 910, 655: 920, 660: 925, 665: 935, 670: 940, 675: 945, 680: 955, 685: 960, 690: 970, 695: 975, 700: 980, 705: 990, 710: 995, 715: 1005, 720: 1010, 725: 1015, 730: 1025, 735: 1030, 740: 1040, 745: 1045, 750: 1050, 755: 1060, 760: 1065, 765: 1075, 770: 1080, 775: 1085, 780: 1095, 785: 1100, 790: 1110, 795: 1115, 800: 1120, 805: 1130, 810: 1135, 815: 1145, 820: 1150, 825: 1155, 830: 1165, 835: 1170, 840: 1180, 845: 1185, 850: 1190, 855: 1200, 860: 1205, 865: 1215, 870: 1220, 875: 1225, 880: 1235, 885: 1240, 890: 1250, 895: 1255, 900: 1260, 905: 1270, 910: 1275, 915: 1285, 920: 1290, 925: 1295, 930: 1305, 935: 1310, 940: 1320, 945: 1325, 950: 1330, 955: 1340, 960: 1345, 965: 1355, 970: 1360, 975: 1365, 980: 1375, 985: 1380, 990: 1390, 995: 1395, 1000: 1400 }

# ==========================================
# 2. الدوال المساعدة
# ==========================================
SUPPLIER_PREFIX_MAP = {"aymanelawamy123": "A", "sasaaccessories": "S", "ayselstore55": "AS", "miyokowatches22": "M", -1001132261086: "P", -1001448553593: "I", -1001682055192: "H"}
P_CHANNEL_TYPES = {"A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه", "C": "كوليه", "E": "حلق", "R": "خاتم", "B": "اسورة"}
REVIEW_KEYWORDS = ["ريفيو", "ريفيوهات", "آراء", "اراء", "رأي", "راي", "وصلنا", "تجربة", "تجربه", "تسلم", "شكرا", "شكرًا"]

last_saved_date = None
daily_post_counter = 0

# تعديل: استخدام تاريخ المنشور الأصلي في الكود
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
    if not original_text: return ""
    if any(word in original_text for word in REVIEW_KEYWORDS): return None
    processed_text = normalize_numbers(original_text)
    prefix = SUPPLIER_PREFIX_MAP.get(source_id, "")
    
    # القناة P - استخراج السعر بذكاء
    if prefix == "P":
        p_match = re.search(r'^([A-Z]+)\d+\s+price\s+(\d+)', processed_text, re.IGNORECASE)
        if p_match:
            code_letter = p_match.group(1).upper()
            prod_name = P_CHANNEL_TYPES.get(code_letter, "قطعة")
            processed_text = re.sub(r'^[A-Z]+\d+\s+price\s+\d+', '', processed_text, flags=re.IGNORECASE).strip()
            if not processed_text:
                processed_text = f"{prod_name} قمر قوي💕\nاستانلس بيور عيار ٣١٦ 💎💯\nلمسة شيك وجودة باينة من أول نظرة ✨"

    if prefix == "I": processed_text = re.sub(r'infinity', 'فاشونيستا', processed_text, flags=re.IGNORECASE)
    if prefix == "AS": processed_text = re.sub(r'ختم\s*AS', '', processed_text, flags=re.IGNORECASE)

    # استخراج السعر الأقل
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
    price_str = f"{final_price_val} ج" if final_price_val else ""
    
    # تنظيف شامل للأكواد وجمل العروض مع الإيموجي
    patterns = [
        r'.*(?:اونلاين|online).*', 
        r'.*(?:سعر القطعه|القطعه بـ|price|بسعر|جمله|جملة).*', 
        r'.*(?:بدل|بكام|عرض خاص|عرض|بس).*', 
        r'^[A-Z]+\d+.*', # مسح الأكواد مثل Cp2756 في بداية السطر
        r'^\d+\s*(?:ج|جنيه)?\s*$'
    ]
    
    clean_lines = []
    for line in processed_text.split('\n'):
        if not any(re.search(p, line, re.IGNORECASE) for p in patterns) and line.strip():
            clean_lines.append(line.strip())
            
    final_text = "\n".join(clean_lines)
    my_code = generate_my_code(source_id, msg_date)
    return f"{final_text}\n\nالكود : 🔖 {my_code}\nالسعر : 💰 {price_str} 🔥"

# ==========================================
# 3. نظام النشر والسحب التاريخي
# ==========================================
async def send_to_targets(client, messages, source_id):
    main_msg = next((m for m in messages if m.caption), messages[0])
    msg_date = main_msg.date.replace(tzinfo=timezone.utc)
    retail_text = build_text(main_msg.caption or main_msg.text, source_id, msg_date)
    if retail_text is None: return
    
    try:
        for m in messages:
            if m.photo: await client.send_photo(RETAIL_CHANNEL, m.photo.file_id)
            elif m.video: await client.send_video(RETAIL_CHANNEL, m.video.file_id)
        await client.send_message(RETAIL_CHANNEL, retail_text)
    except Exception as e: print(f"Publish Error: {e}")

async def fetch_history(client):
    print(f"🔎 سحب القطاعي من {START_DATE} إلى {END_DATE}")
    for channel in SOURCE_CHANNELS:
        all_messages = []
        async for msg in client.get_chat_history(channel):
            msg_date = msg.date.replace(tzinfo=timezone.utc)
            if msg_date < START_DATE: break
            if msg_date > END_DATE: continue
            all_messages.append(msg)
        
        all_messages.reverse()
        current_group_id, group_msgs = None, []
        for msg in all_messages:
            if msg.media_group_id:
                if msg.media_group_id == current_group_id: group_msgs.append(msg)
                else:
                    if group_msgs: await send_to_targets(client, group_msgs, channel)
                    group_msgs, current_group_id = [msg], msg.media_group_id
            else:
                if group_msgs: await send_to_targets(client, group_msgs, channel)
                group_msgs, current_group_id = [], None
                await send_to_targets(client, [msg], channel)
        if group_msgs: await send_to_targets(client, group_msgs, channel)
    print("✅ تم الانتهاء.")

# ==========================================
# 4. تشغيل البوت
# ==========================================
app = Client("retail_v3", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message(filters.chat(SOURCE_CHANNELS) & ~filters.forwarded)
async def main_handler(client, message):
    if not message.media_group_id:
        await send_to_targets(client, [message], message.chat.id)

web_app = Flask(__name__)
@web_app.route('/')
def home(): return "Retail Pro Bot v3.0 Running!"

async def start_bot():
    await app.start()
    asyncio.create_task(fetch_history(app))
    await idle()

if __name__ == "__main__":
    Thread(target=lambda: web_app.run(host="0.0.0.0", port=8000)).start()
    app.run(start_bot())
