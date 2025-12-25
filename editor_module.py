import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper
import watermarker_engine as engine

"""
Editor Module v5.9 (Advanced Layout)
------------------------------------
Features:
- Split View (Canvas vs Control Panel)
- Real-time Result Preview
- Resolution Stats
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

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    # Очищуємо верхній відступ
    st.caption(f"Editing: {os.path.basename(fpath)}")
    
    # Завантаження зображення
    try:
        img_original = Image.open(fpath)
        img_original = ImageOps.exif_transpose(img_original)
        orig_w, orig_h = img_original.size
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return

    # --- LAYOUT: 2 Columns ---
    col_canvas, col_controls = st.columns([2.5, 1], gap="medium")

    # --- RIGHT COLUMN: CONTROLS & PREVIEW ---
    with col_controls:
        st.markdown(f"**{T.get('lbl_tools', 'Tools')}**")
        
        # 1. Rotation Row
        c_rot1, c_rot2 = st.columns(2)
        with c_rot1:
            if st.button("↺ -90°", use_container_width=True, key="btn_rot_l"):
                engine.rotate_image_file(fpath, 90)
                st.rerun()
        with c_rot2:
            if st.button("↻ +90°", use_container_width=True, key="btn_rot_r"):
                engine.rotate_image_file(fpath, -90)
                st.rerun()
        
        # 2. Aspect Ratio
        aspect_choice = st.selectbox(
            T['lbl_aspect'], 
            list(ASPECT_RATIOS.keys()), 
            key="editor_aspect_select"
        )
        aspect_val = ASPECT_RATIOS[aspect_choice]
        
        st.divider()
        
        # 3. Preview Header
        st.markdown(f"**{T.get('lbl_preview', 'Preview')}**")

    # --- LEFT COLUMN: CANVAS (CROPPER) ---
    with col_canvas:
        # Cropper повертає зображення в реальному часі
        cropped_img = st_cropper(
            img_original,
            realtime_update=True,
            box_color='#FF4B4B',
            aspect_ratio=aspect_val,
            should_resize_image=True
        )

    # --- BACK TO RIGHT: SHOW STATS & SAVE ---
    # Ми показуємо прев'ю та кнопку в правій колонці, але дані беремо з лівої (cropped_img)
    with col_controls:
        # Show Preview Thumbnail
        st.image(cropped_img, use_container_width=True)
        
        # Stats
        new_w, new_h = cropped_img.size
        st.caption(f"📏 {orig_w}x{orig_h} → **{new_w}x{new_h}** px")
        
        st.write("") # Spacer
        
        # Save Button (Primary Action)
        if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key="btn_save_main"):
            try:
                cropped_img.save(fpath, quality=95)
                # Clear thumbnail cache
                thumb_path = f"{fpath}.thumb.jpg"
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
                st.toast(T['msg_edit_saved'])
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")
