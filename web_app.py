import streamlit as st
import pandas as pd
from PIL import Image, ImageEnhance
from translitua import translit
import io
import zipfile
import hashlib
import concurrent.futures
import os
from datetime import datetime
import re

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# === 1. BACKEND LOGIC (Pure Python, No UI dependencies) ===

def generate_filename(original_name, naming_mode="Timestamp", prefix="", extension="jpg", file_bytes=None):
    """Генерує стабільне або унікальне ім'я файлу."""
    # ВИПРАВЛЕННЯ: Використовуємо правильну назву змінної original_name
    name_only = os.path.splitext(original_name)[0]
    
    slug = re.sub(r'[\s\W_]+', '-', translit(name_only).lower()).strip('-')
    if not slug: slug = "image"
    
    clean_prefix = re.sub(r'[\s\W_]+', '-', translit(prefix).lower()).strip('-') if prefix else ""
    base = f"{clean_prefix}_{slug}" if clean_prefix else slug

    if naming_mode == "Content Hash" and file_bytes:
        # Генеруємо хеш від вмісту файлу для повної унікальності/стабільності
        file_hash = hashlib.md5(file_bytes).hexdigest()[:8]
        return f"{base}_{file_hash}.{extension}"
    elif naming_mode == "Original + Suffix":
        return f"{base}_wm.{extension}"
    else: # Timestamp (Default)
        timestamp = datetime.now().strftime('%H%M%S_%f')[:9]
        return f"{base}_{timestamp}.{extension}"

@st.cache_data(show_spinner=False)
def get_image_metadata(file_bytes):
    """Кешоване отримання метаданих без повного декодування."""
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            return img.width, img.height, len(file_bytes), img.format
    except Exception:
        return 0, 0, len(file_bytes), "UNKNOWN"

@st.cache_resource(show_spinner=False)
def load_and_process_watermark(wm_file_bytes, opacity):
    """Кешує об'єкт вотермарки. Виконується один раз для всіх фото."""
    if not wm_file_bytes:
        return None
    
    wm = Image.open(io.BytesIO(wm_file_bytes)).convert("RGBA")
    
    # Корекція прозорості
    if opacity < 1.0:
        # Отримуємо альфа-канал
        alpha = wm.split()[3]
        # Змінюємо його яскравість (це і є прозорість для альфа-каналу)
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        # Вставляємо назад
        wm.putalpha(alpha)
        
    return wm

