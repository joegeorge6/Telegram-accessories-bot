import os
import re
import asyncio
import json
import traceback
from datetime import datetime, timezone
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from flask import Flask
from threading import Thread

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
API_ID = int(os.environ.get("API_ID", "10182970"))
API_HASH = os.environ.get("API_HASH", "0f4e456fc8101e8be8e0dad6aeb87041")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

RETAIL_CHANNEL = "@girlsfashionesta"
DB_FILE = "processed_msgs.txt"
COUNTERS_FILE = "counters.json"

SCREENSHOT_RATIO = 1.6

WORDS_TO_REMOVE = ["SASA", "sasa", "PRIBORE", "Women Accessories"]
BLOCK_KEYWORDS = [
    "الرسالة المثبته", "نظام التعامل", "بتجمع / ي اوردورك", "قفل فاتورة",
    "مواعيد العمل يوميا", "الاحد اجازة", "فوادفون كاش", "انستا باي",
    "01289765424", "01272078072", "01505530190", "01012050836",
    "شركه PR", "شركة PR", "النزهه الجديده", "عبدالرحمن", "ريفيو", "وصلنا",
    "تم استلام اكبر اكبر اكبر", "tiktok.com", "تم غلق الحجز",
    "صباح الرزق",
    "جميع الاسعار المتكوبه اسعار الجمله"
]

P_CODE_TRANSLATION = {
    "A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه",
    "C": "كوليه", "E": "حلق", "R": "خاتم", "B": "اسورة"
}

def load_counters():
    if not os.path.exists(COUNTERS_FILE):
        return {}
    with open(COUNTERS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_counter(key, value):
    counters = load_counters()
    counters[key] = value
    temp_file = COUNTERS_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(counters, f)
    os.replace(temp_file, COUNTERS_FILE)

def convert_to_arabic_numbers(text):
    if not text: return ""
    return str(text).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))

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
# 2. المساعدات
# ==========================================
channel_counters = load_counters()
SUPPLIER_PREFIX_MAP = {"aymanelawamy123": "A", "sasaaccessories": "S", "ayselstore55": "AS", "miyokowatches22": "M", -1001132261086: "P", -1001448553593: "I", -1001682055192: "H"}

def is_screenshot(photo):
    if not photo: return False
    try:
        ratio = photo.height / photo.width
        return ratio > SCREENSHOT_RATIO
    except:
        return False

def is_msg_processed(msg_id, source_id):
    if not os.path.exists(DB_FILE): return False
    search_key = f"{source_id}:{msg_id}"
    with open(DB_FILE, "r") as f:
        return search_key in f.read().splitlines()

def mark_msg_as_processed(msg_id, source_id):
    with open(DB_FILE, "a") as f:
        f.write(f"{source_id}:{msg_id}\n")

def extract_real_price(text):
    if not text: return None
    norm_text = normalize_numbers(text)
    clean_for_search = re.sub(r'\d+\s*(?:سم|س|M|CM|ملي|متر|شكل|لون|ق)', '', norm_text, flags=re.IGNORECASE)

    special_offer = re.search(r'عرض\s+خاص\s*(\d+)', clean_for_search, re.IGNORECASE)
    if special_offer:
        return int(special_offer.group(1))

    cart_match = re.search(r'(?:الكارت كله|الكارت)\s*ب\s*(\d+)', clean_for_search, re.IGNORECASE)
    if cart_match:
        return int(cart_match.group(1))

    price_match = re.search(r'(?:الاونلاين|الأونلاين|أونلاين|اونلاين|online|سعر القطعه|قطعه|قطعة|بسعر|السعر|price|L\.E|LE)\s*[:：]?\s*(\d+)', clean_for_search, re.IGNORECASE)
    if price_match:
        return int(price_match.group(1))

    wholesale_match = re.search(r'(?:الجمله|الجملة|جمله|جملة)\s*[:：]?\s*(\d+)', clean_for_search, re.IGNORECASE)
    if wholesale_match:
        return int(wholesale_match.group(1))

    nums = [int(n) for n in re.findall(r'(\d+)', clean_for_search) if 15 <= int(n) <= 2000]
    return nums[-1] if nums else None

def is_emoji_only(text):
    if not text or not text.strip():
        return False
    cleaned = re.sub(r'[\s\u200d]', '', text)
    if not cleaned:
        return False
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U0000FE00-\U0000FE0F"
        "\U0000200D"
        "\U00002B50"
        "\U00002764"
        "\U0001F004"
        "\U0001F0CF"
        "]+", flags=re.UNICODE)
    return bool(emoji_pattern.fullmatch(cleaned))

def is_number_emoji_line(line):
    if not line: return False
    if re.search(r'[A-Za-z\u0600-\u06FF]', line):
        return False
    if re.search(r'\d', line):
        return True
    return False

