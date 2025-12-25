import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper
import watermarker_engine as engine

"""
Editor Module v5.10 (Info & Max Button)
---------------------------------------
Features:
- Detailed File Info (Size, Res, Format)
- "MAX" button to maximize crop box
- Compact UI layout
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
    """Генерує рядок з інформацією про файл."""
    size_bytes = os.path.getsize(fpath)
    size_mb = size_bytes / (1024 * 1024)
    size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_bytes/1024:.1f} KB"
    
    return f"📄 **{os.path.basename(fpath)}** &nbsp; | &nbsp; 📏 **{img.width}x{img.height}** px &nbsp; | &nbsp; 💾 **{size_str}** &nbsp; | &nbsp; 🎞️ **{img.format}**"

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    # Ініціалізація ключа для примусового оновлення кропера (для кнопки MAX)
    if 'cropper_reset_key' not in st.session_state:
        st.session_state['cropper_reset_key'] = 0

    # Завантаження зображення
    try:
        img_original = Image.open(fpath)
        img_original = ImageOps.exif_transpose(img_original)
        orig_w, orig_h = img_original.size
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return

    # 1. INFO BAR (Верхня панель)
    st.markdown(get_file_info_str(fpath, img_original))
    st.divider()

    # --- MAIN LAYOUT ---
    col_canvas, col_controls = st.columns([2.5, 1], gap="medium")

    # --- RIGHT COLUMN: CONTROLS ---
    with col_controls:
        st.markdown(f"**{T.get('lbl_tools', 'Tools')}**")
        
        # A. Rotation Row
        c_rot1, c_rot2 = st.columns(2)
        with c_rot1:
            if st.button("↺ -90°", use_container_width=True, key="btn_rot_l"):
                if engine.rotate_image_file(fpath, 90):
                    st.session_state['cropper_reset_key'] += 1 # Reset cropper on rotate
                    st.rerun()
        with c_rot2:
            if st.button("↻ +90°", use_container_width=True, key="btn_rot_r"):
                if engine.rotate_image_file(fpath, -90):
                    st.session_state['cropper_reset_key'] += 1
                    st.rerun()
        
        st.write("") # Spacer
        
        # B. Aspect Ratio & MAX Row (Compact)
        st.caption(T['lbl_aspect'])
        c_aspect, c_max = st.columns([2, 1], gap="small")
        
        with c_aspect:
            aspect_choice = st.selectbox(
                "Aspect Ratio", 
                list(ASPECT_RATIOS.keys()), 
                key="editor_aspect_select",
                label_visibility="collapsed"
            )
            aspect_val = ASPECT_RATIOS[aspect_choice]
            
        with c_max:
            # Кнопка MAX просто змінює ключ віджета, змушуючи його перемалюватись 
            # на весь розмір (поведінка за замовчуванням)
            if st.button("MAX", use_container_width=True, help="Maximize crop box"):
                st.session_state['cropper_reset_key'] += 1
                st.rerun()
        
        st.divider()
        
        # C. Preview Header
        st.markdown(f"**{T.get('lbl_preview', 'Preview')}**")

    # --- LEFT COLUMN: CANVAS (CROPPER) ---
    with col_canvas:
        # Генеруємо динамічний ключ, щоб кнопка MAX працювала
        dynamic_key = f"cropper_{st.session_state['cropper_reset_key']}"
        
        cropped_img = st_cropper(
            img_original,
            realtime_update=True,
            box_color='#FF4B4B',
            aspect_ratio=aspect_val,
            should_resize_image=True,
            key=dynamic_key # Важливо для MAX
        )

    # --- BACK TO RIGHT: STATS & SAVE ---
    with col_controls:
        # Show Preview Thumbnail
        st.image(cropped_img, use_container_width=True)
        
        # Stats
        new_w, new_h = cropped_img.size
        # Підсвічуємо, якщо розмір змінився
        color_w = "red" if new_w != orig_w else "green"
        st.markdown(f"📏 {orig_w}x{orig_h} → :{color_w}[**{new_w}x{new_h}**] px")
        
        st.write("") 
        
        # Save Button
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
