import streamlit as st
import pandas as pd
import io
import zipfile
import concurrent.futures
from datetime import datetime
import watermarker_engine as engine

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro v4.8", page_icon="📸", layout="wide")

MAX_FILE_SIZE_MB = 50

# --- СТАН (STATE) ---
# Ініціалізація нових та старих значень
if 'file_cache' not in st.session_state: st.session_state['file_cache'] = {}
if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0
if 'lang_code' not in st.session_state: st.session_state['lang_code'] = 'ua'

# Значення для пресетів
if 'resize_val_state' not in st.session_state: st.session_state['resize_val_state'] = 1920
if 'out_fmt_state' not in st.session_state: st.session_state['out_fmt_state'] = "JPEG"
if 'quality_state' not in st.session_state: st.session_state['quality_state'] = 80
if 'resize_on_state' not in st.session_state: st.session_state['resize_on_state'] = True
if 'keep_exif_state' not in st.session_state: st.session_state['keep_exif_state'] = False

# Текстова вотермарка
if 'wm_text_val_state' not in st.session_state: st.session_state['wm_text_val_state'] = "@my_copyright"
if 'wm_text_color_state' not in st.session_state: st.session_state['wm_text_color_state'] = "#FFFFFF"
if 'wm_text_size_state' not in st.session_state: st.session_state['wm_text_size_state'] = 50

# Дефолтні налаштування
DEFAULT_SETTINGS = {
    'wm_pos': 'bottom-right',
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0
}

# Доініціалізація ключів слайдерів
for k, v in DEFAULT_SETTINGS.items():
    key_name = f'{k}_key'
    if key_name not in st.session_state: 
        st.session_state[key_name] = v