def build_text(original_text, source_id, msg_date, current_num):
    if not original_text: return ""
    
    if re.search(r'HEMA\s*STORE', original_text, re.IGNORECASE):
        return ""
    
    norm_text = normalize_numbers(original_text)

    if any(word in norm_text for word in BLOCK_KEYWORDS): return None

    if is_emoji_only(norm_text):
        return ""

    norm_text = re.sub(r'\binfinity\b', 'فاشونيستا', norm_text, flags=re.IGNORECASE)
    norm_text = re.sub(r'(?:استالس|ستالس)', 'استانلس', norm_text, flags=re.IGNORECASE)
    norm_text = re.sub(r'\bبلاتيد\b', 'بليتد', norm_text, flags=re.IGNORECASE)
    norm_text = re.sub(r'\bزركون\b', 'زيركون', norm_text, flags=re.IGNORECASE)

    for word in WORDS_TO_REMOVE:
        norm_text = re.sub(rf'\b{word}\b', '', norm_text, flags=re.IGNORECASE)

    labeled_prices = []
    lines = norm_text.split('\n')
    new_lines = []
    for line in lines:
        if re.search(r'(?:جملة|جمله|اونلاين|online)', line, re.IGNORECASE):
            new_lines.append(line)
            continue

        match = re.search(r'(سعر\s+[\u0600-\u06FF\w]+)\s*[:：]\s*(\d+)', line, re.IGNORECASE)
        if match:
            label_part = match.group(1)
            price = int(match.group(2))
            retail_price = RETAIL_MAPPING.get(price, price)
            arabic_price = convert_to_arabic_numbers(retail_price)
            formatted = f"{label_part}: 💰 {arabic_price} ج 🔥"
            labeled_prices.append(formatted)
            continue
        new_lines.append(line)

    norm_text = "\n".join(new_lines)

    cleaned_lines = []
    for line in norm_text.split('\n'):
        line = line.strip()
        if not line or re.match(r'^[A-Z]+\d+.*$', line, re.IGNORECASE): continue
        
        if re.search(r'(?:الكارت|كارت).*ب\s*\d+\s*ج', line, re.IGNORECASE): continue
        if any(re.search(p, line, re.IGNORECASE) for p in [r'.*(?:جمله|جملة|دسته|دستة|علبه|علبة|اختيار).*']): continue
        if re.search(r'(?:أونلاين|اونلاين|online)', line, re.IGNORECASE): continue
        if re.search(r'بكام', line, re.IGNORECASE): continue

        if re.search(r'عرض', line, re.IGNORECASE) and not re.search(r'سعر', line, re.IGNORECASE):
            continue

        if re.search(r'(?:للحجز|طلب الاوردر|للطلب)', line, re.IGNORECASE):
            continue

        if re.search(r'\b01\d{9}\b', line):
            continue

        if re.match(r'^(\d{2,4})\s+', line):
            num = int(re.match(r'^(\d{2,4})', line).group(1))
            if 15 <= num <= 2000:
                line = re.sub(r'^\d+\s+', '', line).strip()

        line = re.sub(r'(?:السعر|سعر|price|بسعر|قطعه|قطعة|أونلاين|online|اقل من).*', '', line, flags=re.IGNORECASE).strip()
        line = re.sub(r'\s*ب\s*\d+\s*(?:ج|LE|L\.E|egp|جنيه).*', '', line, flags=re.IGNORECASE).strip()
        line = re.sub(r'[:：]?\s*\d+\s*(?:ج|LE|L\.E|egp|جنيه).*', '', line, flags=re.IGNORECASE).strip()

        if is_number_emoji_line(line):
            continue

        if line and len(line.split()) == 1 and not any(c.isascii() and c.isalpha() for c in line):
            continue
        if len(line) <= 3 and not any(c.isascii() and c.isalpha() for c in line):
            continue

        if line: cleaned_lines.append(line)

    description = "\n".join(cleaned_lines)
    
    code_match = re.search(r'([A-Z]+)\d+', normalize_numbers(original_text), re.IGNORECASE)
    original_code_prefix = code_match.group(1).upper() if code_match else ""

    if not any(c.isalpha() or '\u0600' <= c <= '\u06FF' for c in original_text) and original_code_prefix in P_CODE_TRANSLATION:
        item_name = P_CODE_TRANSLATION[original_code_prefix]
        description = f"{item_name} شيك قوي💕💕\nاستانلس بيور عيار ٣١٦ 💎💯"

    today_str = msg_date.strftime("%d%m")
    prefix = SUPPLIER_PREFIX_MAP.get(source_id, "UN")
    my_code = f"{prefix}{current_num:02d}{today_str}"

    parts = [description, "", f"الكود : 🔖 {my_code}"]
    
    if labeled_prices:
        parts.extend(labeled_prices)
    else:
        found_price_val = extract_real_price(original_text)
        final_price_val = RETAIL_MAPPING.get(found_price_val, "")
        price_str_ar = convert_to_arabic_numbers(final_price_val)
        parts.append(f"السعر : 💰 {price_str_ar} ج 🔥")

    return "\n".join(parts)

