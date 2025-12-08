import streamlit as st
from PIL import Image, ImageDraw
from translitua import translit
import io
import zipfile
from datetime import datetime
import re

# --- Налаштування сторінки ---
st.set_page_config(page_title="Watermarker Web", page_icon="📸", layout="centered")

# --- Логіка (функції з вашої програми) ---
def create_safe_filename(original_filename, prefix=""):
    name_only, ext = original_filename.rsplit('.', 1)
    if prefix:
        clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-')
        date_str = datetime.now().strftime('%d-%m-%Y')
        # Додаємо мікросекунди для унікальності в вебі
        unique_id = datetime.now().strftime('%f')[:3] 
        return f"{clean_prefix}-{date_str}-{unique_id}.jpg"
    else:
        slug = translit(name_only).lower()
        slug = re.sub(r'[\s\W_]+', '-', slug).strip('-')
        if not slug: slug = "image"
        return f"{slug}.jpg"

def process_image(image_file, watermark_file, max_dim, quality, wm_scale, wm_margin, wm_position, resize_on):
    img = Image.open(image_file).convert("RGBA")
    
    # 1. Ресайз
    if resize_on and (img.width > max_dim or img.height > max_dim):
        if img.width >= img.height:
            ratio = max_dim / float(img.width)
            new_width, new_height = max_dim, int(float(img.height) * ratio)
        else:
            ratio = max_dim / float(img.height)
            new_width, new_height = int(float(img.width) * ratio), max_dim
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 2. Вотермарка
    if watermark_file:
        wm = Image.open(watermark_file).convert("RGBA")
        new_wm_width = int(img.width * wm_scale)
        w_ratio = new_wm_width / float(wm.width)
        new_wm_height = int(float(wm.height) * w_ratio)
        wm = wm.resize((new_wm_width, new_wm_height), Image.Resampling.LANCZOS)
        
        x, y = 0, 0
        if wm_position == 'bottom-right': x, y = img.width - wm.width - wm_margin, img.height - wm.height - wm_margin
        elif wm_position == 'bottom-left': x, y = wm_margin, img.height - wm.height - wm_margin
        elif wm_position == 'top-right': x, y = img.width - wm.width - wm_margin, wm_margin
        elif wm_position == 'top-left': x, y = wm_margin, wm_margin
        elif wm_position == 'center': x, y = (img.width - wm.width) // 2, (img.height - wm.height) // 2
        
        img.paste(wm, (x, y), wm)

    # 3. Збереження в буфер пам'яті
    img = img.convert("RGB")
    output_buffer = io.BytesIO()
    img.save(output_buffer, format="JPEG", quality=quality)
    output_buffer.seek(0)
    return output_buffer

# --- Інтерфейс ---
st.title("📸 Watermarker Web")
st.markdown("Завантажте фото, накладіть логотип та змініть розмір.")

# Сайдбар з налаштуваннями
with st.sidebar:
    st.header("Налаштування")
    
    prefix = st.text_input("Префікс назви", placeholder="напр. vidpustka")
    
    st.subheader("Зображення")
    resize_on = st.checkbox("Зменшувати зображення", value=True)
    if resize_on:
        max_dim = st.select_slider("Макс. сторона (px)", options=[800, 1024, 1280, 1920, 3840], value=1920)
    else:
        max_dim = 0
        
    quality = st.slider("Якість JPEG", 70, 100, 80, 5)
    
    st.subheader("Водяний знак")
    wm_file = st.file_uploader("Файл логотипа (PNG)", type=["png"])
    if wm_file:
        wm_pos = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
        wm_scale = st.slider("Розмір (%)", 5, 50, 15) / 100
        wm_margin = st.slider("Відступ (px)", 0, 100, 15)

# Головна область
uploaded_files = st.file_uploader("Виберіть фотографії (JPG, PNG)", type=['png', 'jpg', 'jpeg', 'bmp'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"Обробити {len(uploaded_files)} зображень", type="primary"):
        # Створюємо прогрес-бар
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Архів для результатів
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, file in enumerate(uploaded_files):
                status_text.text(f"Обробка: {file.name}")
                
                # Обробка
                processed_img_io = process_image(
                    file, wm_file, max_dim, quality, 
                    wm_scale if wm_file else 0, 
                    wm_margin if wm_file else 0, 
                    wm_pos if wm_file else None,
                    resize_on
                )
                
                # Нове ім'я
                new_name = create_safe_filename(file.name, prefix)
                
                # Додаємо в архів
                zf.writestr(new_name, processed_img_io.getvalue())
                
                # Оновлюємо прогрес
                progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.text("Готово! ✅")
        zip_buffer.seek(0)
        
        # Кнопка завантаження
        st.download_button(
            label="⬇️ Завантажити архів ZIP",
            data=zip_buffer,
            file_name=f"photos_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip"
        )