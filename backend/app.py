from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
import subprocess
import threading
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from pdf2docx import Converter
import yt_dlp
import atexit

app = Flask(__name__)
CORS(app)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['CONVERTED_FOLDER'] = 'converted'

# 创建目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CONVERTED_FOLDER'], exist_ok=True)

# 存储转换任务
conversion_tasks = {}

def cleanup_old_files():
    """清理旧文件"""
    import time
    current_time = time.time()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['CONVERTED_FOLDER']]:
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            # 删除超过1小时的文件
            if os.path.isfile(filepath) and current_time - os.path.getctime(filepath) > 3600:
                try:
                    os.remove(filepath)
                except:
                    pass

# 注册清理函数
atexit.register(cleanup_old_files)

@app.route('/')
def home():
    return jsonify({
        'message': '文件转换API服务运行中',
        'version': '1.0.0',
        'status': 'healthy'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'service': 'file-converter-api',
        'timestamp': '2024-01-01T00:00:00Z'
    })

# MP4转MP3实现
@app.route('/api/convert/mp4-to-mp3', methods=['POST'])
def convert_mp4_to_mp3():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 验证文件类型
        if not file.filename.lower().endswith('.mp4'):
            return jsonify({'error': '请上传MP4文件'}), 400
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
        file.save(input_path)
        
        # 生成输出文件名
        output_filename = filename.replace('.mp4', '.mp3').replace('.MP4', '.mp3')
        output_path = os.path.join(app.config['CONVERTED_FOLDER'], f"{task_id}_{output_filename}")
        
        # 在后台进行转换
        def convert_task():
            try:
                # 使用moviepy进行转换
                video = VideoFileClip(input_path)
                audio = video.audio
                audio.write_audiofile(output_path, verbose=False, logger=None)
                audio.close()
                video.close()
                
                conversion_tasks[task_id] = {
                    'status': 'completed',
                    'output_filename': output_filename,
                    'output_path': output_path
                }
                
                # 清理输入文件
                try:
                    os.remove(input_path)
                except:
                    pass
                    
            except Exception as e:
                conversion_tasks[task_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # 启动转换线程
        thread = threading.Thread(target=convert_task)
        thread.start()
        
        conversion_tasks[task_id] = {
            'status': 'processing',
            'input_filename': filename
        }
        
        return jsonify({
            'status': 'success',
            'message': '转换任务已开始',
            'task_id': task_id,
            'output_filename': output_filename
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

# PDF转Word实现
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
        
        def convert_task():
            try:
                # 使用pdf2docx进行转换
                cv = Converter(input_path)
                cv.convert(output_path, start=0, end=None)
                cv.close()
                
                conversion_tasks[task_id] = {
                    'status': 'completed',
                    'output_filename': output_filename,
                    'output_path': output_path
                }
                
                try:
                    os.remove(input_path)
                except:
                    pass
                    
            except Exception as e:
                conversion_tasks[task_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        thread = threading.Thread(target=convert_task)
        thread.start()
        
        conversion_tasks[task_id] = {
            'status': 'processing',
            'input_filename': filename
        }
        
        return jsonify({
            'status': 'success',
            'message': '转换任务已开始',
            'task_id': task_id,
            'output_filename': output_filename
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

# YouTube下载实现
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
        
        # 验证YouTube URL
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return jsonify({'error': '请输入有效的YouTube链接'}), 400
        
        task_id = str(uuid.uuid4())
        
        def download_task():
            try:
                ydl_opts = {
                    'outtmpl': os.path.join(app.config['CONVERTED_FOLDER'], f'{task_id}_%(title)s.%(ext)s'),
                    'quiet': True,
                }
                
                if format_type == 'mp3':
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    })
                else:  # mp4
                    ydl_opts.update({
                        'format': 'best[height<=720]',
                    })
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    downloaded_file = ydl.prepare_filename(info)
                    
                    if format_type == 'mp3':
                        output_filename = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')
                    else:
                        output_filename = downloaded_file
                    
                    conversion_tasks[task_id] = {
                        'status': 'completed',
                        'output_filename': os.path.basename(output_filename),
                        'output_path': output_filename,
                        'video_title': info.get('title', 'video')
                    }
                    
            except Exception as e:
                conversion_tasks[task_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        thread = threading.Thread(target=download_task)
        thread.start()
        
        conversion_tasks[task_id] = {
            'status': 'processing'
        }
        
        return jsonify({
            'status': 'success',
            'message': '下载任务已开始',
            'task_id': task_id
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

# 检查任务状态
@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = conversion_tasks.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(task)

# 下载文件
@app.route('/api/download/<task_id>', methods=['GET'])
def download_file(task_id):
    task = conversion_tasks.get(task_id)
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

# 清理文件端点
@app.route('/api/cleanup', methods=['POST'])
def cleanup_files():
    cleanup_old_files()
    return jsonify({'message': '清理完成'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
