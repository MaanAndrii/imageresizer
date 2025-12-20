import streamlit as st
import pandas as pd
import io
import zipfile
import concurrent.futures
from datetime import datetime
import watermarker_engine as engine

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# Максимальний розмір файлу (MB)
MAX_FILE_SIZE_MB = 50

# Дефолтні налаштування (винесені в константу)
DEFAULT_SETTINGS = {
    'resize_val': 1920,
    'wm_pos': 'bottom-right',
    'wm_scale': 15,
    'wm_opacity': 1.0,
    'wm_margin': 15,
    'wm_gap': 30,
    'wm_angle': 0
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
# 🌐 ЛОКАЛІЗАЦІЯ (БЕЗ РОСІЙСЬКОЇ)
# ==========================================
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v4.7",
        "lang_select": "Мова / Language",
        "sb_config": "🛠 Налаштування",
        "btn_defaults": "↺ Скинути налаштування",
        
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
        "lbl_wm_margin_edge": "Відступ від краю (px)", 
        "lbl_wm_gap": "Проміжок між лого (px)", 
        "lbl_wm_angle": "Кут нахилу (°)",
        "warn_large_scale": "⚠️ Занадто великий логотип може перекрити фото!",
        
        "files_header": "📂 Робоча область", 
        "uploader_label": "Файли", 
        "tbl_select": "✅", 
        "tbl_name": "Файл",
        "btn_delete": "🗑️ Видалити", 
        "btn_reset": "♻️ Очистити список", 
        "btn_process": "🚀 Обробити", 
        "msg_done": "Готово!",
        "error_file_size": "❌ Файл {} завеликий! Максимум {} MB",
        "error_corrupted": "❌ Файл {} пошкоджений або невалідний",
        "error_wm_load": "❌ Помилка завантаження логотипу: {}",
        
        "res_savings": "Економія", 
        "btn_dl_zip": "📦 Скачати ZIP", 
        "exp_report": "📊 Технічний звіт", 
        "exp_dl_separate": "⬇️ Скачати окремо",
        
        "prev_header": "👁️ Живий перегляд", 
        "prev_rendering": "Генерація...", 
        "prev_size": "Розмір", 
        "prev_weight": "Вага", 
        "prev_info": "Оберіть файл (✅) для тесту.",
        
        "about_prod": "**Продукт:** Watermarker Pro MaAn v4.7", 
        "about_auth": "**Автор:** Marynyuk Andriy", 
        "about_lic": "**Ліцензія:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 Всі права захищено",
        "about_changelog": "**v4.7 Зміни:**\n- Виправлено діагональне замощення\n- Роздільні параметри margin/gap\n- Поворот для всіх режимів\n- Покращена валідація"
    },
    "en": {
        "title": "📸 Watermarker Pro v4.7",
        "lang_select": "Language / Мова",
        "sb_config": "🛠 Configuration",
        "btn_defaults": "↺ Reset to Defaults",
        
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
        "lbl_wm_margin_edge": "Margin from edge (px)", 
        "lbl_wm_gap": "Gap between logos (px)", 
        "lbl_wm_angle": "Rotation Angle (°)",
        "warn_large_scale": "⚠️ Logo too large, may cover the photo!",
        
        "files_header": "📂 Workspace", 
        "uploader_label": "Files", 
        "tbl_select": "✅", 
        "tbl_name": "File",
        "btn_delete": "🗑️ Delete", 
        "btn_reset": "♻️ Clear List", 
        "btn_process": "🚀 Process", 
        "msg_done": "Done!",
        "error_file_size": "❌ File {} is too large! Max {} MB",
        "error_corrupted": "❌ File {} is corrupted or invalid",
        "error_wm_load": "❌ Failed to load watermark: {}",
        
        "res_savings": "Savings", 
        "btn_dl_zip": "📦 Download ZIP", 
        "exp_report": "📊 Technical Report", 
        "exp_dl_separate": "⬇️ Download Separate",
        
        "prev_header": "👁️ Live Preview", 
        "prev_rendering": "Rendering...", 
        "prev_size": "Dimensions", 
        "prev_weight": "Weight", 
        "prev_info": "Select a file (✅) to preview.",
        
        "about_prod": "**Product:** Watermarker Pro MaAn v4.7", 
        "about_auth": "**Author:** Marynyuk Andriy", 
        "about_lic": "**License:** Proprietary", 
        "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", 
        "about_copy": "© 2025 All rights reserved",
        "about_changelog": "**v4.7 Changes:**\n- Fixed diagonal tiling\n- Separate margin/gap params\n- Rotation for all modes\n- Better validation"
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

# --- CALLBACKS & LOGIC ---

def handle_pos_change():
    """Автоматично змінює параметри при зміні типу позиції."""
    new_pos = st.session_state['wm_pos_key']
    
    if new_pos == 'tiled':
        # Налаштування для ЗАМОЩЕННЯ
        st.session_state['wm_scale_key'] = TILED_SETTINGS['wm_scale']
        st.session_state['wm_opacity_key'] = TILED_SETTINGS['wm_opacity']
        st.session_state['wm_gap_key'] = TILED_SETTINGS['wm_gap']
        st.session_state['wm_angle_key'] = TILED_SETTINGS['wm_angle']
    else:
        # Налаштування для КУТІВ
        st.session_state['wm_scale_key'] = CORNER_SETTINGS['wm_scale']
        st.session_state['wm_opacity_key'] = CORNER_SETTINGS['wm_opacity']
        st.session_state['wm_margin_key'] = CORNER_SETTINGS['wm_margin']
        st.session_state['wm_angle_key'] = CORNER_SETTINGS['wm_angle']

def reset_settings():
    """Скидає все до заводського стану."""
    st.session_state['resize_val_state'] = DEFAULT_SETTINGS['resize_val']
    st.session_state['wm_pos_key'] = DEFAULT_SETTINGS['wm_pos']
    st.session_state['wm_scale_key'] = DEFAULT_SETTINGS['wm_scale']
    st.session_state['wm_opacity_key'] = DEFAULT_SETTINGS['wm_opacity']
    st.session_state['wm_margin_key'] = DEFAULT_SETTINGS['wm_margin']
    st.session_state['wm_gap_key'] = DEFAULT_SETTINGS['wm_gap']
    st.session_state['wm_angle_key'] = DEFAULT_SETTINGS['wm_angle']

# --- UI IMPLEMENTATION ---
if 'file_cache' not in st.session_state: 
    st.session_state['file_cache'] = {}
if 'uploader_key' not in st.session_state: 
    st.session_state['uploader_key'] = 0
if 'lang_code' not in st.session_state: 
    st.session_state['lang_code'] = 'ua'

# Початкова ініціалізація
for k, v in DEFAULT_SETTINGS.items():
    key_name = f'{k}_key' if not k.endswith('_val') else f'{k}_state'
    if key_name not in st.session_state: 
        st.session_state[key_name] = v

# Додаємо gap до ініціалізації
if 'wm_gap_key' not in st.session_state:
    st.session_state['wm_gap_key'] = DEFAULT_SETTINGS['wm_gap']

with st.sidebar:
    lang_code = st.session_state['lang_code']
    T = TRANSLATIONS[lang_code]
    
    st.header(T['sb_config'])
    
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

    with st.expander(T['sec_wm'], expanded=True):
        wm_file = st.file_uploader(T['lbl_wm_upload'], type=["png"])
        
        # ВИБІР ПОЗИЦІЇ З CALLBACK
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
        
        # Попередження про великий масштаб
        if wm_scale > 0.5 and wm_pos != 'tiled':
            st.warning(T['warn_large_scale'])
        
        wm_opacity = st.slider(
            T['lbl_wm_opacity'], 
            0.1, 1.0, 
            key='wm_opacity_key', 
            step=0.05
        )
        
        # Окремі параметри для різних режимів
        if wm_pos == 'tiled':
            wm_gap = st.slider(
                T['lbl_wm_gap'], 
                0, 200, 
                key='wm_gap_key'
            )
            wm_margin = wm_gap  # Для бекенду
        else:
            wm_margin = st.slider(
                T['lbl_wm_margin_edge'], 
                0, 100, 
                key='wm_margin_key'
            )
            wm_gap = 0  # Для бекенду
        
        # Кут доступний для всіх режимів
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
    # ТІЛЬКИ УКРАЇНСЬКА І АНГЛІЙСЬКА
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
    uploaded = st.file_uploader(
        T['uploader_label'], 
        type=['png', 'jpg', 'jpeg', 'webp'], 
        accept_multiple_files=True, 
        label_visibility="collapsed", 
        key=f"up_{st.session_state['uploader_key']}"
    )
    
    if uploaded:
        for f in uploaded:
            # Валідація розміру файлу
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
        table_data = []
        corrupted_files = []
        
        for fname in files_names:
            fbytes = files_map[fname]
            w, h, size, fmt = ui_get_metadata(fbytes)
            
            # Валідація метаданих
            if fmt is None:
                corrupted_files.append(fname)
                table_data.append({
                    "Select": False, 
                    "Name": f"❌ {fname}", 
                    "Size": f"{size/1024:.1f} KB", 
                    "Res": "ERROR", 
                    "Fmt": "INVALID"
                })
            else:
                table_data.append({
                    "Select": False, 
                    "Name": fname, 
                    "Size": f"{size/1024:.1f} KB", 
                    "Res": f"{w}x{h}", 
                    "Fmt": fmt
                })
        
        # Показуємо попередження про пошкоджені файли
        if corrupted_files:
            for cf in corrupted_files:
                st.error(T['error_corrupted'].format(cf))
            
        df = pd.DataFrame(table_data)
        edited_df = st.data_editor(
            df, 
            column_config={
                "Select": st.column_config.CheckboxColumn(T['tbl_select'], default=False), 
                "Name": st.column_config.TextColumn(T['tbl_name'], disabled=True)
            }, 
            hide_index=True, 
            use_container_width=True, 
            key="editor_in"
        )
        
        selected_files = edited_df[edited_df["Select"] == True]["Name"].tolist()
        # Видаляємо ❌ prefix для corrupted files
        selected_files = [f.replace("❌ ", "") for f in selected_files]
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
            # Забороняємо обробку якщо є пошкоджені файли
            can_process = len(corrupted_files) == 0 and len(files_names) > 0
            if st.button(
                f"{T['btn_process']} ({len(files_names)})", 
                type="primary", 
                use_container_width=True,
                disabled=not can_process
            ):
                progress_bar = st.progress(0)
                
                # Валідація вотермарки
                wm_bytes = wm_file.getvalue() if wm_file else None
                wm_cached_obj = None
                
                if wm_bytes:
                    try:
                        wm_cached_obj = ui_load_watermark(wm_bytes, wm_opacity)
                    except ValueError as e:
                        st.error(T['error_wm_load'].format(str(e)))
                        st.stop()
                
                resize_cfg = {
                    'enabled': resize_on, 
                    'mode': resize_mode, 
                    'value': resize_val, 
                    'wm_scale': wm_scale, 
                    'wm_margin': wm_margin if wm_pos != 'tiled' else 0,
                    'wm_gap': wm_gap if wm_pos == 'tiled' else 0,
                    'wm_position': wm_pos, 
                    'wm_angle': wm_angle
                }
                
                results_list = []
                report_list = []
                zip_buffer = io.BytesIO()
                total_files = len(files_names)
                
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
                            try:
                                res_bytes, stats = future.result()
                                zf.writestr(stats['filename'], res_bytes)
                                results_list.append((stats['filename'], res_bytes))
                                report_list.append(stats)
                            except Exception as e: 
                                st.error(f"Error processing {futures[future]}: {e}")
                            progress_bar.progress((i + 1) / total_files)

                st.toast(T['msg_done'], icon='🎉')
                st.session_state['results'] = {
                    'zip': zip_buffer.getvalue(), 
                    'files': results_list, 
                    'report': report_list
                }

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
    with st.container(border=True):
        if 'preview_target' in locals() and preview_target:
            raw_bytes = files_map[preview_target]
            
            # Валідація preview
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
                
                resize_cfg = {
                    'enabled': resize_on, 
                    'mode': resize_mode, 
                    'value': resize_val, 
                    'wm_scale': wm_scale, 
                    'wm_margin': wm_margin if wm_pos != 'tiled' else 0,
                    'wm_gap': wm_gap if wm_pos == 'tiled' else 0,
                    'wm_position': wm_pos, 
                    'wm_angle': wm_angle
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
            st.markdown('<div style="height:300px; background:#f0f2f6;"></div>', unsafe_allow_html=True)
