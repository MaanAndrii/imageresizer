import streamlit as st
from PIL import Image
from translitua import translit
import io
import zipfile
from datetime import datetime
import re

# --- 1. ЗМІНА НАЗВИ У ВКЛАДЦІ БРАУЗЕРА ---
st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# --- Логіка (Без змін) ---
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

def process_single_image(uploaded_file, wm_image, max_dim, quality, wm_settings, output_format):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    
    if output_format == "JPEG":
        img = img.convert("RGB")
    else:
        img = img.convert("RGBA")

    original_size = uploaded_file.getbuffer().nbytes
    
    if max_dim > 0 and (img.width > max_dim or img.height > max_dim):
        if img.width >= img.height:
            ratio = max_dim / float(img.width)
            new_width, new_height = max_dim, int(float(img.height) * ratio)
        else:
            ratio = max_dim / float(img.height)
            new_width, new_height = int(float(img.width) * ratio), max_dim
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

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
        
    return output_buffer.getvalue()

# --- ІНТЕРФЕЙС ---

# --- 2. ЗМІНА ГОЛОВНОГО ЗАГОЛОВКА ---
st.title("📸 Watermarker Pro MaAn")
st.markdown("---")

col_settings, col_upload, col_preview = st.columns([1, 1.5, 1], gap="medium")

