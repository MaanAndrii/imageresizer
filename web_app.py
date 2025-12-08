import streamlit as st
from PIL import Image
from translitua import translit
import io
import zipfile
from datetime import datetime
import re

# --- Налаштування сторінки ---
st.set_page_config(page_title="Watermarker Web", page_icon="📸", layout="centered")

# --- Чиста логіка обробки (адаптована для пам'яті) ---
def get_safe_filename(original_filename, prefix=""):
    """Створює безпечне ім'я файлу для веб-завантаження."""
    name_only = original_filename.rsplit('.', 1)[0]
    if prefix:
        clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-')
        # Додаємо час для унікальності
        return f"{clean_prefix}_{datetime.now().strftime('%H%M%S')}.jpg"
    else:
        slug = translit(name_only).lower()
        slug = re.sub(r'[\s\W_]+', '-', slug).strip('-')
        if not slug: slug = "image"
        return f"{slug}.jpg"

def process_single_image(uploaded_file, wm_image, max_dim, quality, wm_settings):
    """
    Обробляє одне зображення в пам'яті.
    Повертає bytes (готовий JPEG).
    """
    # Читаємо зображення з пам'яті
    img = Image.open(uploaded_file).convert("RGBA")
    original_size = uploaded_file.getbuffer().nbytes
    
    # 1. Ресайз (Зміна розміру)
    if max_dim > 0 and (img.width > max_dim or img.height > max_dim):
        if img.width >= img.height:
            ratio = max_dim / float(img.width)
            new_width, new_height = max_dim, int(float(img.height) * ratio)
        else:
            ratio = max_dim / float(img.height)
            new_width, new_height = int(float(img.width) * ratio), max_dim
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 2. Накладання вотермарки
    if wm_image:
        scale = wm_settings['scale']
        margin = wm_settings['margin']
        position = wm_settings['position']
        
        # Ресайз вотермарки відносно фото
        new_wm_width = int(img.width * scale)
        w_ratio = new_wm_width / float(wm_image.width)
        new_wm_height = int(float(wm_image.height) * w_ratio)
        wm_resized = wm_image.resize((new_wm_width, new_wm_height), Image.Resampling.LANCZOS)
        
        # Позиціонування
        x, y = 0, 0
        if position == 'bottom-right': x, y = img.width - wm_resized.width - margin, img.height - wm_resized.height - margin
        elif position == 'bottom-left': x, y = margin, img.height - wm_resized.height - margin
        elif position == 'top-right': x, y = img.width - wm_resized.width - margin, margin
        elif position == 'top-left': x, y = margin, margin
        elif position == 'center': x, y = (img.width - wm_resized.width) // 2, (img.height - wm_resized.height) // 2
        
        img.paste(wm_resized, (x, y), wm_resized)

    # 3. Конвертація та збереження в буфер
    img = img.convert("RGB")
    output_buffer = io.BytesIO()
    img.save(output_buffer, format="JPEG", quality=quality, optimize=True)
    
    # 4. Перевірка на "роздування" файлу (тільки якщо без вотермарки)
    # Якщо вотермарка є - ми мусимо зберегти новий файл, навіть якщо він більший.
    # Якщо вотермарки немає - ми повертаємо оригінал, якщо новий файл вийшов більшим.
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
    
    # Секція 1: Текст
    st.subheader("1. Назва файлів")
    prefix = st.text_input("Префікс (необов'язково)", placeholder="напр. vidpustka")
    
    # Секція 2: Ресайз
    st.subheader("2. Розміри та Якість")
    resize_enabled = st.checkbox("Зменшувати розмір", value=True)
    
    max_dim = 0
    if resize_enabled:
        # Використовуємо ваші стандартні розміри
        max_dim = st.selectbox(
            "Макс. сторона (px)", 
            options=[800, 1024, 1280, 1920, 3840], 
            index=4 # 3840 за замовчуванням
        )
    
    quality = st.slider("Якість JPEG", min_value=70, max_value=100, value=80, step=5)

    # Секція 3: Вотермарка
    st.subheader("3. Водяний знак")
    wm_file_upload = st.file_uploader("Завантажити лого (PNG)", type=["png"])
    
    wm_settings = {}
    if wm_file_upload:
        st.info("Логотип завантажено! Налаштування активовано.")
        wm_settings['position'] = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
        wm_settings['scale'] = st.slider("Розмір (%)", 5, 50, 15) / 100
        wm_settings['margin'] = st.slider("Відступ (px)", 0, 100, 15)

# === ГОЛОВНА ЧАСТИНА ===

uploaded_files = st.file_uploader(
    "📤 Перетягніть фото сюди (можна багато)", 
    type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
    accept_multiple_files=True
)

if uploaded_files:
    # Кнопка запуску
    if st.button(f"🚀 Обробити {len(uploaded_files)} зображень", type="primary"):
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Підготовка вотермарки (один раз)
        wm_image_obj = None
        if wm_file_upload:
            wm_image_obj = Image.open(wm_file_upload).convert("RGBA")

        # Архів для результату
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            total_files = len(uploaded_files)
            
            for i, file in enumerate(uploaded_files):
                status_text.text(f"Обробка: {file.name}...")
                
                # Обробка
                try:
                    processed_bytes = process_single_image(
                        file, 
                        wm_image_obj, 
                        max_dim, 
                        quality, 
                        wm_settings if wm_image_obj else None
                    )
                    
                    # Генерація імені
                    new_name = get_safe_filename(file.name, prefix)
                    
                    # Запис в архів
                    zf.writestr(new_name, processed_bytes)
                    
                except Exception as e:
                    st.error(f"Помилка з файлом {file.name}: {e}")
                
                # Оновлення прогресу
                progress_bar.progress((i + 1) / total_files)
        
        # Фінал
        progress_bar.progress(100)
        status_text.success("✅ Готово!")
        
        # Підготовка кнопки завантаження
        zip_buffer.seek(0)
        st.download_button(
            label="⬇️ Завантажити ZIP-архів",
            data=zip_buffer,
            file_name=f"photos_processed_{datetime.now().strftime('%H%M')}.zip",
            mime="application/zip",
            type="primary" # Робить кнопку виділеною
        )
