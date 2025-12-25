import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v6.10 (Type Fix)
------------------------------
Fixes TypeError: 'float' object is not subscriptable.
1. Reverted ASPECT_RATIOS to tuples (required by library).
2. Updated math logic to handle tuples.
3. Kept Proxy logic for UI stability.
"""

# ВАЖЛИВО: Бібліотека вимагає (int, int), а не float!
ASPECT_RATIOS = {
    "Free / Вільний": None,
    "1:1 (Square)": (1, 1),
    "3:2": (3, 2),
    "4:3": (4, 3),
    "5:4": (5, 4),
    "16:9": (16, 9),
    "9:16": (9, 16)
}

def get_file_info_str(fpath: str, img: Image.Image):
    size_bytes = os.path.getsize(fpath)
    size_mb = size_bytes / (1024 * 1024)
    size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_bytes/1024:.1f} KB"
    return f"📄 **{os.path.basename(fpath)}** &nbsp;•&nbsp; 📏 **{img.width}x{img.height}** &nbsp;•&nbsp; 💾 **{size_str}**"

def create_proxy_image(img: Image.Image, target_width: int = 700):
    w, h = img.size
    if w > target_width:
        ratio = target_width / w
        new_h = int(h * ratio)
        proxy = img.resize((target_width, new_h), Image.Resampling.LANCZOS)
        scale = w / target_width
        return proxy, scale
    return img, 1.0

def get_max_box(img_w, img_h, aspect_data):
    """
    Рахує максимальну рамку.
    aspect_data: tuple (w, h) або None
    """
    if aspect_data is None:
        pad = 10
        return (pad, pad, img_w - 2*pad, img_h - 2*pad)
    
    # Конвертуємо кортеж у float для розрахунків
    ratio_val = aspect_data[0] / aspect_data[1]
    
    # 1. Вписуємо по ширині
    try_w = img_w
    try_h = int(try_w / ratio_val)
    
    if try_h > img_h:
        # Не влізло по висоті, вписуємо по висоті
        try_h = img_h
        try_w = int(try_h * ratio_val)
        
    left = (img_w - try_w) // 2
    top = (img_h - try_h) // 2
    
    return (left, top, try_w, try_h)

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    file_id = os.path.basename(fpath)
    
    # State
    if f'rot_{file_id}' not in st.session_state: st.session_state[f'rot_{file_id}'] = 0
    if f'reset_{file_id}' not in st.session_state: st.session_state[f'reset_{file_id}'] = 0
    if f'def_coords_{file_id}' not in st.session_state: st.session_state[f'def_coords_{file_id}'] = None

    # Load Original
    try:
        img_full = Image.open(fpath)
        img_full = ImageOps.exif_transpose(img_full)
        img_full = img_full.convert('RGB')
        
        angle = st.session_state[f'rot_{file_id}']
        if angle != 0:
            img_full = img_full.rotate(-angle, expand=True)
            
    except Exception as e:
        st.error(f"Error: {e}")
        return

    # Proxy Gen
    img_proxy, scale_factor = create_proxy_image(img_full, target_width=700)
    proxy_w, proxy_h = img_proxy.size

    st.caption(get_file_info_str(fpath, img_full))

    col_canvas, col_controls = st.columns([3, 1], gap="small")

    with col_controls:
        # Rotate
        c1, c2 = st.columns(2)
        with c1:
            if st.button("↺", use_container_width=True, key=f"l_{file_id}"):
                st.session_state[f'rot_{file_id}'] -= 90
                st.session_state[f'reset_{file_id}'] += 1
                st.session_state[f'def_coords_{file_id}'] = None
                st.rerun()
        with c2:
            if st.button("↻", use_container_width=True, key=f"r_{file_id}"):
                st.session_state[f'rot_{file_id}'] += 90
                st.session_state[f'reset_{file_id}'] += 1
                st.session_state[f'def_coords_{file_id}'] = None
                st.rerun()
        
        # Aspect Ratio
        aspect_choice = st.selectbox(
            T['lbl_aspect'], 
            list(ASPECT_RATIOS.keys()), 
            label_visibility="collapsed",
            key=f"asp_{file_id}"
        )
        aspect_val = ASPECT_RATIOS[aspect_choice] # Тут тепер Tuple, як і треба бібліотеці
        
        # MAX Button
        if st.button("MAX ⛶", use_container_width=True, key=f"max_{file_id}"):
            max_box = get_max_box(proxy_w, proxy_h, aspect_val)
            st.session_state[f'def_coords_{file_id}'] = max_box
            st.session_state[f'reset_{file_id}'] += 1
            st.rerun()
            
        st.divider()

    with col_canvas:
        cropper_id = f"crp_{file_id}_{st.session_state[f'reset_{file_id}']}_{aspect_choice}"
        def_coords = st.session_state.get(f'def_coords_{file_id}', None)
        
        rect = st_cropper(
            img_proxy,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_val, # Tuple (int, int) -> OK
            should_resize_image=False, 
            default_coords=def_coords,
            return_type='box',
            key=cropper_id
        )

    with col_controls:
        crop_box = None
        real_w, real_h = 0, 0
        
        if rect:
            left = int(rect['left'] * scale_factor)
            top = int(rect['top'] * scale_factor)
            width = int(rect['width'] * scale_factor)
            height = int(rect['height'] * scale_factor)
            
            # Clamp logic (Safe boundaries)
            orig_w, orig_h = img_full.size
            left = max(0, left)
            top = max(0, top)
            if left + width > orig_w: width = orig_w - left
            if top + height > orig_h: height = orig_h - top
            
            crop_box = (left, top, left + width, top + height)
            real_w, real_h = width, height
        
        st.info(f"📏 **{real_w} x {real_h}** px")
        
        if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key=f"sv_{file_id}"):
            try:
                if crop_box:
                    final_image = img_full.crop(crop_box)
                    final_image.save(fpath, quality=95, subsampling=0)
                    
                    if os.path.exists(f"{fpath}.thumb.jpg"): 
                        os.remove(f"{fpath}.thumb.jpg")
                    
                    keys = [f'rot_{file_id}', f'reset_{file_id}', f'def_coords_{file_id}']
                    for k in keys:
                        if k in st.session_state: del st.session_state[k]
                    
                    st.session_state['close_editor'] = True
                    st.toast(T['msg_edit_saved'])
                    st.rerun()
            except Exception as e:
                st.error(f"Save Failed: {e}")
