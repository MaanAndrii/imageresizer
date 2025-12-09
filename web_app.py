import streamlit as st
from PIL import Image
from translitua import translit
import io
import zipfile
from datetime import datetime
import re

st.set_page_config(page_title="Watermarker Web", page_icon="📸", layout="centered")

# --- Функції (оновлені для форматів) ---
def get_safe_filename(original_filename, prefix="", extension="jpg"):
    name_only = original_filename.rsplit('.', 1)[0]
    if prefix:
        clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-')
        return f"{clean_prefix}_{datetime.now().strftime('%H%M%S')}.{extension}"
    else:
        slug = translit(name_only).lower()
        slug = re.sub(r'[\s\W_]+', '-', slug).strip('-')
        if not slug: slug = "image"
        return f"{slug}.{extension}"

def process_single_image(uploaded_file, wm_image, max_dim, quality, wm_settings, output_format):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    
    # Конвертація для збереження (JPEG не вміє в прозорість)
    if output_format == "JPEG":
        img = img.convert("RGB")
    else:
        img = img.convert("RGBA")

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
        
        # Для коректного накладання вотермарки на RGB зображення
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            img.paste(wm_resized, (x, y), wm_resized)
            if output_format == "JPEG":
                img = img.convert('RGB')
        else:
            img.paste(wm_resized, (x, y), wm_resized)

    # 3. Збереження
    output_buffer = io.BytesIO()
    
    if output_format == "JPEG":
        img.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    elif output_format == "WEBP":
        img.save(output_buffer, format="WEBP", quality=quality, method=6)
    elif output_format == "PNG":
        img.save(output_buffer, format="PNG", optimize=True)

    # 4. Перевірка розміру (тільки якщо без вотермарки і не змінено формат)
    is_same_format = (uploaded_file.name.lower().endswith('.jpg') or uploaded_file.name.lower().endswith('.jpeg')) and output_format == "JPEG"
    
    if not wm_image and is_same_format and output_buffer.getbuffer().nbytes > original_size:
        uploaded_file.seek(0)
        return uploaded_file.read()
        
    return output_buffer.getvalue()

# --- ІНТЕРФЕЙС ---

st.title("📸 Smart Resizer & Watermarker")

# === ГОЛОВНА ЧАСТИНА: ЗАВАНТАЖЕННЯ ===
uploaded_files = st.file_uploader(
    "📤 Крок 1. Виберіть фотографії", 
    type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
    accept_multiple_files=True
)

# === САЙДБАР (НАЛАШТУВАННЯ) ===
with st.sidebar:
    st.header("⚙️ Налаштування")
    
    # 1. Формат (НОВЕ)
    st.subheader("1. Вихідний формат")
    out_fmt = st.selectbox("Формат файлу", ["JPEG", "WEBP", "PNG"], help="WEBP дає найкраще стиснення")
    
    # 2. Назва
    st.subheader("2. Назва файлів")
    prefix = st.text_input("Префікс", placeholder="напр. photo")
    
    # 3. Розміри
    st.subheader("3. Розміри та Якість")
    resize_enabled = st.checkbox("Зменшувати розмір", value=True)
    max_dim = 0
    if resize_enabled:
        max_dim = st.select_slider("Макс. сторона (px)", options=[800, 1024, 1280, 1920, 3840], value=1920)
    
    quality = 80
    if out_fmt != "PNG":
        quality = st.slider("Якість", 50, 100, 80, 5)

    # 4. Вотермарка
    st.subheader("4. Водяний знак")
    wm_file_upload = st.file_uploader("Логотип (PNG)", type=["png"])
    
    wm_settings = {}
    if wm_file_upload:
        wm_settings['position'] = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
        wm_settings['scale'] = st.slider("Розмір (%)", 5, 50, 15) / 100
        wm_settings['margin'] = st.slider("Відступ (px)", 0, 100, 15)

    # === КАЛЬКУЛЯТОР ЕКОНОМІЇ (НОВЕ) ===
    if uploaded_files:
        st.markdown("---")
        st.subheader("📊 Прогноз економії")
        
        # Беремо перше фото для тесту
        sample_file = uploaded_files[0]
        wm_obj_sample = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
        
        # Обробляємо його
        try:
            sample_result = process_single_image(
                sample_file, wm_obj_sample, max_dim, quality, 
                wm_settings if wm_obj_sample else None, out_fmt
            )
            
            orig_size = sample_file.getbuffer().nbytes
            new_size = len(sample_result)
            
            # Відображаємо метрики
            col1, col2 = st.columns(2)
            col1.metric("Було", f"{orig_size/1024:.1f} KB")
            
            # Розрахунок дельти (зелена якщо менше, червона якщо більше)
            delta_color = "normal" 
            if new_size < orig_size: delta_color = "inverse" # зелений у streamlit
            
            col2.metric(
                "Стало", 
                f"{new_size/1024:.1f} KB", 
                f"{((new_size - orig_size) / orig_size) * 100:.1f}%",
                delta_color="normal" if new_size > orig_size else "inverse"
            )
            
            # Візуальна шкала
            if new_size < orig_size:
                saved_percent = 1.0 - (new_size / orig_size)
                st.write(f"Виграш місця: **{saved_percent*100:.1f}%**")
                st.progress(saved_percent)
            else:
                st.warning("Файл може збільшитися (змініть формат або якість)")
                
        except Exception as e:
            st.error("Помилка попереднього перегляду")

# === ЗАПУСК ОБРОБКИ ===

if uploaded_files:
    if st.button(f"🚀 Обробити всі зображення ({len(uploaded_files)} шт)", type="primary"):
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_orig_size = 0
        total_new_size = 0
        
        zip_buffer = io.BytesIO()
        wm_obj = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None

        with zipfile.ZipFile(zip_buffer, "w") as zf:
            total_files = len(uploaded_files)
            
            for i, file in enumerate(uploaded_files):
                status_text.text(f"Обробка: {file.name}...")
                total_orig_size += file.getbuffer().nbytes
                
                try:
                    processed_bytes = process_single_image(
                        file, wm_obj, max_dim, quality, 
                        wm_settings if wm_obj else None, out_fmt
                    )
                    
                    total_new_size += len(processed_bytes)
                    
                    # Визначаємо розширення
                    ext = "jpg"
                    if out_fmt == "PNG": ext = "png"
                    elif out_fmt == "WEBP": ext = "webp"
                    
                    new_name = get_safe_filename(file.name, prefix, ext)
                    zf.writestr(new_name, processed_bytes)
                    
                except Exception as e:
                    st.error(f"Помилка: {e}")
                
                progress_bar.progress((i + 1) / total_files)
        
        progress_bar.progress(100)
        status_text.success("✅ Готово!")
        
        # === ПІДСУМКОВА СТАТИСТИКА ===
        st.success(f"Загальний розмір зменшено з **{total_orig_size/1024/1024:.2f} MB** до **{total_new_size/1024/1024:.2f} MB**")
        
        zip_buffer.seek(0)
        st.download_button(
            label="⬇️ Завантажити ZIP-архів",
            data=zip_buffer,
            file_name=f"processed_{datetime.now().strftime('%H%M')}.zip",
            mime="application/zip",
            type="primary"
        )
