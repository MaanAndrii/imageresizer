import streamlit as st
import pandas as pd
from PIL import Image, ImageEnhance
from translitua import translit
import io
import zipfile
import hashlib
import concurrent.futures
import os
from datetime import datetime
import re

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# ==========================================
# 🌐 ЛОКАЛІЗАЦІЯ
# ==========================================

TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v3.3",
        "lang_select": "Мова / Language",
        
        "sb_config": "🛠 Налаштування",
        "sec_file": "1. Файл та Ім'я",
        "sec_geo": "2. Геометрія (Ресайз)",
        "sec_wm": "3. Вотермарка",
        
        "lbl_format": "Формат",
        "lbl_quality": "Якість",
        "lbl_naming": "Стратегія імен",
        "lbl_prefix": "Префікс",
        
        "chk_resize": "Змінювати розмір",
        "lbl_resize_mode": "Режим",
        "lbl_resize_val": "Розмір (px)",
        "lbl_presets": "Швидкі пресети:",
        
        "lbl_wm_upload": "Завантажити лого (PNG)",
        "lbl_wm_pos": "Позиція",
        "lbl_wm_scale": "Масштаб (%)",
        "lbl_wm_opacity": "Прозорість",
        "lbl_wm_margin": "Відступ (px)",

        "files_header": "📂 Робоча область",
        "uploader_label": "Файли",
        "tbl_select": "✅",
        "tbl_name": "Файл",
        "btn_delete": "🗑️ Видалити",
        "btn_reset": "♻️ Скинути",
        "btn_process": "🚀 Обробити",
        "msg_done": "Готово!",
        
        "res_savings": "Економія",
        "btn_dl_zip": "📦 Скачати ZIP",
        "exp_report": "📊 Технічний звіт",
        "exp_dl_separate": "⬇️ Скачати окремо",
        
        "prev_header": "👁️ Живий перегляд",
        "prev_rendering": "Генерація...",
        "prev_size": "Розмір",
        "prev_weight": "Вага",
        "prev_info": "Оберіть файл (✅) для тесту.",
        
        "about_prod": "**Продукт:** Watermarker Pro MaAn v3.3",
        "about_auth": "**Автор:** Marynyuk Andriy",
        "about_lic": "**Ліцензія:** Proprietary",
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)",
        "about_copy": "© 2025 Всі права захищено"
    },
    "en": {
        "title": "📸 Watermarker Pro v3.3",
        "lang_select": "Language / Мова",
        
        "sb_config": "🛠 Configuration",
        "sec_file": "1. File & Naming",
        "sec_geo": "2. Geometry (Resize)",
        "sec_wm": "3. Watermark",
        
        "lbl_format": "Output Format",
        "lbl_quality": "Quality",
        "lbl_naming": "Naming Strategy",
        "lbl_prefix": "Filename Prefix",
        
        "chk_resize": "Enable Resize",
        "lbl_resize_mode": "Mode",
        "lbl_resize_val": "Size (px)",
        "lbl_presets": "Quick Presets:",
        
        "lbl_wm_upload": "Upload Logo (PNG)",
        "lbl_wm_pos": "Position",
        "lbl_wm_scale": "Scale (%)",
        "lbl_wm_opacity": "Opacity",
        "lbl_wm_margin": "Margin (px)",

        "files_header": "📂 Workspace",
        "uploader_label": "Files",
        "tbl_select": "✅",
        "tbl_name": "File",
        "btn_delete": "🗑️ Delete",
        "btn_reset": "♻️ Reset",
        "btn_process": "🚀 Process",
        "msg_done": "Done!",
        
        "res_savings": "Savings",
        "btn_dl_zip": "📦 Download ZIP",
        "exp_report": "📊 Technical Report",
        "exp_dl_separate": "⬇️ Download Separate",
        
        "prev_header": "👁️ Live Preview",
        "prev_rendering": "Rendering...",
        "prev_size": "Dimensions",
        "prev_weight": "Weight",
        "prev_info": "Select a file (✅) to preview.",
        
        "about_prod": "**Product:** Watermarker Pro MaAn v3.3",
        "about_auth": "**Author:** Marynyuk Andriy",
        "about_lic": "**License:** Proprietary",
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)",
        "about_copy": "© 2025 All rights reserved"
    }
}

