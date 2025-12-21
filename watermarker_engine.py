import io
import os
import re
import hashlib
from datetime import datetime
from PIL import Image, ImageEnhance, ImageOps
from translitua import translit

"""
Watermarker Pro Engine v4.8 (Stable Core)
-----------------------------------------
Changelog:
- Switched from In-Memory bytes to TempFile paths (OOM protection)
- Added Thumbnail generation for Grid View
- Optimized EXIF handling
"""

# === CONFIG ===
DEFAULT_CONFIG = {
    'wm_scale': 0.15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0,
    'wm_position': 'bottom-right'
}

def generate_filename(original_path: str, naming_mode: str, prefix: str = "", extension: str = "jpg", index: int = 1) -> str:
    """Генерує безпечне та унікальне ім'я файлу на основі шляху."""
    original_name = os.path.basename(original_path)
    clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-') if prefix else ""
    
    if naming_mode == "Prefix + Sequence":
        base_name = clean_prefix if clean_prefix else "image"
        return f"{base_name}_{index:03d}.{extension}"
    
    name_only = os.path.splitext(original_name)[0]
    slug = re.sub(r'[\s\W_]+', '-', translit(name_only).lower()).strip('-')
    if not slug: slug = "image"
    
    base = f"{clean_prefix}_{slug}" if clean_prefix else slug

    if naming_mode == "Original + Suffix":
        return f"{base}_wm.{extension}"
    elif naming_mode == "Timestamp":
        timestamp = datetime.now().strftime('%H%M%S_%f')[:9]
        return f"{base}_{timestamp}.{extension}"
    else: 
        return f"{base}.{extension}"

def get_image_metadata(file_path: str) -> tuple:
    """Отримує метадані зображення з файлу на диску."""
    try:
        with Image.open(file_path) as img:
            file_size = os.path.getsize(file_path)
            return img.width, img.height, file_size, img.format
    except Exception:
        return 0, 0, 0, None

def get_thumbnail(file_path: str, size=(300, 300)) -> Image.Image:
    """
    Створює мініатюру.
    Для оптимізації зберігає кеш-файл .thumb поруч з оригіналом.
    """
    thumb_path = f"{file_path}.thumb"
    
    # Якщо мініатюра вже є - повертаємо її
    if os.path.exists(thumb_path):
        try:
            return Image.open(thumb_path)
        except:
            pass # Якщо бита, перестворюємо
            
    try:
        with Image.open(file_path) as img:
            # Конвертуємо в RGB для сумісності (наприклад, якщо CMYK)
            img = img.convert('RGB')
            # Smart crop або thumbnail
            img.thumbnail(size)
            # Зберігаємо кеш
            img.save(thumb_path, "JPEG", quality=60)
            return img
    except Exception as e:
        print(f"Thumb error: {e}")
        return None

def load_and_process_watermark(wm_file_bytes: bytes, opacity: float) -> Image.Image:
    """Завантажує та готує зображення водяного знаку (залишається в RAM, бо мале)."""
    if not wm_file_bytes:
        return None
    try:
        wm = Image.open(io.BytesIO(wm_file_bytes)).convert("RGBA")
        if wm.width < 10 or wm.height < 10:
            raise ValueError("Watermark too small (min 10x10px)")
        
        if opacity < 1.0:
            alpha = wm.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
            wm.putalpha(alpha)
        return wm
    except Exception as e:
        raise ValueError(f"Failed to load watermark: {str(e)}")

