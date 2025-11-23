from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问

# 配置
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB限制
app.config['UPLOAD_FOLDER'] = 'uploads'

# 创建上传目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def cleanup_file(filepath):
    """清理临时文件"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except:
        pass

@app.route('/')
def home():
    return jsonify({
        'message': '文件转换API服务运行中',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/health': '健康检查',
            'POST /api/convert/link': 'YouTube链接转MP3/MP4',
            'POST /api/convert/mp4-to-mp3': 'MP4文件转MP3',
            'POST /api/convert/pdf-to-word': 'PDF文件转Word'
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'service': 'file-converter-api',
        'timestamp': '2024-01-01T00:00:00Z'
    })

# 简单的文件上传测试
@app.route('/api/upload-test', methods=['POST'])
def upload_test():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    filename = secure_filename(file.filename)
    file_size = len(file.read())
    
    return jsonify({
        'message': '文件上传测试成功',
        'filename': filename,
        'size': file_size,
        'status': 'success'
    })

# YouTube链接转换（简化版 - 先确保能运行）
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
        
        # 返回模拟成功响应（先让API能运行）
        return jsonify({
            'status': 'success',
            'message': f'链接转换请求已接收: {url} -> {format_type}',
            'note': '转换功能待实现'
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

# MP4转MP3（简化版）
@app.route('/api/convert/mp4-to-mp3', methods=['POST'])
def convert_mp4_to_mp3():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        filename = secure_filename(file.filename)
        
        # 返回模拟成功响应
        return jsonify({
            'status': 'success',
            'message': f'MP4转MP3请求已接收: {filename}',
            'note': '转换功能待实现'
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

# PDF转Word（简化版）
@app.route('/api/convert/pdf-to-word', methods=['POST'])
def convert_pdf_to_word():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        filename = secure_filename(file.filename)
        
        # 返回模拟成功响应
        return jsonify({
            'status': 'success', 
            'message': f'PDF转Word请求已接收: {filename}',
            'note': '转换功能待实现'
        })
        
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
