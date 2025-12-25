import streamlit as st
import os
from PIL import Image, ImageOps
from streamlit_cropper import st_cropper

"""
Editor Module v6.6 (Proxy Force)
--------------------------------
1. Creates a physical 600px proxy image for the UI (Fixes zoom/overflow).
2. Calculates crop coordinates based on the proxy.
3. Scales coordinates back up to crop the original High-Res image.
4. "MAX" button forces a full-size reset of the crop box.
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

def create_proxy_image(img: Image.Image, target_width: int = 600):
    """
    Створює фізично зменшену копію для відображення в UI.
    Повертає: (proxy_image, scale_factor)
    """
    w, h = img.size
    if w > target_width:
        ratio = target_width / w
        new_h = int(h * ratio)
        # Використовуємо якісний ресайз для прев'ю
        proxy = img.resize((target_width, new_h), Image.Resampling.LANCZOS)
        scale_factor = w / target_width  # Множник, щоб перевести координати назад в оригінал
        return proxy, scale_factor
    return img, 1.0

@st.dialog("🛠 Editor", width="large")
def open_editor_dialog(fpath: str, T: dict):
    file_id = os.path.basename(fpath)
    
    # Ініціалізація стану
    if f'rot_{file_id}' not in st.session_state: st.session_state[f'rot_{file_id}'] = 0
    if f'reset_{file_id}' not in st.session_state: st.session_state[f'reset_{file_id}'] = 0

    # 1. ЗАВАНТАЖЕННЯ ОРИГІНАЛУ
    try:
        img_full = Image.open(fpath)
        img_full = ImageOps.exif_transpose(img_full)
        img_full = img_full.convert('RGB') # Fix for PNG/Palette issues
        
        # Віртуальний поворот оригіналу
        angle = st.session_state[f'rot_{file_id}']
        if angle != 0:
            img_full = img_full.rotate(-angle, expand=True)
            
    except Exception as e:
        st.error(f"Load Error: {e}")
        return

    # 2. СТВОРЕННЯ PROXY (Для UI)
    # Ми працюємо з картинкою шириною 600px. Це вирішує проблему "не влазить".
    img_proxy, scale_factor = create_proxy_image(img_full, target_width=600)

    # Info Bar
    st.caption(get_file_info_str(fpath, img_full))

    # --- UI LAYOUT ---
    col_canvas, col_controls = st.columns([3, 1], gap="medium")

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
        
        # C. MAX Button (Forces reset of the box)
        if st.button("MAX ⛶", use_container_width=True, key=f"max_{file_id}"):
            st.session_state[f'reset_{file_id}'] += 1
            st.rerun()
            
        st.divider()

    # --- LEFT PANEL (CANVAS) ---
    with col_canvas:
        # Генеруємо унікальний ключ. Зміна ключа = повний скидання віджета (ефект MAX)
        cropper_id = f"crp_{file_id}_{st.session_state[f'reset_{file_id}']}_{aspect_choice}"
        
        # ВАЖЛИВО:
        # 1. Передаємо img_proxy (маленьку).
        # 2. should_resize_image=False (бо ми ВЖЕ зменшили її самі, координати будуть 1:1 до proxy).
        # 3. return_type='box' (отримуємо координати, а не картинку).
        rect = st_cropper(
            img_proxy,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=aspect_val,
            should_resize_image=False, 
            return_type='box',
            key=cropper_id
        )

    # --- SAVE & STATS ---
    with col_controls:
        # Розраховуємо реальні координати для ОРИГІНАЛУ
        if rect:
            # rect повертає координати на img_proxy (0-600px)
            # множимо на scale_factor, щоб отримати координати на img_full (напр. 0-4000px)
            real_left = int(rect['left'] * scale_factor)
            real_top = int(rect['top'] * scale_factor)
            real_w = int(rect['width'] * scale_factor)
            real_h = int(rect['height'] * scale_factor)
            
            # Захист меж (на всяк випадок)
            real_left = max(0, real_left)
            real_top = max(0, real_top)
            
            # Відображаємо реальний розмір майбутнього кропу
            st.info(f"📏 **{real_w} x {real_h}** px")
            
            if st.button(T['btn_save_edit'], type="primary", use_container_width=True, key=f"sv_{file_id}"):
                try:
                    # Кропаємо ОРИГІНАЛ
                    crop_box = (real_left, real_top, real_left + real_w, real_top + real_h)
                    final_image = img_full.crop(crop_box)
                    
                    # Зберігаємо файл
                    final_image.save(fpath, quality=95, subsampling=0)
                    
                    # Чистимо кеш
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
