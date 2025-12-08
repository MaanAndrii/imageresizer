import streamlit as st
from PIL import Image
from translitua import translit
import io
import zipfile
from datetime import datetime
import re

# --- Налаштування сторінки ---
st.set_page_config(page_title="Watermarker Web", page_icon="📸", layout="centered")

# --- Логіка обробки ---
def get_safe_filename(original_filename, prefix=""):
    """Створює безпечне ім'я файлу."""
    name_only = original_filename.rsplit('.', 1)[0]
    if prefix:
        clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-')
        return f"{clean_prefix}_{datetime.now().strftime('%H%M%S')}.jpg"
    else:
        slug = translit(name_only).lower()
        slug = re.sub(r'[\s\W_]+', '-', slug).strip('-')
        if not slug: slug = "image"
        return f"{slug}.jpg"

def process_single_image(uploaded_file, wm_image, max_dim, quality, wm_settings):
    """Обробляє зображення в пам'яті."""
    img = Image.open(uploaded_file).convert("RGBA")
    original_size = uploaded_file.getbuffer().nbytes
    
    # 1. Ресайз
    if max_dim > 0 and (img.width > max_dim or img.height > max_dim):
        if img.width >= img.height:
            ratio = max_dim / float(img.width)
            new_width, new_height = max_dim, int(float(img.height) * ratio)
        else:
            ratio = max_dim / float(img.height)
            new_width, new_height = int(float(img.width) * ratio), max_dim
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 2. Вотермарка
    if wm_image:
        scale = wm_settings['scale']
        margin = wm_settings['margin']
        position = wm_settings['position']
        
        new_wm_width = int(img.width * scale)
        w_ratio = new_wm_width / float(wm_image.width)
        new_wm_height = int(float(wm_image.height) * w_ratio)
        wm_resized = wm_image.resize((new_wm_width, new_wm_height), Image.Resampling.LANCZOS)
        
        x, y = 0, 0
        if position == 'bottom-right': x, y = img.width - wm_resized.width - margin, img.height - wm_resized.height - margin
        elif position == 'bottom-left': x, y = margin, img.height - wm_resized.height - margin
        elif position == 'top-right': x, y = img.width - wm_resized.width - margin, margin
        elif position == 'top-left': x, y = margin, margin
        elif position == 'center': x, y = (img.width - wm_resized.width) // 2, (img.height - wm_resized.height) // 2
        
        img.paste(wm_resized, (x, y), wm_resized)

    # 3. Збереження
    img = img.convert("RGB")
    output_buffer = io.BytesIO()
    img.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    
    # 4. Перевірка розміру (якщо без вотермарки)
    if not wm_image and output_buffer.getbuffer().nbytes > original_size:
        uploaded_file.seek(0)
        return uploaded_file.read()
        
    return output_buffer.getvalue()

# --- ВЕБ ІНТЕРФЕЙС ---

st.title("📸 Watermarker & Resizer")
st.write("Онлайн інструмент для зменшення фото та накладання логотипа.")

# === САЙДБАР (НАЛАШТУВАННЯ) ===
with st.sidebar:
    st.header("⚙️ Налаштування")
    
    # 1. Назва
    st.subheader("1. Назва файлів")
    prefix = st.text_input("Префікс (необов'язково)", placeholder="напр. vidpustka")
    
    # 2. Розміри
    st.subheader("2. Розміри та Якість")
    resize_enabled = st.checkbox("Зменшувати розмір", value=True)
    
    max_dim = 0
    if resize_enabled:
        # ЗМІНЕНО: Використовуємо select_slider для фіксованих значень
        max_dim = st.select_slider(
            "Макс. сторона (px)", 
            options=[800, 1024, 1280, 1920, 3840], 
            value=3840
        )
    
    quality = st.slider("Якість JPEG", 70, 100, 80, 5)

    # 3. Вотермарка
    st.subheader("3. Водяний знак")
    wm_file_upload = st.file_uploader("Завантажити лого (PNG)", type=["png"])
    
    wm_settings = {}
    if wm_file_upload:
        st.info("Логотип активовано!")
        wm_settings['position'] = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
        wm_settings['scale'] = st.slider("Розмір лого (%)", 5, 50, 15) / 100
        wm_settings['margin'] = st.slider("Відступ (px)", 0, 100, 15)

# === ГОЛОВНА ЧАСТИНА ===

uploaded_files = st.file_uploader(
    "📤 Перетягніть фото сюди (можна багато)", 
    type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button(f"🚀 Обробити {len(uploaded_files)} зображень", type="primary"):
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            total_files = len(uploaded_files)
            for i, file in enumerate(uploaded_files):
                status_text.text(f"Обробка: {file.name}...")
                try:
                    # Підготовка вотермарки
                    wm_obj = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
                    
                    processed_bytes = process_single_image(
                        file, wm_obj, max_dim, quality, wm_settings if wm_obj else None
                    )
                    new_name = get_safe_filename(file.name, prefix)
                    zf.writestr(new_name, processed_bytes)
                except Exception as e:
                    st.error(f"Помилка: {e}")
                
                progress_bar.progress((i + 1) / total_files)
        
        progress_bar.progress(100)
        status_text.success("✅ Готово!")
        zip_buffer.seek(0)
        
        st.download_button(
            label="⬇️ Завантажити ZIP-архів",
            data=zip_buffer,
            file_name=f"photos_{datetime.now().strftime('%H%M')}.zip",
            mime="application/zip",
            type="primary"
        )
