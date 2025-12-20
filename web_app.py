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
# Ініціалізація дефолтних значень
if 'resize_val_state' not in st.session_state: st.session_state['resize_val_state'] = 1920
if 'out_fmt_state' not in st.session_state: st.session_state['out_fmt_state'] = "JPEG"
if 'quality_state' not in st.session_state: st.session_state['quality_state'] = 80
if 'resize_on_state' not in st.session_state: st.session_state['resize_on_state'] = True
if 'wm_text_state' not in st.session_state: st.session_state['wm_text_state'] = "@my_copyright"

DEFAULT_SETTINGS = {
    'wm_pos': 'bottom-right',
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0
}

# Доініціалізація ключів
for k, v in DEFAULT_SETTINGS.items():
    key_name = f'{k}_key'
    if key_name not in st.session_state: 
        st.session_state[key_name] = v

# --- ЛОКАЛІЗАЦІЯ ---
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v4.8",
        "sb_config": "🛠 Налаштування",
        "presets_title": "⚡ Швидкі пресети",
        "sec_file": "1. Файл та Метадані",
        "sec_geo": "2. Геометрія (Ресайз)",
        "sec_wm": "3. Вотермарка",
        
        "lbl_format": "Формат", 
        "lbl_quality": "Якість", 
        "lbl_keep_exif": "Зберегти EXIF (метадані)",
        
        "lbl_wm_type": "Тип вотермарки",
        "opt_wm_img": "📁 Зображення (Logo)",
        "opt_wm_text": "✍️ Текст",
        "lbl_wm_text_val": "Введіть текст",
        "lbl_wm_text_color": "Колір тексту",
        "lbl_wm_text_size": "Розмір шрифту",
        
        "lbl_wm_upload": "Завантажити лого (PNG)", 
        "btn_process": "🚀 Обробити",
        "msg_done": "Готово!",
        
        # Додати решту перекладів з попередньої версії...
        "files_header": "📂 Робоча область", 
        "uploader_label": "Файли",
        "tbl_name": "Файл",
        "btn_delete": "🗑️ Видалити", 
        "btn_reset": "♻️ Очистити",
        "res_savings": "Економія",
        "btn_dl_zip": "📦 Скачати ZIP",
        "error_wm_load": "Помилка лого: {}",
        "prev_header": "👁️ Живий перегляд",
        "prev_rendering": "Генерація...",
        "prev_size": "Розмір",
        "prev_weight": "Вага",
        "prev_info": "Оберіть файл для тесту."
    },
    "en": {
        "title": "📸 Watermarker Pro v4.8",
        "sb_config": "🛠 Configuration",
        "presets_title": "⚡ Quick Presets",
        "sec_file": "1. File & Metadata",
        "sec_geo": "2. Geometry (Resize)",
        "sec_wm": "3. Watermark",
        
        "lbl_format": "Output Format", 
        "lbl_quality": "Quality", 
        "lbl_keep_exif": "Keep EXIF (Metadata)",
        
        "lbl_wm_type": "Watermark Type",
        "opt_wm_img": "📁 Image (Logo)",
        "opt_wm_text": "✍️ Text",
        "lbl_wm_text_val": "Enter text",
        "lbl_wm_text_color": "Text Color",
        "lbl_wm_text_size": "Font Size",
        
        "lbl_wm_upload": "Upload Logo (PNG)", 
        "btn_process": "🚀 Process",
        "msg_done": "Done!",
        
        "files_header": "📂 Workspace", 
        "uploader_label": "Files",
        "tbl_name": "File",
        "btn_delete": "🗑️ Delete", 
        "btn_reset": "♻️ Clear List",
        "res_savings": "Savings",
        "btn_dl_zip": "📦 Download ZIP",
        "error_wm_load": "Watermark Error: {}",
        "prev_header": "👁️ Live Preview",
        "prev_rendering": "Rendering...",
        "prev_size": "Dimensions", 
        "prev_weight": "Weight", 
        "prev_info": "Select file to preview."
    }
}

if 'lang_code' not in st.session_state: st.session_state['lang_code'] = 'ua'
T = TRANSLATIONS[st.session_state['lang_code']]

# --- ЛОГІКА ПРЕСЕТІВ ---
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

