import io
import os
import re
import hashlib
from datetime import datetime
from PIL import Image, ImageEnhance
from translitua import translit

"""
Watermarker Pro Engine
----------------------
Backend-модуль для обробки зображень.
Не містить залежностей від UI-фреймворків.
Призначений для ресайзу, накладання водяних знаків та конвертації форматів.
"""

def generate_filename(original_name: str, naming_mode: str, prefix: str = "", extension: str = "jpg", index: int = 1, file_bytes: bytes = None) -> str:
    """
    Генерує безпечне та унікальне ім'я файлу на основі обраної стратегії.

    Args:
        original_name (str): Оригінальне ім'я файлу (напр. "photo.jpg").
        naming_mode (str): Стратегія ("Timestamp", "Original + Suffix", "Content Hash", "Keep Original", "Prefix + Sequence").
        prefix (str): Префікс, що додається на початок.
        extension (str): Розширення файлу без крапки (напр. "jpg").
        index (int): Порядковий номер файлу (для стратегії Sequence).
        file_bytes (bytes, optional): Вміст файлу для генерації хешу (потрібен для "Content Hash").

    Returns:
        str: Нове ім'я файлу (напр. "img_001.jpg").
    """
    clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-') if prefix else ""
    
    if naming_mode == "Prefix + Sequence":
        base_name = clean_prefix if clean_prefix else "image"
        return f"{base_name}_{index:03d}.{extension}"
    
    # Базова підготовка слага для інших режимів
    name_only = os.path.splitext(original_name)[0]
    slug = re.sub(r'[\s\W_]+', '-', translit(name_only).lower()).strip('-')
    if not slug: slug = "image"
    
    # Формування бази імені
    base = f"{clean_prefix}_{slug}" if clean_prefix else slug

    if naming_mode == "Content Hash" and file_bytes:
        file_hash = hashlib.md5(file_bytes).hexdigest()[:8]
        return f"{base}_{file_hash}.{extension}"
    elif naming_mode == "Original + Suffix":
        return f"{base}_wm.{extension}"
    elif naming_mode == "Timestamp":
        timestamp = datetime.now().strftime('%H%M%S_%f')[:9]
        return f"{base}_{timestamp}.{extension}"
    else: # Keep Original (Default fallback)
        return f"{base}.{extension}"


def get_image_metadata(file_bytes: bytes) -> tuple:
    """
    Отримує метадані зображення без повного завантаження в пам'ять (Lazy loading).

    Args:
        file_bytes (bytes): Вміст файлу.

    Returns:
        tuple: (width: int, height: int, size_bytes: int, format: str)
    """
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            return img.width, img.height, len(file_bytes), img.format
    except Exception:
        return 0, 0, len(file_bytes), "UNKNOWN"


def load_and_process_watermark(wm_file_bytes: bytes, opacity: float) -> Image.Image:
    """
    Завантажує та готує зображення водяного знака.

    Args:
        wm_file_bytes (bytes): Вміст файлу логотипа (PNG).
        opacity (float): Рівень прозорості від 0.0 до 1.0.

    Returns:
        Image.Image: Об'єкт PIL Image у форматі RGBA або None, якщо вхідні дані пусті.
    """
    if not wm_file_bytes:
        return None
    
    wm = Image.open(io.BytesIO(wm_file_bytes)).convert("RGBA")
    
    if opacity < 1.0:
        alpha = wm.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        wm.putalpha(alpha)
        
    return wm