def process_image(file_path: str, filename: str, wm_obj: Image.Image, resize_config: dict, output_fmt: str, quality: int) -> tuple:
    """Основна функція обробки. Приймає шлях до файлу."""
    
    # Використовуємо контекстний менеджер для автоматичного закриття файлу
    with Image.open(file_path) as img:
        # Збереження EXIF (поки що просте копіювання, якщо формат підтримує)
        exif_dict = img.info.get('exif')
        
        orig_w, orig_h = img.size
        orig_format = img.format
        orig_size = os.path.getsize(file_path)
        
        img = img.convert("RGBA")
        
        # --- RESIZE LOGIC ---
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

        # --- WATERMARK LOGIC ---
        if wm_obj:
            scale = resize_config.get('wm_scale', DEFAULT_CONFIG['wm_scale'])
            position = resize_config.get('wm_position', DEFAULT_CONFIG['wm_position'])
            angle = resize_config.get('wm_angle', DEFAULT_CONFIG['wm_angle'])
            
            if scale > 0.8: scale = 0.8
            
            wm_w_target = int(new_w * scale)
            if wm_w_target < 1: wm_w_target = 1
            
            w_ratio = wm_w_target / float(wm_obj.width)
            wm_h_target = int(float(wm_obj.height) * w_ratio)
            if wm_h_target < 1: wm_h_target = 1
            
            wm_resized = wm_obj.resize((wm_w_target, wm_h_target), Image.Resampling.LANCZOS)

            if angle != 0:
                wm_resized = wm_resized.rotate(angle, expand=True, resample=Image.BICUBIC)

            wm_w_final, wm_h_final = wm_resized.size

            if position == 'tiled':
                gap = resize_config.get('wm_gap', DEFAULT_CONFIG['wm_gap'])
                overlay = Image.new('RGBA', (new_w, new_h), (0, 0, 0, 0))
                step_x = wm_w_final + gap
                step_y = wm_h_final + gap
                if step_x < 10: step_x = 10
                if step_y < 10: step_y = 10
                
                rows_needed = (new_h // step_y) + 3
                cols_needed = (new_w // step_x) + 3
                
                for row in range(-1, rows_needed):
                    for col in range(-1, cols_needed):
                        x = col * step_x + (row * step_x // 2)
                        y = row * step_y
                        if x + wm_w_final > 0 and x < new_w and y + wm_h_final > 0 and y < new_h:
                            overlay.paste(wm_resized, (x, y), wm_resized)
                img = Image.alpha_composite(img, overlay)
            else:
                margin = resize_config.get('wm_margin', DEFAULT_CONFIG['wm_margin'])
                pos_x, pos_y = 0, 0
                if position == 'bottom-right': 
                    pos_x, pos_y = new_w - wm_w_final - margin, new_h - wm_h_final - margin
                elif position == 'bottom-left': 
                    pos_x, pos_y = margin, new_h - wm_h_final - margin
                elif position == 'top-right': 
                    pos_x, pos_y = new_w - wm_w_final - margin, margin
                elif position == 'top-left': 
                    pos_x, pos_y = margin, margin
                elif position == 'center': 
                    pos_x, pos_y = (new_w - wm_w_final) // 2, (new_h - wm_h_final) // 2
                
                pos_x = max(0, min(pos_x, new_w - wm_w_final))
                pos_y = max(0, min(pos_y, new_h - wm_h_final))
                img.paste(wm_resized, (pos_x, pos_y), wm_resized)

        # --- EXPORT ---
        if output_fmt == "JPEG":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif output_fmt == "RGB":
            img = img.convert("RGB")

        output_buffer = io.BytesIO()
        
        save_kwargs = {}
        if output_fmt == "JPEG":
            save_kwargs = {"format": "JPEG", "quality": quality, "optimize": True, "subsampling": 0}
            if exif_dict: save_kwargs["exif"] = exif_dict
        elif output_fmt == "WEBP":
            save_kwargs = {"format": "WEBP", "quality": quality, "method": 6}
            if exif_dict: save_kwargs["exif"] = exif_dict
        elif output_fmt == "PNG":
            save_kwargs = {"format": "PNG", "optimize": True}
            if exif_dict: save_kwargs["exif"] = exif_dict

        img.save(output_buffer, **save_kwargs)
        result_bytes = output_buffer.getvalue()
        
        stats = {
            "filename": filename,
            "orig_res": f"{orig_w}x{orig_h}",
            "new_res": f"{new_w}x{new_h}",
            "orig_size": orig_size,
            "new_size": len(result_bytes),
            "orig_fmt": orig_format or "Unknown",
            "scale_factor": f"{scale_factor:.2f}x",
            "quality": quality if output_fmt != "PNG" else "Lossless"
        }
        
        return result_bytes, stats
