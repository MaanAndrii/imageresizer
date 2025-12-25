import streamlit as st
import pandas as pd
import io
import os
import shutil
import zipfile
import concurrent.futures
import gc
from datetime import datetime
from PIL import Image

# Import Modules
import watermarker_engine as engine
import editor_module as editor
import translations as T_DATA
import utils

# --- SETUP ---
st.set_page_config(page_title="Watermarker Pro v6.0", page_icon="📸", layout="wide")
utils.inject_css()
utils.init_session_state()

# --- LOAD LANGUAGE ---
lang_code = st.session_state['lang_code']
T = T_DATA.TRANSLATIONS[lang_code]

# --- UI START ---
with st.sidebar:
    st.header(T['sb_config'])
    
    # PRESETS
    with st.expander(T['sec_presets'], expanded=False):
        uploaded_preset = st.file_uploader(T['lbl_load_preset'], type=['json'], key='preset_uploader')
        if uploaded_preset is not None:
            if f"processed_{uploaded_preset.name}" not in st.session_state:
                res = utils.apply_settings_from_json(uploaded_preset)
                if res is True:
                    st.session_state[f"processed_{uploaded_preset.name}"] = True
                    st.success(T['msg_preset_loaded'])
                    st.rerun()
                else: 
                    st.error(T['error_preset'].format(res))
        st.divider()
        current_wm_file = st.session_state.get('wm_uploader_obj') 
        json_str = utils.get_current_settings_json(current_wm_file)
        st.download_button(label=T['btn_save_preset'], data=json_str, file_name="wm_preset_full.json", mime="application/json", use_container_width=True)

    # FILE SETTINGS
    with st.expander(T['sec_file']):
        st.selectbox(T['lbl_format'], ["JPEG", "WEBP", "PNG"], key='out_fmt_key')
        out_fmt = st.session_state['out_fmt_key']
        if out_fmt != "PNG": 
            st.slider(T['lbl_quality'], 50, 100, 80, 5, key='out_quality_key')
        st.selectbox(T['lbl_naming'], ["Keep Original", "Prefix + Sequence"], key='naming_mode_key')
        st.text_input(T['lbl_prefix'], placeholder="img", key='naming_prefix_key')

    # GEOMETRY
    with st.expander(T['sec_geo'], expanded=True):
        resize_on = st.checkbox(T['chk_resize'], value=True)
        st.selectbox(T['lbl_mode'], ["Max Side", "Exact Width", "Exact Height"], disabled=not resize_on)
        c1, c2, c3 = st.columns(3)
        def set_res(v): st.session_state['resize_val_state'] = v
        c1.button("HD", on_click=set_res, args=(1280,), use_container_width=True)
        c2.button("FHD", on_click=set_res, args=(1920,), use_container_width=True)
        c3.button("4K", on_click=set_res, args=(3840,), use_container_width=True)
        st.number_input(T['lbl_px'], 100, 8000, key='resize_val_state', disabled=not resize_on)

    # WATERMARK
    with st.expander(T['sec_wm'], expanded=True):
        tab1, tab2 = st.tabs([T['tab_logo'], T['tab_text']])
        wm_type = "image"
        
        with tab1:
            wm_file = st.file_uploader(T['lbl_logo_up'], type=["png"], key="wm_uploader")
            st.session_state['wm_uploader_obj'] = wm_file
            if wm_file: 
                wm_type = "image"
            elif st.session_state.get('preset_wm_bytes_key'):
                wm_type = "image"
                st.info(T['msg_preset_logo_active'])
                try:
                    p_img = Image.open(io.BytesIO(st.session_state['preset_wm_bytes_key']))
                    st.image(p_img, width=150)
                except: pass
        
        with tab2:
            wm_text = st.text_area(T['lbl_text_input'], key='wm_text_key')
            fonts = utils.get_available_fonts()
            f_idx = 0
            current_f = st.session_state.get('font_name_key')
            if current_f and current_f in fonts: f_idx = fonts.index(current_f)
            selected_font_name = st.selectbox(T['lbl_font'], fonts, index=f_idx, key='font_name_key') if fonts else None
            if not fonts: st.caption("No fonts found in assets/fonts. Using default.")
            st.color_picker(T['lbl_color'], '#FFFFFF', key='wm_text_color_key')
            if wm_text: wm_type = "text"

        st.divider()
        wm_pos = st.selectbox(T['lbl_pos'], ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center', 'tiled'], key='wm_pos_key', on_change=utils.handle_pos_change)
        st.slider(T['lbl_scale'], 5, 100, key='wm_scale_key')
        st.slider(T['lbl_opacity'], 0.1, 1.0, key='wm_opacity_key')
        
        if wm_pos == 'tiled':
            st.slider(T['lbl_gap'], 0, 200, key='wm_gap_key')
        else:
            st.slider(T['lbl_margin'], 0, 100, key='wm_margin_key')
        st.slider(T['lbl_angle'], -180, 180, key='wm_angle_key')

    # PERFORMANCE
    with st.expander(T['sec_perf'], expanded=False):
        max_threads = st.slider(T['lbl_threads'], 1, 8, 2, help=T['help_threads'])

    st.divider()
    if st.button(T['btn_defaults'], on_click=utils.reset_settings, use_container_width=True): 
        st.rerun()
    
    # ABOUT
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
            btn_ua_type = "primary" if lang_code == 'ua' else "secondary"
            if st.button("🇺🇦 UA", type=btn_ua_type, use_container_width=True): 
                st.session_state['lang_code'] = 'ua'; st.rerun()
        with lc2:
            btn_en_type = "primary" if lang_code == 'en' else "secondary"
            if st.button("🇺🇸 EN", type=btn_en_type, use_container_width=True): 
                st.session_state['lang_code'] = 'en'; st.rerun()

st.title(T['title'])
c_left, c_right = st.columns([1.8, 1], gap="large")

# --- LEFT COLUMN: FILES ---
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
            fpath, fname = utils.save_uploaded_file(f)
            st.session_state['file_cache'][fname] = fpath
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_map = st.session_state['file_cache']
    files_names = list(files_map.keys())

    if files_names:
        act1, act2, act3 = st.columns([1, 1, 1])
        with act1:
            if st.button(T['grid_select_all'], use_container_width=True): 
                st.session_state['selected_files'] = set(files_names); st.rerun()
        with act2:
            if st.button(T['grid_deselect_all'], use_container_width=True): 
                st.session_state['selected_files'].clear(); st.rerun()
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
                btn_type = "primary" if is_sel else "secondary"
                btn_label = T['btn_selected'] if is_sel else T['btn_select']
                
                if st.button(btn_label, key=f"btn_{fname}", type=btn_type, use_container_width=True):
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
                    if st.session_state['wm_text_key'].strip():
                        font_path = None
                        if selected_font_name: 
                            font_path = os.path.join(os.getcwd(), 'assets', 'fonts', selected_font_name)
                        wm_obj = engine.create_text_watermark(st.session_state['wm_text_key'], font_path, 100, st.session_state['wm_text_color_key'])
                        wm_obj = engine.apply_opacity(wm_obj, st.session_state['wm_opacity_key'])
                    else:
                        wm_bytes = None
                        if wm_file: wm_bytes = wm_file.getvalue()
                        elif st.session_state.get('preset_wm_bytes_key'): wm_bytes = st.session_state['preset_wm_bytes_key']
                        if wm_bytes:
                            wm_obj = engine.load_watermark_from_file(wm_bytes)
                            wm_obj = engine.apply_opacity(wm_obj, st.session_state['wm_opacity_key'])
                except Exception as e: st.error(T['error_wm_load'].format(e)); st.stop()
                
                resize_cfg = {
                    'enabled': resize_on, 
                    'mode': st.session_state['lbl_mode'] if 'lbl_mode' in st.session_state else "Max Side", 
                    'value': st.session_state['resize_val_state'],
                    'wm_scale': st.session_state['wm_scale_key'] / 100, 
                    'wm_margin': st.session_state['wm_margin_key'] if wm_pos!='tiled' else 0,
                    'wm_gap': st.session_state['wm_gap_key'] if wm_pos=='tiled' else 0,
                    'wm_position': st.session_state['wm_pos_key'], 
                    'wm_angle': st.session_state['wm_angle_key']
                }
                results = []; report = []; zip_buffer = io.BytesIO()
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
                    futures = {}
                    for i, fname in enumerate(process_list):
                        fpath = files_map[fname]
                        new_fname = engine.generate_filename(fpath, st.session_state['naming_mode_key'], st.session_state['naming_prefix_key'], st.session_state['out_fmt_key'].lower(), i+1)
                        future = executor.submit(engine.process_image, fpath, new_fname, wm_obj, resize_cfg, st.session_state['out_fmt_key'], st.session_state['out_quality_key'])
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

# --- RIGHT COLUMN: PREVIEW ---
with c_right:
    st.subheader(T['prev_header'])
    selected_list = list(st.session_state['selected_files'])
    target_file = selected_list[-1] if selected_list else None
    
    with st.container(border=True):
        if target_file and target_file in files_map:
            fpath = files_map[target_file]
            
            # POPUP TRIGGER
            if st.button(T['btn_open_editor'], type="primary", use_container_width=True):
                st.session_state['editing_file'] = fpath
                st.session_state['close_editor'] = False
                
            if st.session_state.get('editing_file') == fpath and not st.session_state.get('close_editor'):
                editor.open_editor_dialog(fpath, T)
            
            if st.session_state.get('close_editor'):
                st.session_state['editing_file'] = None

            # PREVIEW GENERATION
            wm_obj = None
            try:
                if st.session_state['wm_text_key'].strip():
                    font_path = None
                    if selected_font_name: 
                        font_path = os.path.join(os.getcwd(), 'assets', 'fonts', selected_font_name)
                    wm_obj = engine.create_text_watermark(st.session_state['wm_text_key'], font_path, 100, st.session_state['wm_text_color_key'])
                    wm_obj = engine.apply_opacity(wm_obj, st.session_state['wm_opacity_key'])
                else:
                    wm_bytes = None
                    if wm_file: wm_bytes = wm_file.getvalue()
                    elif st.session_state.get('preset_wm_bytes_key'): wm_bytes = st.session_state['preset_wm_bytes_key']
                    if wm_bytes:
                        wm_obj = engine.load_watermark_from_file(wm_bytes)
                        wm_obj = engine.apply_opacity(wm_obj, st.session_state['wm_opacity_key'])
            except: pass
            
            resize_cfg = {
                'enabled': resize_on, 
                'mode': st.session_state.get('lbl_mode', "Max Side"), # Safe get
                'value': st.session_state['resize_val_state'],
                'wm_scale': st.session_state['wm_scale_key'] / 100, 
                'wm_margin': st.session_state['wm_margin_key'] if wm_pos!='tiled' else 0,
                'wm_gap': st.session_state['wm_gap_key'] if wm_pos=='tiled' else 0,
                'wm_position': st.session_state['wm_pos_key'], 
                'wm_angle': st.session_state['wm_angle_key']
            }
            
            try:
                preview_fname = engine.generate_filename(fpath, st.session_state['naming_mode_key'], st.session_state['naming_prefix_key'], st.session_state['out_fmt_key'].lower(), 1)
                prev_bytes, stats = engine.process_image(fpath, preview_fname, wm_obj, resize_cfg, st.session_state['out_fmt_key'], st.session_state['out_quality_key'])
                
                st.image(prev_bytes, caption=f"{stats['filename']}", use_container_width=True)
                m1, m2 = st.columns(2)
                delta_size = ((stats['new_size'] - stats['orig_size']) / stats['orig_size']) * 100
                m1.metric(T['stat_res'], stats['new_res'], stats['scale_factor'])
                m2.metric(T['stat_size'], f"{stats['new_size']/1024:.1f} KB", f"{delta_size:.1f}%", delta_color="inverse")
            except Exception as e: st.error(f"Preview Error: {e}")
        else:
            st.markdown(f"""<div class="preview-placeholder"><span class="preview-icon">🖼️</span><p>{T['prev_placeholder']}</p></div>""", unsafe_allow_html=True)