# --- SIDEBAR ---
with st.sidebar:
    st.header(T['sb_config'])
    
    # 1. PRESETS BLOCK
    st.caption(T['presets_title'])
    c1, c2, c3 = st.columns(3)
    c1.button("Insta", on_click=apply_preset, args=('insta',), use_container_width=True)
    c2.button("Web", on_click=apply_preset, args=('web',), use_container_width=True)
    c3.button("Orig", on_click=apply_preset, args=('orig',), use_container_width=True)
    st.divider()

    # 2. FILE SECTION
    with st.expander(T['sec_file'], expanded=False):
        st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"], key='out_fmt_state')
        st.slider(T['lbl_quality'], 50, 100, key='quality_state')
        st.checkbox(T['lbl_keep_exif'], value=False, key='keep_exif_state')
        # Інші налаштування імені можна лишити тут же...

    # 3. GEOMETRY SECTION
    with st.expander(T['sec_geo'], expanded=True):
        st.checkbox("Enable Resize", key='resize_on_state')
        st.number_input("Max Side (px)", 500, 8000, step=100, key='resize_val_state', disabled=not st.session_state['resize_on_state'])

    # 4. WATERMARK SECTION (UPDATED)
    with st.expander(T['sec_wm'], expanded=True):
        wm_type = st.radio(T['lbl_wm_type'], ["img", "text"], 
                           format_func=lambda x: T['opt_wm_img'] if x == "img" else T['opt_wm_text'])
        
        wm_source_obj = None
        is_text_mode = (wm_type == "text")
        
        if is_text_mode:
            wm_text_val = st.text_input(T['lbl_wm_text_val'], key='wm_text_state')
            col1, col2 = st.columns(2)
            wm_color = col1.color_picker(T['lbl_wm_text_color'], "#FFFFFF")
            wm_size = col2.number_input(T['lbl_wm_text_size'], 10, 200, 50)
            
            # Pack text params for backend
            wm_source_obj = {
                'text': wm_text_val,
                'color': wm_color,
                'size': wm_size
            }
        else:
            wm_file = st.file_uploader(T['lbl_wm_upload'], type=["png"])
            if wm_file:
                wm_source_obj = wm_file.getvalue()

        # Common WM settings
        st.selectbox("Position", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], key='wm_pos_key')
        st.slider("Scale (%)", 5, 90, key='wm_scale_key')
        st.slider("Opacity", 0.1, 1.0, key='wm_opacity_key')
        st.slider("Gap/Margin", 0, 100, key='wm_margin_key')
        st.slider("Angle", -180, 180, key='wm_angle_key')


# --- MAIN UI ---
st.title(T['title'])

# (Стандартна логіка завантаження файлів як в попередній версії)
# ...
# Тут я скоротив код завантажувача для стислості, 
# використовуйте логіку з попередньої версії (file_uploader, session_state['file_cache'])

# --- INTEGRATION WITH ENGINE ---
# Коли користувач натискає "Process":

if 'file_cache' not in st.session_state: st.session_state['file_cache'] = {}
uploaded = st.file_uploader(T['uploader_label'], accept_multiple_files=True, key="main_upl")
if uploaded:
    for f in uploaded:
        if f.name not in st.session_state['file_cache']:
            st.session_state['file_cache'][f.name] = f.getvalue()

files_map = st.session_state['file_cache']

if files_map:
    # Таблиця файлів...
    st.write(f"Loaded {len(files_map)} files")
    
    if st.button(T['btn_process'], type="primary"):
        # Підготовка вотермарки
        try:
            wm_final = engine.load_and_process_watermark(
                wm_source_obj, 
                st.session_state['wm_opacity_key'],
                is_text=is_text_mode,
                text_params=wm_source_obj if is_text_mode else None
            )
        except Exception as e:
            st.error(T['error_wm_load'].format(e))
            st.stop()
            
        # Конфіг
        resize_cfg = {
            'enabled': st.session_state['resize_on_state'],
            'value': st.session_state['resize_val_state'],
            'wm_scale': st.session_state['wm_scale_key'] / 100,
            'wm_position': st.session_state['wm_pos_key'],
            'wm_margin': st.session_state['wm_margin_key'],
            'wm_gap': st.session_state['wm_margin_key'], # Simplified for now
            'wm_angle': st.session_state['wm_angle_key']
        }
        
        # Обробка
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for fname, fbytes in files_map.items():
                try:
                    res, _ = engine.process_image(
                        fbytes, fname, wm_final, resize_cfg, 
                        st.session_state['out_fmt_state'], 
                        st.session_state['quality_state'],
                        keep_exif=st.session_state['keep_exif_state']
                    )
                    zf.writestr(f"wm_{fname}", res)
                except Exception as e:
                    st.error(f"Error {fname}: {e}")
                    
        st.success(T['msg_done'])
        st.download_button(T['btn_dl_zip'], zip_buffer.getvalue(), "photos.zip")
