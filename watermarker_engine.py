import io
import os
import re
import hashlib
from datetime import datetime
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from translitua import translit

"""
Watermarker Pro Engine v4.8 (FULL)
---------------------------
Features:
- Text Watermark generation
- EXIF metadata preservation
- Advanced diagonal tiling
- Validation & Error handling
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

def generate_filename(original_name: str, naming_mode: str, prefix: str = "", extension: str = "jpg", index: int = 1, file_bytes: bytes = None) -> str:
    """Генерує безпечне та унікальне ім'я файлу."""
    clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-') if prefix else ""
    
    if naming_mode == "Prefix + Sequence":
        base_name = clean_prefix if clean_prefix else "image"
        return f"{base_name}_{index:03d}.{extension}"
    
    name_only = os.path.splitext(original_name)[0]
    slug = re.sub(r'[\s\W_]+', '-', translit(name_only).lower()).strip('-')
    if not slug: slug = "image"
    
    base = f"{clean_prefix}_{slug}" if clean_prefix else slug

    if naming_mode == "Content Hash" and file_bytes:
        file_hash = hashlib.md5(file_bytes).hexdigest()[:8]
        return f"{base}_{file_hash}.{extension}"
    elif naming_mode == "Original + Suffix":
        return f"{base}_wm.{extension}"
    elif naming_mode == "Timestamp":
        timestamp = datetime.now().strftime('%H%M%S_%f')[:9]
        return f"{base}_{timestamp}.{extension}"
    else: 
        return f"{base}.{extension}"


def get_image_metadata(file_bytes: bytes) -> tuple:
    """Отримує метадані зображення з валідацією."""
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            if img.width == 0 or img.height == 0:
                raise ValueError("Invalid image dimensions")
            return img.width, img.height, len(file_bytes), img.format
    except Exception as e:
        return 0, 0, len(file_bytes), None


def create_text_watermark(text: str, font_size: int = 50, color_hex: str = "#FFFFFF", opacity: float = 1.0) -> Image.Image:
    """Генерує зображення з тексту для використання як вотермарки."""
    dummy_img = Image.new('RGBA', (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)
    
    try:
        # Спроба завантажити системні шрифти
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_size) # Linux/Streamlit Cloud
            except IOError:
                font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # +20px padding
    wm = Image.new('RGBA', (text_w + 20, text_h + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wm)
    
    color_hex = color_hex.lstrip('#')
    rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    
    draw.text((10, 10), text, font=font, fill=rgb + (255,))
    
    if opacity < 1.0:
        alpha = wm.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        wm.putalpha(alpha)
        
    return wm


def load_and_process_watermark(wm_source, opacity: float, is_text: bool = False, text_params: dict = None) -> Image.Image:
    """Універсальний завантажувач вотермарки (Файл або Текст)."""
    if is_text and text_params:
        return create_text_watermark(
            text_params.get('text', 'Copyright'), 
            text_params.get('size', 50),
            text_params.get('color', '#FFFFFF'),
            opacity
        )
    
    if not wm_source:
        return None
    
    try:
        wm = Image.open(io.BytesIO(wm_source)).convert("RGBA")
        if wm.width < 10 or wm.height < 10:
            raise ValueError("Watermark too small (min 10x10px)")
        
        if opacity < 1.0:
            alpha = wm.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
            wm.putalpha(alpha)
            
        return wm
    except Exception as e:
        raise ValueError(f"Failed to load watermark: {str(e)}")


def process_image(file_bytes: bytes, filename: str, wm_obj: Image.Image, resize_config: dict, output_fmt: str, quality: int, keep_exif: bool = False) -> tuple:
    """Основна функція обробки."""
    input_io = io.BytesIO(file_bytes)
    img = Image.open(input_io)
    
    # EXIF Logic
    exif_data = img.info.get('exif') if keep_exif else None
    
    orig_w, orig_h = img.size
    orig_format = img.format
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
        
        if scale > 0.9: scale = 0.9
        
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
            if position == 'bottom-right': pos_x, pos_y = new_w - wm_w_final - margin, new_h - wm_h_final - margin
            elif position == 'bottom-left': pos_x, pos_y = margin, new_h - wm_h_final - margin
            elif position == 'top-right': pos_x, pos_y = new_w - wm_w_final - margin, margin
            elif position == 'top-left': pos_x, pos_y = margin, margin
            elif position == 'center': pos_x, pos_y = (new_w - wm_w_final) // 2, (new_h - wm_h_final) // 2
            
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
    if keep_exif and exif_data:
        save_kwargs['exif'] = exif_data

    if output_fmt == "JPEG":
        img.save(output_buffer, format="JPEG", quality=quality, optimize=True, subsampling=0, **save_kwargs)
    elif output_fmt == "WEBP":
        img.save(output_buffer, format="WEBP", quality=quality, method=6, **save_kwargs)
    elif output_fmt == "PNG":
        img.save(output_buffer, format="PNG", optimize=True, **save_kwargs)

    result_bytes = output_buffer.getvalue()
    
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
