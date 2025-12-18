import streamlit as st
import pandas as pd
from PIL import Image
from translitua import translit
import io
import zipfile
from datetime import datetime
import re

# Налаштування сторінки
st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# --- Логіка (Допоміжні функції) ---
def get_safe_filename(original_filename, prefix="", extension="jpg"):
    name_only = original_filename.rsplit('.', 1)[0]
    timestamp = datetime.now().strftime('%H%M%S_%f')[:9]
    if prefix:
        clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-')
        return f"{clean_prefix}_{timestamp}.{extension}"
    else:
        slug = translit(name_only).lower()
        slug = re.sub(r'[\s\W_]+', '-', slug).strip('-')
        if not slug: slug = "image"
        return f"{slug}_{timestamp}.{extension}"

def get_image_info(file_buffer):
    """Отримує розміри зображення без повного завантаження в пам'ять (якщо можливо)"""
    file_buffer.seek(0)
    img = Image.open(file_buffer)
    width, height = img.size
    size_bytes = file_buffer.getbuffer().nbytes
    file_buffer.seek(0) # Повертаємо курсор на початок!
    return width, height, size_bytes

def process_single_image(uploaded_file, wm_image, max_dim, quality, wm_settings, output_format):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    
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

    is_jpeg = (uploaded_file.name.lower().endswith(('.jpg', '.jpeg')) and output_format == "JPEG")
    if not wm_image and is_jpeg and output_buffer.getbuffer().nbytes > original_size:
        uploaded_file.seek(0)
        return uploaded_file.read()
        
    return output_buffer.getvalue(), img.size # Повертаємо також нові розміри

# --- ІНТЕРФЕЙС ---

col_head1, col_head2 = st.columns([3, 1], vertical_alignment="bottom")
with col_head1:
    st.title("📸 Watermarker Pro MaAn")
with col_head2:
    with st.expander("ℹ️ About"):
        st.markdown("**Product:** Watermarker Pro MaAn")
        st.markdown("**Author:** Marynyuk Andriy")
        st.markdown("**License:** Proprietary")
        st.markdown("[GitHub Repository](https://github.com/MaanAndrii)")
        st.caption("© 2025 All rights reserved")

st.markdown("---")

# НАЛАШТУВАННЯ
with st.expander("⚙️ **Налаштування обробки (Натисніть, щоб розгорнути)**", expanded=True):
    set_col1, set_col2, set_col3 = st.columns(3)
    
    with set_col1:
        st.subheader("1. Формат")
        out_fmt = st.selectbox("Вихідний формат", ["JPEG", "WEBP", "PNG"])
        prefix = st.text_input("Префікс файлу", placeholder="напр. photo_edit")
        
    with set_col2:
        st.subheader("2. Розміри")
        resize_enabled = st.checkbox("Зменшувати розмір", value=True)
        max_dim = 0
        if resize_enabled:
            max_dim = st.select_slider("Макс. сторона (px)", options=[800, 1024, 1280, 1920, 3840], value=1920)
        
        quality = 80
        if out_fmt != "PNG":
            quality = st.slider("Якість стиснення", 50, 100, 80, 5)

    with set_col3:
        st.subheader("3. Логотип")
        wm_file_upload = st.file_uploader("Завантажити PNG", type=["png"])
        
        wm_settings = {}
        if wm_file_upload:
            wm_settings['position'] = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
            wm_settings['scale'] = st.slider("Розмір (%)", 5, 50, 15) / 100
            wm_settings['margin'] = st.slider("Відступ (px)", 0, 100, 15)

# ГОЛОВНА ЗОНА
col_main, col_preview = st.columns([1.5, 1], gap="large")

