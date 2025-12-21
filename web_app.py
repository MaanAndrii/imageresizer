import streamlit as st
import pandas as pd
import io
import os
import shutil
import tempfile
import zipfile
import concurrent.futures
from datetime import datetime
from PIL import Image
import watermarker_engine as engine
import glob

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro v5.0", page_icon="📸", layout="wide")

DEFAULT_SETTINGS = {
    'resize_val': 1920,
    'wm_pos': 'bottom-right',
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0,
    'wm_text': '',
    'wm_text_color': '#FFFFFF'
}

TILED_SETTINGS = {'wm_scale': 15, 'wm_opacity': 0.3, 'wm_gap': 30, 'wm_angle': 45}
CORNER_SETTINGS = {'wm_scale': 15, 'wm_opacity': 1.0, 'wm_margin': 15, 'wm_angle': 0}

# --- ЛОКАЛІЗАЦІЯ ---
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v5.0",
        "sb_config": "🛠 Налаштування",
        "btn_defaults": "↺ Скинути налаштування",
        
        "sec_file": "1. Файл та Ім'я",
        "lbl_format": "Формат виводу",
        "lbl_quality": "Якість (%)",
        "lbl_naming": "Іменування файлів",
        "lbl_prefix": "Префікс файлу",
        
        "sec_geo": "2. Геометрія (Ресайз)",
        "chk_resize": "Змінювати розмір",
        "lbl_mode": "Режим",
        "lbl_px": "Розмір (px)",
        
        "sec_wm": "3. Вотермарка",
        "tab_logo": "🖼️ Логотип",
        "tab_text": "🔤 Текст",
        "lbl_logo_up": "Завантажити (PNG)",
        "lbl_text_input": "Текст вотермарки",
        "lbl_font": "Шрифт",
        "lbl_color": "Колір",
        
        "lbl_pos": "Позиція",
        "opt_pos_tile": "Замощення (Паттерн)",
        "lbl_scale": "Розмір / Масштаб (%)",
        "lbl_opacity": "Прозорість",
        "lbl_gap": "Проміжок (px)",
        "lbl_margin": "Відступ (px)",
        "lbl_angle": "Кут нахилу (°)",
        
        "files_header": "📂 Робоча область", 
        "uploader_label": "Завантажити фото",
        "btn_process": "🚀 Обробити", 
        "msg_done": "Готово!",
        "error_wm_load": "❌ Помилка: {}",
        "btn_dl_zip": "📦 Скачати ZIP",
        "exp_dl_separate": "⬇️ Скачати окремо",
        
        "prev_header": "👁️ Живий перегляд",
        "prev_placeholder": "Оберіть файл (✅) для перегляду",
        "stat_res": "Роздільна здатність",
        "stat_size": "Розмір файлу",
        
        "grid_select_all": "✅ Всі",
        "grid_deselect_all": "⬜ Жодного",
        "grid_delete": "🗑️ Видалити",
        "btn_selected": "✅ Обрано", # ВІДНОВЛЕНО
        "btn_select": "⬜ Обрати",   # ВІДНОВЛЕНО
        "warn_no_files": "⚠️ Спочатку оберіть файли!",
        
        "about_prod": "**Продукт:** Watermarker Pro MaAn v5.0", 
        "about_changelog": "**v5.0 Text & Metadata:**\n- 🔤 Текстові вотермарки\n- 🔄 Авто-поворот фото (EXIF Fix)\n- 💾 Збереження метаданих камери"
    },
    "en": {
        "title": "📸 Watermarker Pro v5.0",
        "sb_config": "🛠 Configuration",
        "btn_defaults": "↺ Reset",
        
        "sec_file": "1. File & Naming",
        "lbl_format": "Output Format",
        "lbl_quality": "Quality (%)",
        "lbl_naming": "Naming",
        "lbl_prefix": "Prefix",
        
        "sec_geo": "2. Geometry",
        "chk_resize": "Resize",
        "lbl_mode": "Mode",
        "lbl_px": "Size (px)",
        
        "sec_wm": "3. Watermark",
        "tab_logo": "🖼️ Logo",
        "tab_text": "🔤 Text",
        "lbl_logo_up": "Upload (PNG)",
        "lbl_text_input": "Watermark Text",
        "lbl_font": "Font",
        "lbl_color": "Color",
        
        "lbl_pos": "Position",
        "opt_pos_tile": "Tiled (Pattern)",
        "lbl_scale": "Size / Scale (%)",
        "lbl_opacity": "Opacity",
        "lbl_gap": "Gap (px)",
        "lbl_margin": "Margin (px)",
        "lbl_angle": "Angle (°)",
        
        "files_header": "📂 Workspace", 
        "uploader_label": "Upload Photos",
        "btn_process": "🚀 Process", 
        "msg_done": "Done!",
        "error_wm_load": "❌ Error: {}",
        "btn_dl_zip": "📦 Download ZIP",
        "exp_dl_separate": "⬇️ Download Separate",
        
        "prev_header": "👁️ Live Preview",
        "prev_placeholder": "Select a file (✅) to preview",
        "stat_res": "Resolution",
        "stat_size": "File Size",
        
        "grid_select_all": "✅ All",
        "grid_deselect_all": "⬜ None",
        "grid_delete": "🗑️ Delete",
        "btn_selected": "✅ Selected", # RESTORED
        "btn_select": "⬜ Select",     # RESTORED
        "warn_no_files": "⚠️ Select files first!",
        
        "about_prod": "**Product:** Watermarker Pro MaAn v5.0", 
        "about_changelog": "**v5.0 Text & Metadata:**\n- 🔤 Text Watermarks\n- 🔄 Auto-Rotation (EXIF Fix)\n- 💾 Metadata Preservation"
    }
}

