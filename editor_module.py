import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v6.7 (Clamp Fix)
------------------------------
1. Removed manual Proxy scaling (caused coordinate drift).
2. Added strict mathematical clamping (cannot exceed original size).
3. Using 'should_resize_image=True' with original to let library handle display ratio.
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

def clamp_coordinates(rect: dict, max_w: int, max_h: int):
    """
    Жорстко обрізає координати, щоб вони не виходили за межі зображення.
    Виправляє баг '1639px on 960px image'.
    """
    if not rect: return None
    
    # 1. Округляємо
    left = int(rect['left'])
    top = int(rect['top'])
    width = int(rect['width'])
    height = int(rect['height'])
    
    # 2. Обмежуємо початок (не менше 0)
    left = max(0, left)
    top = max(0, top)
    
    # 3. Обмежуємо кінець (початок + ширина не більше максимуму)
    # Якщо рамка вилізла, зменшуємо ширину/висоту
    if left + width > max_w:
        width = max_w - left
    if top + height > max_h:
        height = max_h - top
        
    return (left, top, left + width, top + height), width, height

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    file_id = os.path.basename(fpath)
    
    # State Keys
    if f'rot_{file_id}' not in st.session_state: st.session_state[f'rot_{file_id}'] = 0
    if f'reset_{file_id}' not in st.session_state: st.session_state[f'reset_{file_id}'] = 0

    # 1. LOAD ORIGINAL
    try:
        img_full = Image.open(fpath)
        img_full = ImageOps.exif_transpose(img_full)
        img_full = img_full.convert('RGB')
        
        # Віртуальний поворот
        angle = st.session_state[f'rot_{file_id}']
        if angle != 0:
            img_full = img_full.rotate(-angle, expand=True)
            
        orig_w, orig_h = img_full.size
    except Exception as e:
        st.error(f"Load Error: {e}")
        return

    # Info Bar
    st.caption(get_file_info_str(fpath, img_full))

    # --- UI LAYOUT ---
    col_canvas, col_controls = st.columns([3, 1], gap="small")

    # --- RIGHT PANEL (CONTROLS) ---
    with col_controls:
        # A. Rotate
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
        
        # B. Aspect Ratio
        aspect_choice = st.selectbox(
            T['lbl_aspect'], 
            list(ASPECT_RATIOS.keys()), 
            label_visibility="collapsed",
            key=f"asp_{file_id}"
        )
        aspect_val = ASPECT_RATIOS[aspect_choice]
        
        # C. MAX Button (Forces reset)
        if st.button("MAX ⛶", use_container_width=True, key=f"max_{file_id}", help="Reset box to center"):
            st.session_state[f'reset_{file_id}'] += 1
            st.rerun()
            
        st.divider()

    # --- LEFT PANEL (CANVAS) ---
    with col_canvas:
        cropper_id = f"crp_{file_id}_{st.session_state[f'reset_{file_id}']}_{aspect_choice}"
        
        # ВАЖЛИВО v6.7: 
        # Ми передаємо ПОВНУ картинку (img_full), а не проксі.
        # should_resize_image=True змушує бібліотеку саму вписати її в екран,
        # але повертає координати ВІДНОСНО ОРИГІНАЛУ. Це найнадійніший спосіб.
        raw_rect = st_cropper(
            img_full,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_val,
            should_resize_image=True, 
            return_type='box',
            key=cropper_id
        )

    # --- SAVE & STATS ---
    with col_controls:
        # Валідація і обрізка координат (Clamping)
        crop_box, real_w, real_h = clamp_coordinates(raw_rect, orig_w, orig_h)
        
        # Статистика
        is_changed = (real_w != orig_w or real_h != orig_h)
        color_tag = "orange" if is_changed else "green"
        st.info(f"📏 **{real_w} x {real_h}** px")
        
        if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key=f"sv_{file_id}"):
            try:
                # Кроп по безпечних координатах
                final_image = img_full.crop(crop_box)
                
                # Перезапис файлу
                final_image.save(fpath, quality=95, subsampling=0)
                
                # Очистка кешів
                thumb_path = f"{fpath}.thumb.jpg"
                if os.path.exists(thumb_path): os.remove(thumb_path)
                
                # Закриваємо
                del st.session_state[f'rot_{file_id}']
                del st.session_state[f'reset_{file_id}']
                st.session_state['close_editor'] = True
                st.toast(T['msg_edit_saved'])
                st.rerun()
                    
            except Exception as e:
                st.error(f"Save Failed: {e}")
