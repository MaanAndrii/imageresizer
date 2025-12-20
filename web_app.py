import streamlit as st
import pandas as pd
import io
import zipfile
import concurrent.futures
from datetime import datetime
import watermarker_engine as engine

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# ==========================================
# 🌐 ЛОКАЛІЗАЦІЯ
# ==========================================
TRANSLATIONS = {
    "ua": {
        "title": "📸 Watermarker Pro v4.3",
        "lang_select": "Мова / Language",
        "sb_config": "🛠 Налаштування",
        "btn_defaults": "↺ Скинути налаштування",
        
        "sec_file": "1. Файл та Ім'я",
        "sec_geo": "2. Геометрія (Ресайз)",
        "sec_wm": "3. Вотермарка",
        
        "lbl_format": "Формат", "lbl_quality": "Якість", "lbl_naming": "Стратегія імен", "lbl_prefix": "Префікс",
        "chk_resize": "Змінювати розмір", "lbl_resize_mode": "Режим", "lbl_resize_val": "Розмір (px)", "lbl_presets": "Швидкі пресети:",
        
        "lbl_wm_upload": "Завантажити лого (PNG)", "lbl_wm_pos": "Позиція", 
        "lbl_wm_scale": "Масштаб (%)", "lbl_wm_opacity": "Прозорість", 
        "lbl_wm_margin_edge": "Відступ від краю (px)", 
        "lbl_wm_margin_gap": "Відступ між лого (px)", 
        "lbl_wm_angle": "Кут нахилу (°)",
        
        "files_header": "📂 Робоча область", "uploader_label": "Файли", "tbl_select": "✅", "tbl_name": "Файл",
        "btn_delete": "🗑️ Видалити", "btn_reset": "♻️ Очистити список", "btn_process": "🚀 Обробити", "msg_done": "Готово!",
        "res_savings": "Економія", "btn_dl_zip": "📦 Скачати ZIP", "exp_report": "📊 Технічний звіт", "exp_dl_separate": "⬇️ Скачати окремо",
        "prev_header": "👁️ Живий перегляд", "prev_rendering": "Генерація...", "prev_size": "Розмір", "prev_weight": "Вага", "prev_info": "Оберіть файл (✅) для тесту.",
        "about_prod": "**Продукт:** Watermarker Pro MaAn v4.3", "about_auth": "**Автор:** Marynyuk Andriy", "about_lic": "**Ліцензія:** Proprietary", "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", "about_copy": "© 2025 Всі права захищено"
    },
    "en": {
        "title": "📸 Watermarker Pro v4.3",
        "lang_select": "Language / Мова",
        "sb_config": "🛠 Configuration",
        "btn_defaults": "↺ Reset to Defaults",
        
        "sec_file": "1. File & Naming",
        "sec_geo": "2. Geometry (Resize)",
        "sec_wm": "3. Watermark",
        
        "lbl_format": "Output Format", "lbl_quality": "Quality", "lbl_naming": "Naming Strategy", "lbl_prefix": "Filename Prefix",
        "chk_resize": "Enable Resize", "lbl_resize_mode": "Mode", "lbl_resize_val": "Size (px)", "lbl_presets": "Quick Presets:",
        
        "lbl_wm_upload": "Upload Logo (PNG)", "lbl_wm_pos": "Position", 
        "lbl_wm_scale": "Scale (%)", "lbl_wm_opacity": "Opacity", 
        "lbl_wm_margin_edge": "Margin from edge (px)", 
        "lbl_wm_margin_gap": "Gap between logos (px)", 
        "lbl_wm_angle": "Angle (°)",
        
        "files_header": "📂 Workspace", "uploader_label": "Files", "tbl_select": "✅", "tbl_name": "File",
        "btn_delete": "🗑️ Delete", "btn_reset": "♻️ Clear List", "btn_process": "🚀 Process", "msg_done": "Done!",
        "res_savings": "Savings", "btn_dl_zip": "📦 Download ZIP", "exp_report": "📊 Technical Report", "exp_dl_separate": "⬇️ Download Separate",
        "prev_header": "👁️ Live Preview", "prev_rendering": "Rendering...", "prev_size": "Dimensions", "prev_weight": "Weight", "prev_info": "Select a file (✅) to preview.",
        "about_prod": "**Product:** Watermarker Pro MaAn v4.3", "about_auth": "**Author:** Marynyuk Andriy", "about_lic": "**License:** Proprietary", "about_repo": "[GitHub Repository](https://github.com/MaanAndrii)", "about_copy": "© 2025 All rights reserved"
    }
}

