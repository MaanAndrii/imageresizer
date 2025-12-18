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

# --- Логіка ---
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

def get_image_info(file_obj):
    """Отримує розміри зображення"""
    file_obj.seek(0)
    img = Image.open(file_obj)
    width, height = img.size
    size_bytes = file_obj.getbuffer().nbytes
    file_obj.seek(0)
    return width, height, size_bytes

def process_single_image(uploaded_file, wm_image, max_dim, quality, wm_settings, output_format):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    
    if output_format == "JPEG":
        img = img.convert("RGB")
    else:
        img = img.convert("RGBA")

    original_size = uploaded_file.getbuffer().nbytes
    
    # Ресайз
    if max_dim > 0 and (img.width > max_dim or img.height > max_dim):
        if img.width >= img.height:
            ratio = max_dim / float(img.width)
            new_width, new_height = max_dim, int(float(img.height) * ratio)
        else:
            ratio = max_dim / float(img.height)
            new_width, new_height = int(float(img.width) * ratio), max_dim
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Вотермарка
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

    # Збереження
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
        
    return output_buffer.getvalue(), img.size

# --- ІНТЕРФЕЙС ---

# Ініціалізація сесії для файлів
if 'all_files' not in st.session_state:
    st.session_state['all_files'] = {} # словник {ім'я_файлу: об'єкт_файлу}
if 'preview_target' not in st.session_state:
    st.session_state['preview_target'] = None

col_head1, col_head2 = st.columns([3, 1], vertical_alignment="bottom")
with col_head1:
    st.title("📸 Watermarker Pro MaAn")
with col_head2:
    with st.expander("ℹ️ About"):
        st.markdown("**Product:** Watermarker Pro MaAn")
        st.caption("© 2025 All rights reserved")

st.markdown("---")

# НАЛАШТУВАННЯ
with st.expander("⚙️ **Налаштування**", expanded=True):
    set_col1, set_col2, set_col3 = st.columns(3)
    with set_col1:
        st.subheader("1. Формат")
        out_fmt = st.selectbox("Вихідний формат", ["JPEG", "WEBP", "PNG"])
        prefix = st.text_input("Префікс", placeholder="photo_edit")
    with set_col2:
        st.subheader("2. Розміри")
        resize_enabled = st.checkbox("Зменшувати розмір", value=True)
        max_dim = 0
        if resize_enabled:
            max_dim = st.select_slider("Макс. сторона (px)", options=[800, 1024, 1280, 1920, 3840], value=1920)
        quality = 80
        if out_fmt != "PNG":
            quality = st.slider("Якість", 50, 100, 80, 5)
    with set_col3:
        st.subheader("3. Логотип")
        wm_file_upload = st.file_uploader("PNG Лого", type=["png"])
        wm_settings = {}
        if wm_file_upload:
            wm_settings['position'] = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
            wm_settings['scale'] = st.slider("Розмір (%)", 5, 50, 15) / 100
            wm_settings['margin'] = st.slider("Відступ (px)", 0, 100, 15)

col_main, col_preview = st.columns([1.5, 1], gap="large")

