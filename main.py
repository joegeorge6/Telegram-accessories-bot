import os
import re
import asyncio 
from datetime import datetime
from pyrogram import Client, filters

# ==========================================
# إعدادات من المتغيرات البيئية (Render / Koyeb)
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# ✅ تم التصحيح: تحويل القنوات بطريقة آمنة (تقبل الأرقام والكلام)
raw_channels = os.environ.get("SOURCE_CHANNELS", "").split()
SOURCE_CHANNELS = []
for ch in raw_channels:
    try:
        SOURCE_CHANNELS.append(int(ch)) # لو رقم خليه رقم
    except ValueError:
        SOURCE_CHANNELS.append(ch)      # لو كلام (يوزرنيم) خليه كلام

TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "")

# ==========================================
# 1. جدول الأسعار
# ==========================================
PRICE_MAPPING = {
    25: 55, 30: 60, 35: 65, 40: 70, 45: 75, 50: 80, 55: 85, 60: 90, 65: 95, 70: 100,
    75: 105, 80: 115, 85: 120, 90: 130, 95: 135, 100: 140, 105: 150, 110: 155, 115: 165,
    120: 170, 125: 175, 130: 185, 135: 190, 140: 200, 145: 205, 150: 210, 155: 220,
    160: 225, 165: 235, 170: 240, 175: 245, 180: 255, 185: 260, 190: 270, 195: 275,
    200: 280, 205: 290, 210: 295, 215: 305, 220: 310, 225: 315, 230: 325, 235: 330,
    240: 340, 245: 345, 250: 350, 255: 360, 260: 365, 265: 375, 270: 380, 275: 385,
    280: 395, 285: 400, 290: 410, 295: 415, 300: 420, 305: 430, 310: 435, 315: 445,
    320: 450, 325: 455, 330: 465, 335: 470, 340: 480, 345: 485, 350: 490, 355: 500,
    360: 505, 365: 515, 370: 520, 375: 525, 380: 535, 385: 540, 390: 550, 395: 555,
    400: 560
}

# ==========================================
# 2. نظام الكود الخاص بك
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
# 3. دوال استخراج النوع والمقاس والسعر
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
            code = p_match.group(1).upper()
            p_map = {
                "A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه",
                "E": "حلق", "R": "خاتم", "B": "اسورة"
            }
            return p_map.get(code, "قطعة")

    keywords = ["طقم", "سلسلة", "اسورة", "اسوره", "خاتم", "خواتم", "حلق", "حلقان", "كوليه", "خلخال", "بيرسينج", "بروش", "انسيال"]
    for word in keywords:
        if word in text_lower:
            return word
    return "قطعة"

def get_ring_size_info(text):
    size_match = re.search(r'(مقاس(?:ات)?(?:\s+من)?\s+\d+\s*ل(?:ـ)?\s*\d+)', text)
    if size_match:
        return size_match.group(1) 
    if "فري" in text or "سايز" in text or "مقاس واحد" in text or "عالمي" in text:
        return "فري سايز"
    return ""

def extract_and_modify_price(text, source_name):
    if not text: return "حددنا لك"
    clean_text = normalize_numbers(text)
    
    online_price_channels = ["sasaaccessories", -1001682055192, "miyokowatches22"]
    found_price = None
    
    if source_name in online_price_channels:
        online_match = re.search(r'(?:اونلاين|اون لاين|الاون لاين)[^\d]*(\d+)', clean_text)
        if online_match:
            found_price = int(online_match.group(1))
            
    if found_price is None:
        normal_match = re.search(r'(\d+)(\s*جنيه|\s*ج\.?|\s*ج)', clean_text)
        if normal_match:
            found_price = int(normal_match.group(1))

    if found_price:
        new_price = PRICE_MAPPING.get(found_price)
        return str(new_price) if new_price else str(found_price + 30)
        
    return "حددنا لك"

# ==========================================
# 4. دالة تجميع النص النهائي
# ==========================================

