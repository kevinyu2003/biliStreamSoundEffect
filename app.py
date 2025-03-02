from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import shutil
import time
import webbrowser

app = Flask(__name__)

# Configuration file path
CONFIG_FILE = 'config.json'

# Ensure the sound directory exists
def ensure_sound_dir():
    sound_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sound')
    if not os.path.exists(sound_dir):
        os.makedirs(sound_dir)
    return sound_dir

# Load configuration
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'idCode': '',
        'soundMappings': {
            'likeSound': ['Waga.wav'],
            'giftSound1': ['Ouye.wav'],
            'giftSound2': ['Hachimi.wav'],
            'giftSound3': ['Wow.wav'],
            'messageSound': ['Manbo1.wav'],
            'superChatSound': ['SuperChat.wav'],
            'guardSound': ['Guard.wav'],
            'enterSound': ['Enter.wav'],
            'followSound': ['Follow.wav']
        },
        'volumeSettings': {},
        'multiLikeEnabled': True,
        'probabilitySettings': {
            'likeSound': 1.0,
            'messageSound': 1.0
        }
    }

# Save configuration
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

@app.route('/')
def index():
    config = load_config()
    # Ensure volumeSettings exists
    if 'volumeSettings' not in config:
        config['volumeSettings'] = {}
    return render_template('index.html', config=config)

@app.route('/delete-sound', methods=['POST'])
def delete_sound():
    try:
        sound_dir = ensure_sound_dir()
        config = load_config()
        filename = request.json.get('filename')
        sound_type = request.json.get('soundType')
        
        if not filename or not sound_type:
            return jsonify({
                'success': False,
                'message': '缺少文件名或音效类型'
            })
        
        # Remove file from filesystem
        file_path = os.path.join(sound_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove file from config
        if sound_type in config['soundMappings']:
            if filename in config['soundMappings'][sound_type]:
                config['soundMappings'][sound_type].remove(filename)
                save_config(config)
        
        return jsonify({
            'success': True,
            'message': '音效文件删除成功！'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'删除音效文件时发生错误：{str(e)}'
        })

@app.route('/save-settings', methods=['POST'])
def save_settings():
    try:
        sound_dir = ensure_sound_dir()
        config = load_config()
        
        # Update idCode, multiLikeEnabled, and probability settings
        config['idCode'] = request.form.get('idCode', '')
        config['multiLikeEnabled'] = request.form.get('multiLikeEnabled') == 'true'
        
        # Update probability settings
        if 'probabilitySettings' not in config:
            config['probabilitySettings'] = {}
        like_prob = request.form.get('likeProbability')
        message_prob = request.form.get('messageProbability')
        if like_prob is not None and like_prob != '':
            config['probabilitySettings']['likeSound'] = float(like_prob)
        if message_prob is not None and message_prob != '':
            config['probabilitySettings']['messageSound'] = float(message_prob)
        
        # Get current sound mappings from config
        sound_mappings = config.get('soundMappings', {})
        
        # Ensure all sound mappings are lists
        for key in sound_mappings:
            if not isinstance(sound_mappings[key], list):
                sound_mappings[key] = [sound_mappings[key]] if sound_mappings[key] else []
        
        # Handle multiple file uploads for each sound type
        for sound_key in sound_mappings.keys():
            files = request.files.getlist(sound_key)
            if files and files[0].filename:  # Only update if new files are uploaded
                # Keep track of new files
                new_files = []
                for sound_file in files:
                    if sound_file.filename:
                        # Keep original filename but ensure uniqueness
                        base_name = os.path.splitext(sound_file.filename)[0]
                        ext = os.path.splitext(sound_file.filename)[1]
                        filename = f"{base_name}{ext}"
                        filepath = os.path.join(sound_dir, filename)
                        
                        # If file already exists, add timestamp
                        if os.path.exists(filepath):
                            timestamp = int(time.time())
                            filename = f"{base_name}_{timestamp}{ext}"
                            filepath = os.path.join(sound_dir, filename)
                        
                        sound_file.save(filepath)
                        new_files.append(filename)
                
                # Append new files to existing list instead of replacing
                if new_files:
                    sound_mappings[sound_key].extend(new_files)
        
        config['soundMappings'] = sound_mappings
        save_config(config)
        
        return jsonify({
            'success': True,
            'message': '设置保存成功！'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'保存设置时发生错误：{str(e)}'
        })

@app.route('/sound/<filename>')
def serve_sound(filename):
    sound_dir = ensure_sound_dir()
    return send_from_directory(sound_dir, filename)

@app.route('/save-volume', methods=['POST'])
@app.route('/save-probability', methods=['POST'])
def save_probability():
    try:
        config = load_config()
        data = request.json
        prob_type = data.get('type')
        probability = data.get('probability')
        
        if not prob_type or probability is None:
            return jsonify({
                'success': False,
                'message': '缺少音效类型或概率设置'
            })
        
        # Update probability settings
        if 'probabilitySettings' not in config:
            config['probabilitySettings'] = {}
        config['probabilitySettings'][prob_type] = float(probability)
        save_config(config)
        
        return jsonify({
            'success': True,
            'message': '概率设置已保存'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'保存概率设置时发生错误：{str(e)}'
        })

# Flag to track if browser has been opened
browser_opened = False

def open_browser():
    global browser_opened
    if not browser_opened:
        # Check if this is the main process
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            webbrowser.open('http://127.0.0.1:5000/')
            browser_opened = True


if __name__ == '__main__':
    open_browser()
    app.run(debug=False)
    