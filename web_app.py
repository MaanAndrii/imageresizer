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

# === Ініціалізація Session State ===
if 'file_cache' not in st.session_state:
    st.session_state['file_cache'] = {}
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

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
    file_obj.seek(0)
    img = Image.open(file_obj)
    width, height = img.size
    size_bytes = file_obj.getbuffer().nbytes
    file_obj.seek(0)
    return width, height, size_bytes

def process_single_image(uploaded_file, wm_image, max_dim, quality, wm_settings, output_format):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    
    # 1. RGBA для шарів
    img = img.convert("RGBA")

    # 2. Ресайз (LANCZOS)
    if max_dim > 0 and (img.width > max_dim or img.height > max_dim):
        if img.width >= img.height:
            ratio = max_dim / float(img.width)
            new_width, new_height = max_dim, int(float(img.height) * ratio)
        else:
            ratio = max_dim / float(img.height)
            new_width, new_height = int(float(img.width) * ratio), max_dim
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 3. Вотермарка
    if wm_image:
        wm_rgba = wm_image.convert("RGBA")
        
        scale = wm_settings['scale']
        margin = wm_settings['margin']
        position = wm_settings['position']
        
        new_wm_width = int(img.width * scale)
        w_ratio = new_wm_width / float(wm_rgba.width)
        new_wm_height = int(float(wm_rgba.height) * w_ratio)
        
        wm_resized = wm_rgba.resize((new_wm_width, new_wm_height), Image.Resampling.LANCZOS)
        
        x, y = 0, 0
        if position == 'bottom-right': x, y = img.width - wm_resized.width - margin, img.height - wm_resized.height - margin
        elif position == 'bottom-left': x, y = margin, img.height - wm_resized.height - margin
        elif position == 'top-right': x, y = img.width - wm_resized.width - margin, margin
        elif position == 'top-left': x, y = margin, margin
        elif position == 'center': x, y = (img.width - wm_resized.width) // 2, (img.height - wm_resized.height) // 2
        
        # Накладання з маскою прозорості
        img.paste(wm_resized, (x, y), wm_resized)

    # 4. Фон для JPEG
    if output_format == "JPEG":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif output_format == "RGB":
         img = img.convert("RGB")

    # 5. Збереження (HQ)
    output_buffer = io.BytesIO()
    if output_format == "JPEG":
        img.save(output_buffer, format="JPEG", quality=quality, optimize=True, subsampling=0)
    elif output_format == "WEBP":
        img.save(output_buffer, format="WEBP", quality=quality, method=6)
    elif output_format == "PNG":
        img.save(output_buffer, format="PNG", optimize=True)

    return output_buffer.getvalue(), img.size

# --- ІНТЕРФЕЙС ---

# ЗМІНА: Просто заголовок, без About справа
st.title("📸 Watermarker Pro MaAn")
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

col_left, col_right = st.columns([1.5, 1], gap="large")

