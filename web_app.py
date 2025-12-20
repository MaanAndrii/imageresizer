import streamlit as st
import pandas as pd
import io
import zipfile
import concurrent.futures
from datetime import datetime
import watermarker_engine as engine
from PIL import Image

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(
    page_title="Watermarker Pro MaAn", 
    page_icon="📸", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Максимальний розмір файлу (MB)
MAX_FILE_SIZE_MB = 50

# Дефолтні налаштування
DEFAULT_SETTINGS = {
    'resize_val': 1920,
    'wm_pos': 'bottom-right',
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0,
    'crop_enabled': False,
    'crop_x': 0,
    'crop_y': 0,
    'crop_w': 100,
    'crop_h': 100
}

TILED_SETTINGS = {
    'wm_scale': 15,
    'wm_opacity': 0.3,
    'wm_gap': 30,
    'wm_angle': 45
}

CORNER_SETTINGS = {
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_angle': 0
}

# ==========================================
# 🌐 ЛОКАЛІЗАЦІЯ
# ==========================================
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v4.8",
        "lang_select": "Мова / Language",
        "theme_select": "Тема / Theme",
        "sb_config": "🛠 Налаштування",
        "btn_defaults": "↺ Скинути налаштування",
        
        "sec_file": "1. Файл та Ім'я",
        "sec_geo": "2. Геометрія",
        "sec_crop": "✂️ Обрізання (Crop)",
        "sec_wm": "3. Вотермарка",
        
        "lbl_format": "Формат", 
        "lbl_quality": "Якість", 
        "lbl_naming": "Стратегія імен", 
        "lbl_prefix": "Префікс",
        "chk_resize": "Змінювати розмір", 
        "lbl_resize_mode": "Режим", 
        "lbl_resize_val": "Розмір (px)", 
        "lbl_presets": "Швидкі пресети:",
        
        "chk_crop": "Увімкнути обрізання",
        "lbl_crop_x": "X (ліво)",
        "lbl_crop_y": "Y (верх)",
        "lbl_crop_w": "Ширина",
        "lbl_crop_h": "Висота",
        "lbl_crop_aspect": "Співвідношення:",
        "crop_info": "💡 Координати у відсотках від оригінального розміру",
        
        "lbl_wm_upload": "Завантажити лого (PNG)", 
        "lbl_wm_pos": "Позиція", 
        "lbl_wm_scale": "Масштаб (%)", 
        "lbl_wm_opacity": "Прозорість", 
        "lbl_wm_margin_edge": "Відступ від краю (px)", 
        "lbl_wm_gap": "Проміжок між лого (px)", 
        "lbl_wm_angle": "Кут нахилу (°)",
        "warn_large_scale": "⚠️ Занадто великий логотип може перекрити фото!",
        
        "files_header": "📂 Робоча область", 
        "uploader_label": "📤 Перетягніть файли сюди або натисніть для вибору", 
        "tbl_select": "✅", 
        "tbl_name": "Файл",
        "tbl_preview": "🖼️",
        "btn_delete": "🗑️ Видалити", 
        "btn_reset": "♻️ Очистити список", 
        "btn_process": "🚀 Обробити", 
        "msg_done": "Готово!",
        "error_file_size": "❌ Файл {} завеликий! Максимум {} MB",
        "error_corrupted": "❌ Файл {} пошкоджений або невалідний",
        "error_wm_load": "❌ Помилка завантаження логотипу: {}",
        
        "progress_header": "⏳ Обробка...",
        "progress_file": "Файл:",
        "progress_step": "Крок:",
        "progress_time": "Час:",
        
        "res_savings": "Економія", 
        "btn_dl_zip": "📦 Скачати ZIP", 
        "exp_report": "📊 Технічний звіт", 
        "exp_dl_separate": "⬇️ Скачати окремо",
        
        "prev_header": "👁️ Перегляд", 
        "prev_compare": "⚖️ До / Після",
        "prev_rendering": "Генерація...", 
        "prev_size": "Розмір", 
        "prev_weight": "Вага", 
        "prev_info": "Оберіть файл для перегляду",
        
        "about_prod": "**Продукт:** Watermarker Pro MaAn v4.8", 
        "about_auth": "**Автор:** Marynyuk Andriy", 
        "about_lic": "**Ліцензія:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 Всі права захищено",
        "about_changelog": "**v4.8 Нові функції:**\n- ✂️ Обрізання (Crop)\n- 🖼️ Grid preview\n- ⚖️ Before/After порівняння\n- 🎨 Темна/Світла теми\n- ⏱️ Детальний прогрес"
    },
    "en": {
        "title": "📸 Watermarker Pro v4.8",
        "lang_select": "Language / Мова",
        "theme_select": "Theme / Тема",
        "sb_config": "🛠 Configuration",
        "btn_defaults": "↺ Reset to Defaults",
        
        "sec_file": "1. File & Naming",
        "sec_geo": "2. Geometry",
        "sec_crop": "✂️ Crop",
        "sec_wm": "3. Watermark",
        
        "lbl_format": "Output Format", 
        "lbl_quality": "Quality", 
        "lbl_naming": "Naming Strategy", 
        "lbl_prefix": "Filename Prefix",
        "chk_resize": "Enable Resize", 
        "lbl_resize_mode": "Mode", 
        "lbl_resize_val": "Size (px)", 
        "lbl_presets": "Quick Presets:",
        
        "chk_crop": "Enable Crop",
        "lbl_crop_x": "X (left)",
        "lbl_crop_y": "Y (top)",
        "lbl_crop_w": "Width",
        "lbl_crop_h": "Height",
        "lbl_crop_aspect": "Aspect Ratio:",
        "crop_info": "💡 Coordinates in % of original size",
        
        "lbl_wm_upload": "Upload Logo (PNG)", 
        "lbl_wm_pos": "Position", 
        "lbl_wm_scale": "Scale (%)", 
        "lbl_wm_opacity": "Opacity", 
        "lbl_wm_margin_edge": "Margin from edge (px)", 
        "lbl_wm_gap": "Gap between logos (px)", 
        "lbl_wm_angle": "Rotation Angle (°)",
        "warn_large_scale": "⚠️ Logo too large, may cover the photo!",
        
        "files_header": "📂 Workspace", 
        "uploader_label": "📤 Drag & Drop files here or click to browse", 
        "tbl_select": "✅", 
        "tbl_name": "File",
        "tbl_preview": "🖼️",
        "btn_delete": "🗑️ Delete", 
        "btn_reset": "♻️ Clear List", 
        "btn_process": "🚀 Process", 
        "msg_done": "Done!",
        "error_file_size": "❌ File {} is too large! Max {} MB",
        "error_corrupted": "❌ File {} is corrupted or invalid",
        "error_wm_load": "❌ Failed to load watermark: {}",
        
        "progress_header": "⏳ Processing...",
        "progress_file": "File:",
        "progress_step": "Step:",
        "progress_time": "Time:",
        
        "res_savings": "Savings", 
        "btn_dl_zip": "📦 Download ZIP", 
        "exp_report": "📊 Technical Report", 
        "exp_dl_separate": "⬇️ Download Separate",
        
        "prev_header": "👁️ Preview", 
        "prev_compare": "⚖️ Before / After",
        "prev_rendering": "Rendering...", 
        "prev_size": "Dimensions", 
        "prev_weight": "Weight", 
        "prev_info": "Select a file to preview",
        
        "about_prod": "**Product:** Watermarker Pro MaAn v4.8", 
        "about_auth": "**Author:** Marynyuk Andriy", 
        "about_lic": "**License:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 All rights reserved",
        "about_changelog": "**v4.8 New Features:**\n- ✂️ Crop tool\n- 🖼️ Grid preview\n- ⚖️ Before/After comparison\n- 🎨 Dark/Light themes\n- ⏱️ Detailed progress"
    }
}

