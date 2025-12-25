import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v5.12 (Fixed & Compact)
-------------------------------------
Fixes:
- Added lock_aspect_ratio (User cannot break aspect)
- Compact layout (Reduced vertical space)
- Removed redundant reruns inside logic where possible
"""

ASPECT_RATIOS = {
    "Free": None,
    "1:1": (1, 1),
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
    # Компактний рядок в один рядок
    return f"📄 **{os.path.basename(fpath)}** &nbsp;•&nbsp; 📏 **{img.width}x{img.height}** &nbsp;•&nbsp; 💾 **{size_str}**"

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    # --- SESSION STATE ---
    # Використовуємо ID файлу для унікальності ключів віджетів
    file_id = os.path.basename(fpath)
    
    if f'rot_{file_id}' not in st.session_state: st.session_state[f'rot_{file_id}'] = 0
    if f'reset_{file_id}' not in st.session_state: st.session_state[f'reset_{file_id}'] = 0

    # --- LOAD IMAGE ---
    try:
        img_original = Image.open(fpath)
        img_original = ImageOps.exif_transpose(img_original)
        
        # Застосовуємо поворот в пам'яті
        current_angle = st.session_state[f'rot_{file_id}']
        if current_angle != 0:
            img_original = img_original.rotate(-current_angle, expand=True)
            
        orig_w, orig_h = img_original.size
    except Exception as e:
        st.error(f"Error: {e}")
        return

    # 1. INFO BAR (Very Compact)
    st.caption(get_file_info_str(fpath, img_original))

    # --- LAYOUT ---
    # Змінюємо пропорції: більше місця для канвасу, менше для меню
    col_canvas, col_controls = st.columns([3, 1], gap="small")

    # --- RIGHT: CONTROLS ---
    with col_controls:
        # A. Rotate (Icons only to save space)
        c_rot1, c_rot2 = st.columns(2)
        with c_rot1:
            if st.button("↺", use_container_width=True, key=f"btn_l_{file_id}", help="-90°"):
                st.session_state[f'rot_{file_id}'] = (st.session_state[f'rot_{file_id}'] - 90) % 360
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        with c_rot2:
            if st.button("↻", use_container_width=True, key=f"btn_r_{file_id}", help="+90°"):
                st.session_state[f'rot_{file_id}'] = (st.session_state[f'rot_{file_id}'] + 90) % 360
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        
        # B. Aspect Ratio
        aspect_choice = st.selectbox(
            T['lbl_aspect'], 
            list(ASPECT_RATIOS.keys()), 
            label_visibility="collapsed",
            key=f"aspect_{file_id}"
        )
        aspect_val = ASPECT_RATIOS[aspect_choice]
        
        # C. MAX Button
        if st.button("MAX ⛶", use_container_width=True, key=f"btn_max_{file_id}"):
            st.session_state[f'reset_{file_id}'] += 1
            st.rerun()
            
        st.divider()

    # --- LEFT: CANVAS ---
    with col_canvas:
        cropper_key = f"cropper_{file_id}_{st.session_state[f'reset_{file_id}']}"
        
        # ВАЖЛИВО: lock_aspect_ratio блокує зміну пропорцій мишкою
        cropped_img = st_cropper(
            img_original,
            realtime_update=True,
            box_color='#FF4B4B',
            aspect_ratio=aspect_val,
            lock_aspect_ratio=(aspect_val is not None), # Блокуємо якщо не Free
            should_resize_image=True,
            key=cropper_key
        )

    # --- RIGHT: PREVIEW & SAVE ---
    with col_controls:
        # Міні-прев'ю (висота обмежена, щоб не розтягувати вікно)
        st.image(cropped_img, use_container_width=True)
        
        new_w, new_h = cropped_img.size
        color_tag = "red" if (new_w != orig_w or new_h != orig_h) else "green"
        st.caption(f"Result: :{color_tag}[{new_w}x{new_h}]")
        
        # Save Button
        if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key=f"save_{file_id}"):
            try:
                cropped_img.save(fpath, quality=95, subsampling=0)
                
                # Cleanup
                thumb_path = f"{fpath}.thumb.jpg"
                if os.path.exists(thumb_path): os.remove(thumb_path)
                del st.session_state[f'rot_{file_id}']
                del st.session_state[f'reset_{file_id}']
                
                # Close Dialog Signal
                st.session_state['close_editor'] = True
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")
