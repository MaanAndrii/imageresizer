import streamlit as st
import base64
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
        # Повертаємо placeholder при помилці
        return None


def render_gallery(files_dict, selected_files=None, key="gallery"):
    """
    Рендерить галерею зображень з можливістю вибору.
    
    Args:
        files_dict: dict {filename: file_bytes}
        selected_files: set of selected filenames
        key: unique key for component
    
    Returns:
        tuple: (selected_files_set, clicked_file)
    """
    if selected_files is None:
        selected_files = set()
    
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
                padding-top: 100%; /* 1:1 Aspect Ratio */
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
                    <strong id="total-count">{len(gallery_data)}</strong> файлів
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
            const galleryData = {gallery_data};
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
                grid.innerHTML = '';
                
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
                sendSelectionToStreamlit();
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
                sendSelectionToStreamlit();
            }}
            
            function clearSelection() {{
                selectedFiles.clear();
                renderGallery();
                sendSelectionToStreamlit();
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
            
            function sendSelectionToStreamlit() {{
                const data = {{
                    selected: Array.from(selectedFiles),
                    lastClicked: lastClickedFile
                }};
                
                // Відправка даних в Streamlit через window.parent.postMessage
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    data: data
                }}, '*');
            }}
            
            // Початковий рендер
            renderGallery();
        </script>
    </body>
    </html>
    """
    
    # Рендеримо компонент
    result = st.components.v1.html(
        html_code,
        height=600,
        scrolling=True
    )
    
    # Обробка результату
    if result:
        new_selected = set(result.get('selected', []))
        clicked = result.get('lastClicked', None)
        return new_selected, clicked
    
    return selected_files, None
