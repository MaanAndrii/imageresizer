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

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# Дефолтні налаштування
DEFAULT_SETTINGS = {
    'resize_val': 1920,
    'wm_pos': 'bottom-right',
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0
}

TILED_SETTINGS = {'wm_scale': 15, 'wm_opacity': 0.3, 'wm_gap': 30, 'wm_angle': 45}
CORNER_SETTINGS = {'wm_scale': 15, 'wm_opacity': 1.0, 'wm_margin': 15, 'wm_angle': 0}

# Локалізація
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v4.8",
        "sb_config": "🛠 Налаштування",
        "btn_defaults": "↺ Скинути налаштування",
        "sec_file": "1. Файл та Ім'я",
        "sec_geo": "2. Геометрія (Ресайз)",
        "sec_wm": "3. Вотермарка",
        "files_header": "📂 Робоча область", 
        "uploader_label": "Завантажити фото",
        "btn_process": "🚀 Обробити", 
        "msg_done": "Готово!",
        "error_wm_load": "❌ Помилка логотипу: {}",
        "res_savings": "Економія", 
        "btn_dl_zip": "📦 Скачати ZIP",
        "exp_dl_separate": "⬇️ Скачати окремо", # Повернуто
        "prev_header": "👁️ Живий перегляд",
        "grid_select_all": "✅ Обрати всі",
        "grid_deselect_all": "⬜ Зняти всі",
        "grid_delete": "🗑️ Видалити",
        "btn_selected": "✅ Обрано",
        "btn_select": "⬜ Обрати",
        "warn_no_files": "⚠️ Спочатку оберіть файли для обробки!",
        "lang_select": "Мова / Language",
        # About Section
        "about_prod": "**Продукт:** Watermarker Pro MaAn v4.8", 
        "about_auth": "**Автор:** Marynyuk Andriy", 
        "about_lic": "**Ліцензія:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 Всі права захищено",
        "about_changelog_title": "📝 Історія змін",
        "about_changelog": "**v4.8 Stable Core:**\n- ⚡ Оптимізація пам'яті (TempFile)\n- 🖼️ Новий режим галереї (Grid View)\n- 🚀 Швидкі мініатюри\n- ⬇️ Пофайлове завантаження"
    },
    "en": {
        "title": "📸 Watermarker Pro v4.8",
        "sb_config": "🛠 Configuration",
        "btn_defaults": "↺ Reset",
        "sec_file": "1. File & Naming",
        "sec_geo": "2. Geometry",
        "sec_wm": "3. Watermark",
        "files_header": "📂 Workspace", 
        "uploader_label": "Upload Photos",
        "btn_process": "🚀 Process", 
        "msg_done": "Done!",
        "error_wm_load": "❌ Logo error: {}",
        "res_savings": "Savings", 
        "btn_dl_zip": "📦 Download ZIP",
        "exp_dl_separate": "⬇️ Download Separate", # Returned
        "prev_header": "👁️ Live Preview",
        "grid_select_all": "✅ Select All",
        "grid_deselect_all": "⬜ Deselect All",
        "grid_delete": "🗑️ Delete",
        "btn_selected": "✅ Selected",
        "btn_select": "⬜ Select",
        "warn_no_files": "⚠️ Please select files first!",
        "lang_select": "Language / Мова",
        # About Section
        "about_prod": "**Product:** Watermarker Pro MaAn v4.8", 
        "about_auth": "**Author:** Marynyuk Andriy", 
        "about_lic": "**License:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 All rights reserved",
        "about_changelog_title": "📝 Changelog",
        "about_changelog": "**v4.8 Stable Core:**\n- ⚡ Memory Optimization (TempFile)\n- 🖼️ New Grid View Gallery\n- 🚀 Fast Thumbnails\n- ⬇️ Per-file download"
    }
}