def process_image_core(file_bytes, filename, wm_obj, resize_config, output_fmt, quality):
    """
    Ядро обробки. Приймає байти, повертає байти + детальний звіт.
    Це backend-ready функція.
    """
    input_io = io.BytesIO(file_bytes)
    img = Image.open(input_io)
    
    # Метадані вхідні
    orig_w, orig_h = img.size
    orig_format = img.format
    
    # 1. Підготовка (RGBA)
    img = img.convert("RGBA")
    
    # 2. Логіка ресайзу
    target_value = resize_config['value']
    mode = resize_config['mode']
    
    new_w, new_h = orig_w, orig_h
    scale_factor = 1.0

    if resize_config['enabled']:
        if mode == "Max Side" and (orig_w > target_value or orig_h > target_value):
            if orig_w >= orig_h:
                scale_factor = target_value / float(orig_w)
                new_w, new_h = target_value, int(float(orig_h) * scale_factor)
            else:
                scale_factor = target_value / float(orig_h)
                new_w, new_h = int(float(orig_w) * scale_factor), target_value
                
        elif mode == "Exact Width":
            scale_factor = target_value / float(orig_w)
            new_w, new_h = target_value, int(float(orig_h) * scale_factor)
            
        elif mode == "Exact Height":
            scale_factor = target_value / float(orig_h)
            new_w, new_h = int(float(orig_w) * scale_factor), target_value

        if scale_factor != 1.0:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 3. Накладання вотермарки
    if wm_obj:
        # wm_obj вже має правильну прозорість з кешу
        scale = resize_config['wm_scale']
        margin = resize_config['wm_margin']
        position = resize_config['wm_position']
        
        # Розрахунок розміру лого
        wm_w_target = int(new_w * scale)
        # Захист від ділення на нуль або мікро-розмірів
        if wm_w_target < 1: wm_w_target = 1
        
        w_ratio = wm_w_target / float(wm_obj.width)
        wm_h_target = int(float(wm_obj.height) * w_ratio)
        if wm_h_target < 1: wm_h_target = 1
        
        # Ресайз лого (LANCZOS для чіткості)
        wm_resized = wm_obj.resize((wm_w_target, wm_h_target), Image.Resampling.LANCZOS)
        
        # Координати
        pos_x, pos_y = 0, 0
        if position == 'bottom-right': pos_x, pos_y = new_w - wm_w_target - margin, new_h - wm_h_target - margin
        elif position == 'bottom-left': pos_x, pos_y = margin, new_h - wm_h_target - margin
        elif position == 'top-right': pos_x, pos_y = new_w - wm_w_target - margin, margin
        elif position == 'top-left': pos_x, pos_y = margin, margin
        elif position == 'center': pos_x, pos_y = (new_w - wm_w_target) // 2, (new_h - wm_h_target) // 2
        
        # Накладання (використовуємо paste з маскою самого зображення для альфи)
        img.paste(wm_resized, (pos_x, pos_y), wm_resized)

    # 4. Експорт
    if output_fmt == "JPEG":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif output_fmt == "RGB":
         img = img.convert("RGB")

    output_buffer = io.BytesIO()
    
    if output_fmt == "JPEG":
        img.save(output_buffer, format="JPEG", quality=quality, optimize=True, subsampling=0)
    elif output_fmt == "WEBP":
        img.save(output_buffer, format="WEBP", quality=quality, method=6)
    elif output_fmt == "PNG":
        img.save(output_buffer, format="PNG", optimize=True)

    result_bytes = output_buffer.getvalue()
    
    # 5. Генерація детального звіту
    stats = {
        "filename": filename,
        "orig_res": f"{orig_w}x{orig_h}",
        "new_res": f"{new_w}x{new_h}",
        "orig_size": len(file_bytes),
        "new_size": len(result_bytes),
        "orig_fmt": orig_format or "Unknown",
        "scale_factor": f"{scale_factor:.2f}x",
        "quality": quality if output_fmt != "PNG" else "Lossless"
    }
    
    return result_bytes, stats

# === 2. UI & STATE ===

if 'file_cache' not in st.session_state:
    st.session_state['file_cache'] = {}
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

st.title("📸 Watermarker Pro v3.0 (Parallel)")
st.markdown("---")