def build_final_text(original_text, source_channel_id):
    if not original_text:
        original_text = ""
        
    processed_text = normalize_numbers(original_text)
    text_lower = processed_text.lower()

    product_name = extract_product_type(processed_text, source_channel_id)
    
    size_info = ""
    if product_name in ["خاتم", "خواتم"]:
        size_info = get_ring_size_info(processed_text)
    
    product_size = f"{product_name} {size_info}" if size_info else product_name

    my_new_code = generate_my_code(source_channel_id)
    new_price = extract_and_modify_price(processed_text, source_channel_id)

    final_text = ""

    if "بيرسينج بول باك مع تكه كونكت فصوص زيركون" in text_lower:
        final_text = f"""بيرسينج بول باك مع تكه كونكت فصوص زيركون قمر قوي💕
عمود استانلس بيور عيار ٣١٦ 💎💯
لمسة شيك وجودة باينة من أول نظرة ✨
الكود : 🔖  {my_new_code}
البيرسينج فردة واحدة بسعر : 💰   {new_price}   ج  🔥"""

    elif "بيرسينج بول باك" in text_lower:
        final_text = f"""بيرسينج بول باك شيك قوي💕💕
عمود استانلس بيور عيار ٣١٦ فصوص زيركون💎💯
لمسة شيك وجودة باينة من أول نظرة ✨️
الكود : 🔖  {my_new_code}
البيرسينج فردة واحدة بسعر : 💰   {new_price}   ج  🔥"""

    elif "بيرسينج تكه" in text_lower or "قطرة ٨ مم" in text_lower or "ينفع اطفالي" in text_lower:
        final_text = f"""كوليكشن بيرسينج تكه قطرة ٨ مم ينفع اطفالي شيك قوي💕💕
عمود استانلس بيور عيار ٣١٦ فصوص زيركون💎💯
لمسة شيك وجودة باينة من أول نظرة ✨️
الكود : 🔖  {my_new_code}
الفردة بسعر : 💰   {new_price}   ج  🔥"""

    elif "الدلاية جولد بليتد" in text_lower or "الدلاية دهب صيني" in text_lower or "الدلاية بلاتين" in text_lower:
        dalaia_type = "الدلاية جولد بليتد"
        if "الدلاية دهب صيني" in text_lower: dalaia_type = "الدلاية دهب صيني"
        elif "الدلاية بلاتين" in text_lower: dalaia_type = "الدلاية بلاتين"
        
        final_text = f"""سلسلة تريندي قمر قوي 💕💕
استانلس بيور عيار ٣١٦ 💎💯
⚠️ {dalaia_type}
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "دهب صيني فصوص زيركون" in text_lower:
        final_text = f"""{product_size} شيك قوي 💛✨
دهب صيني فصوص زيركون ✨
لمعة حلوة وشكل شيك يلفت النظر 💛
بيدي إحساس الدهب من غير تكلفة 💸
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "بانجل" in text_lower or "بانجلز" in text_lower:
        final_text = f"""كوليكشن بانجلز تريندي بالوانها 🌈💖
ألوان حلوة وشياكة بسيطة تكمل أي لوك 👌
خفيف ومريح على الإيد، يدي لمسة مميزة كل يوم ✨
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "الغويشه الاستك" in text_lower or "استك التريند" in text_lower:
        final_text = f"""الغويشه الاستك التريند فى shein
غويشه استك تلبس اى مقاس خامه اكلريك و عاج قمر قوي 💕
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "تشارمز إيطاليان" in text_lower:
        final_text = f"""تشارمز إيطاليان برسليت ✨💕
تفصيلة مميزة تكمّل شكل الإيد ببساطة 💖
ستايل شيك ينفع كل يوم وكل خروجة 👌
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "حزام معدن" in text_lower:
        final_text = f"""حزام معدن تريندي ✨
من أحدث موديلات SHEIN ويكمّل أي لوك بسهولة 👌
تفصيلة بسيطة بس بتفرق في الشكل 💛
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "حلقان اكليرك" in text_lower:
        final_text = f"""كوليكشن حلقان أكليرك ✨
ألوان جذابة ولمسة شيك تكمّل أي لوك 👌
خفيفة ومناسبة لكل خروجة 💖
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "ميدالية تريندي" in text_lower:
        final_text = f"""ميدالية تريندي ✨🔑
تفصيلة على الموضة تكمّل شنطتك أو مفاتيحك بسهولة 👌
لمسة شيك تفرق في الشكل 💖
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    elif "كف استانلس" in text_lower or "كف استالنس" in text_lower:
        final_text = f"""هاند تشين قمر قوي💕
استانلس بيور عيار ٣١٦ 💎💯
لمسة شيك وجودة باينة من أول نظرة ✨
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    else:
        if "ستانلس" in text_lower or "استالنس" in text_lower:
            final_text = f"""{product_size} قمر قوي💕
استانلس بيور عيار ٣١٦ 💎💯
لمسة شيك وجودة باينة من أول نظرة ✨
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""
        else:
            final_text = f"""{product_size} مميز جداً ✨
لو عايز تتميز دوس على الطلب 💎
الكود : 🔖  {my_new_code}
بسعر : 💰   {new_price}   ج  🔥"""

    final_text = re.sub(r'\s+', ' ', final_text).strip()
    
    return final_text, my_new_code

# ==========================================
# 5. دالة إرسال المنشور
# ==========================================

async def forward_post(client, message):
    try:
        orig = message.caption or message.text or ""
        source_name = message.chat.username if message.chat.username else message.chat.id
        
        final_text, generated_code = build_final_text(orig, source_name)
        
        if message.photo:
            path = await message.download()
            await client.send_photo(TARGET_CHANNEL, path, caption=final_text)
            try: os.remove(path)
            except: pass
        elif message.video:
            path = await message.download()
            await client.send_video(TARGET_CHANNEL, path, caption=final_text)
            try: os.remove(path)
            except: pass
        elif message.text:
            await client.send_message(TARGET_CHANNEL, final_text)
            
        print(f"✅ تم النقل | الكود الجديد: {generated_code}")
    except Exception as e:
        print(f"❌ خطأ: {e}")

# ==========================================
# 6. إعداد وتشغيل البوت
# ==========================================

app = Client(
    "auto_poster",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

@app.on_message(filters.chat(SOURCE_CHANNELS) & ~filters.forwarded)
async def new_post(client, message):
    await asyncio.sleep(3) 
    await forward_post(client, message)

print("🚀 البوت الذكي شغال (بدون واجهات، مباشر على السيرفر)...")
app.run()
