import streamlit as st
import os
import glob
import json
import tempfile
import watermarker_engine as engine

"""
Utils Module for Watermarker Pro
Handles Settings, Files, JSON logic, and CSS.
"""

# --- CONSTANTS ---
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

# --- CSS ---
def inject_css():
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

# --- INIT SESSION ---
def init_session_state():
    if 'temp_dir' not in st.session_state: st.session_state['temp_dir'] = tempfile.mkdtemp(prefix="wm_pro_")
    if 'file_cache' not in st.session_state: st.session_state['file_cache'] = {} 
    if 'selected_files' not in st.session_state: st.session_state['selected_files'] = set()
    if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0
    if 'lang_code' not in st.session_state: st.session_state['lang_code'] = 'ua'
    if 'editing_file' not in st.session_state: st.session_state['editing_file'] = None
    if 'close_editor' not in st.session_state: st.session_state['close_editor'] = False
    
    # Init settings keys if missing
    for k, v in DEFAULT_SETTINGS.items():
        key_name = f'{k}_key' if not k.endswith('_val') else f'{k}_state'
        if key_name not in st.session_state: st.session_state[key_name] = v

# --- FILE HELPERS ---
def save_uploaded_file(uploaded_file):
    temp_dir = st.session_state['temp_dir']
    file_path = os.path.join(temp_dir, uploaded_file.name)
    if os.path.exists(file_path):
        base, ext = os.path.splitext(uploaded_file.name)
        # Unique timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        file_path = os.path.join(temp_dir, f"{base}_{timestamp}{ext}")
    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
    return file_path, os.path.basename(file_path)

def get_available_fonts():
    font_dir = os.path.join(os.getcwd(), 'assets', 'fonts')
    if not os.path.exists(font_dir): return []
    fonts = glob.glob(os.path.join(font_dir, "*.ttf")) + glob.glob(os.path.join(font_dir, "*.otf"))
    return [os.path.basename(f) for f in fonts]

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
    for k, v in DEFAULT_SETTINGS.items():
        key_name = f'{k}_key' if not k.endswith('_val') else f'{k}_state'
        st.session_state[key_name] = v

# --- JSON PRESETS LOGIC ---
def get_current_settings_json(uploaded_wm_file):
    wm_b64 = None
    if uploaded_wm_file: 
        wm_b64 = engine.image_to_base64(uploaded_wm_file.getvalue())
    elif st.session_state.get('preset_wm_bytes_key'): 
        wm_b64 = engine.image_to_base64(st.session_state['preset_wm_bytes_key'])
        
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
