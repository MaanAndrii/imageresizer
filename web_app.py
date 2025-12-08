import streamlit as st
from PIL import Image
from translitua import translit
import io
import zipfile
from datetime import datetime
import re

st.set_page_config(page_title="Watermarker Web", page_icon="📸", layout="centered")

# --- Логіка (без змін) ---
def get_safe_filename(original_filename, prefix=""):
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
    
    # 4. Перевірка розміру
    if not wm_image and output_buffer.getbuffer().nbytes > original_size:
        uploaded_file.seek(0)
        return uploaded_file.read()
        
    return output_buffer.getvalue()

# --- ІНТЕРФЕЙС ---

st.title("📸 Watermarker & Resizer")
st.write("Завантажте фото, обробіть та завантажте результат.")

# Сайдбар
with st.sidebar:
    st.header("⚙️ Налаштування")
    
    st.subheader("1. Назва файлів")
    prefix = st.text_input("Префікс", placeholder="напр. vidpustka")
    
    st.subheader("2. Розміри та Якість")
    resize_enabled = st.checkbox("Зменшувати розмір", value=True)
    
    max_dim = 0
    if resize_enabled:
        max_dim = st.select_slider(
            "Макс. сторона (px)", 
            options=[800, 1024, 1280, 1920, 3840], 
            value=3840
        )
    
    quality = st.slider("Якість JPEG", 70, 100, 80, 5)

    st.subheader("3. Водяний знак")
    wm_file_upload = st.file_uploader("Завантажити лого (PNG)", type=["png"])
    
    wm_settings = {}
    if wm_file_upload:
        st.info("Логотип активовано!")
        wm_settings['position'] = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
        wm_settings['scale'] = st.slider("Розмір лого (%)", 5, 50, 15) / 100
        wm_settings['margin'] = st.slider("Відступ (px)", 0, 100, 15)

# Основна частина
uploaded_files = st.file_uploader(
    "📤 Виберіть фотографії", 
    type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button(f"🚀 Обробити {len(uploaded_files)} зображень", type="primary"):
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Списки для результатів
        processed_images = [] # Тут будемо зберігати (ім'я, байти) для окремого завантаження
        zip_buffer = io.BytesIO()
        
        wm_obj = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None

        with zipfile.ZipFile(zip_buffer, "w") as zf:
            total_files = len(uploaded_files)
            
            for i, file in enumerate(uploaded_files):
                status_text.text(f"Обробка: {file.name}...")
                try:
                    processed_bytes = process_single_image(
                        file, wm_obj, max_dim, quality, wm_settings if wm_obj else None
                    )
                    
                    new_name = get_safe_filename(file.name, prefix)
                    
                    # 1. Додаємо в ZIP
                    zf.writestr(new_name, processed_bytes)
                    
                    # 2. Додаємо в список для окремого відображення
                    processed_images.append((new_name, processed_bytes))
                    
                except Exception as e:
                    st.error(f"Помилка з файлом {file.name}: {e}")
                
                progress_bar.progress((i + 1) / total_files)
        
        progress_bar.progress(100)
        status_text.success("✅ Готово!")
        
        # --- ВАРІАНТИ ЗАВАНТАЖЕННЯ ---
        
        st.divider() # Горизонтальна лінія
        
        # 1. Велика кнопка для ZIP
        zip_buffer.seek(0)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.download_button(
                label="📦 Завантажити все архівом (ZIP)",
                data=zip_buffer,
                file_name=f"photos_{datetime.now().strftime('%H%M')}.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
            
        # 2. Список окремих файлів
        with st.expander("📂 Або завантажити файли окремо"):
            for name, img_bytes in processed_images:
                # Робимо гарний рядок: Мініатюра -> Назва -> Кнопка
                row_col1, row_col2, row_col3 = st.columns([1, 3, 2])
                
                with row_col1:
                    st.image(img_bytes, width=60) # Маленька мініатюра
                with row_col2:
                    st.write(f"**{name}**")
                    # Показуємо розмір файлу в КБ
                    size_kb = len(img_bytes) / 1024
                    st.caption(f"{size_kb:.1f} KB")
                with row_col3:
                    st.download_button(
                        label="⬇️ Завантажити",
                        data=img_bytes,
                        file_name=name,
                        key=name, # Унікальний ключ потрібен для Streamlit
                        mime="image/jpeg"
                    )