# === ЛІВА ЧАСТИНА ===
with col_left:
    st.header("📂 Менеджер файлів")
    
    uploaded = st.file_uploader(
        "Додати файли", 
        type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['uploader_key']}"
    )
    
    if uploaded:
        for f in uploaded:
            if f.name not in st.session_state['file_cache']:
                st.session_state['file_cache'][f.name] = f
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_list = list(st.session_state['file_cache'].values())
    preview_file_name = None
    
    if files_list:
        table_data = []
        for f in files_list:
            w, h, size = get_image_info(f)
            table_data.append({
                "Обрати": False,
                "Файл": f.name,
                "Розмір": f"{size/1024:.1f} KB",
                "Інфо": f"{w}x{h}"
            })
        
        df = pd.DataFrame(table_data)
        
        st.caption("Позначте файли галочкою **Обрати**, щоб побачити Прев'ю або Видалити.")
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Обрати": st.column_config.CheckboxColumn("✅", help="Вибрати для дій", default=False),
                "Файл": st.column_config.TextColumn("Ім'я файлу", disabled=True),
                "Розмір": st.column_config.TextColumn("Вага", disabled=True),
                "Інфо": st.column_config.TextColumn("px", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key="files_editor"
        )
        
        selected_rows = edited_df[edited_df["Обрати"] == True]
        selected_filenames = selected_rows["Файл"].tolist()
        
        if selected_filenames:
            preview_file_name = selected_filenames[-1]
        
        # === ПАНЕЛЬ ДІЙ ===
        c_act1, c_act2, c_act3 = st.columns([1, 1, 1.2])
        
        with c_act1:
            if selected_filenames:
                if st.button(f"🗑️ Видалити ({len(selected_filenames)})", type="secondary", use_container_width=True):
                    for fname in selected_filenames:
                        del st.session_state['file_cache'][fname]
                    st.rerun()
            else:
                 st.button("🗑️ Видалити", disabled=True, use_container_width=True)

        with c_act2:
            if st.button("♻️ Очистити все", type="secondary", use_container_width=True):
                st.session_state['file_cache'] = {}
                st.session_state['res_list'] = []
                st.session_state['res_zip'] = None
                st.session_state['uploader_key'] += 1
                st.rerun()

        with c_act3:
            if st.button(f"🚀 Обробити ({len(files_list)})", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status = st.empty()
                results = []
                report = []
                total_orig = 0
                total_new = 0
                
                wm_obj = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
                zip_buf = io.BytesIO()
                
                with zipfile.ZipFile(zip_buf, "w") as zf:
                    count = len(files_list)
                    for i, file_obj in enumerate(files_list):
                        status.text(f"Обробка: {file_obj.name}...")
                        w, h, orig_b = get_image_info(file_obj)
                        total_orig += orig_b
                        
                        try:
                            res_bytes, (nw, nh) = process_single_image(
                                file_obj, wm_obj, max_dim, quality, wm_settings if wm_obj else None, out_fmt
                            )
                            total_new += len(res_bytes)
                            
                            ext = out_fmt.lower()
                            new_name = get_safe_filename(file_obj.name, prefix, ext)
                            
                            zf.writestr(new_name, res_bytes)
                            results.append((new_name, res_bytes))
                            
                            report.append({
                                "Файл": new_name,
                                "Економія": ((orig_b - len(res_bytes))/orig_b)*100,
                                "Розмір": f"{nw}x{nh}"
                            })
                        except Exception as e: st.error(f"Err: {e}")
                        progress_bar.progress((i+1)/count)
                
                status.success("Готово!")
                st.session_state['res_zip'] = zip_buf.getvalue()
                st.session_state['res_list'] = results
                st.session_state['res_report'] = report
                st.session_state['res_stats'] = {'orig': total_orig, 'new': total_new}

    # === РЕЗУЛЬТАТИ ===
    if 'res_list' in st.session_state and st.session_state['res_list']:
        st.divider()
        stats = st.session_state['res_stats']
        saved_mb = (stats['orig'] - stats['new']) / (1024*1024)
        
        st.success(f"Економія: **{saved_mb:.1f} MB**")
        st.download_button("📦 Скачати ZIP", st.session_state['res_zip'], "photos.zip", "application/zip", type="primary", use_container_width=True)
        
        with st.expander("📊 Детальний звіт"):
            st.dataframe(pd.DataFrame(st.session_state['res_report']), use_container_width=True, column_config={"Економія": st.column_config.ProgressColumn(format="%f", min_value=0, max_value=100)})

        with st.expander("⬇️ Скачати окремо"):
            for idx, (fname, fbytes) in enumerate(st.session_state['res_list']):
                col_dl1, col_dl2 = st.columns([4, 1])
                with col_dl1: st.write(f"📄 {fname} ({len(fbytes)/1024:.1f} KB)")
                with col_dl2: st.download_button("⬇️", data=fbytes, file_name=fname, mime=f"image/{out_fmt.lower()}", key=f"btn_dl_{idx}")

# === ПРАВА ЧАСТИНА: ПРЕВ'Ю ===
with col_right:
    st.header("👁️ Прев'ю")
    
    with st.container(border=True):
        if preview_file_name and preview_file_name in st.session_state['file_cache']:
            
            target_file = st.session_state['file_cache'][preview_file_name]
            orig_w, orig_h, orig_s = get_image_info(target_file)
            
            wm_obj_preview = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
            
            try:
                with st.spinner("Генерація..."):
                    res_bytes, (nw, nh) = process_single_image(
                        target_file, wm_obj_preview, max_dim, quality, 
                        wm_settings if wm_obj_preview else None, out_fmt
                    )
                
                st.image(res_bytes, caption=f"Результат: {preview_file_name}", use_container_width=True)
                
                delta = ((len(res_bytes) - orig_s) / orig_s) * 100
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Розміри", f"{nw}x{nh}")
                col_m2.metric("Вага", f"{len(res_bytes)/1024:.0f} KB", f"{delta:.1f}%", delta_color="inverse")
                
            except Exception as e:
                st.error(f"Помилка: {e}")
                
        elif files_list:
            st.info("⬅️ Оберіть файл ✅ для перегляду.")
            st.markdown('<div style="height:200px; display:flex; align-items:center; justify-content:center; color:#ccc;">...</div>', unsafe_allow_html=True)
        else:
            st.info("Завантажте файли зліва.")
            st.markdown('<div style="height:200px; display:flex; align-items:center; justify-content:center; color:#ccc;">Немає файлів</div>', unsafe_allow_html=True)

    # === НОВЕ РОЗМІЩЕННЯ ABOUT ===
    st.divider()
    with st.expander("ℹ️ About"):
        st.markdown("**Product:** Watermarker Pro MaAn")
        st.markdown("**Author:** Marynyuk Andriy")
        st.markdown("**License:** Proprietary")
        st.markdown("[GitHub Repository](https://github.com/MaanAndrii)")
        st.caption("© 2025 All rights reserved")
