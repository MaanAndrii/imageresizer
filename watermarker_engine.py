import io
import os
import re
import base64
from datetime import datetime
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont
from translitua import translit

"""
Watermarker Pro Engine v5.6 (Editor Support)
--------------------------------------------
Updates:
- Added rotate_image_file() for permanent rotation
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

# --- HELPERS ---
def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode('utf-8')

def base64_to_bytes(base64_string: str) -> bytes:
    return base64.b64decode(base64_string)

def generate_filename(original_path: str, naming_mode: str, prefix: str = "", extension: str = "jpg", index: int = 1) -> str:
    original_name = os.path.basename(original_path)
    clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-') if prefix else ""
    
    if naming_mode == "Prefix + Sequence":
        base_name = clean_prefix if clean_prefix else "image"
        return f"{base_name}_{index:03d}.{extension}"
    
    name_only = os.path.splitext(original_name)[0]
    slug = re.sub(r'[\s\W_]+', '-', translit(name_only).lower()).strip('-')
    if not slug: slug = "image"
    
    base = f"{clean_prefix}_{slug}" if clean_prefix else slug
    return f"{base}.{extension}"

def get_thumbnail(file_path: str, size=(300, 300)) -> str:
    thumb_path = f"{file_path}.thumb.jpg"
    # Якщо файл існує, повертаємо його.
    # ВАЖЛИВО: Для v5.6 ми будемо видаляти thumb при редагуванні, тому ця перевірка коректна.
    if os.path.exists(thumb_path): return thumb_path
    try:
        with Image.open(file_path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert('RGB')
            img.thumbnail(size)
            img.save(thumb_path, "JPEG", quality=70)
            return thumb_path
    except Exception as e:
        print(f"Thumb error: {e}")
        return None

def rotate_image_file(file_path: str, angle: int):
    """Повертає зображення на диску на заданий кут (90/-90) і перезаписує його."""
    try:
        with Image.open(file_path) as img:
            # Фікс орієнтації перед поворотом, щоб не було сюрпризів
            img = ImageOps.exif_transpose(img)
            # Expand=True змінює розмір полотна, щоб фото не обрізалось
            rotated = img.rotate(angle, expand=True)
            rotated.save(file_path, quality=95, subsampling=0)
        
        # Очищуємо кеш мініатюри, бо вона тепер неактуальна
        thumb_path = f"{file_path}.thumb.jpg"
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        return True
    except Exception as e:
        print(f"Rotate error: {e}")
        return False

def load_watermark_from_file(wm_file_bytes: bytes) -> Image.Image:
    if not wm_file_bytes: return None
    try:
        wm = Image.open(io.BytesIO(wm_file_bytes)).convert("RGBA")
        return wm
    except Exception as e:
        raise ValueError(f"Failed to load logo: {str(e)}")

def create_text_watermark(text: str, font_path: str, size_pt: int, color_hex: str) -> Image.Image:
    if not text: return None
    try:
        font = ImageFont.truetype(font_path, size_pt) if font_path else ImageFont.load_default()
    except:
        font = ImageFont.load_default()
        
    dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    wm = Image.new('RGBA', (w + 20, h + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wm)
    
    color = color_hex.lstrip('#')
    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    
    draw.text((10, 10), text, font=font, fill=rgb + (255,))
    return wm

def apply_opacity(image: Image.Image, opacity: float) -> Image.Image:
    if opacity >= 1.0: return image
    alpha = image.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    image.putalpha(alpha)
    return image

def process_image(file_path: str, filename: str, wm_obj: Image.Image, resize_config: dict, output_fmt: str, quality: int) -> tuple:
    with Image.open(file_path) as img:
        img = ImageOps.exif_transpose(img)
        exif_data = img.info.get('exif')
        
        orig_w, orig_h = img.size
        orig_size = os.path.getsize(file_path)
        img = img.convert("RGBA")
        
        # Resize
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

        # Watermark
        if wm_obj:
            scale = resize_config.get('wm_scale', DEFAULT_CONFIG['wm_scale'])
            position = resize_config.get('wm_position', DEFAULT_CONFIG['wm_position'])
            angle = resize_config.get('wm_angle', DEFAULT_CONFIG['wm_angle'])
            
            if scale > 0.9: scale = 0.9
            
            wm_w_target = int(new_w * scale)
            if wm_w_target < 10: wm_w_target = 10
            
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

        # Export
        if output_fmt == "JPEG":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif output_fmt == "RGB":
            img = img.convert("RGB")

        output_buffer = io.BytesIO()
        save_kwargs = {}
        if exif_data: save_kwargs['exif'] = exif_data

        if output_fmt == "JPEG":
            save_kwargs.update({"format": "JPEG", "quality": quality, "optimize": True, "subsampling": 0})
        elif output_fmt == "WEBP":
            save_kwargs.update({"format": "WEBP", "quality": quality, "method": 6})
        elif output_fmt == "PNG":
            save_kwargs.update({"format": "PNG", "optimize": True})

        img.save(output_buffer, **save_kwargs)
        result_bytes = output_buffer.getvalue()
        
        stats = {
            "filename": filename,
            "orig_res": f"{orig_w}x{orig_h}",
            "new_res": f"{new_w}x{new_h}",
            "orig_size": orig_size,
            "new_size": len(result_bytes),
            "scale_factor": f"{scale_factor:.2f}x"
        }
        return result_bytes, stats
