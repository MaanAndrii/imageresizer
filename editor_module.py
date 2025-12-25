import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v6.3 (Display Fix)
--------------------------------
Fixes:
- Re-enabled 'should_resize_image=True' to fix "Zoomed In" UI issue.
- Added .convert('RGB') to fix blank canvas on load.
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
    return f"📄 **{os.path.basename(fpath)}** &nbsp;•&nbsp; 📏 **{img.width}x{img.height}** &nbsp;•&nbsp; 💾 **{size_str}**"

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    file_id = os.path.basename(fpath)
    
    # State Init
    if f'rot_{file_id}' not in st.session_state: st.session_state[f'rot_{file_id}'] = 0
    if f'reset_{file_id}' not in st.session_state: st.session_state[f'reset_{file_id}'] = 0

    # Load Image
    try:
        img_original = Image.open(fpath)
        img_original = ImageOps.exif_transpose(img_original)
        
        # FIX: Convert to RGB ensures consistent display in browser
        img_original = img_original.convert('RGB')
        
        # Apply Rotation (In Memory)
        current_angle = st.session_state[f'rot_{file_id}']
        if current_angle != 0:
            img_original = img_original.rotate(-current_angle, expand=True)
            
        orig_w, orig_h = img_original.size
    except Exception as e:
        st.error(f"Error: {e}")
        return

    # Info Bar
    st.caption(get_file_info_str(fpath, img_original))

    # Layout
    col_canvas, col_controls = st.columns([3, 1], gap="small")

    # --- CONTROLS ---
    with col_controls:
        # A. Rotate
        c1, c2 = st.columns(2)
        with c1:
            if st.button("↺", use_container_width=True, key=f"l_{file_id}", help="-90°"):
                st.session_state[f'rot_{file_id}'] -= 90
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        with c2:
            if st.button("↻", use_container_width=True, key=f"r_{file_id}", help="+90°"):
                st.session_state[f'rot_{file_id}'] += 90
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        
        # B. Aspect Ratio
        aspect_choice = st.selectbox(
            T['lbl_aspect'], 
            list(ASPECT_RATIOS.keys()), 
            label_visibility="collapsed",
            key=f"asp_{file_id}"
        )
        aspect_val = ASPECT_RATIOS[aspect_choice]
        
        # C. Reset Button
        if st.button("Reset ⛶", use_container_width=True, key=f"rst_{file_id}", help="Center crop box"):
            st.session_state[f'reset_{file_id}'] += 1
            st.rerun()
            
        st.divider()

    # --- CANVAS ---
    with col_canvas:
        cropper_key = f"crp_{file_id}_{st.session_state[f'reset_{file_id}']}"
        
        # FIX: should_resize_image=True змушує фото вписатись в ширину колонки
        cropped_img = st_cropper(
            img_original,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_val,
            should_resize_image=True, 
            key=cropper_key
        )

    # --- PREVIEW & SAVE ---
    with col_controls:
        # Preview
        st.image(cropped_img, use_container_width=True)
        
        new_w, new_h = cropped_img.size
        is_changed = abs(new_w - orig_w) > 5 or abs(new_h - orig_h) > 5
        color_tag = "red" if is_changed else "green"
        
        st.caption(f"Result: :{color_tag}[{new_w}x{new_h}]")
        
        if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key=f"sv_{file_id}"):
            try:
                cropped_img.save(fpath, quality=95, subsampling=0)
                
                # Cleanup
                thumb_path = f"{fpath}.thumb.jpg"
                if os.path.exists(thumb_path): os.remove(thumb_path)
                del st.session_state[f'rot_{file_id}']
                del st.session_state[f'reset_{file_id}']
                
                st.session_state['close_editor'] = True
                st.rerun()
            except Exception as e:
                st.error(f"Save error: {e}")