# === ЛІВА КОЛОНКА ===
with col_main:
    st.header("📤 Завантаження")
    
    uploaded_files = st.file_uploader(
        "Перетягніть фото сюди (підтримується мультизавантаження)", 
        type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
        accept_multiple_files=True
    )

    if uploaded_files:
        # --- НОВЕ: ТАБЛИЦЯ ВХІДНИХ ФАЙЛІВ ---
        st.caption(f"Вибрано файлів: {len(uploaded_files)}")
        
        # Збираємо дані для таблиці
        input_data = []
        for f in uploaded_files:
            w, h, size = get_image_info(f)
            input_data.append({
                "Файл": f.name,
                "Розмір (KB)": f"{size/1024:.1f}",
                "Пікселі": f"{w} x {h}"
            })
        
        # Відображаємо гарну таблицю
        df_input = pd.DataFrame(input_data)
        st.dataframe(df_input, use_container_width=True, hide_index=True)
        # -------------------------------------
        
        if st.button(f"🚀 Обробити ({len(uploaded_files)} шт.)", type="primary", use_container_width=True):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            temp_results = [] # Для скачування
            report_data = []  # Для таблиці звіту
            total_orig_size = 0
            total_new_size = 0
            
            wm_obj = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w") as zf:
                total_files = len(uploaded_files)
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Обробка: {file.name}...")
                    
                    # Отримуємо старі розміри ще раз для точності звіту
                    orig_w, orig_h, orig_bytes_len = get_image_info(file)
                    total_orig_size += orig_bytes_len
                    
                    try:
                        processed_bytes, (new_w, new_h) = process_single_image(
                            file, wm_obj, max_dim, quality, 
                            wm_settings if wm_obj else None, out_fmt
                        )
                        new_bytes_len = len(processed_bytes)
                        total_new_size += new_bytes_len
                        
                        ext = out_fmt.lower()
                        new_name = get_safe_filename(file.name, prefix, ext)
                        
                        zf.writestr(new_name, processed_bytes)
                        
                        # Дані для скачування
                        temp_results.append((new_name, processed_bytes))
                        
                        # Дані для звіту (таблиця)
                        savings = ((orig_bytes_len - new_bytes_len) / orig_bytes_len) * 100
                        report_data.append({
                            "Файл": new_name,
                            "Було (KB)": f"{orig_bytes_len/1024:.1f}",
                            "Стало (KB)": f"{new_bytes_len/1024:.1f}",
                            "Економія": f"{savings:.1f}%",
                            "Новий розмір": f"{new_w} x {new_h}"
                        })
                        
                    except Exception as e:
                        st.error(f"Помилка: {e}")
                    progress_bar.progress((i + 1) / total_files)
            
            progress_bar.progress(100)
            status_text.success("Готово!")
            
            # Збереження в сесію
            st.session_state['processed_data'] = temp_results
            st.session_state['report_data'] = report_data # Зберігаємо таблицю
            st.session_state['zip_bytes'] = zip_buffer.getvalue()
            st.session_state['stats'] = {
                'orig': total_orig_size,
                'new': total_new_size
            }

        # Блок відображення результатів
        if 'processed_data' in st.session_state and st.session_state['processed_data']:
            st.divider()
            st.subheader("🏁 Результати")
            
            # Статистика
            stats = st.session_state['stats']
            saved_size = stats['orig'] - stats['new']
            saved_mb = saved_size / (1024 * 1024)
            saved_percent = (saved_size / stats['orig']) * 100 if stats['orig'] > 0 else 0
            
            col_res_info, col_res_dl = st.columns([2, 1])
            with col_res_info:
                st.info(f"Загальна економія: **{saved_mb:.1f} MB ({saved_percent:.0f}%)**")
            with col_res_dl:
                st.download_button(
                    label="📦 Завантажити ZIP",
                    data=st.session_state['zip_bytes'],
                    file_name=f"processed_{datetime.now().strftime('%H%M')}.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
            
            # --- НОВЕ: ТАБЛИЦЯ РЕЗУЛЬТАТІВ ---
            with st.expander("📊 Детальний звіт (Таблиця)", expanded=True):
                df_report = pd.DataFrame(st.session_state['report_data'])
                st.dataframe(
                    df_report, 
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Економія": st.column_config.ProgressColumn(
                            "Економія",
                            format="%f",
                            min_value=0,
                            max_value=100,
                        )
                    }
                )
            # ----------------------------------

            # Окремі файли (Список з кнопками)
            with st.expander("⬇️ Скачати окремо"):
                for idx, (p_name, p_bytes) in enumerate(st.session_state['processed_data']):
                    c1, c2, c3 = st.columns([1, 4, 2], vertical_alignment="center")
                    with c1: st.image(p_bytes, width=40)
                    with c2: st.caption(p_name)
                    with c3:
                        st.download_button(
                            "⬇️",
                            data=p_bytes,
                            file_name=p_name,
                            mime=f"image/{out_fmt.lower()}",
                            key=f"dl_{idx}_{p_name}"
                        )

# === ПРАВА КОЛОНКА ===
with col_preview:
    st.header("📊 Тест")
    
    with st.container(border=True):
        if uploaded_files:
            file_names = [f.name for f in uploaded_files]
            selected_file_name = st.selectbox("Виберіть файл:", file_names)
            
            sample_file = next(f for f in uploaded_files if f.name == selected_file_name)
            
            # Отримуємо інфо
            orig_w, orig_h, orig_size = get_image_info(sample_file)
            
            wm_obj_sample = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
            
            try:
                with st.spinner("Генерація..."):
                    # Зверніть увагу, функція тепер повертає два значення
                    result_bytes, (new_w, new_h) = process_single_image(
                        sample_file, wm_obj_sample, max_dim, quality, 
                        wm_settings if wm_obj_sample else None, out_fmt
                    )
                
                new_size = len(result_bytes)
                
                st.image(result_bytes, caption=f"Результат", use_container_width=True)
                
                st.divider()
                st.write(f"**Оригінал:** {orig_w}x{orig_h} ({orig_size/1024:.1f} KB)")
                st.write(f"**Результат:** {new_w}x{new_h} ({new_size/1024:.1f} KB)")
                
                delta = ((new_size - orig_size) / orig_size) * 100
                st.metric("Ефективність", f"{delta:.1f}%", delta_color="inverse")

            except Exception as e:
                st.error(f"Помилка прев'ю: {e}")
        else:
            st.info("Додайте фото для тесту.")
            st.markdown(
                """
                <div style="height: 200px; background-color: #f0f2f6; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #888;">
                    📸
                </div>
                """, 
                unsafe_allow_html=True
            )