# --- SIDEBAR / EXPANDER SETTINGS ---
with st.expander("⚙️ **Конфігурація обробки**", expanded=True):
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.subheader("1. Файл та Ім'я")
        out_fmt = st.selectbox("Формат", ["JPEG", "WEBP", "PNG"])
        quality = 80
        if out_fmt != "PNG":
            quality = st.slider("Якість", 50, 100, 80, 5)
        
        naming_mode = st.selectbox("Стратегія імен", ["Timestamp", "Original + Suffix", "Content Hash"])
        prefix = st.text_input("Префікс", placeholder="img")
        
    with c2:
        st.subheader("2. Геометрія")
        resize_on = st.checkbox("Змінювати розмір", value=True)
        resize_mode = st.selectbox("Режим ресайзу", ["Max Side", "Exact Width", "Exact Height"], disabled=not resize_on)
        resize_val = st.number_input("Значення (px)", min_value=100, max_value=8000, value=1920, step=100, disabled=not resize_on)

    with c3:
        st.subheader("3. Вотермарка")
        wm_file = st.file_uploader("Лого (PNG)", type=["png"])
        wm_pos = st.selectbox("Позиція", ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center'])
        wm_scale = st.slider("Розмір (%)", 5, 50, 15) / 100
        wm_opacity = st.slider("Прозорість", 0.1, 1.0, 1.0, 0.1)
        wm_margin = st.slider("Відступ (px)", 0, 100, 15)

# --- FILE MANAGER ---
c_left, c_right = st.columns([1.5, 1], gap="large")

with c_left:
    st.header("📂 Вхідні файли")
    
    uploaded = st.file_uploader("Drop files here", type=['png', 'jpg', 'jpeg', 'webp'], accept_multiple_files=True, label_visibility="collapsed", key=f"up_{st.session_state['uploader_key']}")
    
    if uploaded:
        for f in uploaded:
            # Читаємо байти одразу, щоб звільнити upload buffer і працювати з пам'яттю
            if f.name not in st.session_state['file_cache']:
                st.session_state['file_cache'][f.name] = f.getvalue()
        st.session_state['uploader_key'] += 1
        st.rerun()

    files_map = st.session_state['file_cache']
    files_names = list(files_map.keys())
    
    # Таблиця вхідних даних
    if files_names:
        table_data = []
        for fname in files_names:
            fbytes = files_map[fname]
            w, h, size, fmt = get_image_metadata(fbytes)
            table_data.append({
                "Select": False,
                "Name": fname,
                "Size": f"{size/1024:.1f} KB",
                "Res": f"{w}x{h}",
                "Fmt": fmt
            })
            
        df = pd.DataFrame(table_data)
        edited_df = st.data_editor(
            df, 
            column_config={
                "Select": st.column_config.CheckboxColumn("✅", default=False),
                "Name": st.column_config.TextColumn("Файл", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key="editor_in"
        )
        
        selected_files = edited_df[edited_df["Select"] == True]["Name"].tolist()
        preview_target = selected_files[-1] if selected_files else None

        # --- ACTIONS ---
        act1, act2, act3 = st.columns([1, 1, 1.5])
        with act1:
            if st.button("🗑️ Видалити", disabled=not selected_files, use_container_width=True):
                for fn in selected_files: del st.session_state['file_cache'][fn]
                st.rerun()
        with act2:
            if st.button("♻️ Скинути", use_container_width=True):
                st.session_state['file_cache'] = {}
                st.session_state['results'] = None
                st.rerun()
        with act3:
            if st.button(f"🚀 Обробити ({len(files_names)})", type="primary", use_container_width=True):
                
                # --- PARALLEL PROCESSING START ---
                progress_bar = st.progress(0)
                status = st.empty()
                
                # Підготовка ресурсів
                wm_bytes = wm_file.getvalue() if wm_file else None
                wm_cached_obj = load_and_process_watermark(wm_bytes, wm_opacity)
                
                resize_cfg = {
                    'enabled': resize_on, 'mode': resize_mode, 'value': resize_val,
                    'wm_scale': wm_scale, 'wm_margin': wm_margin, 'wm_position': wm_pos
                }
                
                results_list = []
                report_list = []
                zip_buffer = io.BytesIO()
                
                total_files = len(files_names)
                
                # ThreadPoolExecutor для паралельної обробки
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {}
                    for fname in files_names:
                        fbytes = files_map[fname]
                        
                        # Генеруємо нове ім'я заздалегідь
                        ext = out_fmt.lower()
                        new_fname = generate_filename(fname, naming_mode, prefix, ext, fbytes)
                        
                        # Запускаємо задачу
                        future = executor.submit(
                            process_image_core, 
                            fbytes, new_fname, wm_cached_obj, resize_cfg, out_fmt, quality
                        )
                        futures[future] = fname

                    # Збір результатів по мірі готовності
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i, future in enumerate(concurrent.futures.as_completed(futures)):
                            fname = futures[future]
                            try:
                                res_bytes, stats = future.result()
                                
                                # Запис в ZIP
                                zf.writestr(stats['filename'], res_bytes)
                                results_list.append((stats['filename'], res_bytes))
                                report_list.append(stats)
                                
                            except Exception as e:
                                st.error(f"Error processing {fname}: {e}")
                            
                            progress_bar.progress((i + 1) / total_files)

                status.success("Done!")
                st.session_state['results'] = {
                    'zip': zip_buffer.getvalue(),
                    'files': results_list,
                    'report': report_list
                }
                # --- PARALLEL PROCESSING END ---

    # --- OUTPUT SECTION ---
    if 'results' in st.session_state and st.session_state['results']:
        res = st.session_state['results']
        report = res['report']
        
        # Обчислення загальної статистики
        total_orig = sum(r['orig_size'] for r in report)
        total_new = sum(r['new_size'] for r in report)
        saved_mb = (total_orig - total_new) / (1024*1024)
        
        st.divider()
        st.success(f"Економія: **{saved_mb:.2f} MB**")
        
        st.download_button(
            label="📦 Скачати ZIP архів",
            data=res['zip'],
            file_name=f"batch_{datetime.now().strftime('%H%M')}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )
        
        with st.expander("📊 Детальний звіт (Технічний)"):
            df_rep = pd.DataFrame(report)
            # Додаємо колонку економії у відсотках для краси
            df_rep['savings %'] = ((df_rep['orig_size'] - df_rep['new_size']) / df_rep['orig_size'] * 100).round(1)
            
            st.dataframe(
                df_rep,
                column_config={
                    "savings %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%f%%"),
                    "scale_factor": "Scale",
                    "orig_fmt": "Input"
                },
                use_container_width=True
            )
            
        with st.expander("⬇️ Скачати окремо"):
            for name, data in res['files']:
                col1, col2 = st.columns([3, 1])
                col1.write(f"📄 {name}")
                col2.download_button("⬇️", data, file_name=name, key=f"dl_{name}")

# --- RIGHT COLUMN: PREVIEW ---
with c_right:
    st.header("👁️ Прев'ю")
    
    with st.container(border=True):
        if 'preview_target' in locals() and preview_target:
            
            # Отримуємо сирі байти з кешу
            raw_bytes = files_map[preview_target]
            
            # Підготовка вотермарки (кешовано)
            wm_bytes = wm_file.getvalue() if wm_file else None
            wm_obj = load_and_process_watermark(wm_bytes, wm_opacity)
            
            resize_cfg = {
                'enabled': resize_on, 'mode': resize_mode, 'value': resize_val,
                'wm_scale': wm_scale, 'wm_margin': wm_margin, 'wm_position': wm_pos
            }
            
            try:
                # Виклик backend-функції для генерації одного прев'ю
                with st.spinner("Рендеринг..."):
                    p_bytes, p_stats = process_image_core(
                        raw_bytes, "preview", wm_obj, resize_cfg, out_fmt, quality
                    )
                
                st.image(p_bytes, caption=f"Preview: {preview_target}", use_container_width=True)
                
                # Показ статистики
                k1, k2 = st.columns(2)
                k1.metric("Розмір", p_stats['new_res'], p_stats['scale_factor'])
                
                delta = ((p_stats['new_size'] - p_stats['orig_size']) / p_stats['orig_size']) * 100
                k2.metric("Вага", f"{p_stats['new_size']/1024:.1f} KB", f"{delta:.1f}%", delta_color="inverse")
                
                st.caption(f"Input: {p_stats['orig_fmt']} | Output: {out_fmt} (Q={p_stats['quality']})")
                
            except Exception as e:
                st.error(f"Preview Error: {e}")
        else:
            st.info("Виберіть файл зліва (✅), щоб побачити результат.")
            st.markdown('<div style="height:300px; background:#f0f2f6;"></div>', unsafe_allow_html=True)

    # === ABOUT ===
    st.divider()
    with st.expander("ℹ️ About"):
        st.markdown("**Product:** Watermarker Pro MaAn v3.0")
        st.markdown("**Author:** Marynyuk Andriy")
        st.markdown("**License:** Proprietary")
        st.markdown("[GitHub Repository](https://github.com/MaanAndrii)")
        st.caption("© 2025 All rights reserved")
