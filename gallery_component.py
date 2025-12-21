import streamlit as st
import base64
import json
from io import BytesIO
from PIL import Image

def generate_thumbnail(file_bytes, size=(200, 200)):
    """Генерує мініатюру та повертає base64 encoded string."""
    try:
        img = Image.open(BytesIO(file_bytes))
        
        # Обробка EXIF орієнтації
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except:
            pass
        
        # Створюємо thumbnail зі збереженням пропорцій
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Конвертуємо в RGB якщо потрібно
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
            img = background
        
        # Конвертуємо в base64
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        return None


def render_gallery(files_dict, key="gallery"):
    """
    Рендерить галерею зображень з можливістю вибору.
    
    Args:
        files_dict: dict {filename: file_bytes}
        key: unique key for component
    
    Returns:
        None (uses session_state)
    """
    # Ініціалізація state
    if f'{key}_selected' not in st.session_state:
        st.session_state[f'{key}_selected'] = set()
    if f'{key}_clicked' not in st.session_state:
        st.session_state[f'{key}_clicked'] = None
    
    selected_files = st.session_state[f'{key}_selected']
    
    # Генеруємо thumbnails з кешуванням
    thumbnails = {}
    file_info = {}
    
    for fname, fbytes in files_dict.items():
        # Кешуємо thumbnail
        cache_key = f"thumb_{fname}_{len(fbytes)}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = generate_thumbnail(fbytes)
        thumbnails[fname] = st.session_state[cache_key]
        
        # Збираємо metadata
        try:
            img = Image.open(BytesIO(fbytes))
            file_info[fname] = {
                'width': img.width,
                'height': img.height,
                'size': len(fbytes),
                'format': img.format or 'Unknown'
            }
        except:
            file_info[fname] = {
                'width': 0,
                'height': 0,
                'size': len(fbytes),
                'format': 'Invalid'
            }
    
    # Підготовка даних для JS
    gallery_data = []
    for fname in files_dict.keys():
        gallery_data.append({
            'filename': fname,
            'thumbnail': thumbnails[fname] or '',
            'selected': fname in selected_files,
            'info': file_info[fname]
        })
    
    # Конвертуємо в JSON безпечно
    gallery_json = json.dumps(gallery_data, ensure_ascii=False)
    
    # HTML + CSS + JS компонент
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: transparent;
                padding: 10px;
            }}
            
            .gallery-container {{
                width: 100%;
            }}
            
            .gallery-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            
            .gallery-info {{
                font-size: 14px;
                color: #495057;
            }}
            
            .select-all-btn {{
                padding: 6px 16px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.2s;
            }}
            
            .select-all-btn:hover {{
                background: #0056b3;
                transform: translateY(-1px);
            }}
            
            .select-all-btn:active {{
                transform: translateY(0);
            }}
            
            .gallery-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                gap: 16px;
                margin-bottom: 20px;
            }}
            
            .gallery-item {{
                position: relative;
                cursor: pointer;
                border-radius: 12px;
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                background: white;
                border: 2px solid #e9ecef;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            
            .gallery-item:hover {{
                transform: translateY(-4px);
                box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                border-color: #dee2e6;
            }}
            
            .gallery-item.selected {{
                border-color: #007bff;
                box-shadow: 0 4px 16px rgba(0,123,255,0.3);
            }}
            
            .gallery-item.selected:hover {{
                border-color: #0056b3;
            }}
            
            .gallery-item.error {{
                border-color: #dc3545;
                background: #fff5f5;
            }}
            
            .thumbnail-wrapper {{
                position: relative;
                width: 100%;
                padding-top: 100%;
                background: #f8f9fa;
                overflow: hidden;
            }}
            
            .thumbnail-img {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform 0.3s ease;
            }}
            
            .gallery-item:hover .thumbnail-img {{
                transform: scale(1.08);
            }}
            
            .error-placeholder {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 48px;
                color: #dc3545;
            }}
            
            .selection-badge {{
                position: absolute;
                top: 8px;
                right: 8px;
                width: 28px;
                height: 28px;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            }}
            
            .gallery-item.selected .selection-badge {{
                background: #007bff;
            }}
            
            .checkmark {{
                display: none;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }}
            
            .gallery-item.selected .checkmark {{
                display: block;
            }}
            
            .checkbox-circle {{
                width: 18px;
                height: 18px;
                border: 2px solid #adb5bd;
                border-radius: 50%;
                transition: all 0.2s;
            }}
            
            .gallery-item.selected .checkbox-circle {{
                display: none;
            }}
            
            .gallery-item:hover .checkbox-circle {{
                border-color: #007bff;
                transform: scale(1.1);
            }}
            
            .file-info {{
                padding: 10px;
                background: white;
            }}
            
            .filename {{
                font-size: 12px;
                font-weight: 500;
                color: #212529;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                margin-bottom: 4px;
            }}
            
            .file-meta {{
                font-size: 11px;
                color: #6c757d;
                display: flex;
                justify-content: space-between;
            }}
            
            .selection-summary {{
                position: sticky;
                bottom: 0;
                background: linear-gradient(to top, white 80%, transparent);
                padding: 15px 10px 5px;
                margin-top: 20px;
            }}
            
            .summary-content {{
                background: #e7f3ff;
                border: 2px solid #007bff;
                border-radius: 10px;
                padding: 12px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .summary-text {{
                font-size: 14px;
                font-weight: 600;
                color: #004085;
            }}
            
            .clear-btn {{
                padding: 6px 14px;
                background: white;
                color: #007bff;
                border: 2px solid #007bff;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 600;
                transition: all 0.2s;
            }}
            
            .clear-btn:hover {{
                background: #007bff;
                color: white;
            }}
            
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: scale(0.95); }}
                to {{ opacity: 1; transform: scale(1); }}
            }}
            
            .gallery-item {{
                animation: fadeIn 0.3s ease-out;
            }}
        </style>
    </head>
    <body>
        <div class="gallery-container">
            <div class="gallery-header">
                <div class="gallery-info">
                    <strong id="total-count">0</strong> файлів
                </div>
                <button class="select-all-btn" onclick="toggleSelectAll()">
                    Вибрати всі
                </button>
            </div>
            
            <div class="gallery-grid" id="gallery-grid"></div>
            
            <div class="selection-summary" id="summary" style="display: none;">
                <div class="summary-content">
                    <span class="summary-text">
                        Вибрано: <strong id="selected-count">0</strong> файлів
                    </span>
                    <button class="clear-btn" onclick="clearSelection()">
                        Скасувати вибір
                    </button>
                </div>
            </div>
        </div>
        
        <script>
            const galleryData = {gallery_json};
            let selectedFiles = new Set();
            let lastClickedFile = null;
            
            // Ініціалізація вибраних файлів
            galleryData.forEach(item => {{
                if (item.selected) {{
                    selectedFiles.add(item.filename);
                }}
            }});
            
            function formatFileSize(bytes) {{
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            }}
            
            function renderGallery() {{
                const grid = document.getElementById('gallery-grid');
                const totalCount = document.getElementById('total-count');
                grid.innerHTML = '';
                totalCount.textContent = galleryData.length;
                
                galleryData.forEach((item, index) => {{
                    const isSelected = selectedFiles.has(item.filename);
                    const isError = !item.thumbnail || item.info.format === 'Invalid';
                    
                    const itemDiv = document.createElement('div');
                    itemDiv.className = `gallery-item ${{isSelected ? 'selected' : ''}} ${{isError ? 'error' : ''}}`;
                    itemDiv.onclick = () => toggleSelection(item.filename);
                    
                    itemDiv.innerHTML = `
                        <div class="thumbnail-wrapper">
                            ${{item.thumbnail ? 
                                `<img src="${{item.thumbnail}}" class="thumbnail-img" alt="${{item.filename}}">` :
                                '<div class="error-placeholder">⚠️</div>'
                            }}
                            <div class="selection-badge">
                                <span class="checkmark">✓</span>
                                <div class="checkbox-circle"></div>
                            </div>
                        </div>
                        <div class="file-info">
                            <div class="filename" title="${{item.filename}}">${{item.filename}}</div>
                            <div class="file-meta">
                                <span>${{item.info.width}}×${{item.info.height}}</span>
                                <span>${{formatFileSize(item.info.size)}}</span>
                            </div>
                        </div>
                    `;
                    
                    grid.appendChild(itemDiv);
                }});
                
                updateSummary();
            }}
            
            function toggleSelection(filename) {{
                if (selectedFiles.has(filename)) {{
                    selectedFiles.delete(filename);
                }} else {{
                    selectedFiles.add(filename);
                }}
                
                lastClickedFile = filename;
                renderGallery();
                notifyStreamlit();
            }}
            
            function toggleSelectAll() {{
                if (selectedFiles.size === galleryData.length) {{
                    selectedFiles.clear();
                }} else {{
                    galleryData.forEach(item => {{
                        selectedFiles.add(item.filename);
                    }});
                }}
                renderGallery();
                notifyStreamlit();
            }}
            
            function clearSelection() {{
                selectedFiles.clear();
                renderGallery();
                notifyStreamlit();
            }}
            
            function updateSummary() {{
                const summary = document.getElementById('summary');
                const count = document.getElementById('selected-count');
                const btn = document.querySelector('.select-all-btn');
                
                count.textContent = selectedFiles.size;
                
                if (selectedFiles.size > 0) {{
                    summary.style.display = 'block';
                }} else {{
                    summary.style.display = 'none';
                }}
                
                btn.textContent = selectedFiles.size === galleryData.length ? 
                    'Скасувати всі' : 'Вибрати всі';
            }}
            
            function notifyStreamlit() {{
                // Використовуємо Streamlit query params для комунікації
                const params = new URLSearchParams(window.location.search);
                params.set('gallery_selected', Array.from(selectedFiles).join(','));
                params.set('gallery_clicked', lastClickedFile || '');
                params.set('gallery_timestamp', Date.now());
                
                // Оновлюємо URL без перезавантаження
                const newUrl = window.location.pathname + '?' + params.toString();
                window.history.replaceState(null, '', newUrl);
                
                // Trigger Streamlit rerun через iframe communication
                if (window.parent) {{
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: {{
                            selected: Array.from(selectedFiles),
                            clicked: lastClickedFile
                        }}
                    }}, '*');
                }}
            }}
            
            // Початковий рендер
            renderGallery();
        </script>
    </body>
    </html>
    """
    
    # Рендеримо компонент БЕЗ очікування результату
    st.components.v1.html(
        html_code,
        height=600,
        scrolling=True
    )
    
    # Читаємо стан з query params (якщо є)
    try:
        query_params = st.query_params
        if 'gallery_selected' in query_params:
            selected_str = query_params.get('gallery_selected', '')
            if selected_str:
                new_selected = set(selected_str.split(','))
            else:
                new_selected = set()
            
            clicked = query_params.get('gallery_clicked', '')
            
            # Оновлюємо тільки якщо змінилось
            if new_selected != st.session_state[f'{key}_selected']:
                st.session_state[f'{key}_selected'] = new_selected
            
            if clicked and clicked != st.session_state[f'{key}_clicked']:
                st.session_state[f'{key}_clicked'] = clicked
    except:
        pass


def get_gallery_state(key="gallery"):
    """Отримує поточний стан галереї."""
    selected_key = f'{key}_selected'
    clicked_key = f'{key}_clicked'
    
    if selected_key not in st.session_state:
        st.session_state[selected_key] = set()
    if clicked_key not in st.session_state:
        st.session_state[clicked_key] = None
    
    return (
        st.session_state[selected_key],
        st.session_state[clicked_key]
    )