# --- CSS STYLING ---
st.markdown("""
<style>
    div[data-testid="column"] {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #eee;
        transition: all 0.2s ease;
    }
    div[data-testid="column"]:hover {
        border-color: #ff4b4b;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div[data-testid="column"] button { width: 100%; margin-top: 5px; }
    .block-container { padding-top: 2rem; }
    .preview-placeholder {
        border: 2px dashed #e0e0e0; border-radius: 10px;
        padding: 40px 20px; text-align: center; color: #888;
        background-color: #fafafa; margin-top: 10px;
    }
    .preview-icon { font-size: 40px; margin-bottom: 10px; display: block; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'temp_dir' not in st.session_state: st.session_state['temp_dir'] = tempfile.mkdtemp(prefix="wm_pro_")
if 'file_cache' not in st.session_state: st.session_state['file_cache'] = {} 
if 'selected_files' not in st.session_state: st.session_state['selected_files'] = set()
if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0
if 'lang_code' not in st.session_state: st.session_state['lang_code'] = 'ua'

# --- HELPERS ---
def save_uploaded_file(uploaded_file):
    temp_dir = st.session_state['temp_dir']
    file_path = os.path.join(temp_dir, uploaded_file.name)
    if os.path.exists(file_path):
        base, ext = os.path.splitext(uploaded_file.name)
        timestamp = datetime.now().strftime("%H%M%S")
        file_path = os.path.join(temp_dir, f"{base}_{timestamp}{ext}")
    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
    return file_path, os.path.basename(file_path)

def get_available_fonts():
    """Шукає шрифти в папці assets/fonts."""
    font_dir = os.path.join(os.getcwd(), 'assets', 'fonts')
    if not os.path.exists(font_dir):
        return []
    fonts = glob.glob(os.path.join(font_dir, "*.ttf")) + glob.glob(os.path.join(font_dir, "*.otf"))
    return [os.path.basename(f) for f in fonts]

# --- INIT SETTINGS ---
for k, v in DEFAULT_SETTINGS.items():
    key_name = f'{k}_key' if not k.endswith('_val') else f'{k}_state'
    if key_name not in st.session_state: st.session_state[key_name] = v

def handle_pos_change():
    if st.session_state['wm_pos_key'] == 'tiled':
        st.session_state['wm_scale_key'] = TILED_SETTINGS['wm_scale']
        st.session_state['wm_opacity_key'] = TILED_SETTINGS['wm_opacity']
        st.session_state['wm_gap_key'] = TILED_SETTINGS['wm_gap']
        st.session_state['wm_angle_key'] = TILED_SETTINGS['wm_angle']
    else:
        st.session_state['wm_scale_key'] = CORNER_SETTINGS['wm_scale']
        st.session_state['wm_opacity_key'] = CORNER_SETTINGS['wm_opacity']
        st.session_state['wm_margin_key'] = CORNER_SETTINGS['wm_margin']
        st.session_state['wm_angle_key'] = CORNER_SETTINGS['wm_angle']

def reset_settings():
    st.session_state['resize_val_state'] = DEFAULT_SETTINGS['resize_val']
    st.session_state['wm_pos_key'] = DEFAULT_SETTINGS['wm_pos']
    st.session_state['wm_scale_key'] = DEFAULT_SETTINGS['wm_scale']
    st.session_state['wm_opacity_key'] = DEFAULT_SETTINGS['wm_opacity']
    st.session_state['wm_margin_key'] = DEFAULT_SETTINGS['wm_margin']
    st.session_state['wm_gap_key'] = DEFAULT_SETTINGS['wm_gap']
    st.session_state['wm_angle_key'] = DEFAULT_SETTINGS['wm_angle']
    st.session_state['wm_text_key'] = DEFAULT_SETTINGS['wm_text']
    st.session_state['wm_text_color_key'] = DEFAULT_SETTINGS['wm_text_color']

# --- UI START ---
with st.sidebar:
    lang_code = st.session_state['lang_code']
    T = TRANSLATIONS[lang_code]
    
    st.header(T['sb_config'])
    
    with st.expander(T['sec_file']):
        out_fmt = st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"])
        quality = 80
        if out_fmt != "PNG": quality = st.slider(T['lbl_quality'], 50, 100, 80, 5)
        naming_mode = st.selectbox(T['lbl_naming'], ["Keep Original", "Prefix + Sequence"])
        prefix = st.text_input(T['lbl_prefix'], placeholder="img")

    with st.expander(T['sec_geo'], expanded=True):
        resize_on = st.checkbox(T['chk_resize'], value=True)
        resize_mode = st.selectbox(T['lbl_mode'], ["Max Side", "Exact Width", "Exact Height"], disabled=not resize_on)
        c1, c2, c3 = st.columns(3)
        def set_res(v): st.session_state['resize_val_state'] = v
        c1.button("HD", on_click=set_res, args=(1280,), use_container_width=True)
        c2.button("FHD", on_click=set_res, args=(1920,), use_container_width=True)
        c3.button("4K", on_click=set_res, args=(3840,), use_container_width=True)
        resize_val = st.number_input(T['lbl_px'], 100, 8000, key='resize_val_state', disabled=not resize_on)

    with st.expander(T['sec_wm'], expanded=True):
        # Вкладки: Логотип / Текст
        tab1, tab2 = st.tabs([T['tab_logo'], T['tab_text']])
        
        wm_type = "image"
        
        with tab1:
            wm_file = st.file_uploader(T['lbl_logo_up'], type=["png"], key="wm_uploader")
            if wm_file: wm_type = "image"
            
        with tab2:
            wm_text = st.text_area(T['lbl_text_input'], key='wm_text_key')
            
            # Пошук шрифтів
            fonts = get_available_fonts()
            selected_font_name = None
            if fonts:
                selected_font_name = st.selectbox(T['lbl_font'], fonts)
            else:
                st.caption("No fonts found in assets/fonts. Using default.")
                
            wm_text_color = st.color_picker(T['lbl_color'], '#FFFFFF', key='wm_text_color_key')
            if wm_text: wm_type = "text"

        st.divider()
        
        # Спільні налаштування
        wm_pos = st.selectbox(T['lbl_pos'], ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], 
                              key='wm_pos_key', on_change=handle_pos_change)
        
        wm_scale = st.slider(T['lbl_scale'], 5, 100, key='wm_scale_key') / 100
        wm_opacity = st.slider(T['lbl_opacity'], 0.1, 1.0, key='wm_opacity_key')
        
        if wm_pos == 'tiled':
            wm_gap = st.slider(T['lbl_gap'], 0, 200, key='wm_gap_key')
            wm_margin = wm_gap
        else:
            wm_margin = st.slider(T['lbl_margin'], 0, 100, key='wm_margin_key')
            wm_gap = 0
            
        wm_angle = st.slider(T['lbl_angle'], -180, 180, key='wm_angle_key')

    st.divider()
    if st.button(T['btn_defaults'], on_click=reset_settings, use_container_width=True): st.rerun()
    
    with st.expander("ℹ️ About", expanded=False):
        st.markdown(T['about_prod'])
        st.markdown(T['about_changelog'])
        st.divider()
        lang_col1, lang_col2 = st.columns(2)
        with lang_col1:
            if st.button("🇺🇦 UA", type="primary" if lang_code == 'ua' else "secondary", use_container_width=True):
                st.session_state['lang_code'] = 'ua'; st.rerun()
        with lang_col2:
            if st.button("🇺🇸 EN", type="primary" if lang_code == 'en' else "secondary", use_container_width=True):
                st.session_state['lang_code'] = 'en'; st.rerun()

st.title(T['title'])
c_left, c_right = st.columns([1.8, 1], gap="large")

with c_left:
    st.subheader(T['files_header'])
    
    uploaded = st.file_uploader(T['uploader_label'], type=['jpg','jpeg','png','webp'], accept_multiple_files=True, label_visibility="collapsed", key=f"up_{st.session_state['uploader_key']}")
    
    if uploaded:
        for f in uploaded:
            fpath, fname = save_uploaded_file(f)
            st.session_state['file_cache'][fname] = fpath
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_map = st.session_state['file_cache']
    files_names = list(files_map.keys())

    if files_names:
        act1, act2, act3 = st.columns([1, 1, 1])
        with act1:
            if st.button(T['grid_select_all'], use_container_width=True):
                st.session_state['selected_files'] = set(files_names)
                st.rerun()
        with act2:
            if st.button(T['grid_deselect_all'], use_container_width=True):
                st.session_state['selected_files'].clear()
                st.rerun()
        with act3:
            sel_count = len(st.session_state['selected_files'])
            if st.button(f"{T['grid_delete']} ({sel_count})", type="primary", use_container_width=True, disabled=sel_count==0):
                for f in list(st.session_state['selected_files']):
                    if f in files_map: del files_map[f]
                st.session_state['selected_files'].clear()
                st.rerun()
        
        st.divider()
        
        cols_count = 4
        cols = st.columns(cols_count)
        
        for i, fname in enumerate(files_names):
            col = cols[i % cols_count]
            fpath = files_map[fname]
            with col:
                thumb = engine.get_thumbnail(fpath)
                if thumb: st.image(thumb, use_container_width=True)
                else: st.warning("Error")
                
                is_sel = fname in st.session_state['selected_files']
                if st.button(T['btn_selected'] if is_sel else T['btn_select'], key=f"btn_{fname}", type="primary" if is_sel else "secondary", use_container_width=True):
                    if is_sel: st.session_state['selected_files'].remove(fname)
                    else: st.session_state['selected_files'].add(fname)
                    st.rerun()

        st.caption(f"Files: {len(files_names)} | Selected: {len(st.session_state['selected_files'])}")
        
        process_list = list(st.session_state['selected_files'])
        can_process = len(process_list) > 0
        
        if st.button(T['btn_process'], type="primary", use_container_width=True):
            if not can_process:
                st.warning(T['warn_no_files'])
            else:
                progress = st.progress(0)
                
                # --- ЛОГІКА ПІДГОТОВКИ ВОТЕРМАРКИ ---
                wm_obj = None
                try:
                    if wm_text.strip():
                        font_path = None
                        if selected_font_name:
                            font_path = os.path.join(os.getcwd(), 'assets', 'fonts', selected_font_name)
                        wm_obj = engine.create_text_watermark(wm_text, font_path, 100, wm_text_color)
                        wm_obj = engine.apply_opacity(wm_obj, wm_opacity)
                    elif wm_file:
                        wm_bytes = wm_file.getvalue()
                        wm_obj = engine.load_watermark_from_file(wm_bytes)
                        wm_obj = engine.apply_opacity(wm_obj, wm_opacity)
                except Exception as e:
                    st.error(T['error_wm_load'].format(e))
                    st.stop()
                
                resize_cfg = {
                    'enabled': resize_on, 'mode': resize_mode, 'value': resize_val,
                    'wm_scale': wm_scale, 'wm_margin': wm_margin if wm_pos!='tiled' else 0,
                    'wm_gap': wm_gap if wm_pos=='tiled' else 0,
                    'wm_position': wm_pos, 'wm_angle': wm_angle
                }
                
                results = []
                report = []
                zip_buffer = io.BytesIO()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {}
                    for i, fname in enumerate(process_list):
                        fpath = files_map[fname]
                        new_fname = engine.generate_filename(fpath, naming_mode, prefix, out_fmt.lower(), i+1)
                        future = executor.submit(engine.process_image, fpath, new_fname, wm_obj, resize_cfg, out_fmt, quality)
                        futures[future] = fname
                    
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i, fut in enumerate(concurrent.futures.as_completed(futures)):
                            try:
                                res_bytes, stats = fut.result()
                                zf.writestr(stats['filename'], res_bytes)
                                results.append((stats['filename'], res_bytes))
                                report.append(stats)
                            except Exception as e: st.error(f"Error {futures[fut]}: {e}")
                            progress.progress((i+1)/len(process_list))
                
                st.session_state['results'] = {'zip': zip_buffer.getvalue(), 'files': results, 'report': report}
                st.toast(T['msg_done'], icon='🎉')

    if 'results' in st.session_state and st.session_state['results']:
        res = st.session_state['results']
        st.success("Batch Processing Complete!")
        st.download_button(T['btn_dl_zip'], res['zip'], "photos.zip", "application/zip", type="primary")
        with st.expander(T['exp_dl_separate']):
            for name, data in res['files']:
                c1, c2 = st.columns([3, 1])
                c1.write(f"📄 {name}")
                c2.download_button("⬇️", data, file_name=name, key=f"dl_{name}")

with c_right:
    st.subheader(T['prev_header'])
    selected_list = list(st.session_state['selected_files'])
    target_file = selected_list[-1] if selected_list else None
    
    with st.container(border=True):
        if target_file and target_file in files_map:
            fpath = files_map[target_file]
            
            wm_obj = None
            try:
                if wm_text.strip():
                    font_path = None
                    if selected_font_name:
                        font_path = os.path.join(os.getcwd(), 'assets', 'fonts', selected_font_name)
                    wm_obj = engine.create_text_watermark(wm_text, font_path, 100, wm_text_color)
                    if wm_obj: wm_obj = engine.apply_opacity(wm_obj, wm_opacity)
                elif wm_file:
                    wm_obj = engine.load_watermark_from_file(wm_file.getvalue())
                    if wm_obj: wm_obj = engine.apply_opacity(wm_obj, wm_opacity)
            except: pass
            
            resize_cfg = {
                'enabled': resize_on, 'mode': resize_mode, 'value': resize_val,
                'wm_scale': wm_scale, 'wm_margin': wm_margin if wm_pos!='tiled' else 0,
                'wm_gap': wm_gap if wm_pos=='tiled' else 0,
                'wm_position': wm_pos, 'wm_angle': wm_angle
            }
            
            try:
                preview_fname = engine.generate_filename(fpath, naming_mode, prefix, out_fmt.lower(), 1)
                prev_bytes, stats = engine.process_image(fpath, preview_fname, wm_obj, resize_cfg, out_fmt, quality)
                
                st.image(prev_bytes, caption=f"{stats['filename']}", use_container_width=True)
                m1, m2 = st.columns(2)
                delta_size = ((stats['new_size'] - stats['orig_size']) / stats['orig_size']) * 100
                m1.metric(T['stat_res'], stats['new_res'], stats['scale_factor'])
                m2.metric(T['stat_size'], f"{stats['new_size']/1024:.1f} KB", f"{delta_size:.1f}%", delta_color="inverse")
            except Exception as e: st.error(f"Preview Error: {e}")
        else:
            st.markdown(f"""<div class="preview-placeholder"><span class="preview-icon">🖼️</span><p>{T['prev_placeholder']}</p></div>""", unsafe_allow_html=True)