# === ЛІВА КОЛОНКА: КЕРУВАННЯ ФАЙЛАМИ ===
with col_main:
    st.header("📂 Файли")
    
    # 1. Завантажувач (Додає файли до існуючих)
    new_uploaded_files = st.file_uploader(
        "Додати файли", 
        type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    # Додаємо нові файли в сесію
    if new_uploaded_files:
        for f in new_uploaded_files:
            if f.name not in st.session_state['all_files']:
                st.session_state['all_files'][f.name] = f
        # Очищаємо завантажувач (хак для Streamlit, щоб не дублювати додавання)
        # st.rerun() # Можна розкоментувати, якщо будуть проблеми з дублями

    # Якщо файли є в пам'яті
    current_files = list(st.session_state['all_files'].values())
    
    if current_files:
        # Формуємо дані для редактора
        editor_data = []
        for f in current_files:
            w, h, size = get_image_info(f)
            # Визначаємо, чи цей файл зараз вибраний для прев'ю
            is_preview = (f.name == st.session_state['preview_target'])
            
            editor_data.append({
                "Прев'ю": is_preview,
                "Файл": f.name,
                "Розмір": f"{size/1024:.1f} KB",
                "Інфо": f"{w}x{h}",
                "Видалити": False # Чекбокс для видалення
            })
        
        df_editor = pd.DataFrame(editor_data)

        # 2. ІНТЕРАКТИВНА ТАБЛИЦЯ
        st.caption("Виберіть файл у колонці **Прев'ю** для перегляду справа. Позначте **Видалити**, щоб прибрати файл.")
        
        edited_df = st.data_editor(
            df_editor,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Прев'ю": st.column_config.CheckboxColumn("👁️", help="Показати прев'ю", default=False),
                "Видалити": st.column_config.CheckboxColumn("🗑️", help="Видалити файл", default=False),
                "Файл": st.column_config.TextColumn("Назва файлу", disabled=True),
                "Розмір": st.column_config.TextColumn("Вага", disabled=True),
                "Інфо": st.column_config.TextColumn("px", disabled=True),
            },
            key="file_editor"
        )

        # 3. ЛОГІКА ОБРОБКИ ЗМІН В ТАБЛИЦІ
        # Перевіряємо видалення
        files_to_delete = edited_df[edited_df["Видалити"] == True]["Файл"].tolist()
        if files_to_delete:
            for fname in files_to_delete:
                del st.session_state['all_files'][fname]
                # Якщо видалили той, що на прев'ю - скидаємо прев'ю
                if st.session_state['preview_target'] == fname:
                    st.session_state['preview_target'] = None
            st.rerun()

        # Перевіряємо вибір прев'ю (дозволяємо тільки один вибір)
        preview_selected = edited_df[edited_df["Прев'ю"] == True]["Файл"].tolist()
        if preview_selected:
            # Беремо останній клікнутий (або перший у списку)
            new_target = preview_selected[-1]
            if new_target != st.session_state['preview_target']:
                st.session_state['preview_target'] = new_target
                st.rerun()
        
        # Кнопка запуску (тільки для актуальних файлів)
        actual_files = list(st.session_state['all_files'].values())
        if actual_files:
            if st.button(f"🚀 Обробити ({len(actual_files)} шт.)", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                temp_results = []
                report_data = []
                total_orig = 0
                total_new = 0
                
                wm_obj = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    total = len(actual_files)
                    for i, file in enumerate(actual_files):
                        status_text.text(f"Обробка: {file.name}...")
                        w, h, orig_b = get_image_info(file)
                        total_orig += orig_b
                        
                        try:
                            p_bytes, (nw, nh) = process_single_image(
                                file, wm_obj, max_dim, quality, wm_settings if wm_obj else None, out_fmt
                            )
                            new_b = len(p_bytes)
                            total_new += new_b
                            
                            ext = out_fmt.lower()
                            new_name = get_safe_filename(file.name, prefix, ext)
                            zf.writestr(new_name, p_bytes)
                            
                            temp_results.append((new_name, p_bytes))
                            report_data.append({
                                "Файл": new_name,
                                "Економія": ((orig_b - new_b)/orig_b)*100,
                                "Розмір": f"{nw}x{nh}"
                            })
                        except Exception as e: st.error(f"Err: {e}")
                        progress_bar.progress((i+1)/total)
                
                progress_bar.progress(100)
                status_text.success("Готово!")
                
                st.session_state['processed'] = temp_results
                st.session_state['report'] = report_data
                st.session_state['zip'] = zip_buffer.getvalue()
                st.session_state['stats'] = {'orig': total_orig, 'new': total_new}

    # Відображення результатів
    if 'processed' in st.session_state and st.session_state['processed']:
        st.divider()
        stats = st.session_state['stats']
        saved = stats['orig'] - stats['new']
        st.info(f"Загальна економія: **{saved/(1024*1024):.1f} MB**")
        
        st.download_button("📦 Завантажити ZIP", st.session_state['zip'], f"photos.zip", "application/zip", type="primary", use_container_width=True)
        
        with st.expander("📊 Звіт"):
            st.dataframe(pd.DataFrame(st.session_state['report']), use_container_width=True, column_config={"Економія": st.column_config.ProgressColumn(format="%f", min_value=0, max_value=100)})

# === ПРАВА КОЛОНКА: ПРЕВ'Ю ===
with col_preview:
    st.header("👁️ Прев'ю")
    target_name = st.session_state.get('preview_target')
    
    # Шукаємо файл об'єкт по імені
    target_file = st.session_state['all_files'].get(target_name) if target_name else None

    with st.container(border=True):
        if target_file:
            # Логіка генерації прев'ю
            orig_w, orig_h, orig_s = get_image_info(target_file)
            wm_obj_s = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
            
            try:
                with st.spinner("Генерація..."):
                    res_bytes, (nw, nh) = process_single_image(
                        target_file, wm_obj_s, max_dim, quality, wm_settings if wm_obj_s else None, out_fmt
                    )
                st.image(res_bytes, caption=f"{target_name} ({nw}x{nh})", use_container_width=True)
                
                delta = ((len(res_bytes) - orig_s) / orig_s) * 100
                st.metric("Ефективність", f"{delta:.1f}%", delta_color="inverse")
                
            except Exception as e:
                st.error(f"Помилка: {e}")
        else:
            st.info("Поставте галочку 👁️ навпроти файлу зліва.")
            st.markdown('<div style="height:200px;background:#f0f2f6;"></div>', unsafe_allow_html=True)
