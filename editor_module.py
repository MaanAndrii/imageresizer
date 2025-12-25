import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v6.8 (Calculated MAX)
-----------------------------------
Feature:
- "MAX" button now mathematically calculates the largest possible crop box
  for the selected aspect ratio and forces the cropper to use it.
"""

ASPECT_RATIOS = {
    "Free / Вільний": None,
    "1:1 (Square)": 1/1,
    "3:2": 3/2,
    "4:3": 4/3,
    "5:4": 5/4,
    "16:9": 16/9,
    "9:16": 9/16
}

def get_file_info_str(fpath: str, img: Image.Image):
    size_bytes = os.path.getsize(fpath)
    size_mb = size_bytes / (1024 * 1024)
    size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_bytes/1024:.1f} KB"
    return f"📄 **{os.path.basename(fpath)}** &nbsp;•&nbsp; 📏 **{img.width}x{img.height}** &nbsp;•&nbsp; 💾 **{size_str}**"

def get_max_box(img_w, img_h, aspect_ratio):
    """
    Рахує координати (top, left, height, width) для максимальної рамки.
    """
    if aspect_ratio is None:
        # Free mode: Весь розмір
        return (0, 0, img_h, img_w)
    
    # Спробуємо вписати по висоті
    target_h = img_h
    target_w = int(target_h * aspect_ratio)
    
    if target_w > img_w:
        # Не влізло по ширині, вписуємо по ширині
        target_w = img_w
        target_h = int(target_w / aspect_ratio)
    
    # Центруємо
    left = (img_w - target_w) // 2
    top = (img_h - target_h) // 2
    
    return (top, left, target_h, target_w)

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    file_id = os.path.basename(fpath)
    
    # Init State
    if f'rot_{file_id}' not in st.session_state: st.session_state[f'rot_{file_id}'] = 0
    if f'reset_{file_id}' not in st.session_state: st.session_state[f'reset_{file_id}'] = 0
    # Зберігаємо кастомні координати для кнопки MAX
    if f'def_coords_{file_id}' not in st.session_state: st.session_state[f'def_coords_{file_id}'] = None

    # Load Image
    try:
        img_full = Image.open(fpath)
        img_full = ImageOps.exif_transpose(img_full)
        img_full = img_full.convert('RGB')
        
        # Apply Rotation
        angle = st.session_state[f'rot_{file_id}']
        if angle != 0:
            img_full = img_full.rotate(-angle, expand=True)
            
        orig_w, orig_h = img_full.size
    except Exception as e:
        st.error(f"Load Error: {e}")
        return

    st.caption(get_file_info_str(fpath, img_full))

    col_canvas, col_controls = st.columns([3, 1], gap="small")

    # --- CONTROLS ---
    with col_controls:
        # Rotate
        c1, c2 = st.columns(2)
        with c1:
            if st.button("↺", use_container_width=True, key=f"l_{file_id}"):
                st.session_state[f'rot_{file_id}'] -= 90
                st.session_state[f'reset_{file_id}'] += 1
                st.session_state[f'def_coords_{file_id}'] = None # Скидаємо при повороті
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
        aspect_val = ASPECT_RATIOS[aspect_choice]
        
        # MAX BUTTON (Now Calculates!)
        if st.button("MAX ⛶", use_container_width=True, key=f"max_{file_id}"):
            # 1. Рахуємо ідеальні координати
            max_box = get_max_box(orig_w, orig_h, aspect_val)
            # 2. Записуємо їх у state
            st.session_state[f'def_coords_{file_id}'] = max_box
            # 3. Оновлюємо кропер
            st.session_state[f'reset_{file_id}'] += 1
            st.rerun()
            
        st.divider()

    # --- CANVAS ---
    with col_canvas:
        cropper_id = f"crp_{file_id}_{st.session_state[f'reset_{file_id}']}_{aspect_choice}"
        
        # Беремо координати з кнопки MAX, якщо вони є
        default_box = st.session_state.get(f'def_coords_{file_id}', None)
        
        raw_rect = st_cropper(
            img_full,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_val,
            should_resize_image=True, 
            default_coords=default_box, # <--- ТУТ МАГІЯ
            return_type='box',
            key=cropper_id
        )

    # --- SAVE ---
    with col_controls:
        crop_box, real_w, real_h = None, 0, 0
        
        if raw_rect:
            # Функція clamp (із v6.7) інтегрована сюди для простоти
            left, top = int(raw_rect['left']), int(raw_rect['top'])
            width, height = int(raw_rect['width']), int(raw_rect['height'])
            
            # Clamp limits
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
                    
                    # Clean cache & state
                    thumb_path = f"{fpath}.thumb.jpg"
                    if os.path.exists(thumb_path): os.remove(thumb_path)
                    
                    # Clean specific keys
                    keys_to_del = [f'rot_{file_id}', f'reset_{file_id}', f'def_coords_{file_id}']
                    for k in keys_to_del:
                        if k in st.session_state: del st.session_state[k]
                    
                    st.session_state['close_editor'] = True
                    st.toast(T['msg_edit_saved'])
                    st.rerun()
            except Exception as e:
                st.error(f"Save Failed: {e}")