# --- ЛОКАЛІЗАЦІЯ ---
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v4.8",
        "lang_select": "Мова / Language",
        "sb_config": "🛠 Налаштування",
        "presets_title": "⚡ Швидкі пресети",
        "btn_defaults": "↺ Скинути",
        
        "sec_file": "1. Файл та Метадані",
        "sec_geo": "2. Геометрія (Ресайз)",
        "sec_wm": "3. Вотермарка",
        
        "lbl_format": "Формат", 
        "lbl_quality": "Якість", 
        "lbl_keep_exif": "Зберегти EXIF (дату, камеру)",
        "lbl_naming": "Стратегія імен", 
        "lbl_prefix": "Префікс",
        "chk_resize": "Змінювати розмір", 
        "lbl_resize_mode": "Режим", 
        "lbl_resize_val": "Розмір (px)",
        
        "lbl_wm_type": "Тип вотермарки",
        "opt_wm_img": "📁 Зображення (Logo)",
        "opt_wm_text": "✍️ Текст",
        "lbl_wm_text_val": "Введіть текст",
        "lbl_wm_text_color": "Колір",
        "lbl_wm_text_size": "Розмір шрифту",
        
        "lbl_wm_upload": "Завантажити лого (PNG)", 
        "lbl_wm_pos": "Позиція", 
        "lbl_wm_scale": "Масштаб (%)", 
        "lbl_wm_opacity": "Прозорість", 
        "lbl_wm_margin_edge": "Відступ (px)", 
        "lbl_wm_gap": "Проміжок (px)", 
        "lbl_wm_angle": "Кут нахилу (°)",
        
        "files_header": "📂 Робоча область", 
        "uploader_label": "Файли", 
        "tbl_select": "✅", 
        "tbl_name": "Файл",
        "btn_delete": "🗑️ Видалити", 
        "btn_reset": "♻️ Очистити список", 
        "btn_process": "🚀 Обробити", 
        "msg_done": "Готово!",
        
        "error_file_size": "❌ Файл {} завеликий! Макс {} MB",
        "error_corrupted": "❌ Файл {} пошкоджений",
        "error_wm_load": "❌ Помилка вотермарки: {}",
        
        "res_savings": "Економія", 
        "btn_dl_zip": "📦 Скачати ZIP", 
        "exp_report": "📊 Технічний звіт", 
        "exp_dl_separate": "⬇️ Скачати окремо",
        
        "prev_header": "👁️ Живий перегляд", 
        "prev_rendering": "Генерація...", 
        "prev_size": "Розмір", 
        "prev_weight": "Вага", 
        "prev_info": "Оберіть файл (✅) для тесту."
    },
    "en": {
        "title": "📸 Watermarker Pro v4.8",
        "lang_select": "Language / Мова",
        "sb_config": "🛠 Configuration",
        "presets_title": "⚡ Quick Presets",
        "btn_defaults": "↺ Reset",
        
        "sec_file": "1. File & Metadata",
        "sec_geo": "2. Geometry (Resize)",
        "sec_wm": "3. Watermark",
        
        "lbl_format": "Output Format", 
        "lbl_quality": "Quality", 
        "lbl_keep_exif": "Keep EXIF (Metadata)",
        "lbl_naming": "Naming Strategy", 
        "lbl_prefix": "Filename Prefix",
        "chk_resize": "Enable Resize", 
        "lbl_resize_mode": "Mode", 
        "lbl_resize_val": "Size (px)",
        
        "lbl_wm_type": "Watermark Type",
        "opt_wm_img": "📁 Image (Logo)",
        "opt_wm_text": "✍️ Text",
        "lbl_wm_text_val": "Enter text",
        "lbl_wm_text_color": "Color",
        "lbl_wm_text_size": "Font Size",
        
        "lbl_wm_upload": "Upload Logo (PNG)", 
        "lbl_wm_pos": "Position", 
        "lbl_wm_scale": "Scale (%)", 
        "lbl_wm_opacity": "Opacity", 
        "lbl_wm_margin_edge": "Margin (px)", 
        "lbl_wm_gap": "Gap (px)", 
        "lbl_wm_angle": "Angle (°)",
        
        "files_header": "📂 Workspace", 
        "uploader_label": "Files", 
        "tbl_select": "✅", 
        "tbl_name": "File",
        "btn_delete": "🗑️ Delete", 
        "btn_reset": "♻️ Clear List", 
        "btn_process": "🚀 Process", 
        "msg_done": "Done!",
        
        "error_file_size": "❌ File {} too large! Max {} MB",
        "error_corrupted": "❌ File {} is corrupted",
        "error_wm_load": "❌ Watermark Error: {}",
        
        "res_savings": "Savings", 
        "btn_dl_zip": "📦 Download ZIP", 
        "exp_report": "📊 Technical Report", 
        "exp_dl_separate": "⬇️ Download Separate",
        
        "prev_header": "👁️ Live Preview", 
        "prev_rendering": "Rendering...", 
        "prev_size": "Dimensions", 
        "prev_weight": "Weight", 
        "prev_info": "Select a file (✅) to preview."
    }
}

OPTIONS_MAP = {
    "ua": {
        "Keep Original": "Зберегти назву", "Prefix + Sequence": "Префікс + Номер (001)",
        "Max Side": "Макс. сторона", "Exact Width": "Точна ширина", "Exact Height": "Точна висота",
        "bottom-right": "Знизу-праворуч", "bottom-left": "Знизу-ліворуч", "top-right": "Зверху-праворуч", "top-left": "Зверху-ліворуч", "center": "Центр", "tiled": "Замощення"
    },
    "en": {
        "Keep Original": "Keep Original", "Prefix + Sequence": "Prefix + Sequence (001)",
        "Max Side": "Max Side", "Exact Width": "Exact Width", "Exact Height": "Exact Height",
        "bottom-right": "Bottom-Right", "bottom-left": "Bottom-Left", "top-right": "Top-Right", "top-left": "Top-Left", "center": "Center", "tiled": "Tiled"
    }
}

