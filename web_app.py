import streamlit as st
import pandas as pd
from PIL import Image, ImageEnhance
from translitua import translit
import io
import zipfile
from datetime import datetime
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Watermarker Pro MaAn", page_icon="📸", layout="wide")

# ===== Session state =====
if "file_cache" not in st.session_state:
    st.session_state.file_cache = {}
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ===== Utils =====
@st.cache_data
def get_image_info(data: bytes):
    bio = io.BytesIO(data)
    img = Image.open(bio)
    return img.size[0], img.size[1], len(data)

@st.cache_resource
def load_watermark(data: bytes):
    return Image.open(io.BytesIO(data)).convert("RGBA")

def safe_name(original, prefix, ext, mode, idx, data):
    base = prefix if prefix else original.rsplit(".", 1)[0]
    base = translit(base).lower()
    base = re.sub(r"[\W_]+", "-", base).strip("-") or "image"
    if mode == "timestamp":
        tag = datetime.now().strftime("%H%M%S_%f")[:9]
    elif mode == "index":
        tag = f"{idx:04d}"
    else:
        tag = hashlib.sha1(data).hexdigest()[:10]
    return f"{base}_{tag}.{ext}"

def resize_image(img, mode, w, h):
    if mode == "none":
        return img
    if mode == "max":
        if img.width <= w and img.height <= w:
            return img
        r = w / max(img.width, img.height)
        return img.resize((int(img.width*r), int(img.height*r)), Image.Resampling.LANCZOS)
    if mode == "width":
        r = w / img.width
        return img.resize((w, int(img.height*r)), Image.Resampling.LANCZOS)
    if mode == "height":
        r = h / img.height
        return img.resize((int(img.width*r), h), Image.Resampling.LANCZOS)
    if mode == "box":
        img.thumbnail((w, h), Image.Resampling.LANCZOS)
        return img

def apply_watermark(img, wm, scale, margin, pos, alpha):
    wm = wm.copy()
    nw = int(img.width * scale)
    r = nw / wm.width
    wm = wm.resize((nw, int(wm.height*r)), Image.Resampling.LANCZOS)
    if alpha < 100:
        a = wm.split()[3]
        a = ImageEnhance.Brightness(a).enhance(alpha/100)
        wm.putalpha(a)
    if pos == "bottom-right":
        x, y = img.width-wm.width-margin, img.height-wm.height-margin
    elif pos == "bottom-left":
        x, y = margin, img.height-wm.height-margin
    elif pos == "top-right":
        x, y = img.width-wm.width-margin, margin
    elif pos == "top-left":
        x, y = margin, margin
    else:
        x, y = (img.width-wm.width)//2, (img.height-wm.height)//2
    img.paste(wm, (x, y), wm)
    return img

def process_image(data, cfg, idx):
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    ow, oh = img.size
    img = resize_image(img, cfg["resize_mode"], cfg["resize_w"], cfg["resize_h"])
    if cfg["wm"]:
        img = apply_watermark(img, cfg["wm"], cfg["wm_scale"], cfg["wm_margin"], cfg["wm_pos"], cfg["wm_alpha"])
    if cfg["format"] == "JPEG":
        bg = Image.new("RGB", img.size, (255,255,255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif cfg["format"] == "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    if cfg["format"] == "JPEG":
        img.save(buf, "JPEG", quality=cfg["quality"], optimize=True, subsampling=0)
    elif cfg["format"] == "WEBP":
        img.save(buf, "WEBP", quality=cfg["quality"], method=6)
    else:
        img.save(buf, "PNG", optimize=True)
    res = buf.getvalue()
    return {
        "name": safe_name(cfg["orig_name"], cfg["prefix"], cfg["format"].lower(), cfg["name_mode"], idx, data),
        "bytes": res,
        "orig_size": len(data),
        "new_size": len(res),
        "orig_dim": f"{ow}x{oh}",
        "new_dim": f"{img.width}x{img.height}",
        "format": cfg["format"],
        "quality": cfg["quality"]
    }

# ===== UI =====
st.title("📸 Watermarker Pro MaAn")
st.markdown("---")

with st.expander("⚙️ Налаштування", expanded=True):
    c1,c2,c3 = st.columns(3)
    with c1:
        out_fmt = st.selectbox("Формат", ["JPEG","WEBP","PNG"])
        prefix = st.text_input("Префікс")
        name_mode = st.selectbox("Імена файлів", ["timestamp","index","hash"])
    with c2:
        resize_mode = st.selectbox("Ресайз", ["none","max","width","height","box"])
        resize_w = st.number_input("Ширина / max", 0, 8000, 1920)
        resize_h = st.number_input("Висота", 0, 8000, 1080)
        quality = st.slider("Якість",50,100,80) if out_fmt!="PNG" else 100
    with c3:
        wm_file = st.file_uploader("PNG логотип", type=["png"])
        wm_pos = st.selectbox("Позиція", ["bottom-right","bottom-left","top-right","top-left","center"])
        wm_scale = st.slider("Розмір %",5,50,15)/100
        wm_margin = st.slider("Відступ",0,100,15)
        wm_alpha = st.slider("Прозорість %",10,100,100)

dry_run = st.checkbox("Dry-run (без збереження)")

uploaded = st.file_uploader(
    "Додати файли",
    type=["jpg","jpeg","png","webp","bmp"],
    accept_multiple_files=True,
    key=f"up_{st.session_state.uploader_key}"
)

if uploaded:
    for f in uploaded:
        st.session_state.file_cache[f.name] = f.read()
    st.session_state.uploader_key += 1
    st.rerun()

files = list(st.session_state.file_cache.items())

if st.button(f"🚀 Обробити ({len(files)})", disabled=not files):
    wm_obj = load_watermark(wm_file.read()) if wm_file else None
    cfg_base = {
        "format": out_fmt,
        "quality": quality,
        "resize_mode": resize_mode,
        "resize_w": resize_w,
        "resize_h": resize_h,
        "wm": wm_obj,
        "wm_scale": wm_scale,
        "wm_margin": wm_margin,
        "wm_pos": wm_pos,
        "wm_alpha": wm_alpha,
        "prefix": prefix,
        "name_mode": name_mode
    }
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = []
        for i,(name,data) in enumerate(files):
            cfg = cfg_base | {"orig_name": name}
            futures.append(ex.submit(process_image, data, cfg, i))
        for f in as_completed(futures):
            results.append(f.result())

    df = pd.DataFrame([{
        "Файл": r["name"],
        "Було": r["orig_dim"],
        "Стало": r["new_dim"],
        "KB було": r["orig_size"]/1024,
        "KB стало": r["new_size"]/1024,
        "Економія %": (r["orig_size"]-r["new_size"])/r["orig_size"]*100,
        "Формат": r["format"],
        "Якість": r["quality"]
    } for r in results])

    st.dataframe(df, use_container_width=True)

    if not dry_run:
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf,"w") as zf:
            for r in results:
                zf.writestr(r["name"], r["bytes"])
        st.download_button("📦 Скачати ZIP", zbuf.getvalue(), "photos.zip")