# ==========================
# 1. ЛІВИЙ СТОВПЕЦЬ
# ==========================
with col_settings:
    st.header("⚙️ Опції")
    
    with st.container(border=True):
        st.subheader("Формат та Ім'я")
        out_fmt = st.selectbox("Вихідний формат", ["JPEG", "WEBP", "PNG"])
        prefix = st.text_input("Префікс файлу", placeholder="напр. photo_edit")
    
    with st.container(border=True):
        st.subheader("Розміри")
        resize_enabled = st.checkbox("Зменшувати розмір", value=True)
        max_dim = 0
        if resize_enabled:
            max_dim = st.select_slider("Макс. сторона (px)", options=[800, 1024, 1280, 1920, 3840], value=1920)
        
        quality = 80
        if out_fmt != "PNG":
            quality = st.slider("Якість стиснення", 50, 100, 80, 5)

    with st.container(border=True):
        st.subheader("Водяний знак")
        wm_file_upload = st.file_uploader("Завантажити лого (PNG)", type=["png"])
        
        wm_settings = {}
        if wm_file_upload:
            wm_settings['position'] = st.selectbox("Розміщення", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
            wm_settings['scale'] = st.slider("Масштаб (%)", 5, 50, 15) / 100
            wm_settings['margin'] = st.slider("Відступ (px)", 0, 100, 15)

    st.markdown("---")
    
    # --- 3. ПРИХОВАНИЙ БЛОК "ABOUT" ---
    with st.expander("ℹ️ About"):
        st.markdown("**Product:** Watermarker Pro MaAn")
        st.markdown("**Author:** Marynyuk Andriy")
        st.markdown("**License:** GNU GPLv3")
        st.markdown("[GitHub Repository](https://github.com/MaanAndrii)")
        st.caption("© 2025 All rights reserved")

# ==========================
# 2. ЦЕНТРАЛЬНИЙ СТОВПЕЦЬ
# ==========================
with col_upload:
    st.header("📤 Завантаження")
    
    uploaded_files = st.file_uploader(
        "Перетягніть фото сюди", 
        type=['png', 'jpg', 'jpeg', 'bmp', 'webp'], 
        accept_multiple_files=True
    )

    if uploaded_files:
        st.success(f"Вибрано файлів: {len(uploaded_files)}")
        
        if st.button(f"🚀 Обробити та Скачати", type="primary", use_container_width=True):
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            temp_results = []
            total_orig_size = 0
            total_new_size = 0
            
            wm_obj = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
            zip_buffer = io.BytesIO()

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
                        
                        ext = out_fmt.lower()
                        new_name = get_safe_filename(file.name, prefix, ext)
                        
                        zf.writestr(new_name, processed_bytes)
                        temp_results.append((new_name, processed_bytes))
                        
                    except Exception as e:
                        st.error(f"Помилка: {e}")
                    progress_bar.progress((i + 1) / total_files)
            
            progress_bar.progress(100)
            status_text.success("Готово!")
            
            st.session_state['processed_data'] = temp_results
            st.session_state['zip_bytes'] = zip_buffer.getvalue()
            st.session_state['stats'] = {
                'orig': total_orig_size,
                'new': total_new_size
            }

        if 'processed_data' in st.session_state and st.session_state['processed_data']:
            
            stats = st.session_state['stats']
            saved_size = stats['orig'] - stats['new']
            saved_mb = saved_size / (1024 * 1024)
            saved_percent = (saved_size / stats['orig']) * 100 if stats['orig'] > 0 else 0
            
            st.info(
                f"📊 **Результат:** Загальний розмір зменшено з "
                f"**{stats['orig']/1024/1024:.1f} MB** до **{stats['new']/1024/1024:.1f} MB**.\n\n"
                f"✂️ Економія: **{saved_mb:.1f} MB ({saved_percent:.0f}%)**"
            )
            
            st.download_button(
                label="📦 Завантажити все архівом (ZIP)",
                data=st.session_state['zip_bytes'],
                file_name=f"processed_{datetime.now().strftime('%H%M')}.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
            
            st.divider()
            with st.expander("📂 Завантажити файли окремо", expanded=True):
                for idx, (p_name, p_bytes) in enumerate(st.session_state['processed_data']):
                    r1, r2, r3 = st.columns([1, 3, 2], vertical_alignment="center")
                    with r1:
                        st.image(p_bytes, width=50)
                    with r2:
                        st.write(f"**{p_name}**")
                        st.caption(f"{len(p_bytes)/1024:.1f} KB")
                    with r3:
                        st.download_button(
                            label="⬇️ Скачати",
                            data=p_bytes,
                            file_name=p_name,
                            mime=f"image/{out_fmt.lower()}",
                            key=f"dl_{idx}_{p_name}"
                        )

# ==========================
# 3. ПРАВИЙ СТОВПЕЦЬ
# ==========================
with col_preview:
    st.header("📊 Прогноз")
    
    if uploaded_files:
        file_names = [f.name for f in uploaded_files]
        selected_file_name = st.selectbox("Файл для огляду:", file_names)
        
        sample_file = next(f for f in uploaded_files if f.name == selected_file_name)
        
        sample_file.seek(0)
        original_img = Image.open(sample_file)
        orig_w, orig_h = original_img.size
        
        wm_obj_sample = Image.open(wm_file_upload).convert("RGBA") if wm_file_upload else None
        
        try:
            with st.spinner("Аналізуємо..."):
                result_bytes = process_single_image(
                    sample_file, wm_obj_sample, max_dim, quality, 
                    wm_settings if wm_obj_sample else None, out_fmt
                )
            
            orig_size = sample_file.getbuffer().nbytes
            new_size = len(result_bytes)
            
            st.write("**Оригінал:**")
            col_res1, col_res2 = st.columns(2)
            col_res1.metric("Вага", f"{orig_size/1024:.1f} KB")
            col_res2.metric("Розмір", f"{orig_w} x {orig_h}")
            
            delta_percent = ((new_size - orig_size) / orig_size) * 100
            
            st.divider()
            st.metric(
                "Прогноз (Вага)", 
                f"{new_size/1024:.1f} KB",
                f"{delta_percent:.1f}%",
                delta_color="inverse"
            )
            
            if new_size < orig_size:
                saved_ratio = 1.0 - (new_size / orig_size)
                st.progress(saved_ratio)
            
            st.write("Попередній перегляд:")
            st.image(result_bytes, caption=f"Результат: {selected_file_name}", use_container_width=True)

        except Exception as e:
            st.error("Неможливо створити прев'ю")
    else:
        st.info("Додайте фото, щоб побачити прогноз.")