OPTIONS_MAP = {
    "ua": {
        "Keep Original": "Зберегти назву", "Prefix + Sequence": "Префікс + Номер (001)", "Timestamp": "Таймстемп", "Original + Suffix": "Оригінал + Суфікс", "Content Hash": "Хеш контенту",
        "Max Side": "Макс. сторона", "Exact Width": "Точна ширина", "Exact Height": "Точна висота",
        "bottom-right": "Знизу-праворуч", "bottom-left": "Знизу-ліворуч", "top-right": "Зверху-праворуч", "top-left": "Зверху-ліворуч", "center": "Центр", "tiled": "Замощення (Паттерн)"
    },
    "en": {
        "Keep Original": "Keep Original", "Prefix + Sequence": "Prefix + Sequence (001)", "Timestamp": "Timestamp", "Original + Suffix": "Original + Suffix", "Content Hash": "Content Hash",
        "Max Side": "Max Side", "Exact Width": "Exact Width", "Exact Height": "Exact Height",
        "bottom-right": "Bottom-Right", "bottom-left": "Bottom-Left", "top-right": "Top-Right", "top-left": "Top-Left", "center": "Center", "tiled": "Tiled (Pattern)"
    }
}

# --- PROXY FUNCTIONS ---
@st.cache_data(show_spinner=False)
def ui_get_metadata(file_bytes): return engine.get_image_metadata(file_bytes)

@st.cache_resource(show_spinner=False)
def ui_load_watermark(wm_bytes, opacity): return engine.load_and_process_watermark(wm_bytes, opacity)

# --- CALLBACKS ---
def reset_settings():
    """Скидає налаштування до заводських значень."""
    st.session_state['resize_val_state'] = 1920
    # ВИПРАВЛЕНО: тут має бути 15 (ціле число), а не 0.15
    st.session_state['wm_scale_key'] = 15 
    st.session_state['wm_opacity_key'] = 1.0
    st.session_state['wm_margin_key'] = 15
    st.session_state['wm_angle_key'] = 0

# --- UI IMPLEMENTATION ---
if 'file_cache' not in st.session_state: st.session_state['file_cache'] = {}
if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0

