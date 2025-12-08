import os
import sys
import re
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from translitua import translit
import threading
import subprocess
from datetime import datetime
import shutil # <--- ДОДАНО: Для копіювання файлів

# ... (інші функції load_config, open_folder, create_safe_filename залишаються БЕЗ ЗМІН) ...

# --- ОНОВЛЕНА ЛОГІКА ОБРОБКИ ---
def process_images_backend(config, status_callback, progress_callback):
    try:
        output_folder = config['OUTPUT_FOLDER']
        if not output_folder: output_folder = os.path.join(os.getcwd(), "output_images")
        
        files_to_process = []
        if config['PROCESSING_MODE'] == "folder":
            source_path = config['SOURCE_FOLDER']
            if not source_path: raise ValueError("Папку з зображеннями не вибрано!")
            files_to_process = [os.path.join(source_path, f) for f in os.listdir(source_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
            if not config['OUTPUT_FOLDER']: output_folder = os.path.join(source_path, "resize")
        elif config['PROCESSING_MODE'] == "file":
            files_to_process = config['SELECTED_FILES']
            if not files_to_process: raise ValueError("Файли для обробки не вибрано!")
            if not config['OUTPUT_FOLDER']: output_folder = os.path.join(os.path.dirname(files_to_process[0]), "resize")

        if not files_to_process: raise ValueError("Не знайдено файлів для обробки.")
        os.makedirs(output_folder, exist_ok=True)
        
        watermark_image = None
        is_watermark_active = False # Прапорець, чи використовується вотермарка
        if config['APPLY_WATERMARK'] and config['WATERMARK_IMAGE_PATH']:
            watermark_image = Image.open(config['WATERMARK_IMAGE_PATH']).convert("RGBA")
            is_watermark_active = True
        
        status_callback(f"Знайдено {len(files_to_process)} зображень. Починаємо...")
        
        for i, image_path in enumerate(files_to_process):
            filename = os.path.basename(image_path)
            output_path, final_filename = create_safe_filename(filename, output_folder, config['PREFIX'])
            
            status_callback(f"Обробка [{i+1}/{len(files_to_process)}]: {filename}")
            progress_callback(float(i + 1) / len(files_to_process))
            
            with Image.open(image_path).convert("RGBA") as image:
                # 1. Ресайз
                if config['RESIZE_IMAGES'] and (image.width > config['MAX_DIMENSION'] or image.height > config['MAX_DIMENSION']):
                    max_dim = config['MAX_DIMENSION']
                    if image.width >= image.height: ratio = max_dim/float(image.width); new_width,new_height = max_dim, int(float(image.height)*ratio)
                    else: ratio = max_dim/float(image.height); new_width,new_height = int(float(image.width)*ratio), max_dim
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 2. Вотермарка
                if watermark_image:
                    scale, margin, position = config['WATERMARK_SCALE'], config['MARGIN'], config['POSITION']
                    new_watermark_width = int(image.width * scale)
                    w_ratio = new_watermark_width / float(watermark_image.width)
                    new_watermark_height = int(float(watermark_image.height) * w_ratio)
                    resized_watermark = watermark_image.resize((new_watermark_width, new_watermark_height), Image.Resampling.LANCZOS)
                    
                    if position == 'bottom-right': x, y = image.width-resized_watermark.width-margin, image.height-resized_watermark.height-margin
                    elif position == 'bottom-left': x, y = margin, image.height-resized_watermark.height-margin
                    elif position == 'top-right': x, y = image.width-resized_watermark.width-margin, margin
                    elif position == 'top-left': x, y = margin, margin
                    elif position == 'center': x, y = (image.width-resized_watermark.width)//2, (image.height-resized_watermark.height)//2
                    image.paste(resized_watermark, (x, y), resized_watermark)
                
                # 3. Збереження з оптимізацією
                final_image = image.convert("RGB")
                
                # ЗМІНЕНО: Додано optimize=True
                final_image.save(output_path, 'JPEG', quality=config['QUALITY'], optimize=True)

            # 4. Перевірка розміру ("Запобіжник")
            # Логіка: Якщо ми НЕ ставили вотермарку (тобто нам не важлива візуальна зміна),
            # і файл став більшим за оригінал -> ми повертаємо оригінал.
            if not is_watermark_active:
                source_size = os.path.getsize(image_path)
                output_size = os.path.getsize(output_path)
                
                if output_size > source_size:
                    # Якщо новий файл більший і вотермарки немає - просто копіюємо оригінал
                    # (але перейменовуємо його як треба)
                    shutil.copy2(image_path, output_path)
                    # Можна додати примітку в лог, якщо потрібно, але поки що тихо

        status_callback("Успішно завершено!")
        progress_callback(1.0)
        messagebox.showinfo("Готово", f"Обробка {len(files_to_process)} зображень успішно завершена!")
        open_folder(output_folder)

    except Exception as e:
        status_callback(f"Помилка: {e}")
        messagebox.showerror("Помилка", f"Сталася помилка: {e}")

# ... (Клас App та if __name__ == "__main__" залишаються БЕЗ ЗМІН) ...