OPTIONS_MAP = {
    "ua": {
        "Keep Original": "Зберегти назву", 
        "Prefix + Sequence": "Префікс + Номер (001)",
        "Max Side": "Макс. сторона", 
        "Exact Width": "Точна ширина", 
        "Exact Height": "Точна висота",
        "bottom-right": "Знизу-праворуч", 
        "bottom-left": "Знизу-ліворуч", 
        "top-right": "Зверху-праворуч", 
        "top-left": "Зверху-ліворуч", 
        "center": "Центр",
        "tiled": "Замощення (Паттерн)"
    },
    "en": {
        "Keep Original": "Keep Original", 
        "Prefix + Sequence": "Prefix + Sequence (001)",
        "Max Side": "Max Side", 
        "Exact Width": "Exact Width", 
        "Exact Height": "Exact Height",
        "bottom-right": "Bottom-Right", 
        "bottom-left": "Bottom-Left", 
        "top-right": "Top-Right", 
        "top-left": "Top-Left", 
        "center": "Center",
        "tiled": "Tiled (Pattern)"
    }
}

# --- PROXY FUNCTIONS ---
@st.cache_data(show_spinner=False)
def ui_get_metadata(file_bytes): 
    return engine.get_image_metadata(file_bytes)

@st.cache_resource(show_spinner=False)
def ui_load_watermark(wm_bytes, opacity): 
    return engine.load_and_process_watermark(wm_bytes, opacity)

