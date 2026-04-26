import os
import re
import asyncio
import cv2
import numpy as np
from datetime import datetime, timezone
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait
from flask import Flask
from threading import Thread

# ملاحظة: ستحتاج لتثبيت easyocr عن طريق: pip install easyocr
import easyocr

# ==========================================
# 1. الإعدادات الأساسية والذاكرة
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

RETAIL_CHANNEL = "@girlsfashionesta"
DB_FILE = "processed_msgs.txt"

# قارئ النصوص من الصور (OCR) - يدعم الإنجليزية والعربية
reader = easyocr.Reader(['en', 'ar'])

# الكلمات الممنوع ظهورها في الصور أو النصوص
FORBIDDEN_BRANDS = ["SASA", "sasa", "PRIBORE", "Women Accessoreis"]

P_CODE_TRANSLATION = {
    "A": "انسيال", "K": "خلخال", "N": "سلسلة", "CP": "كوليه", 
    "C": "كوليه", "E": "حلق", "R": "خاتم", "B": "اسورة"
}

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# ==========================================
# 2. وظائف الفلترة البصرية والذكية
# ==========================================

async def has_forbidden_watermark(client, message):
    """يفحص إذا كانت الصورة تحتوي على علامة مائية محظورة"""
    if not message.photo:
        return False
    
    try:
        # تحميل الصورة مؤقتاً للفحص
        file_path = await client.download_media(message, file_name="temp_check.jpg")
        
        # قراءة النص من الصورة
        results = reader.readtext(file_path, detail=0)
        full_text = " ".join(results).upper()
        
        # حذف الملف المؤقت فوراً
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # التأكد من وجود أي كلمة محظورة
        for brand in FORBIDDEN_BRANDS:
            if brand.upper() in full_text:
                print(f"🚫 [OCR] Watermark detected: {brand}")
                return True
        return False
    except Exception as e:
        print(f"⚠️ [OCR] Error: {e}")
        return False

def convert_to_arabic_numbers(text):
    if not text: return ""
    return str(text).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))

def normalize_numbers(text):
    if not text: return ""
    return text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

def extract_real_price(text):
    if not text: return None
    norm_text = normalize_numbers(text)
    clean_for_search = re.sub(r'\d+\s*(?:سم|س|M|CM|ملي|متر|شكل|لون|ق)', '', norm_text, flags=re.IGNORECASE)
    price_match = re.search(r'(?:أونلاين|اونلاين|online|سعر القطعه|قطعه|قطعة|بسعر|السعر|price|L\.E|LE)\s*[:：]?\s*(\d+)', clean_for_search, re.IGNORECASE)
    if price_match: return int(price_match.group(1))
    wholesale_match = re.search(r'(?:الجمله|الجملة|جمله|جملة)\s*[:：]?\s*(\d+)', clean_for_search, re.IGNORECASE)
    if wholesale_match: return int(wholesale_match.group(1))
    nums = [int(n) for n in re.findall(r'(\d+)', clean_for_search) if 15 <= int(n) <= 2000]
    return nums[-1] if nums else None

def build_text(original_text, source_id, msg_date):
    if not original_text: return ""
    norm_text = normalize_numbers(original_text)
    
    # منع النسخ لو النص فيه براندات محظورة
    if any(brand.upper() in norm_text.upper() for brand in FORBIDDEN_BRANDS):
        return None

    found_price_val = extract_real_price(original_text)
    final_price_val = RETAIL_MAPPING.get(found_price_val, "")
    price_str_ar = convert_to_arabic_numbers(final_price_val)
    
    code_match = re.search(r'([A-Z]+)\d+', norm_text, re.IGNORECASE)
    original_code_prefix = code_match.group(1).upper() if code_match else ""

    cleaned_lines = []
    for line in norm_text.split('\n'):
        line = line.strip()
        if not line or re.match(r'^[A-Z]+\d+.*$', line, re.IGNORECASE): continue
        if any(re.search(p, line, re.IGNORECASE) for p in [r'.*(?:جمله|دسته|علبه|اختيار).*']): continue
        line = re.sub(r'(?:السعر|سعر|price|بسعر|قطعه|قطعة|أونلاين|online|اقل من).*', '', line, flags=re.IGNORECASE).strip()
        line = re.sub(r'[:：]?\s*\d+\s*(?:ج|LE|L\.E|egp|جنيه).*', '', line, flags=re.IGNORECASE).strip()
        if line: cleaned_lines.append(line)

    description = "\n".join(cleaned_lines)
    if not any(c.isalpha() or '\u0600' <= c <= '\u06FF' for c in description) and original_code_prefix in P_CODE_TRANSLATION:
        item_name = P_CODE_TRANSLATION[original_code_prefix]
        description = f"{item_name} شيك قوي💕💕\nاستانلس بيور عيار ٣١٦ 💎💯"

    today_str = msg_date.strftime("%d%m")
    counter_key = f"{source_id}_{today_str}"
    current_num = channel_counters.get(counter_key, 0) + 1
    prefix = SUPPLIER_PREFIX_MAP.get(source_id, "UN")
    my_code = f"{prefix}{current_num:02d}{today_str}"

    return f"{description}\n\nالكود : 🔖 {my_code}\nالسعر : 💰 {price_str_ar} ج 🔥"

# ==========================================
# 3. نظام النشر
# ==========================================
channel_counters = {}
processed_media_groups = set()

async def safe_send(client, messages, source_id):
    if not messages: return
    msg_id = messages[0].id
    
    # فحص الـ OCR للصور في المجموعة
    for m in messages:
        if await has_forbidden_watermark(client, m):
            print(f"🚫 [SafeSend] Forbidden watermark found in ID {msg_id}. Skipping entire post.")
            return

    valid_messages = [m for m in messages if not m.poll]
    main_msg = next((m for m in valid_messages if (m.caption or m.text)), valid_messages[0])
    msg_date = main_msg.date.replace(tzinfo=timezone.utc)
    
    retail_text = build_text(main_msg.caption or main_msg.text, source_id, msg_date)
    if retail_text is None: return
    
    try:
        for m in valid_messages:
            if m.photo: await client.send_photo(RETAIL_CHANNEL, m.photo.file_id)
            elif m.video: await client.send_video(RETAIL_CHANNEL, m.video.file_id)
            elif m.animation: await client.send_animation(RETAIL_CHANNEL, m.animation.file_id)
            await asyncio.sleep(2) 
        
        if retail_text != "": 
            await client.send_message(RETAIL_CHANNEL, retail_text)
            counter_key = f"{source_id}_{msg_date.strftime('%d%m')}"
            channel_counters[counter_key] = channel_counters.get(counter_key, 0) + 1
        
        with open(DB_FILE, "a") as f: f.write(str(msg_id) + "\n")
        await asyncio.sleep(3)
    except: pass

# ... (باقي دوال fetch_history و main_handler كما هي في النسخة المستقرة السابقة)
