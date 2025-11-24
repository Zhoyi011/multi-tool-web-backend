from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import threading
import requests
from werkzeug.utils import secure_filename
import tempfile
import atexit

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['CONVERTED_FOLDER'] = 'converted'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CONVERTED_FOLDER'], exist_ok=True)

tasks = {}

def cleanup_old_files():
    """清理旧文件"""
    import time
    current_time = time.time()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['CONVERTED_FOLDER']]:
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath) and current_time - os.path.getctime(filepath) > 3600:
                try:
                    os.remove(filepath)
                except:
                    pass

atexit.register(cleanup_old_files)

# MP4转MP3 - 使用在线转换API
def convert_mp4_to_mp3_online(task_id, input_path, output_path, output_filename):
    try:
        # 使用在线转换服务
        conversion_url = "https://api.online-convert.com/convert-to-mp3"
        
        # 上传文件到在线服务
        with open(input_path, 'rb') as f:
            files = {'file': (output_filename, f, 'video/mp4')}
            response = requests.post(conversion_url, files=files, timeout=300)
        
        if response.status_code == 200:
            # 下载转换后的文件
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            tasks[task_id] = {
                'status': 'completed',
                'output_filename': output_filename,
                'output_path': output_path
            }
        else:
            tasks[task_id] = {
                'status': 'error',
                'error': '在线转换服务失败'
            }
            
    except Exception as e:
        tasks[task_id] = {
            'status': 'error',
            'error': f'转换失败: {str(e)}'
        }
    finally:
        # 清理输入文件
        try:
            os.remove(input_path)
        except:
            pass

# PDF转Word - 使用pdf2docx
def convert_pdf_to_docx(task_id, input_path, output_path, output_filename):
    try:
        from pdf2docx import Converter
        
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
        
        tasks[task_id] = {
            'status': 'completed',
            'output_filename': output_filename,
            'output_path': output_path
        }
        
    except Exception as e:
        tasks[task_id] = {
            'status': 'error',
            'error': f'PDF转换失败: {str(e)}'
        }
    finally:
        try:
            os.remove(input_path)
        except:
            pass

# YouTube下载 - 使用yt-dlp
def download_youtube_video(task_id, url, format_type, output_path, output_filename):
    try:
        import yt_dlp
        
        ydl_opts = {
            'outtmpl': output_path.replace('.mp3', '').replace('.mp4', ''),
            'quiet': True,
        }
        
        if format_type == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
            })
        else:
            ydl_opts.update({
                'format': 'best[height<=720]',
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 找到实际生成的文件
        actual_output_path = output_path
        if format_type == 'mp3':
            actual_output_path = output_path.replace('.mp4', '.mp3')
        
        tasks[task_id] = {
            'status': 'completed',
            'output_filename': output_filename,
            'output_path': actual_output_path
        }
        
    except Exception as e:
        tasks[task_id] = {
            'status': 'error',
            'error': f'YouTube下载失败: {str(e)}'
        }

@app.route('/')
def home():
    return jsonify({
        'message': '真实文件转换API服务运行中',
        'status': 'healthy',
        'mode': 'real-conversion'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

# MP4转MP3端点
@app.route('/api/convert/mp4-to-mp3', methods=['POST'])
def convert_mp4_to_mp3():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        if not file.filename.lower().endswith('.mp4'):
            return jsonify({'error': '请上传MP4文件'}), 400

        task_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(input_path)
        
        output_filename = filename.replace('.mp4', '.mp3').replace('.MP4', '.mp3')
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], f"{task_id}_{output_filename}")
        
        tasks[task_id] = {
            'status': 'processing',
            'input_filename': filename
        }
        
        # 使用在线转换服务
        thread = threading.Thread(
            target=convert_mp4_to_mp3_online,
            args=(task_id, input_path, output_path, output_filename)
        )
        thread.start()
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'output_filename': output_filename,
            'message': '开始转换MP4到MP3'
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

# PDF转Word端点
@app.route('/api/convert/pdf-to-word', methods=['POST'])
def convert_pdf_to_word():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': '请上传PDF文件'}), 400

        task_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(input_path)
        
        output_filename = filename.replace('.pdf', '.docx').replace('.PDF', '.docx')
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], f"{task_id}_{output_filename}")
        
        tasks[task_id] = {
            'status': 'processing',
            'input_filename': filename
        }
        
        thread = threading.Thread(
            target=convert_pdf_to_docx,
            args=(task_id, input_path, output_path, output_filename)
        )
        thread.start()
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'output_filename': output_filename,
            'message': '开始转换PDF到Word'
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

# YouTube下载端点
@app.route('/api/convert/link', methods=['POST'])
def convert_link():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '缺少JSON数据'}), 400
            
        url = data.get('url')
        format_type = data.get('format', 'mp3')
        
        if not url:
            return jsonify({'error': '缺少URL参数'}), 400
        
        task_id = str(uuid.uuid4())
        output_filename = f"youtube_video.{format_type}"
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], f"{task_id}_{output_filename}")
        
        tasks[task_id] = {
            'status': 'processing'
        }
        
        thread = threading.Thread(
            target=download_youtube_video,
            args=(task_id, url, format_type, output_path, output_filename)
        )
        thread.start()
        
        return jsonify({
            'status': 'success',
            'task_id': task_id,
            'output_filename': output_filename,
            'message': '开始下载YouTube视频'
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(task)

@app.route('/api/download/<task_id>', methods=['GET'])
def download_file(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': '文件不存在'}), 404
    
    if task['status'] != 'completed':
        return jsonify({'error': '文件尚未转换完成'}), 400
    
    try:
        return send_file(
            task['output_path'],
            as_attachment=True,
            download_name=task['output_filename']
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