@st.cache_data(show_spinner=False)
def get_thumbnail(file_bytes, size=(150, 150)):
    """Створює мініатюру для preview"""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.thumbnail(size, Image.Resampling.LANCZOS)
        return img
    except:
        return None

# --- CALLBACKS & LOGIC ---

def handle_pos_change():
    """Автоматично змінює параметри при зміні типу позиції."""
    new_pos = st.session_state['wm_pos_key']
    
    if new_pos == 'tiled':
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
    """Скидає все до заводського стану."""
    for k, v in DEFAULT_SETTINGS.items():
        key_name = f'{k}_key' if not k.endswith('_val') else f'{k}_state'
        st.session_state[key_name] = v

def set_crop_aspect(ratio):
    """Встановлює співвідношення сторін для crop"""
    if ratio == "1:1":
        st.session_state['crop_w_key'] = 50
        st.session_state['crop_h_key'] = 50
    elif ratio == "16:9":
        st.session_state['crop_w_key'] = 80
        st.session_state['crop_h_key'] = 45
    elif ratio == "4:3":
        st.session_state['crop_w_key'] = 80
        st.session_state['crop_h_key'] = 60

# --- CSS для кастомізації ---
def load_custom_css(theme="light"):
    if theme == "dark":
        css = """
        <style>
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        }
        .uploadedFile {
            border: 2px dashed #4a9eff !important;
            background: rgba(74, 158, 255, 0.1) !important;
        }
        .stProgress > div > div {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        </style>
        """
    else:
        css = """
        <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .uploadedFile {
            border: 2px dashed #1976d2 !important;
            background: rgba(25, 118, 210, 0.05) !important;
        }
        .stProgress > div > div {
            background: linear-gradient(90deg, #1976d2 0%, #42a5f5 100%);
        }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

# --- UI IMPLEMENTATION ---
if 'file_cache' not in st.session_state: 
    st.session_state['file_cache'] = {}
if 'uploader_key' not in st.session_state: 
    st.session_state['uploader_key'] = 0
if 'lang_code' not in st.session_state: 
    st.session_state['lang_code'] = 'ua'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'show_comparison' not in st.session_state:
    st.session_state['show_comparison'] = False

# Початкова ініціалізація
for k, v in DEFAULT_SETTINGS.items():
    key_name = f'{k}_key' if not k.endswith('_val') else f'{k}_state'
    if key_name not in st.session_state: 
        st.session_state[key_name] = v

# Завантажуємо CSS для теми
load_custom_css(st.session_state['theme'])

with st.sidebar:
    lang_code = st.session_state['lang_code']
    T = TRANSLATIONS[lang_code]
    
    st.header(T['sb_config'])
    
    # Вибір теми
    theme_col1, theme_col2 = st.columns(2)
    with theme_col1:
        if st.button("☀️ Light", use_container_width=True, 
                    type="primary" if st.session_state['theme'] == 'light' else "secondary"):
            st.session_state['theme'] = 'light'
            st.rerun()
    with theme_col2:
        if st.button("🌙 Dark", use_container_width=True,
                    type="primary" if st.session_state['theme'] == 'dark' else "secondary"):
            st.session_state['theme'] = 'dark'
            st.rerun()
    
    st.divider()
    
    with st.expander(T['sec_file'], expanded=False):
        out_fmt = st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"])
        quality = 80
        if out_fmt != "PNG": 
            quality = st.slider(T['lbl_quality'], 50, 100, 80, 5)
        naming_mode = st.selectbox(
            T['lbl_naming'], 
            ["Keep Original", "Prefix + Sequence"], 
            format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x)
        )
        prefix = st.text_input(T['lbl_prefix'], placeholder="img")

    with st.expander(T['sec_geo'], expanded=True):
        resize_on = st.checkbox(T['chk_resize'], value=True)
        resize_mode = st.selectbox(
            T['lbl_resize_mode'], 
            ["Max Side", "Exact Width", "Exact Height"], 
            disabled=not resize_on, 
            format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x)
        )
        st.write(T['lbl_presets'])
        col_p1, col_p2, col_p3 = st.columns(3)
        def set_res(val): 
            st.session_state['resize_val_state'] = val
        with col_p1: 
            st.button("HD", on_click=set_res, args=(1280,), disabled=not resize_on, use_container_width=True)
        with col_p2: 
            st.button("FHD", on_click=set_res, args=(1920,), disabled=not resize_on, use_container_width=True)
        with col_p3: 
            st.button("4K", on_click=set_res, args=(3840,), disabled=not resize_on, use_container_width=True)
        resize_val = st.number_input(
            T['lbl_resize_val'], 
            min_value=100, 
            max_value=8000, 
            step=100, 
            key='resize_val_state', 
            disabled=not resize_on
        )

    with st.expander(T['sec_crop'], expanded=False):
        crop_on = st.checkbox(T['chk_crop'], key='crop_enabled_key')
        
        if crop_on:
            st.info(T['crop_info'])
            
            # Кнопки швидкого вибору співвідношення
            st.write(T['lbl_crop_aspect'])
            c1, c2, c3 = st.columns(3)
            with c1:
                st.button("1:1", on_click=set_crop_aspect, args=("1:1",), 
                         use_container_width=True, disabled=not crop_on)
            with c2:
                st.button("16:9", on_click=set_crop_aspect, args=("16:9",), 
                         use_container_width=True, disabled=not crop_on)
            with c3:
                st.button("4:3", on_click=set_crop_aspect, args=("4:3",), 
                         use_container_width=True, disabled=not crop_on)
            
            crop_x = st.slider(T['lbl_crop_x'], 0, 100, key='crop_x_key', disabled=not crop_on)
            crop_y = st.slider(T['lbl_crop_y'], 0, 100, key='crop_y_key', disabled=not crop_on)
            crop_w = st.slider(T['lbl_crop_w'], 10, 100, key='crop_w_key', disabled=not crop_on)
            crop_h = st.slider(T['lbl_crop_h'], 10, 100, key='crop_h_key', disabled=not crop_on)

    with st.expander(T['sec_wm'], expanded=True):
        wm_file = st.file_uploader(T['lbl_wm_upload'], type=["png"])
        
        wm_pos = st.selectbox(
            T['lbl_wm_pos'], 
            ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], 
            key='wm_pos_key',
            on_change=handle_pos_change, 
            format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x)
        )
        
        wm_scale = st.slider(
            T['lbl_wm_scale'], 
            5, 80, 
            key='wm_scale_key'
        ) / 100
        
        if wm_scale > 0.5 and wm_pos != 'tiled':
            st.warning(T['warn_large_scale'])
        
        wm_opacity = st.slider(
            T['lbl_wm_opacity'], 
            0.1, 1.0, 
            key='wm_opacity_key', 
            step=0.05
        )
        
        if wm_pos == 'tiled':
            wm_gap = st.slider(
                T['lbl_wm_gap'], 
                0, 200, 
                key='wm_gap_key'
            )
            wm_margin = wm_gap
        else:
            wm_margin = st.slider(
                T['lbl_wm_margin_edge'], 
                0, 100, 
                key='wm_margin_key'
            )
            wm_gap = 0
        
        wm_angle = st.slider(
            T['lbl_wm_angle'], 
            -180, 180, 
            key='wm_angle_key'
        )

    st.divider()
    if st.button(T['btn_defaults'], on_click=reset_settings, use_container_width=True):
        st.rerun()

    with st.expander("ℹ️ About"):
        st.markdown(T['about_prod'])
        st.markdown(T['about_auth'])
        st.markdown(T['about_lic'])
        st.markdown(T['about_repo'])
        st.caption(T['about_copy'])
        with st.expander("📝 Changelog"):
            st.markdown(T['about_changelog'])

    st.divider()
    current_idx = 0 if st.session_state['lang_code'] == 'ua' else 1
    selected_lang = st.selectbox(
        T['lang_select'], 
        ["🇺🇦 Українська", "🇺🇸 English"], 
        index=current_idx
    )
    new_code = "ua" if "Українська" in selected_lang else "en"
    if new_code != st.session_state['lang_code']:
        st.session_state['lang_code'] = new_code
        st.rerun()

st.title(T['title'])
c_left, c_right = st.columns([1.5, 1], gap="large")

with c_left:
    st.subheader(T['files_header'])
    
    # Покращена зона завантаження
    uploaded = st.file_uploader(
        T['uploader_label'], 
        type=['png', 'jpg', 'jpeg', 'webp'], 
        accept_multiple_files=True, 
        label_visibility="visible", 
        key=f"up_{st.session_state['uploader_key']}"
    )
    
    if uploaded:
        for f in uploaded:
            file_size_mb = len(f.getvalue()) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                st.error(T['error_file_size'].format(f.name, MAX_FILE_SIZE_MB))
                continue
            
            if f.name not in st.session_state['file_cache']:
                st.session_state['file_cache'][f.name] = f.getvalue()
        
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_map = st.session_state['file_cache']
    files_names = list(files_map.keys())
    
    if files_names:
        # Grid Preview з мініатюрами
        st.write("### 🖼️ Превью файлів")
        cols_per_row = 4
        for i in range(0, len(files_names), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(files_names):
                    fname = files_names[i + j]
                    fbytes = files_map[fname]
                    thumb = get_thumbnail(fbytes)
                    
                    with col:
                        if thumb:
                            st.image(thumb, use_container_width=True)
                        st.checkbox(
                            fname[:20] + "..." if len(fname) > 20 else fname,
                            key=f"select_{fname}",
                            label_visibility="visible"
                        )
        
        st.divider()
        
        # Отримуємо вибрані файли
        selected_files = [fn for fn in files_names if st.session_state.get(f"select_{fn}", False)]
        preview_target = selected_files[-1] if selected_files else None

        act1, act2, act3 = st.columns([1, 1, 1.5])
        with act1:
            if st.button(T['btn_delete'], disabled=not selected_files, use_container_width=True):
                for fn in selected_files: 
                    del st.session_state['file_cache'][fn]
                st.rerun()
        with act2:
            if st.button(T['btn_reset'], use_container_width=True):
                st.session_state['file_cache'] = {}
                st.session_state['results'] = None
                st.rerun()
        with act3:
            can_process = len(files_names) > 0
            if st.button(
                f"{T['btn_process']} ({len(files_names)})", 
                type="primary", 
                use_container_width=True,
                disabled=not can_process
            ):
                # Детальний прогрес
                st.write(f"### {T['progress_header']}")
                progress_bar = st.progress(0)
                status_text = st.empty()
                time_text = st.empty()
                
                wm_bytes = wm_file.getvalue() if wm_file else None
                wm_cached_obj = None
                
                if wm_bytes:
                    try:
                        wm_cached_obj = ui_load_watermark(wm_bytes, wm_opacity)
                    except ValueError as e:
                        st.error(T['error_wm_load'].format(str(e)))
                        st.stop()
                
                crop_cfg = {
                    'enabled': st.session_state.get('crop_enabled_key', False),
                    'x': st.session_state.get('crop_x_key', 0),
                    'y': st.session_state.get('crop_y_key', 0),
                    'w': st.session_state.get('crop_w_key', 100),
                    'h': st.session_state.get('crop_h_key', 100)
                }
                
                resize_cfg = {
                    'enabled': resize_on, 
                    'mode': resize_mode, 
                    'value': resize_val, 
                    'wm_scale': wm_scale, 
                    'wm_margin': wm_margin if wm_pos != 'tiled' else 0,
                    'wm_gap': wm_gap if wm_pos == 'tiled' else 0,
                    'wm_position': wm_pos, 
                    'wm_angle': wm_angle,
                    'crop': crop_cfg
                }
                
                results_list = []
                report_list = []
                zip_buffer = io.BytesIO()
                total_files = len(files_names)
                
                start_time = datetime.now()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {}
                    for i, fname in enumerate(files_names):
                        fbytes = files_map[fname]
                        ext = out_fmt.lower()
                        new_fname = engine.generate_filename(
                            fname, naming_mode, prefix, ext, 
                            index=i+1, file_bytes=fbytes
                        )
                        future = executor.submit(
                            engine.process_image, 
                            fbytes, new_fname, wm_cached_obj, 
                            resize_cfg, out_fmt, quality
                        )
                        futures[future] = fname

                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            fname = futures[future]
                            
                            # Оновлюємо статус
                            status_text.markdown(f"**{T['progress_file']}** `{fname}`  \n**{T['progress_step']}** {i+1}/{total_files}")
                            elapsed = (datetime.now() - start_time).total_seconds()
                            time_text.caption(f"{T['progress_time']} {elapsed:.1f}s")
                            
                            try:
                                res_bytes, stats = future.result()
                                zf.writestr(stats['filename'], res_bytes)
                                results_list.append((stats['filename'], res_bytes))
                                report_list.append(stats)
                            except Exception as e: 
                                st.error(f"Error processing {fname}: {e}")
                            
                            progress_bar.progress((i + 1) / total_files)

                total_time = (datetime.now() - start_time).total_seconds()
                st.toast(f"{T['msg_done']} {total_time:.1f}s", icon='🎉')
                st.session_state['results'] = {
                    'zip': zip_buffer.getvalue(), 
                    'files': results_list, 
                    'report': report_list
                }
                st.rerun()

    if 'results' in st.session_state and st.session_state['results']:
        res = st.session_state['results']
        report = res['report']
        total_orig = sum(r['orig_size'] for r in report)
        total_new = sum(r['new_size'] for r in report)
        saved_mb = (total_orig - total_new) / (1024*1024)
        
        st.divider()
        st.success(f"{T['res_savings']}: **{saved_mb:.2f} MB**")
        st.download_button(
            T['btn_dl_zip'], 
            res['zip'], 
            f"batch_{datetime.now().strftime('%H%M')}.zip", 
            "application/zip", 
            type="primary", 
            use_container_width=True
        )
        
        with st.expander(T['exp_report']):
            df_rep = pd.DataFrame(report)
            df_rep['savings %'] = (
                (df_rep['orig_size'] - df_rep['new_size']) / df_rep['orig_size'] * 100
            ).round(1)
            st.dataframe(
                df_rep, 
                column_config={
                    "savings %": st.column_config.ProgressColumn(
                        min_value=0, max_value=100, format="%f%%"
                    )
                }, 
                use_container_width=True
            )
            
        with st.expander(T['exp_dl_separate']):
            for name, data in res['files']:
                c1, c2 = st.columns([3, 1])
                c1.write(f"📄 {name}")
                c2.download_button("⬇️", data, file_name=name, key=f"dl_{name}")

with c_right:
    st.subheader(T['prev_header'])
    
    # Кнопка перемикання режиму порівняння
    if st.button(T['prev_compare'], use_container_width=True):
        st.session_state['show_comparison'] = not st.session_state['show_comparison']
    
    with st.container(border=True):
        if 'preview_target' in locals() and preview_target:
            raw_bytes = files_map[preview_target]
            
            w, h, size, fmt = ui_get_metadata(raw_bytes)
            if fmt is None:
                st.error(T['error_corrupted'].format(preview_target))
            else:
                wm_bytes = wm_file.getvalue() if wm_file else None
                wm_obj = None
                
                if wm_bytes:
                    try:
                        wm_obj = ui_load_watermark(wm_bytes, wm_opacity)
                    except ValueError as e:
                        st.warning(T['error_wm_load'].format(str(e)))
                
                crop_cfg = {
                    'enabled': st.session_state.get('crop_enabled_key', False),
                    'x': st.session_state.get('crop_x_key', 0),
                    'y': st.session_state.get('crop_y_key', 0),
                    'w': st.session_state.get('crop_w_key', 100),
                    'h': st.session_state.get('crop_h_key', 100)
                }
                
                resize_cfg = {
                    'enabled': resize_on, 
                    'mode': resize_mode, 
                    'value': resize_val, 
                    'wm_scale': wm_scale, 
                    'wm_margin': wm_margin if wm_pos != 'tiled' else 0,
                    'wm_gap': wm_gap if wm_pos == 'tiled' else 0,
                    'wm_position': wm_pos, 
                    'wm_angle': wm_angle,
                    'crop': crop_cfg
                }
                
                try:
                    with st.spinner(T['prev_rendering']):
                        preview_name = engine.generate_filename(
                            preview_target, naming_mode, prefix, 
                            out_fmt.lower(), index=1, file_bytes=raw_bytes
                        )
                        p_bytes, p_stats = engine.process_image(
                            raw_bytes, preview_name, wm_obj, 
                            resize_cfg, out_fmt, quality
                        )
                    
                    if st.session_state['show_comparison']:
                        # Before/After режим
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption("Before")
                            st.image(raw_bytes, use_container_width=True)
                        with col2:
                            st.caption("After")
                            st.image(p_bytes, use_container_width=True)
                    else:
                        # Звичайний режим
                        st.image(p_bytes, caption=f"Preview: {preview_name}", use_container_width=True)
                    
                    k1, k2 = st.columns(2)
                    k1.metric(T['prev_size'], p_stats['new_res'], p_stats['scale_factor'])
                    delta = ((p_stats['new_size'] - p_stats['orig_size']) / p_stats['orig_size']) * 100
                    k2.metric(
                        T['prev_weight'], 
                        f"{p_stats['new_size']/1024:.1f} KB", 
                        f"{delta:.1f}%", 
                        delta_color="inverse"
                    )
                except Exception as e: 
                    st.error(f"Preview Error: {e}")
        else:
            st.info(T['prev_info'])
            st.markdown('<div style="height:300px; display:flex; align-items:center; justify-content:center; background:#f0f2f6; border-radius:10px;"><p style="color:#999; font-size:18px;">🖼️</p></div>', unsafe_allow_html=True)
