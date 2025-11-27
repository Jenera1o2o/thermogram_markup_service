from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'Thermogram Markup API',
        'endpoint': '/markup',
        'method': 'POST'
    })

@app.route('/markup', methods=['POST'])
def add_markup():
    try:
        data = request.json
        
        # Валидация входных данных
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        image_url = data.get('imageUrl')
        defects = data.get('defects', [])
        image_width = data.get('imageWidth')
        image_height = data.get('imageHeight')
        
        if not image_url:
            return jsonify({'error': 'imageUrl is required'}), 400
        
        if not defects:
            return jsonify({'error': 'No defects provided'}), 400
        
        # Загружаем изображение
        print(f"Downloading image from: {image_url}")
        response = requests.get(image_url, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to download image'}), 400
        
        img = Image.open(BytesIO(response.content)).convert('RGB')
        
        # Создаем объект для рисования
        draw = ImageDraw.Draw(img)
        
        # Вычисляем масштаб (300мм = ширина панели)
        pixels_per_mm = img.width / 300
        
        print(f"Processing {len(defects)} defects")
        
        # Загружаем шрифты
        try:
            font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            font_number = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        except Exception as e:
            print(f"Font loading failed: {e}, using default")
            font_label = ImageFont.load_default()
            font_number = ImageFont.load_default()
        
        # Рисуем каждый дефект
        for index, defect in enumerate(defects):
            x = int(defect.get('x', 0))
            y = int(defect.get('y', 0))
            diameter_mm = float(defect.get('diameter_mm', 10))
            
            # Вычисляем радиус в пикселях
            radius = int((diameter_mm * pixels_per_mm) / 2)
            
            print(f"Defect {index + 1}: x={x}, y={y}, diameter={diameter_mm}mm, radius={radius}px")
            
            # КРАСНЫЙ КРУГ вокруг дефекта
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                outline=(255, 0, 0),
                width=5
            )
            
            # ПОДПИСЬ РАЗМЕРА (над кругом)
            label = f"{diameter_mm:.1f}mm"
            
            # Фон для текста (для читаемости)
            bbox = draw.textbbox((0, 0), label, font=font_label)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            label_x = x - text_width // 2
            label_y = y - radius - text_height - 10
            
            # Черный фон под текстом
            draw.rectangle(
                [label_x - 5, label_y - 3, label_x + text_width + 5, label_y + text_height + 3],
                fill=(0, 0, 0)
            )
            
            # Красный текст
            draw.text(
                (label_x, label_y),
                label,
                fill=(255, 0, 0),
                font=font_label
            )
            
            # БЕЛЫЙ КРУГ для номера (в центре дефекта)
            circle_radius = 25
            draw.ellipse(
                [x - circle_radius, y - circle_radius, x + circle_radius, y + circle_radius],
                fill=(255, 255, 255),
                outline=(0, 0, 0),
                width=3
            )
            
            # НОМЕР ДЕФЕКТА (черный текст по центру)
            number = str(index + 1)
            bbox = draw.textbbox((0, 0), number, font=font_number)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            draw.text(
                (x - text_width // 2, y - text_height // 2 - 2),
                number,
                fill=(0, 0, 0),
                font=font_number
            )
        
        print("Markup complete, generating output")
        
        # Сохраняем результат в буфер
        output = BytesIO()
        img.save(output, format='PNG', quality=95, optimize=True)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'thermogram_marked_{len(defects)}_defects.png'
        )
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