# Мапування опцій для Selectbox
OPTIONS_MAP = {
    "ua": {
        # Нові стратегії
        "Keep Original": "Зберегти назву",
        "Prefix + Sequence": "Префікс + Номер (001)",
        
        "Max Side": "Макс. сторона", "Exact Width": "Точна ширина", "Exact Height": "Точна висота",
        "bottom-right": "Знизу-праворуч", "bottom-left": "Знизу-ліворуч", 
        "top-right": "Зверху-праворуч", "top-left": "Зверху-ліворуч", "center": "Центр"
    },
    "en": {
        "Keep Original": "Keep Original",
        "Prefix + Sequence": "Prefix + Sequence (001)",
        
        "Max Side": "Max Side", "Exact Width": "Exact Width", "Exact Height": "Exact Height",
        "bottom-right": "Bottom-Right", "bottom-left": "Bottom-Left", 
        "top-right": "Top-Right", "top-left": "Top-Left", "center": "Center"
    }
}

# --- BACKEND ---
def generate_filename(original_name, naming_mode, prefix="", extension="jpg", index=1):
    """
    Нова логіка іменування:
    1. Keep Original: (prefix_) + clean_original_name
    2. Prefix + Sequence: (prefix_) + 001
    """
    # Очистка префікса
    clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-') if prefix else ""
    
    if naming_mode == "Prefix + Sequence":
        # Якщо префікса немає, даємо дефолтний "img"
        base_name = clean_prefix if clean_prefix else "image"
        # Формат: prefix_001.ext
        return f"{base_name}_{index:03d}.{extension}"
        
    else: # Keep Original (Default)
        # Очистка оригінального імені
        name_only = os.path.splitext(original_name)[0]
        slug = re.sub(r'[\s\W_]+', '-', translit(name_only).lower()).strip('-')
        if not slug: slug = "image"
        
        if clean_prefix:
            return f"{clean_prefix}_{slug}.{extension}"
        else:
            return f"{slug}.{extension}"

@st.cache_data(show_spinner=False)
def get_image_metadata(file_bytes):
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            return img.width, img.height, len(file_bytes), img.format
    except Exception:
        return 0, 0, len(file_bytes), "UNKNOWN"

@st.cache_resource(show_spinner=False)
def load_and_process_watermark(wm_file_bytes, opacity):
    if not wm_file_bytes: return None
    wm = Image.open(io.BytesIO(wm_file_bytes)).convert("RGBA")
    if opacity < 1.0:
        alpha = wm.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        wm.putalpha(alpha)
    return wm

def process_image_core(file_bytes, filename, wm_obj, resize_config, output_fmt, quality):
    input_io = io.BytesIO(file_bytes)
    img = Image.open(input_io)
    orig_w, orig_h = img.size
    orig_format = img.format
    img = img.convert("RGBA")
    
    target_value = resize_config['value']
    mode = resize_config['mode']
    new_w, new_h = orig_w, orig_h
    scale_factor = 1.0

    if resize_config['enabled']:
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

    if wm_obj:
        scale = resize_config['wm_scale']
        margin = resize_config['wm_margin']
        position = resize_config['wm_position']
        wm_w_target = int(new_w * scale)
        if wm_w_target < 1: wm_w_target = 1
        w_ratio = wm_w_target / float(wm_obj.width)
        wm_h_target = int(float(wm_obj.height) * w_ratio)
        if wm_h_target < 1: wm_h_target = 1
        wm_resized = wm_obj.resize((wm_w_target, wm_h_target), Image.Resampling.LANCZOS)
        
        pos_x, pos_y = 0, 0
        if position == 'bottom-right': pos_x, pos_y = new_w - wm_w_target - margin, new_h - wm_h_target - margin
        elif position == 'bottom-left': pos_x, pos_y = margin, new_h - wm_h_target - margin
        elif position == 'top-right': pos_x, pos_y = new_w - wm_w_target - margin, margin
        elif position == 'top-left': pos_x, pos_y = margin, margin
        elif position == 'center': pos_x, pos_y = (new_w - wm_w_target) // 2, (new_h - wm_h_target) // 2
        img.paste(wm_resized, (pos_x, pos_y), wm_resized)

    if output_fmt == "JPEG":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif output_fmt == "RGB":
         img = img.convert("RGB")

    output_buffer = io.BytesIO()
    if output_fmt == "JPEG":
        img.save(output_buffer, format="JPEG", quality=quality, optimize=True, subsampling=0)
    elif output_fmt == "WEBP":
        img.save(output_buffer, format="WEBP", quality=quality, method=6)
    elif output_fmt == "PNG":
        img.save(output_buffer, format="PNG", optimize=True)

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

