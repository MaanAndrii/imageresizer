import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper
import watermarker_engine as engine

"""
Editor Module for Watermarker Pro
Handles the Popup Dialog logic for Cropping & Rotating
"""

# Константи для пропорцій
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
    """
    Відображає модальне вікно редагування.
    fpath: шлях до файлу
    T: словник перекладів для поточної мови
    """
    st.caption(f"{os.path.basename(fpath)}")
    
    # 1. Панель інструментів (Toolbar)
    col_aspect, col_rot_l, col_rot_r = st.columns([2, 1, 1])
    
    with col_aspect:
        # Вибір пропорцій
        aspect_choice = st.radio(
            T['lbl_aspect'], 
            list(ASPECT_RATIOS.keys()), 
            horizontal=True, 
            label_visibility="collapsed",
            key="editor_aspect_radio"
        )
        aspect_val = ASPECT_RATIOS[aspect_choice]
        
    with col_rot_l:
        if st.button(T['btn_rotate_left'], use_container_width=True, key="btn_rot_l"):
            engine.rotate_image_file(fpath, 90)
            st.rerun()
            
    with col_rot_r:
        if st.button(T['btn_rotate_right'], use_container_width=True, key="btn_rot_r"):
            engine.rotate_image_file(fpath, -90)
            st.rerun()
            
    st.divider()

    # 2. Область кропера
    try:
        # Відкриваємо файл свіжим
        img_to_crop = Image.open(fpath)
        img_to_crop = ImageOps.exif_transpose(img_to_crop)
        
        # Віджет кропера
        cropped_img = st_cropper(
            img_to_crop,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_val,
            should_resize_image=True # Важливо для великих фото в модалці
        )
        
        # Кнопка збереження
        if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key="btn_save_crop"):
            # Зберігаємо результат (перезапис)
            cropped_img.save(fpath, quality=95)
            
            # Видаляємо старий кеш мініатюри, щоб оновити галерею
            thumb_path = f"{fpath}.thumb.jpg"
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
                
            st.toast(T['msg_edit_saved'])
            st.rerun() # Закриває діалог і оновлює інтерфейс
            
    except Exception as e:
        st.error(f"Editor Error: {e}")
