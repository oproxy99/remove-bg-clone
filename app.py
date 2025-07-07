import os
from flask import Flask, request, send_file, make_response
from werkzeug.utils import secure_filename
from rembg import remove
from PIL import Image, ImageFilter
import io
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  

UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE_MB = 10

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return "Flask API running. Use /remove-bg, /custom-bg, or /blur-bg endpoints."


@app.route('/remove-bg', methods=['POST'])
def remove_bg():
    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return "Invalid file type", 400

    try:
        now = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, f"{now}_{filename}")
        output_filename = f"{now}_no_bg.png"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        file.save(input_path)

        with open(input_path, 'rb') as i:
            input_data = i.read()

        output_data = remove(input_data)

        with open(output_path, 'wb') as o:
            o.write(output_data)

        response = make_response(send_file(output_path, mimetype='image/png'))
        response.headers['Content-Disposition'] = f'attachment; filename="{output_filename}"'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'

        return response

    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500


@app.route('/custom-bg', methods=['POST'])
def custom_bg():
    if 'file' not in request.files or 'background' not in request.files:
        return "Both foreground and background images are required.", 400

    file = request.files['file']
    background = request.files['background']

    if file.filename == '' or background.filename == '':
        return "Please select both images.", 400

    if not (allowed_file(file.filename) and allowed_file(background.filename)):
        return "Invalid file type. Allowed types: png, jpg, jpeg, webp.", 400

    try:
        now = datetime.now().strftime('%Y%m%d%H%M%S')
        fg_filename = secure_filename(file.filename)
        bg_filename = secure_filename(background.filename)

        input_path = os.path.join(UPLOAD_FOLDER, f"{now}_{fg_filename}")
        bg_path = os.path.join(UPLOAD_FOLDER, f"{now}_{bg_filename}")
        output_filename = f"{now}_custom_bg.png"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        file.save(input_path)
        background.save(bg_path)

        input_image = Image.open(input_path).convert("RGBA")
        img_byte_arr = io.BytesIO()
        input_image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        fg_removed = Image.open(io.BytesIO(remove(img_bytes))).convert("RGBA")

        bg_image = Image.open(bg_path).convert("RGBA")
        bg_resized = bg_image.resize(fg_removed.size)

        result = Image.alpha_composite(bg_resized, fg_removed)
        result.save(output_path)

        response = make_response(send_file(output_path, mimetype='image/png'))
        response.headers['Content-Disposition'] = f'attachment; filename="{output_filename}"'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'

        return response

    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500


@app.route('/blur-bg', methods=['POST'])
def blur_bg():
    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return "Invalid file type", 400

    try:
        now = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, f"{now}_{filename}")
        output_filename = f"{now}_blur_bg.png"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        file.save(input_path)

        original = Image.open(input_path).convert("RGBA")

        with open(input_path, 'rb') as i:
            input_data = i.read()

        output_data = remove(input_data)
        fg_img = Image.open(io.BytesIO(output_data)).convert("RGBA")

        blurred_bg = original.filter(ImageFilter.GaussianBlur(radius=15))

        fg_alpha = fg_img.split()[-1]

        combined = Image.composite(fg_img, blurred_bg, fg_alpha)

        combined.save(output_path, format='PNG')

        response = make_response(send_file(output_path, mimetype='image/png'))
        response.headers['Content-Disposition'] = f'attachment; filename="{output_filename}"'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'

        return response

    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
