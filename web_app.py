import streamlit as st
import pandas as pd
import io
import os
import shutil
import tempfile
import zipfile
import concurrent.futures
import gc
import json
from datetime import datetime
from PIL import Image
import watermarker_engine as engine
import editor_module as editor # NEW IMPORT
import glob

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro v5.8", page_icon="📸", layout="wide")

DEFAULT_SETTINGS = {
    'resize_val': 1920,
    'wm_pos': 'bottom-right',
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0,
    'wm_text': '',
    'wm_text_color': '#FFFFFF',
    'out_fmt': 'JPEG',
    'out_quality': 80,
    'naming_mode': 'Keep Original',
    'naming_prefix': '',
    'font_name': None,
    'preset_wm_bytes': None
}

TILED_SETTINGS = {'wm_scale': 15, 'wm_opacity': 0.3, 'wm_gap': 30, 'wm_angle': 45}
CORNER_SETTINGS = {'wm_scale': 15, 'wm_opacity': 1.0, 'wm_margin': 15, 'wm_angle': 0}

# --- ЛОКАЛІЗАЦІЯ ---
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v5.8",
        "sb_config": "🛠 Налаштування",
        "btn_defaults": "↺ Скинути налаштування",
        
        "sec_presets": "💾 Менеджер пресетів",
        "lbl_load_preset": "Завантажити пресет (.json)",
        "btn_save_preset": "⬇️ Зберегти повний пресет",
        "msg_preset_loaded": "✅ Пресет завантажено!",
        "error_preset": "❌ Помилка пресету: {}",
        
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
        "msg_preset_logo_active": "ℹ️ Логотип із пресету активний.",
        
        "lbl_pos": "Позиція",
        "opt_pos_tile": "Замощення (Паттерн)",
        "lbl_scale": "Розмір / Масштаб (%)",
        "lbl_opacity": "Прозорість",
        "lbl_gap": "Проміжок (px)",
        "lbl_margin": "Відступ (px)",
        "lbl_angle": "Кут нахилу (°)",
        
        "sec_perf": "⚙️ Продуктивність",
        "lbl_threads": "Потоки (Threads)",
        "help_threads": "Зменшіть число, якщо вилітає.",
        
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
        "btn_selected": "✅ Обрано",
        "btn_select": "⬜ Обрати",
        "warn_no_files": "⚠️ Спочатку оберіть файли!",
        "btn_clear_workspace": "♻️ Очистити все",
        "expander_add_files": "📤 Додати файли",
        "lang_select": "Мова інтерфейсу / Interface Language",
        
        # Editor Keys
        "btn_open_editor": "🛠 Відкрити редактор (Popup)",
        "lbl_aspect": "Пропорції",
        "btn_rotate_left": "↺ -90°",
        "btn_rotate_right": "↻ +90°",
        "btn_save_edit": "💾 Зберегти та Закрити",
        "msg_edit_saved": "Зміни збережено!",
        
        "about_expander": "ℹ️ Про програму",
        "about_prod": "**Продукт:** Watermarker Pro MaAn v5.8",
        "about_auth": "**Автор:** Marynyuk Andriy", 
        "about_lic": "**Ліцензія:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 Всі права захищено",
        "about_changelog_title": "📝 Історія змін",
        "about_changelog": "**v5.8 Refactor:**\n- 🏗️ Редактор винесено в окремий модуль\n- 🧹 Чистий код та архітектура\n- 🚀 Оптимізація імпортів"
    },
    "en": {
        "title": "📸 Watermarker Pro v5.8",
        "sb_config": "🛠 Configuration",
        "btn_defaults": "↺ Reset",
        
        "sec_presets": "💾 Presets Manager",
        "lbl_load_preset": "Load Preset (.json)",
        "btn_save_preset": "⬇️ Save Full Preset",
        "msg_preset_loaded": "✅ Preset loaded!",
        "error_preset": "❌ Preset error: {}",
        
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
        "msg_preset_logo_active": "ℹ️ Using logo from preset.",
        
        "lbl_pos": "Position",
        "opt_pos_tile": "Tiled (Pattern)",
        "lbl_scale": "Size / Scale (%)",
        "lbl_opacity": "Opacity",
        "lbl_gap": "Gap (px)",
        "lbl_margin": "Margin (px)",
        "lbl_angle": "Angle (°)",
        
        "sec_perf": "⚙️ Performance",
        "lbl_threads": "Max Threads",
        "help_threads": "Reduce this number if the app crashes.",
        
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
        "btn_selected": "✅ Selected",
        "btn_select": "⬜ Select",
        "warn_no_files": "⚠️ Select files first!",
        "btn_clear_workspace": "♻️ Clear Workspace",
        "expander_add_files": "📤 Add Files",
        "lang_select": "Interface Language / Мова інтерфейсу",
        
        # Editor Keys
        "btn_open_editor": "🛠 Open Editor (Popup)",
        "lbl_aspect": "Aspect Ratio",
        "btn_rotate_left": "↺ -90°",
        "btn_rotate_right": "↻ +90°",
        "btn_save_edit": "💾 Save & Close",
        "msg_edit_saved": "Changes saved!",
        
        "about_expander": "ℹ️ About",
        "about_prod": "**Product:** Watermarker Pro MaAn v5.8",
        "about_auth": "**Author:** Marynyuk Andriy", 
        "about_lic": "**License:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 All rights reserved",
        "about_changelog_title": "📝 Changelog",
        "about_changelog": "**v5.8 Refactor:**\n- 🏗️ Editor moved to separate module\n- 🧹 Clean code architecture\n- 🚀 Optimized imports"
    }
}