# === STATE INIT ===
if 'file_cache' not in st.session_state: st.session_state['file_cache'] = {}
if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0
if 'resize_val_state' not in st.session_state: st.session_state['resize_val_state'] = 1920

# === SIDEBAR ===
with st.sidebar:
    lang_choice = st.selectbox("Language / Мова", ["Українська", "English"])
    lang_code = "ua" if lang_choice == "Українська" else "en"
    T = TRANSLATIONS[lang_code]
    
    st.divider()
    st.header(T['sb_config'])
    
    with st.expander(T['sec_file'], expanded=False):
        out_fmt = st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"])
        quality = 80
        if out_fmt != "PNG":
            quality = st.slider(T['lbl_quality'], 50, 100, 80, 5)
        
        # НОВІ ОПЦІЇ ІМЕНУВАННЯ
        naming_mode = st.selectbox(
            T['lbl_naming'], 
            options=["Keep Original", "Prefix + Sequence"], 
            format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x)
        )
        prefix = st.text_input(T['lbl_prefix'], placeholder="img")

    with st.expander(T['sec_geo'], expanded=True):
        resize_on = st.checkbox(T['chk_resize'], value=True)
        resize_mode = st.selectbox(T['lbl_resize_mode'], options=["Max Side", "Exact Width", "Exact Height"], disabled=not resize_on, format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        
        st.write(T['lbl_presets'])
        col_p1, col_p2, col_p3 = st.columns(3)
        def set_res(val): st.session_state['resize_val_state'] = val
            
        with col_p1: st.button("HD", on_click=set_res, args=(1280,), disabled=not resize_on, use_container_width=True, help="1280 px")
        with col_p2: st.button("FHD", on_click=set_res, args=(1920,), disabled=not resize_on, use_container_width=True, help="1920 px")
        with col_p3: st.button("4K", on_click=set_res, args=(3840,), disabled=not resize_on, use_container_width=True, help="3840 px")
        
        resize_val = st.number_input(T['lbl_resize_val'], min_value=100, max_value=8000, step=100, key='resize_val_state', disabled=not resize_on)

    with st.expander(T['sec_wm'], expanded=True):
        wm_file = st.file_uploader(T['lbl_wm_upload'], type=["png"])
        wm_pos = st.selectbox(T['lbl_wm_pos'], options=['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'], format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        wm_scale = st.slider(T['lbl_wm_scale'], 5, 50, 15) / 100
        wm_opacity = st.slider(T['lbl_wm_opacity'], 0.1, 1.0, 1.0, 0.1)
        wm_margin = st.slider(T['lbl_wm_margin'], 0, 100, 15)

    st.divider()
    with st.expander("ℹ️ About"):
        st.markdown(T['about_prod'])
        st.markdown(T['about_auth'])
        st.markdown(T['about_lic'])
        st.markdown(T['about_repo'])
        st.caption(T['about_copy'])

# === MAIN PAGE ===
st.title(T['title'])

c_left, c_right = st.columns([1.5, 1], gap="large")

with c_left:
    st.subheader(T['files_header'])
    uploaded = st.file_uploader(T['uploader_label'], type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True, label_visibility="collapsed", key=f"up_{st.session_state['uploader_key']}")
    
    if uploaded:
        for f in uploaded:
            if f.name not in st.session_state['file_cache']:
                st.session_state['file_cache'][f.name] = f.getvalue()
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_map = st.session_state['file_cache']
    files_names = list(files_map.keys())
    
    if files_names:
        table_data = []
        for fname in files_names:
            fbytes = files_map[fname]
            w, h, size, fmt = get_image_metadata(fbytes)
            table_data.append({"Select": False, "Name": fname, "Size": f"{size/1024:.1f} KB", "Res": f"{w}x{h}", "Fmt": fmt})
            
        df = pd.DataFrame(table_data)
        edited_df = st.data_editor(df, column_config={"Select": st.column_config.CheckboxColumn(T['tbl_select'], default=False), "Name": st.column_config.TextColumn(T['tbl_name'], disabled=True)}, hide_index=True, use_container_width=True, key="editor_in")
        selected_files = edited_df[edited_df["Select"] == True]["Name"].tolist()
        preview_target = selected_files[-1] if selected_files else None

        act1, act2, act3 = st.columns([1, 1, 1.5])
        with act1:
            if st.button(T['btn_delete'], disabled=not selected_files, use_container_width=True):
                for fn in selected_files: del st.session_state['file_cache'][fn]
                st.rerun()
        with act2:
            if st.button(T['btn_reset'], use_container_width=True):
                st.session_state['file_cache'] = {}; st.session_state['results'] = None; st.rerun()
        with act3:
            if st.button(f"{T['btn_process']} ({len(files_names)})", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status = st.empty()
                
                wm_bytes = wm_file.getvalue() if wm_file else None
                wm_cached_obj = load_and_process_watermark(wm_bytes, wm_opacity)
                resize_cfg = {'enabled': resize_on, 'mode': resize_mode, 'value': resize_val, 'wm_scale': wm_scale, 'wm_margin': wm_margin, 'wm_position': wm_pos}
                
                results_list = []
                report_list = []
                zip_buffer = io.BytesIO()
                total_files = len(files_names)
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {}
                    # Використовуємо enumerate для індексу (1, 2, 3...)
                    for i, fname in enumerate(files_names):
                        fbytes = files_map[fname]
                        ext = out_fmt.lower()
                        # Передаємо index=i+1 для нумерації з одиниці
                        new_fname = generate_filename(fname, naming_mode, prefix, ext, index=i+1)
                        future = executor.submit(process_image_core, fbytes, new_fname, wm_cached_obj, resize_cfg, out_fmt, quality)
                        futures[future] = fname

                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            try:
                                res_bytes, stats = future.result()
                                zf.writestr(stats['filename'], res_bytes)
                                results_list.append((stats['filename'], res_bytes))
                                report_list.append(stats)
                            except Exception as e: st.error(f"Error: {e}")
                            progress_bar.progress((i + 1) / total_files)

                status.success(T['msg_done'])
                st.session_state['results'] = {'zip': zip_buffer.getvalue(), 'files': results_list, 'report': report_list}

    if 'results' in st.session_state and st.session_state['results']:
        res = st.session_state['results']
        report = res['report']
        total_orig = sum(r['orig_size'] for r in report)
        total_new = sum(r['new_size'] for r in report)
        saved_mb = (total_orig - total_new) / (1024*1024)
        
        st.divider()
        st.success(f"{T['res_savings']}: **{saved_mb:.2f} MB**")
        st.download_button(T['btn_dl_zip'], res['zip'], f"batch_{datetime.now().strftime('%H%M')}.zip", "application/zip", type="primary", use_container_width=True)
        
        with st.expander(T['exp_report']):
            df_rep = pd.DataFrame(report)
            df_rep['savings %'] = ((df_rep['orig_size'] - df_rep['new_size']) / df_rep['orig_size'] * 100).round(1)
            st.dataframe(df_rep, column_config={"savings %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%f%%")}, use_container_width=True)
            
        with st.expander(T['exp_dl_separate']):
            for name, data in res['files']:
                c1, c2 = st.columns([3, 1])
                c1.write(f"📄 {name}")
                c2.download_button("⬇️", data, file_name=name, key=f"dl_{name}")

with c_right:
    st.subheader(T['prev_header'])
    with st.container(border=True):
        if 'preview_target' in locals() and preview_target:
            raw_bytes = files_map[preview_target]
            wm_bytes = wm_file.getvalue() if wm_file else None
            wm_obj = load_and_process_watermark(wm_bytes, wm_opacity)
            resize_cfg = {'enabled': resize_on, 'mode': resize_mode, 'value': resize_val, 'wm_scale': wm_scale, 'wm_margin': wm_margin, 'wm_position': wm_pos}
            try:
                with st.spinner(T['prev_rendering']):
                    # Для прев'ю передаємо фіктивний індекс 1
                    preview_name = generate_filename(preview_target, naming_mode, prefix, out_fmt.lower(), index=1)
                    p_bytes, p_stats = process_image_core(raw_bytes, preview_name, wm_obj, resize_cfg, out_fmt, quality)
                st.image(p_bytes, caption=f"Preview: {preview_name}", use_container_width=True)
                k1, k2 = st.columns(2)
                k1.metric(T['prev_size'], p_stats['new_res'], p_stats['scale_factor'])
                delta = ((p_stats['new_size'] - p_stats['orig_size']) / p_stats['orig_size']) * 100
                k2.metric(T['prev_weight'], f"{p_stats['new_size']/1024:.1f} KB", f"{delta:.1f}%", delta_color="inverse")
            except Exception as e: st.error(f"Error: {e}")
        else:
            st.info(T['prev_info'])
            st.markdown('<div style="height:300px; background:#f0f2f6;"></div>', unsafe_allow_html=True)