# --- PROXY FUNCTIONS ---
@st.cache_data(show_spinner=False)
def ui_get_metadata(file_bytes): 
    return engine.get_image_metadata(file_bytes)

# --- ПРЕСЕТИ ---
def apply_preset(name):
    st.session_state['resize_on_state'] = True
    if name == 'insta':
        st.session_state['resize_val_state'] = 1080
        st.session_state['out_fmt_state'] = 'JPEG'
        st.session_state['quality_state'] = 90
    elif name == 'web':
        st.session_state['resize_val_state'] = 1280
        st.session_state['out_fmt_state'] = 'WEBP'
        st.session_state['quality_state'] = 85
    elif name == 'orig':
        st.session_state['resize_on_state'] = False
        st.session_state['quality_state'] = 100

def handle_pos_change():
    if st.session_state['wm_pos_key'] == 'tiled':
        st.session_state['wm_opacity_key'] = 0.3
    else:
        st.session_state['wm_opacity_key'] = 1.0

# --- UI START ---
lang_code = st.session_state['lang_code']
T = TRANSLATIONS[lang_code]

with st.sidebar:
    st.header(T['sb_config'])
    
    # === 0. ПРЕСЕТИ ===
    st.caption(T['presets_title'])
    c1, c2, c3 = st.columns(3)
    c1.button("Insta", on_click=apply_preset, args=('insta',), use_container_width=True)
    c2.button("Web", on_click=apply_preset, args=('web',), use_container_width=True)
    c3.button("Orig", on_click=apply_preset, args=('orig',), use_container_width=True)
    st.divider()
    
    # === 1. ФАЙЛ ===
    with st.expander(T['sec_file'], expanded=False):
        out_fmt = st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"], key='out_fmt_state')
        quality = 80
        if out_fmt != "PNG": 
            quality = st.slider(T['lbl_quality'], 50, 100, key='quality_state')
        st.checkbox(T['lbl_keep_exif'], key='keep_exif_state')
        
        naming_mode = st.selectbox(T['lbl_naming'], ["Keep Original", "Prefix + Sequence"], format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        prefix = st.text_input(T['lbl_prefix'], placeholder="img")

    # === 2. ГЕОМЕТРІЯ ===
    with st.expander(T['sec_geo'], expanded=True):
        resize_on = st.checkbox(T['chk_resize'], key='resize_on_state')
        resize_mode = st.selectbox(T['lbl_resize_mode'], ["Max Side", "Exact Width", "Exact Height"], disabled=not resize_on, format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        resize_val = st.number_input(T['lbl_resize_val'], min_value=100, max_value=8000, step=100, key='resize_val_state', disabled=not resize_on)

    # === 3. ВОТЕРМАРКА ===
    with st.expander(T['sec_wm'], expanded=True):
        wm_type = st.radio(T['lbl_wm_type'], ["img", "text"], format_func=lambda x: T['opt_wm_img'] if x == "img" else T['opt_wm_text'])
        
        wm_source_obj = None
        is_text_mode = (wm_type == "text")
        
        if is_text_mode:
            wm_text_val = st.text_input(T['lbl_wm_text_val'], key='wm_text_val_state')
            col1, col2 = st.columns(2)
            wm_color = col1.color_picker(T['lbl_wm_text_color'], key='wm_text_color_state')
            wm_size = col2.number_input(T['lbl_wm_text_size'], 10, 200, key='wm_text_size_state')
            
            # Об'єкт для передачі в двигун
            wm_source_obj = {
                'text': wm_text_val,
                'color': wm_color,
                'size': wm_size
            }
        else:
            wm_file = st.file_uploader(T['lbl_wm_upload'], type=["png"])
            if wm_file:
                wm_source_obj = wm_file.getvalue()
        
        wm_pos = st.selectbox(T['lbl_wm_pos'], ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], key='wm_pos_key', on_change=handle_pos_change, format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        wm_scale = st.slider(T['lbl_wm_scale'], 5, 90, key='wm_scale_key') / 100
        wm_opacity = st.slider(T['lbl_wm_opacity'], 0.1, 1.0, key='wm_opacity_key', step=0.05)
        
        if wm_pos == 'tiled':
            wm_gap = st.slider(T['lbl_wm_gap'], 0, 200, key='wm_gap_key')
            wm_margin = wm_gap
        else:
            wm_margin = st.slider(T['lbl_wm_margin_edge'], 0, 100, key='wm_margin_key')
            wm_gap = 0
            
        wm_angle = st.slider(T['lbl_wm_angle'], -180, 180, key='wm_angle_key')

    # --- FOOTER ---
    st.divider()
    selected_lang = st.selectbox(T['lang_select'], ["🇺🇦 Українська", "🇺🇸 English"], index=0 if lang_code == 'ua' else 1)
    new_code = "ua" if "Українська" in selected_lang else "en"
    if new_code != lang_code:
        st.session_state['lang_code'] = new_code
        st.rerun()

# --- MAIN PAGE ---
st.title(T['title'])
c_left, c_right = st.columns([1.5, 1], gap="large")

with c_left:
    st.subheader(T['files_header'])
    uploaded = st.file_uploader(T['uploader_label'], type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True, label_visibility="collapsed", key=f"up_{st.session_state['uploader_key']}")
    
    if uploaded:
        for f in uploaded:
            if len(f.getvalue()) / (1024*1024) > MAX_FILE_SIZE_MB:
                st.error(T['error_file_size'].format(f.name, MAX_FILE_SIZE_MB))
                continue
            if f.name not in st.session_state['file_cache']:
                st.session_state['file_cache'][f.name] = f.getvalue()
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_map = st.session_state['file_cache']
    files_names = list(files_map.keys())
    
    if files_names:
        table_data = []
        corrupted_files = []
        for fname in files_names:
            w, h, size, fmt = ui_get_metadata(files_map[fname])
            if fmt is None:
                corrupted_files.append(fname)
                table_data.append({"Select": False, "Name": f"❌ {fname}", "Size": "ERR", "Res": "ERR"})
            else:
                table_data.append({"Select": False, "Name": fname, "Size": f"{size/1024:.1f} KB", "Res": f"{w}x{h}"})
        
        df = pd.DataFrame(table_data)
        edited_df = st.data_editor(df, column_config={"Select": st.column_config.CheckboxColumn(T['tbl_select'], default=False), "Name": st.column_config.TextColumn(T['tbl_name'], disabled=True)}, hide_index=True, use_container_width=True, key="editor_in")
        
        selected_files = edited_df[edited_df["Select"] == True]["Name"].tolist()
        selected_files = [f.replace("❌ ", "") for f in selected_files]
        preview_target = selected_files[-1] if selected_files else None

        c_act1, c_act2, c_act3 = st.columns([1, 1, 1.5])
        with c_act1:
            if st.button(T['btn_delete'], disabled=not selected_files, use_container_width=True):
                for fn in selected_files: del st.session_state['file_cache'][fn]
                st.rerun()
        with c_act2:
            if st.button(T['btn_reset'], use_container_width=True):
                st.session_state['file_cache'] = {}
                st.rerun()
        with c_act3:
            can_process = len(corrupted_files) == 0 and len(files_names) > 0
            if st.button(f"{T['btn_process']} ({len(files_names)})", type="primary", use_container_width=True, disabled=not can_process):
                progress_bar = st.progress(0)
                
                # Підготовка вотермарки ОДИН РАЗ
                try:
                    wm_final_obj = engine.load_and_process_watermark(wm_source_obj, wm_opacity, is_text=is_text_mode, text_params=wm_source_obj if is_text_mode else None)
                except ValueError as e:
                    st.error(T['error_wm_load'].format(e))
                    st.stop()
                
                resize_cfg = {
                    'enabled': resize_on, 'mode': resize_mode, 'value': resize_val, 
                    'wm_scale': wm_scale, 'wm_margin': wm_margin if wm_pos != 'tiled' else 0,
                    'wm_gap': wm_gap if wm_pos == 'tiled' else 0,
                    'wm_position': wm_pos, 'wm_angle': wm_angle
                }
                
                res_files = []
                report_list = []
                zip_buffer = io.BytesIO()
                total = len(files_names)
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {}
                    for i, fname in enumerate(files_names):
                        fbytes = files_map[fname]
                        new_fname = engine.generate_filename(fname, naming_mode, prefix, out_fmt.lower(), index=i+1, file_bytes=fbytes)
                        # Передаємо keep_exif
                        future = executor.submit(engine.process_image, fbytes, new_fname, wm_final_obj, resize_cfg, out_fmt, quality, st.session_state['keep_exif_state'])
                        futures[future] = fname

                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            try:
                                res_bytes, stats = future.result()
                                zf.writestr(stats['filename'], res_bytes)
                                res_files.append((stats['filename'], res_bytes))
                                report_list.append(stats)
                            except Exception as e:
                                st.error(f"Error {futures[future]}: {e}")
                            progress_bar.progress((i + 1) / total)

                st.session_state['results'] = {'zip': zip_buffer.getvalue(), 'files': res_files, 'report': report_list}
                st.toast(T['msg_done'], icon='🎉')

    # RESULT BLOCK
    if 'results' in st.session_state and st.session_state['results']:
        res = st.session_state['results']
        st.divider()
        st.download_button(T['btn_dl_zip'], res['zip'], f"batch_{datetime.now().strftime('%H%M')}.zip", "application/zip", type="primary", use_container_width=True)
        
        with st.expander(T['exp_report']):
            st.dataframe(pd.DataFrame(res['report']), use_container_width=True)
        
        with st.expander(T['exp_dl_separate']):
            for name, data in res['files']:
                col1, col2 = st.columns([3, 1])
                col1.write(f"📄 {name}")
                col2.download_button("⬇️", data, file_name=name, key=f"dl_{name}")

with c_right:
    st.subheader(T['prev_header'])
    with st.container(border=True):
        if 'preview_target' in locals() and preview_target:
            raw_bytes = files_map[preview_target]
            try:
                # Live rendering
                wm_prev_obj = engine.load_and_process_watermark(wm_source_obj, wm_opacity, is_text=is_text_mode, text_params=wm_source_obj if is_text_mode else None)
                
                prev_cfg = {
                    'enabled': resize_on, 'mode': resize_mode, 'value': resize_val, 
                    'wm_scale': wm_scale, 'wm_margin': wm_margin if wm_pos != 'tiled' else 0,
                    'wm_gap': wm_gap if wm_pos == 'tiled' else 0,
                    'wm_position': wm_pos, 'wm_angle': wm_angle
                }
                
                with st.spinner(T['prev_rendering']):
                    p_name = engine.generate_filename(preview_target, naming_mode, prefix, out_fmt.lower(), 1, raw_bytes)
                    p_bytes, p_stats = engine.process_image(raw_bytes, p_name, wm_prev_obj, prev_cfg, out_fmt, quality, st.session_state['keep_exif_state'])
                
                st.image(p_bytes, caption=f"Preview: {p_name}", use_container_width=True)
                k1, k2 = st.columns(2)
                k1.metric(T['prev_size'], p_stats['new_res'])
                delta = ((p_stats['new_size'] - p_stats['orig_size']) / p_stats['orig_size']) * 100
                k2.metric(T['prev_weight'], f"{p_stats['new_size']/1024:.1f} KB", f"{delta:.1f}%", delta_color="inverse")
            except Exception as e:
                st.error(f"Preview Error: {e}")
        else:
            st.info(T['prev_info'])
