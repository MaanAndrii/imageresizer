import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v5.11 (In-Memory Processing)
------------------------------------------
Fixes:
- Dialog closing on Rotate (Moved to RAM editing)
- Dialog closing on MAX (Fixed state logic)
- Crop bounds safety
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
    return f"📄 **{os.path.basename(fpath)}** &nbsp; | &nbsp; 📏 **{img.width}x{img.height}** px &nbsp; | &nbsp; 💾 **{size_str}** &nbsp; | &nbsp; 🎞️ **{img.format}**"

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    # --- SESSION STATE (Local to Editor) ---
    # Ми використовуємо унікальні ключі для кожного файлу, щоб стан не змішувався
    file_id = os.path.basename(fpath)
    
    if f'rot_{file_id}' not in st.session_state:
        st.session_state[f'rot_{file_id}'] = 0
        
    if f'reset_{file_id}' not in st.session_state:
        st.session_state[f'reset_{file_id}'] = 0

    # --- LOAD IMAGE ---
    try:
        # Відкриваємо оригінал
        img_original = Image.open(fpath)
        # Виправляємо орієнтацію EXIF (щоб не крутило саме по собі)
        img_original = ImageOps.exif_transpose(img_original)
        
        # 1. ЗАСТОСОВУЄМО ПОВОРОТ В ПАМ'ЯТІ (Не чіпаючи файл на диску)
        current_angle = st.session_state[f'rot_{file_id}']
        if current_angle != 0:
            # Expand=True розширює полотно, щоб кути не обрізались
            img_original = img_original.rotate(-current_angle, expand=True)
            
        orig_w, orig_h = img_original.size
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return

    # --- INFO BAR ---
    st.markdown(get_file_info_str(fpath, img_original))
    st.divider()

    # --- LAYOUT ---
    col_canvas, col_controls = st.columns([2.5, 1], gap="medium")

    # --- RIGHT: CONTROLS ---
    with col_controls:
        st.markdown(f"**{T.get('lbl_tools', 'Tools')}**")
        
        # A. Rotate Buttons (Змінюють лише змінну в пам'яті)
        c_rot1, c_rot2 = st.columns(2)
        with c_rot1:
            if st.button("↺ -90°", use_container_width=True, key=f"btn_l_{file_id}"):
                st.session_state[f'rot_{file_id}'] = (st.session_state[f'rot_{file_id}'] - 90) % 360
                st.session_state[f'reset_{file_id}'] += 1 # Скидаємо рамку при повороті
                st.rerun()
        with c_rot2:
            if st.button("↻ +90°", use_container_width=True, key=f"btn_r_{file_id}"):
                st.session_state[f'rot_{file_id}'] = (st.session_state[f'rot_{file_id}'] + 90) % 360
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        
        st.write("")
        
        # B. Aspect Ratio & MAX
        st.caption(T['lbl_aspect'])
        c_aspect, c_max = st.columns([2, 1], gap="small")
        
        with c_aspect:
            aspect_choice = st.selectbox(
                "Ratio", 
                list(ASPECT_RATIOS.keys()), 
                label_visibility="collapsed",
                key=f"aspect_{file_id}"
            )
            aspect_val = ASPECT_RATIOS[aspect_choice]
            
        with c_max:
            # Кнопка MAX просто змінює ID кропера, змушуючи його перестворитись
            if st.button("MAX", use_container_width=True, help="Reset crop box to max", key=f"btn_max_{file_id}"):
                st.session_state[f'reset_{file_id}'] += 1
                st.rerun()
        
        st.divider()
        st.markdown(f"**{T.get('lbl_preview', 'Preview')}**")

    # --- LEFT: CANVAS ---
    with col_canvas:
        # Унікальний ключ змушує віджет оновлюватись при натисканні MAX або повороті
        cropper_key = f"cropper_{file_id}_{st.session_state[f'reset_{file_id}']}"
        
        cropped_img = st_cropper(
            img_original,
            realtime_update=True,
            box_color='#FF4B4B',
            aspect_ratio=aspect_val,
            should_resize_image=True, # Оптимізація для відображення великих фото
            key=cropper_key
        )

    # --- BACK TO RIGHT: SAVE ---
    with col_controls:
        # Показуємо мініатюру результату
        st.image(cropped_img, use_container_width=True)
        
        new_w, new_h = cropped_img.size
        # Підсвітка зміни розміру
        color_tag = "red" if (new_w != orig_w or new_h != orig_h) else "green"
        st.markdown(f"📏 {orig_w}x{orig_h} → :{color_tag}[**{new_w}x{new_h}**]")
        
        st.write("")
        
        if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key=f"save_{file_id}"):
            try:
                # ТУТ ми нарешті зберігаємо зміни на диск
                # cropped_img вже містить і поворот, і кроп
                cropped_img.save(fpath, quality=95, subsampling=0)
                
                # Очистка кешів
                thumb_path = f"{fpath}.thumb.jpg"
                if os.path.exists(thumb_path): os.remove(thumb_path)
                
                # Очистка сесії редактора
                del st.session_state[f'rot_{file_id}']
                del st.session_state[f'reset_{file_id}']
                
                st.toast(T['msg_edit_saved'])
                st.rerun()
            except Exception as e:
                st.error(f"Save failed: {e}")