# Ініціалізація значень за замовчуванням
defaults = {
    'resize_val_state': 1920,
    'wm_scale_key': 15, # ВИПРАВЛЕНО: 15 (int) замість 0.15
    'wm_opacity_key': 1.0,
    'wm_margin_key': 15,
    'wm_angle_key': 0
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

with st.sidebar:
    lang_choice = st.selectbox("Language / Мова", ["Українська", "English"])
    lang_code = "ua" if lang_choice == "Українська" else "en"
    T = TRANSLATIONS[lang_code]
    
    st.divider()
    
    # Кнопка скидання (верх сайдбару)
    if st.button(T['btn_defaults'], on_click=reset_settings, use_container_width=True):
        pass 
    
    st.header(T['sb_config'])
    
    with st.expander(T['sec_file'], expanded=False):
        out_fmt = st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"])
        quality = 80
        if out_fmt != "PNG": quality = st.slider(T['lbl_quality'], 50, 100, 80, 5)
        naming_mode = st.selectbox(T['lbl_naming'], ["Keep Original", "Prefix + Sequence", "Timestamp", "Original + Suffix", "Content Hash"], format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        prefix = st.text_input(T['lbl_prefix'], placeholder="img")

    with st.expander(T['sec_geo'], expanded=True):
        resize_on = st.checkbox(T['chk_resize'], value=True)
        resize_mode = st.selectbox(T['lbl_resize_mode'], ["Max Side", "Exact Width", "Exact Height"], disabled=not resize_on, format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        st.write(T['lbl_presets'])
        col_p1, col_p2, col_p3 = st.columns(3)
        def set_res(val): st.session_state['resize_val_state'] = val
        with col_p1: st.button("HD", on_click=set_res, args=(1280,), disabled=not resize_on, use_container_width=True)
        with col_p2: st.button("FHD", on_click=set_res, args=(1920,), disabled=not resize_on, use_container_width=True)
        with col_p3: st.button("4K", on_click=set_res, args=(3840,), disabled=not resize_on, use_container_width=True)
        resize_val = st.number_input(T['lbl_resize_val'], min_value=100, max_value=8000, step=100, key='resize_val_state', disabled=not resize_on)

    with st.expander(T['sec_wm'], expanded=True):
        wm_file = st.file_uploader(T['lbl_wm_upload'], type=["png"])
        
        # Позиція
        wm_pos = st.selectbox(T['lbl_wm_pos'], ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], format_func=lambda x: OPTIONS_MAP[lang_code].get(x, x))
        
        # Масштаб і Прозорість
        # Тепер слайдер працює з цілим числом 15, а ділимо на 100 ми вже тут
        wm_scale = st.slider(T['lbl_wm_scale'], 5, 50, key='wm_scale_key') / 100
        wm_opacity = st.slider(T['lbl_wm_opacity'], 0.1, 1.0, key='wm_opacity_key')
        
        # ЛОГІКА ВІДОБРАЖЕННЯ
        if wm_pos == 'tiled':
            wm_angle = st.slider(T['lbl_wm_angle'], -180, 180, key='wm_angle_key')
            wm_margin = st.slider(T['lbl_wm_margin_gap'], 0, 200, key='wm_margin_key')
        else:
            wm_angle = 0
            wm_margin = st.slider(T['lbl_wm_margin_edge'], 0, 100, key='wm_margin_key')

    st.divider()
    with st.expander("ℹ️ About"):
        st.markdown(T['about_prod']); st.markdown(T['about_auth']); st.markdown(T['about_lic']); st.markdown(T['about_repo']); st.caption(T['about_copy'])

st.title(T['title'])
c_left, c_right = st.columns([1.5, 1], gap="large")

with c_left:
    st.subheader(T['files_header'])
    uploaded = st.file_uploader(T['uploader_label'], type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True, label_visibility="collapsed", key=f"up_{st.session_state['uploader_key']}")
    if uploaded:
        for f in uploaded:
            if f.name not in st.session_state['file_cache']: st.session_state['file_cache'][f.name] = f.getvalue()
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_map = st.session_state['file_cache']
    files_names = list(files_map.keys())
    
    if files_names:
        table_data = []
        for fname in files_names:
            fbytes = files_map[fname]
            w, h, size, fmt = ui_get_metadata(fbytes)
            table_data.append({"Select": False, "Name": fname, "Size": f"{size/1024:.1f} KB", "Res": f"{w}x{h}", "Fmt": fmt})
            
        df = pd.DataFrame(table_data)
        edited_df = st.data_editor(df, column_config={"Select": st.column_config.CheckboxColumn(T['tbl_select'], default=False), "Name": st.column_config.TextColumn(T['tbl_name'], disabled=True)}, hide_index=True, use_container_width=True, key="editor_in")
        selected_files = edited_df[edited_df["Select"] == True]["Name"].tolist()
        preview_target = selected_files[-1] if selected_files else None

        act1, act2, act3 = st.columns([1, 1, 1.5])
        with act1:
            if st.button(T['btn_delete'], disabled=not selected_files, use_container_width=True):
                for fn in selected_files: del st.session_state['file_cache'][fn]; st.rerun()
        with act2:
            if st.button(T['btn_reset'], use_container_width=True):
                st.session_state['file_cache'] = {}; st.session_state['results'] = None; st.rerun()
        with act3:
            if st.button(f"{T['btn_process']} ({len(files_names)})", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                
                wm_bytes = wm_file.getvalue() if wm_file else None
                wm_cached_obj = ui_load_watermark(wm_bytes, wm_opacity)
                
                resize_cfg = {
                    'enabled': resize_on, 'mode': resize_mode, 'value': resize_val, 
                    'wm_scale': wm_scale, 'wm_margin': wm_margin, 
                    'wm_position': wm_pos, 'wm_angle': wm_angle
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
                        new_fname = engine.generate_filename(fname, naming_mode, prefix, ext, index=i+1, file_bytes=fbytes)
                        future = executor.submit(engine.process_image, fbytes, new_fname, wm_cached_obj, resize_cfg, out_fmt, quality)
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

                st.toast(T['msg_done'], icon='🎉')
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
            wm_obj = ui_load_watermark(wm_bytes, wm_opacity)
            
            resize_cfg = {
                'enabled': resize_on, 'mode': resize_mode, 'value': resize_val, 
                'wm_scale': wm_scale, 'wm_margin': wm_margin, 
                'wm_position': wm_pos, 'wm_angle': wm_angle
            }
            try:
                with st.spinner(T['prev_rendering']):
                    preview_name = engine.generate_filename(preview_target, naming_mode, prefix, out_fmt.lower(), index=1, file_bytes=raw_bytes)
                    p_bytes, p_stats = engine.process_image(raw_bytes, preview_name, wm_obj, resize_cfg, out_fmt, quality)
                st.image(p_bytes, caption=f"Preview: {preview_name}", use_container_width=True)
                k1, k2 = st.columns(2)
                k1.metric(T['prev_size'], p_stats['new_res'], p_stats['scale_factor'])
                delta = ((p_stats['new_size'] - p_stats['orig_size']) / p_stats['orig_size']) * 100
                k2.metric(T['prev_weight'], f"{p_stats['new_size']/1024:.1f} KB", f"{delta:.1f}%", delta_color="inverse")
            except Exception as e: st.error(f"Error: {e}")
        else:
            st.info(T['prev_info'])
            st.markdown('<div style="height:300px; background:#f0f2f6;"></div>', unsafe_allow_html=True)
