import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v6.4 (Proxy Image Logic)
--------------------------------------
Fixes:
1. "Image too big": Uses a resized proxy for UI, applies crop to high-res original.
2. "Out of bounds": UI image fits container perfectly.
3. "Quality": Final crop is done on the original 100% quality image.
"""

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

def resize_for_ui(img: Image.Image, max_width: int = 700):
    """Створює зменшену копію для UI та повертає коефіцієнт масштабування."""
    w, h = img.size
    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        img_ui = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
        return img_ui, ratio
    return img, 1.0

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    file_id = os.path.basename(fpath)
    
    # State Keys
    if f'rot_{file_id}' not in st.session_state: st.session_state[f'rot_{file_id}'] = 0
    if f'reset_{file_id}' not in st.session_state: st.session_state[f'reset_{file_id}'] = 0

    # 1. LOAD ORIGINAL
    try:
        img_orig = Image.open(fpath)
        img_orig = ImageOps.exif_transpose(img_orig)
        img_orig = img_orig.convert('RGB') # Fix for indexed colors/transparency
        
        # Apply Rotation to Original (Virtual)
        current_angle = st.session_state[f'rot_{file_id}']
        if current_angle != 0:
            img_orig = img_orig.rotate(-current_angle, expand=True)
            
    except Exception as e:
        st.error(f"Error loading: {e}")
        return

    # 2. CREATE PROXY (UI IMAGE)
    # Ми показуємо користувачу зменшену версію, щоб вона влазила в екран
    img_ui, scale_factor = resize_for_ui(img_orig, max_width=700)

    # Info Bar
    st.caption(get_file_info_str(fpath, img_orig))

    # --- LAYOUT ---
    col_canvas, col_controls = st.columns([3, 1], gap="small")

    # --- CONTROLS ---
    with col_controls:
        # Rotate
        c1, c2 = st.columns(2)
        with c1:
            if st.button("↺", use_container_width=True, key=f"l_{file_id}"):
                st.session_state[f'rot_{file_id}'] -= 90
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        with c2:
            if st.button("↻", use_container_width=True, key=f"r_{file_id}"):
                st.session_state[f'rot_{file_id}'] += 90
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        
        # Aspect Ratio
        aspect_choice = st.selectbox(
            T['lbl_aspect'], 
            list(ASPECT_RATIOS.keys()), 
            label_visibility="collapsed",
            key=f"asp_{file_id}"
        )
        aspect_val = ASPECT_RATIOS[aspect_choice]
        
        # Reset
        if st.button("Reset ⛶", use_container_width=True, key=f"rst_{file_id}", help="Скинути рамку"):
            st.session_state[f'reset_{file_id}'] += 1
            st.rerun()
            
        st.divider()

    # --- CANVAS ---
    with col_canvas:
        cropper_key = f"crp_{file_id}_{st.session_state[f'reset_{file_id}']}"
        
        # ВАЖЛИВО: box=True повертає координати, а не картинку!
        # should_resize_image=False, тому що ми вже самі зробили ресайз (img_ui)
        crop_rect = st_cropper(
            img_ui,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_val,
            should_resize_image=False, 
            box=True, # Повертає словник {left, top, width, height}
            key=cropper_key
        )

    # --- SAVE LOGIC ---
    with col_controls:
        # Розраховуємо реальні розміри кропу
        # Координати з UI (crop_rect) ділимо на scale_factor, щоб отримати координати Оригіналу
        if crop_rect:
            real_left = int(crop_rect['left'] / scale_factor)
            real_top = int(crop_rect['top'] / scale_factor)
            real_width = int(crop_rect['width'] / scale_factor)
            real_height = int(crop_rect['height'] / scale_factor)
            
            # Прев'ю розміру
            st.markdown(f"📏 **{real_width} x {real_height}** px")
            
            # Кнопка збереження
            if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key=f"sv_{file_id}"):
                try:
                    # Кропаємо ОРИГІНАЛ
                    crop_box = (real_left, real_top, real_left + real_width, real_top + real_height)
                    final_image = img_orig.crop(crop_box)
                    
                    # Зберігаємо
                    final_image.save(fpath, quality=95, subsampling=0)
                    
                    # Чистимо сміття
                    thumb_path = f"{fpath}.thumb.jpg"
                    if os.path.exists(thumb_path): os.remove(thumb_path)
                    del st.session_state[f'rot_{file_id}']
                    del st.session_state[f'reset_{file_id}']
                    
                    st.session_state['close_editor'] = True
                    st.toast(T['msg_edit_saved'])
                    st.rerun()
                except Exception as e:
                    st.error(f"Save error: {e}")