# ==========================================
# 3. نظام النشر
# ==========================================
async def safe_send(client, messages, source_id):
    if not messages or is_msg_processed(messages[0].id, source_id):
        return

    valid_messages = [m for m in messages if not m.poll and not (m.photo and is_screenshot(m.photo))]
    if not valid_messages:
        return

    # 🔍 اختيار أي رسالة في المجموعة تحمل نصاً (وليس فقط الأولى)
    main_msg = None
    for m in valid_messages:
        if m.caption or m.text:
            main_msg = m
            break
    if main_msg is None:
        main_msg = valid_messages[0]

    msg_date = main_msg.date.replace(tzinfo=timezone.utc)
    if END_DATE_LIMIT and msg_date > END_DATE_LIMIT:
        return

    raw_caption = main_msg.caption or main_msg.text or ""
    print(f"🔍 [DEBUG] Raw caption: {repr(raw_caption[:150])}")

    today_str = msg_date.strftime("%d%m")
    counter_key = f"{source_id}_{today_str}"

    current_num = channel_counters.get(counter_key, 0) + 1

    retail_text = build_text(raw_caption, source_id, msg_date, current_num)
    if retail_text is None:
        print("⛔ [DEBUG] retail_text is None (post blocked)")
        mark_msg_as_processed(messages[0].id, source_id)
        return

    if retail_text == "":
        print("📝 [DEBUG] retail_text empty, sending media only")

    try:
        media_count = len(valid_messages)
        print(f"📤 Sending group of {media_count} media, ID {messages[0].id}, Code: {current_num:02d}")
        for m in valid_messages:
            if m.photo: await client.send_photo(RETAIL_CHANNEL, m.photo.file_id)
            elif m.video: await client.send_video(RETAIL_CHANNEL, m.video.file_id)
            elif m.animation: await client.send_animation(RETAIL_CHANNEL, m.animation.file_id)
            await asyncio.sleep(2)

        if retail_text != "":
            await client.send_message(RETAIL_CHANNEL, retail_text)
            if raw_caption:
                channel_counters[counter_key] = current_num
                save_counter(counter_key, current_num)

        mark_msg_as_processed(messages[0].id, source_id)
        await asyncio.sleep(3)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        print(f"❌ Error: {e}")

async def fetch_history(client):
    print(f"🚀 Scanning history...")
    for channel in SOURCE_CHANNELS:
        all_items, group_processed = [], set()
        count = 0
        async for msg in client.get_chat_history(channel, limit=10000):
            m_date = msg.date.replace(tzinfo=timezone.utc)
            count += 1
            if count % 200 == 0:
                print(f"⏳ {channel}: {m_date.strftime('%Y-%m-%d')}")
            if m_date < START_DATE: break
            if (END_DATE_LIMIT and m_date > END_DATE_LIMIT) or is_msg_processed(msg.id, channel):
                continue

            if msg.media_group_id:
                if msg.media_group_id in group_processed: continue
                group_processed.add(msg.media_group_id)
                try:
                    group = await client.get_media_group(channel, msg.id)
                except:
                    continue
                all_items.append(group)
            else:
                all_items.append([msg])

        all_items.reverse()
        print(f"📦 {channel}: {len(all_items)} posts/groups")
        for item in all_items:
            await safe_send(client, item, channel)
    print("✅ History finished.")

# ==========================================
# 4. تشغيل البوت
# ==========================================
app = Client("retail_bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING, in_memory=True)

@app.on_message(filters.chat(SOURCE_CHANNELS))
async def main_handler(client, message):
    if message.photo and is_screenshot(message.photo):
        return
    if message.poll or is_msg_processed(message.id, message.chat.id):
        return
    m_date = message.date.replace(tzinfo=timezone.utc)
    if m_date < START_DATE or (END_DATE_LIMIT and m_date > END_DATE_LIMIT):
        return
    if message.media_group_id:
        if is_msg_processed(message.id, message.chat.id):
            return
        try:
            msgs = await client.get_media_group(message.chat.id, message.id)
            for m in msgs:
                mark_msg_as_processed(m.id, message.chat.id)
            await safe_send(client, msgs, message.chat.id)
        except: pass
    else:
        await safe_send(client, [message], message.chat.id)

web_app = Flask(__name__)
@web_app.route('/')
def home():
    return "Bot is running!"

async def start_bot():
    global channel_counters
    channel_counters = load_counters()
    await app.start()
    asyncio.create_task(fetch_history(app))
    await idle()

if __name__ == "__main__":
    try:
        print("🚀 بدء التطبيق...")
        port = int(os.environ.get("PORT", 8000))
        Thread(target=lambda: web_app.run(host="0.0.0.0", port=port, debug=False)).start()
        app.run(start_bot())
    except Exception as e:
        print(f"💥 فشل بدء التشغيل: {e}")
        traceback.print_exc()
        while True:
            import time as _time
            _time.sleep(3600)