# --- CSS STYLING ---
st.markdown("""
<style>
    /* Робимо колонки схожими на картки */
    div[data-testid="column"] {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #eee;
        transition: all 0.2s ease;
    }
    
    /* Ефект при наведенні */
    div[data-testid="column"]:hover {
        border-color: #ff4b4b;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Кнопки на всю ширину */
    div[data-testid="column"] button {
        width: 100%;
        margin-top: 5px;
    }
    
    /* Прибираємо зайві відступи */
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE & TEMP MANAGER ---
if 'temp_dir' not in st.session_state:
    st.session_state['temp_dir'] = tempfile.mkdtemp(prefix="wm_pro_")
if 'file_cache' not in st.session_state:
    st.session_state['file_cache'] = {} # Dict: filename -> filepath
if 'selected_files' not in st.session_state:
    st.session_state['selected_files'] = set()
if 'uploader_key' not in st.session_state: 
    st.session_state['uploader_key'] = 0
if 'lang_code' not in st.session_state: 
    st.session_state['lang_code'] = 'ua'

# --- HELPERS ---
def save_uploaded_file(uploaded_file):
    """Зберігає завантажений файл у tempdir і повертає шлях."""
    temp_dir = st.session_state['temp_dir']
    file_path = os.path.join(temp_dir, uploaded_file.name)
    
    if os.path.exists(file_path):
        base, ext = os.path.splitext(uploaded_file.name)
        timestamp = datetime.now().strftime("%H%M%S")
        file_path = os.path.join(temp_dir, f"{base}_{timestamp}{ext}")
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path, os.path.basename(file_path)

# --- INIT SETTINGS ---
for k, v in DEFAULT_SETTINGS.items():
    key_name = f'{k}_key' if not k.endswith('_val') else f'{k}_state'
    if key_name not in st.session_state: 
        st.session_state[key_name] = v
if 'wm_gap_key' not in st.session_state:
    st.session_state['wm_gap_key'] = DEFAULT_SETTINGS['wm_gap']

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

# --- UI START ---
with st.sidebar:
    lang_code = st.session_state['lang_code']
    T = TRANSLATIONS[lang_code]
    st.header(T['sb_config'])
    
    with st.expander(T['sec_file']):
        out_fmt = st.selectbox("Format", ["JPEG", "WEBP", "PNG"])
        quality = 80
        if out_fmt != "PNG": quality = st.slider("Quality", 50, 100, 80, 5)
        naming_mode = st.selectbox("Naming", ["Keep Original", "Prefix + Sequence"])
        prefix = st.text_input("Prefix", placeholder="img")

    with st.expander(T['sec_geo'], expanded=True):
        resize_on = st.checkbox("Resize", value=True)
        resize_mode = st.selectbox("Mode", ["Max Side", "Exact Width", "Exact Height"], disabled=not resize_on)
        c1, c2, c3 = st.columns(3)
        def set_res(v): st.session_state['resize_val_state'] = v
        c1.button("HD", on_click=set_res, args=(1280,), use_container_width=True)
        c2.button("FHD", on_click=set_res, args=(1920,), use_container_width=True)
        c3.button("4K", on_click=set_res, args=(3840,), use_container_width=True)
        resize_val = st.number_input("Px", 100, 8000, key='resize_val_state', disabled=not resize_on)

    with st.expander(T['sec_wm'], expanded=True):
        wm_file = st.file_uploader("Logo (PNG)", type=["png"])
        wm_pos = st.selectbox("Position", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], 
                              key='wm_pos_key', on_change=handle_pos_change)
        wm_scale = st.slider("Scale %", 5, 80, key='wm_scale_key') / 100
        wm_opacity = st.slider("Opacity", 0.1, 1.0, key='wm_opacity_key')
        
        if wm_pos == 'tiled':
            wm_gap = st.slider("Gap px", 0, 200, key='wm_gap_key')
            wm_margin = wm_gap
        else:
            wm_margin = st.slider("Margin px", 0, 100, key='wm_margin_key')
            wm_gap = 0
            
        wm_angle = st.slider("Angle", -180, 180, key='wm_angle_key')

    st.divider()
    if st.button(T['btn_defaults'], on_click=reset_settings, use_container_width=True): st.rerun()
    
    # --- ABOUT & LANGUAGE SECTION ---
    with st.expander("ℹ️ About / Про програму", expanded=False):
        st.markdown(T['about_prod'])
        st.markdown(T['about_auth'])
        st.markdown(T['about_lic'])
        st.markdown(T['about_repo'])
        st.caption(T['about_copy'])
        
        with st.expander(T['about_changelog_title']):
            st.markdown(T['about_changelog'])
            
        st.divider()
        # Вибір мови
        sel_lang = st.selectbox(
            T['lang_select'], 
            ["🇺🇦 Українська", "🇺🇸 English"], 
            index=0 if lang_code == 'ua' else 1
        )
        new_lang = 'ua' if 'Українська' in sel_lang else 'en'
        if new_lang != lang_code:
            st.session_state['lang_code'] = new_lang
            st.rerun()

st.title(T['title'])
c_left, c_right = st.columns([1.8, 1], gap="large")

with c_left:
    st.subheader(T['files_header'])
    
    # Uploader (Batch to Temp)
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
        # Action Bar
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
                    if f in files_map:
                        del files_map[f]
                st.session_state['selected_files'].clear()
                st.rerun()
        
        st.divider()
        
        # --- GRID VIEW ---
        cols_count = 4
        cols = st.columns(cols_count)
        
        for i, fname in enumerate(files_names):
            col = cols[i % cols_count]
            fpath = files_map[fname]
            
            with col:
                # Отримуємо закешовану мініатюру
                thumb = engine.get_thumbnail(fpath)
                
                if thumb:
                    st.image(thumb, use_container_width=True)
                else:
                    st.warning("No Preview")
                
                is_sel = fname in st.session_state['selected_files']
                
                if st.button(
                    T['btn_selected'] if is_sel else T['btn_select'],
                    key=f"btn_{fname}",
                    type="primary" if is_sel else "secondary",
                    use_container_width=True
                ):
                    if is_sel:
                        st.session_state['selected_files'].remove(fname)
                    else:
                        st.session_state['selected_files'].add(fname)
                    st.rerun()

        st.caption(f"Files: {len(files_names)} | Selected: {len(st.session_state['selected_files'])}")
        
        # Processing Trigger
        process_list = list(st.session_state['selected_files'])
        can_process = len(process_list) > 0
        
        if st.button(T['btn_process'], type="primary", use_container_width=True):
            if not can_process:
                st.warning(T['warn_no_files'])
            else:
                progress = st.progress(0)
                
                # Load Watermark (Once)
                wm_bytes = wm_file.getvalue() if wm_file else None
                wm_obj = None
                if wm_bytes:
                    try:
                        wm_obj = engine.load_and_process_watermark(wm_bytes, wm_opacity)
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
                            except Exception as e:
                                st.error(f"Error {futures[fut]}: {e}")
                            progress.progress((i+1)/len(process_list))
                
                st.session_state['results'] = {'zip': zip_buffer.getvalue(), 'files': results, 'report': report}
                st.toast(T['msg_done'], icon='🎉')

    if 'results' in st.session_state and st.session_state['results']:
        res = st.session_state['results']
        st.success("Batch Processing Complete!")
        st.download_button(T['btn_dl_zip'], res['zip'], "photos.zip", "application/zip", type="primary")
        
        with st.expander("Report"):
            st.dataframe(pd.DataFrame(res['report']))
            
        # --- БЛОК ПОФАЙЛОВОГО ЗАВАНТАЖЕННЯ (ВІДНОВЛЕНО) ---
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
            
            wm_bytes = wm_file.getvalue() if wm_file else None
            wm_obj = None
            if wm_bytes:
                try: wm_obj = engine.load_and_process_watermark(wm_bytes, wm_opacity)
                except: pass
            
            resize_cfg = {
                'enabled': resize_on, 'mode': resize_mode, 'value': resize_val,
                'wm_scale': wm_scale, 'wm_margin': wm_margin if wm_pos!='tiled' else 0,
                'wm_gap': wm_gap if wm_pos=='tiled' else 0,
                'wm_position': wm_pos, 'wm_angle': wm_angle
            }
            
            try:
                prev_bytes, stats = engine.process_image(fpath, "preview", wm_obj, resize_cfg, out_fmt, quality)
                st.image(prev_bytes, caption=f"Preview: {stats['new_res']}", use_container_width=True)
                st.caption(f"Size: {stats['new_size']/1024:.0f} KB ({stats['scale_factor']})")
            except Exception as e:
                st.error(f"Preview Error: {e}")
        else:
            st.info("Select a file (✅) to preview")
            st.markdown('<div style="height:200px; background:#f0f2f6;"></div>', unsafe_allow_html=True)