def process_image(file_bytes: bytes, filename: str, wm_obj: Image.Image, resize_config: dict, output_fmt: str, quality: int) -> tuple:
    """
    Основна функція обробки зображення (Pipeline).

    Args:
        file_bytes (bytes): Вхідне зображення.
        filename (str): Ім'я файлу для звіту.
        wm_obj (Image.Image): Підготовлений об'єкт вотермарки (може бути None).
        resize_config (dict): Конфігурація ресайзу та позиціювання.
            Очікувані ключі:
            - 'enabled' (bool): Чи ввімкнено ресайз.
            - 'mode' (str): "Max Side", "Exact Width", "Exact Height".
            - 'value' (int): Цільовий розмір у пікселях.
            - 'wm_scale' (float): Масштаб лого (напр. 0.15).
            - 'wm_margin' (int): Відступ у пікселях.
            - 'wm_position' (str): 'bottom-right', 'center' і т.д.
        output_fmt (str): "JPEG", "PNG", "WEBP".
        quality (int): Якість збереження (1-100).

    Returns:
        tuple: (result_bytes: bytes, stats: dict)
    """
    input_io = io.BytesIO(file_bytes)
    img = Image.open(input_io)
    
    orig_w, orig_h = img.size
    orig_format = img.format
    
    # 1. Конвертація в RGBA для коректної роботи шарів
    img = img.convert("RGBA")
    
    # 2. Логіка ресайзу
    target_value = resize_config.get('value', 1920)
    mode = resize_config.get('mode', 'Max Side')
    enabled = resize_config.get('enabled', False)
    
    new_w, new_h = orig_w, orig_h
    scale_factor = 1.0

    if enabled:
        if mode == "Max Side" and (orig_w > target_value or orig_h > target_value):
            if orig_w >= orig_h:
                scale_factor = target_value / float(orig_w)
                new_w, new_h = target_value, int(float(orig_h) * scale_factor)
            else:
                scale_factor = target_value / float(orig_h)
                new_w, new_h = int(float(orig_w) * scale_factor), target_value
                
        elif mode == "Exact Width":
            scale_factor = target_value / float(orig_w)
            new_w, new_h = target_value, int(float(orig_h) * scale_factor)
            
        elif mode == "Exact Height":
            scale_factor = target_value / float(orig_h)
            new_w, new_h = int(float(orig_w) * scale_factor), target_value

        if scale_factor != 1.0:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 3. Накладання вотермарки
    if wm_obj:
        scale = resize_config.get('wm_scale', 0.15)
        margin = resize_config.get('wm_margin', 15)
        position = resize_config.get('wm_position', 'bottom-right')
        
        # Розрахунок розміру лого
        wm_w_target = int(new_w * scale)
        if wm_w_target < 1: wm_w_target = 1
        
        w_ratio = wm_w_target / float(wm_obj.width)
        wm_h_target = int(float(wm_obj.height) * w_ratio)
        if wm_h_target < 1: wm_h_target = 1
        
        wm_resized = wm_obj.resize((wm_w_target, wm_h_target), Image.Resampling.LANCZOS)
        
        # Розрахунок координат
        pos_x, pos_y = 0, 0
        if position == 'bottom-right': pos_x, pos_y = new_w - wm_w_target - margin, new_h - wm_h_target - margin
        elif position == 'bottom-left': pos_x, pos_y = margin, new_h - wm_h_target - margin
        elif position == 'top-right': pos_x, pos_y = new_w - wm_w_target - margin, margin
        elif position == 'top-left': pos_x, pos_y = margin, margin
        elif position == 'center': pos_x, pos_y = (new_w - wm_w_target) // 2, (new_h - wm_h_target) // 2
        
        img.paste(wm_resized, (pos_x, pos_y), wm_resized)

    # 4. Фінальна підготовка формату
    if output_fmt == "JPEG":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif output_fmt == "RGB":
         img = img.convert("RGB")

    # 5. Збереження
    output_buffer = io.BytesIO()
    
    if output_fmt == "JPEG":
        img.save(output_buffer, format="JPEG", quality=quality, optimize=True, subsampling=0)
    elif output_fmt == "WEBP":
        img.save(output_buffer, format="WEBP", quality=quality, method=6)
    elif output_fmt == "PNG":
        img.save(output_buffer, format="PNG", optimize=True)

    result_bytes = output_buffer.getvalue()
    
    # 6. Формування статистики
    stats = {
        "filename": filename,
        "orig_res": f"{orig_w}x{orig_h}",
        "new_res": f"{new_w}x{new_h}",
        "orig_size": len(file_bytes),
        "new_size": len(result_bytes),
        "orig_fmt": orig_format or "Unknown",
        "scale_factor": f"{scale_factor:.2f}x",
        "quality": quality if output_fmt != "PNG" else "Lossless"
    }
    
    return result_bytes, stats