# --- CSS STYLING ---
st.markdown("""
<style>
    div[data-testid="column"] {
        background-color: #f8f9fa; border-radius: 8px; padding: 10px;
        border: 1px solid #eee; transition: all 0.2s ease;
    }
    div[data-testid="column"]:hover {
        border-color: #ff4b4b; transform: translateY(-2px);
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
    font_dir = os.path.join(os.getcwd(), 'assets', 'fonts')
    if not os.path.exists(font_dir): return []
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
    st.session_state['out_fmt_key'] = DEFAULT_SETTINGS['out_fmt']
    st.session_state['out_quality_key'] = DEFAULT_SETTINGS['out_quality']
    st.session_state['naming_mode_key'] = DEFAULT_SETTINGS['naming_mode']
    st.session_state['naming_prefix_key'] = DEFAULT_SETTINGS['naming_prefix']
    st.session_state['font_name_key'] = DEFAULT_SETTINGS['font_name']
    st.session_state['preset_wm_bytes_key'] = None

def get_current_settings_json(uploaded_wm_file):
    wm_b64 = None
    if uploaded_wm_file: wm_b64 = engine.image_to_base64(uploaded_wm_file.getvalue())
    elif st.session_state.get('preset_wm_bytes_key'): wm_b64 = engine.image_to_base64(st.session_state['preset_wm_bytes_key'])
        
    settings = {
        'resize_val': st.session_state.get('resize_val_state', 1920),
        'wm_pos': st.session_state.get('wm_pos_key', 'bottom-right'),
        'wm_scale': st.session_state.get('wm_scale_key', 15),
        'wm_opacity': st.session_state.get('wm_opacity_key', 1.0),
        'wm_margin': st.session_state.get('wm_margin_key', 15),
        'wm_gap': st.session_state.get('wm_gap_key', 30),
        'wm_angle': st.session_state.get('wm_angle_key', 0),
        'wm_text': st.session_state.get('wm_text_key', ''),
        'wm_text_color': st.session_state.get('wm_text_color_key', '#FFFFFF'),
        'font_name': st.session_state.get('font_name_key', None),
        'out_fmt': st.session_state.get('out_fmt_key', 'JPEG'),
        'out_quality': st.session_state.get('out_quality_key', 80),
        'naming_mode': st.session_state.get('naming_mode_key', 'Keep Original'),
        'naming_prefix': st.session_state.get('naming_prefix_key', ''),
        'wm_image_b64': wm_b64
    }
    return json.dumps(settings, indent=4)

def apply_settings_from_json(json_data):
    try:
        data = json.load(json_data)
        if 'resize_val' in data: st.session_state['resize_val_state'] = data['resize_val']
        if 'wm_pos' in data: st.session_state['wm_pos_key'] = data['wm_pos']
        if 'wm_scale' in data: st.session_state['wm_scale_key'] = data['wm_scale']
        if 'wm_opacity' in data: st.session_state['wm_opacity_key'] = data['wm_opacity']
        if 'wm_margin' in data: st.session_state['wm_margin_key'] = data['wm_margin']
        if 'wm_gap' in data: st.session_state['wm_gap_key'] = data['wm_gap']
        if 'wm_angle' in data: st.session_state['wm_angle_key'] = data['wm_angle']
        if 'wm_text' in data: st.session_state['wm_text_key'] = data['wm_text']
        if 'wm_text_color' in data: st.session_state['wm_text_color_key'] = data['wm_text_color']
        if 'font_name' in data: st.session_state['font_name_key'] = data['font_name']
        if 'out_fmt' in data: st.session_state['out_fmt_key'] = data['out_fmt']
        if 'out_quality' in data: st.session_state['out_quality_key'] = data['out_quality']
        if 'naming_mode' in data: st.session_state['naming_mode_key'] = data['naming_mode']
        if 'naming_prefix' in data: st.session_state['naming_prefix_key'] = data['naming_prefix']
        
        if 'wm_image_b64' in data and data['wm_image_b64']:
            img_bytes = engine.base64_to_bytes(data['wm_image_b64'])
            st.session_state['preset_wm_bytes_key'] = img_bytes
        else:
            st.session_state['preset_wm_bytes_key'] = None
        return True
    except Exception as e: return str(e)

# --- UI START ---
with st.sidebar:
    lang_code = st.session_state['lang_code']
    T = TRANSLATIONS[lang_code]
    st.header(T['sb_config'])
    
    with st.expander(T['sec_presets'], expanded=False):
        uploaded_preset = st.file_uploader(T['lbl_load_preset'], type=['json'], key='preset_uploader')
        if uploaded_preset is not None:
            if f"processed_{uploaded_preset.name}" not in st.session_state:
                res = apply_settings_from_json(uploaded_preset)
                if res is True:
                    st.session_state[f"processed_{uploaded_preset.name}"] = True
                    st.success(T['msg_preset_loaded']); st.rerun()
                else: st.error(T['error_preset'].format(res))
        st.divider()
        current_wm_file = st.session_state.get('wm_uploader_obj') 
        json_str = get_current_settings_json(current_wm_file)
        st.download_button(label=T['btn_save_preset'], data=json_str, file_name="wm_preset_full.json", mime="application/json", use_container_width=True)

    with st.expander(T['sec_file']):
        out_fmt = st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"], key='out_fmt_key')
        quality = 80
        if out_fmt != "PNG": quality = st.slider(T['lbl_quality'], 50, 100, 80, 5, key='out_quality_key')
        naming_mode = st.selectbox(T['lbl_naming'], ["Keep Original", "Prefix + Sequence"], key='naming_mode_key')
        prefix = st.text_input(T['lbl_prefix'], placeholder="img", key='naming_prefix_key')

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
        tab1, tab2 = st.tabs([T['tab_logo'], T['tab_text']])
        wm_type = "image"
        with tab1:
            wm_file = st.file_uploader(T['lbl_logo_up'], type=["png"], key="wm_uploader")
            st.session_state['wm_uploader_obj'] = wm_file
            if wm_file: wm_type = "image"
            elif st.session_state.get('preset_wm_bytes_key'):
                wm_type = "image"
                st.info(T['msg_preset_logo_active'])
                try:
                    p_img = Image.open(io.BytesIO(st.session_state['preset_wm_bytes_key']))
                    st.image(p_img, width=150)
                except: pass
        with tab2:
            wm_text = st.text_area(T['lbl_text_input'], key='wm_text_key')
            fonts = get_available_fonts()
            f_idx = 0
            current_f = st.session_state.get('font_name_key')
            if current_f and current_f in fonts: f_idx = fonts.index(current_f)
            selected_font_name = st.selectbox(T['lbl_font'], fonts, index=f_idx, key='font_name_key') if fonts else None
            if not fonts: st.caption("No fonts found in assets/fonts. Using default.")
            wm_text_color = st.color_picker(T['lbl_color'], '#FFFFFF', key='wm_text_color_key')
            if wm_text: wm_type = "text"

        st.divider()
        wm_pos = st.selectbox(T['lbl_pos'], ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], key='wm_pos_key', on_change=handle_pos_change)
        wm_scale = st.slider(T['lbl_scale'], 5, 100, key='wm_scale_key') / 100
        wm_opacity = st.slider(T['lbl_opacity'], 0.1, 1.0, key='wm_opacity_key')
        if wm_pos == 'tiled':
            wm_gap = st.slider(T['lbl_gap'], 0, 200, key='wm_gap_key')
            wm_margin = wm_gap
        else:
            wm_margin = st.slider(T['lbl_margin'], 0, 100, key='wm_margin_key')
            wm_gap = 0
        wm_angle = st.slider(T['lbl_angle'], -180, 180, key='wm_angle_key')

    with st.expander(T['sec_perf'], expanded=False):
        max_threads = st.slider(T['lbl_threads'], 1, 8, 2, help=T['help_threads'])

    st.divider()
    if st.button(T['btn_defaults'], on_click=reset_settings, use_container_width=True): st.rerun()
    
    with st.expander(T['about_expander'], expanded=False):
        st.markdown(T['about_prod'])
        st.markdown(T['about_auth'])
        st.markdown(T['about_lic'])
        st.markdown(T['about_repo'])
        st.caption(T['about_copy'])
        with st.expander(T['about_changelog_title']): st.markdown(T['about_changelog'])
        st.divider()
        st.caption(T['lang_select'])
        lc1, lc2 = st.columns(2)
        with lc1:
            if st.button("🇺🇦 UA", type="primary" if lang_code=='ua' else "secondary", use_container_width=True): st.session_state['lang_code']='ua'; st.rerun()
        with lc2:
            if st.button("🇺🇸 EN", type="primary" if lang_code=='en' else "secondary", use_container_width=True): st.session_state['lang_code']='en'; st.rerun()

st.title(T['title'])
c_left, c_right = st.columns([1.8, 1], gap="large")

with c_left:
    col_head, col_clear = st.columns([2, 1])
    with col_head: st.subheader(T['files_header'])
    with col_clear:
        if st.button(T['btn_clear_workspace'], type="secondary", use_container_width=True):
            st.session_state['file_cache'] = {}
            st.session_state['selected_files'] = set()
            st.session_state['uploader_key'] += 1
            st.session_state['results'] = None
            if os.path.exists(st.session_state['temp_dir']):
                shutil.rmtree(st.session_state['temp_dir'])
                st.session_state['temp_dir'] = tempfile.mkdtemp(prefix="wm_pro_")
            st.rerun()
    
    has_files = len(st.session_state['file_cache']) > 0
    with st.expander(T['expander_add_files'], expanded=not has_files):
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
            if st.button(T['grid_select_all'], use_container_width=True): st.session_state['selected_files'] = set(files_names); st.rerun()
        with act2:
            if st.button(T['grid_deselect_all'], use_container_width=True): st.session_state['selected_files'].clear(); st.rerun()
        with act3:
            sel_count = len(st.session_state['selected_files'])
            if st.button(f"{T['grid_delete']} ({sel_count})", type="primary", use_container_width=True, disabled=sel_count==0):
                for f in list(st.session_state['selected_files']):
                    if f in files_map: del files_map[f]
                st.session_state['selected_files'].clear(); st.rerun()
        
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
            if not can_process: st.warning(T['warn_no_files'])
            else:
                progress = st.progress(0)
                wm_obj = None
                try:
                    if wm_text.strip():
                        font_path = None
                        if selected_font_name: font_path = os.path.join(os.getcwd(), 'assets', 'fonts', selected_font_name)
                        wm_obj = engine.create_text_watermark(wm_text, font_path, 100, wm_text_color)
                        wm_obj = engine.apply_opacity(wm_obj, wm_opacity)
                    else:
                        wm_bytes = None
                        if wm_file: wm_bytes = wm_file.getvalue()
                        elif st.session_state.get('preset_wm_bytes_key'): wm_bytes = st.session_state['preset_wm_bytes_key']
                        if wm_bytes:
                            wm_obj = engine.load_watermark_from_file(wm_bytes)
                            wm_obj = engine.apply_opacity(wm_obj, wm_opacity)
                except Exception as e: st.error(T['error_wm_load'].format(e)); st.stop()
                
                resize_cfg = {
                    'enabled': resize_on, 'mode': resize_mode, 'value': resize_val,
                    'wm_scale': wm_scale, 'wm_margin': wm_margin if wm_pos!='tiled' else 0,
                    'wm_gap': wm_gap if wm_pos=='tiled' else 0,
                    'wm_position': wm_pos, 'wm_angle': wm_angle
                }
                results = []; report = []; zip_buffer = io.BytesIO()
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
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
                                results.append((stats['filename'], res_bytes)); report.append(stats)
                                del res_bytes; gc.collect()
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
                c1.write(f"📄 {name}"); c2.download_button("⬇️", data, file_name=name, key=f"dl_{name}")

with c_right:
    st.subheader(T['prev_header'])
    selected_list = list(st.session_state['selected_files'])
    target_file = selected_list[-1] if selected_list else None
    
    with st.container(border=True):
        if target_file and target_file in files_map:
            fpath = files_map[target_file]
            
            # --- POPUP TRIGGER ---
            if st.button(T['btn_open_editor'], type="primary", use_container_width=True):
                editor.open_editor_dialog(fpath, T)

            # Normal Preview
            wm_obj = None
            try:
                if wm_text.strip():
                    font_path = None
                    if selected_font_name: font_path = os.path.join(os.getcwd(), 'assets', 'fonts', selected_font_name)
                    wm_obj = engine.create_text_watermark(wm_text, font_path, 100, wm_text_color)
                    if wm_obj: wm_obj = engine.apply_opacity(wm_obj, wm_opacity)
                else:
                    wm_bytes = None
                    if wm_file: wm_bytes = wm_file.getvalue()
                    elif st.session_state.get('preset_wm_bytes_key'): wm_bytes = st.session_state['preset_wm_bytes_key']
                    if wm_bytes:
                        wm_obj = engine.load_watermark_from_file(wm_bytes)
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
