# app.py
import os
import uuid
import zipfile
import shutil
import json
import queue as queue_module
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename
from plyer import notification
import threading
import time

from models import db, Asset, Setting
from video_processor import create_full_video, create_short_video

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ASSETS_FOLDER = os.path.join(UPLOAD_FOLDER, 'assets')
IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
OUTPUT_FULL_FOLDER = os.path.join(OUTPUT_FOLDER, 'full')
OUTPUT_SHORT_FOLDER = os.path.join(OUTPUT_FOLDER, 'short')

for p in [UPLOAD_FOLDER, ASSETS_FOLDER, IMAGES_FOLDER, OUTPUT_FOLDER, OUTPUT_FULL_FOLDER, OUTPUT_SHORT_FOLDER]:
    os.makedirs(p, exist_ok=True)

# ensure subfolders for assets
for at in ('music', 'bg_video'):
    os.makedirs(os.path.join(ASSETS_FOLDER, at), exist_ok=True)

ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg'}
ALLOWED_MUSIC_EXT = {'mp3', 'wav', 'm4a', 'aac'}
ALLOWED_VIDEO_EXT = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "app.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    # ensure counters exist
    for key in ('music_counter', 'bg_video_counter'):
        if not Setting.query.get(key):
            s = Setting(key=key, value='0')
            db.session.add(s)
    db.session.commit()

# In-memory job registry for live progress streaming
jobs = {}

def get_next_asset(asset_type):
    assets = Asset.query.filter_by(asset_type=asset_type).order_by(Asset.id).all()
    if not assets:
        return None
    key = f"{asset_type}_counter"
    setting = Setting.query.get(key)
    if not setting:
        setting = Setting(key=key, value='0')
        db.session.add(setting)
        db.session.commit()
    idx = int(setting.value) % len(assets)
    chosen = assets[idx]
    # increment
    setting.value = str((idx + 1) % len(assets))
    db.session.commit()
    return chosen

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/assets', methods=['GET'])
def api_assets():
    assets = Asset.query.order_by(Asset.asset_type, Asset.id).all()
    arr = [{
        'id': a.id,
        'filename': a.filename,
        'asset_type': a.asset_type,
        'original_name': a.original_name,
        'created_at': a.created_at.isoformat()
    } for a in assets]
    music_counter = Setting.query.get('music_counter').value
    bg_counter = Setting.query.get('bg_video_counter').value
    return jsonify({'assets': arr, 'counters': {'music_counter': music_counter, 'bg_counter': bg_counter}})

@app.route('/api/upload_asset', methods=['POST'])
def upload_asset():
    """
    POST fields:
      - asset_type: 'music' or 'bg_video'
      - file: the file
    """
    if 'file' not in request.files:
        return jsonify({'error': 'no file'}), 400
    f = request.files['file']
    asset_type = request.form.get('asset_type')
    if not f or f.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    if asset_type not in ('music', 'bg_video'):
        return jsonify({'error': 'invalid asset_type'}), 400

    ext = f.filename.rsplit('.', 1)[1].lower()
    allowed = ALLOWED_MUSIC_EXT if asset_type == 'music' else ALLOWED_VIDEO_EXT
    if ext not in allowed:
        return jsonify({'error': 'invalid file extension'}), 400

    filename = secure_filename(f"{uuid.uuid4().hex}_{f.filename}")
    dest_dir = os.path.join(ASSETS_FOLDER, asset_type)
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, filename)
    f.save(path)
    asset = Asset(filename=os.path.join(asset_type, filename), asset_type=asset_type, original_name=f.filename)
    db.session.add(asset)
    db.session.commit()
    return jsonify({'ok': True, 'asset_id': asset.id})

# 🔽 NEW ROUTE ADDED BELOW 🔽
@app.route('/api/upload_assets_zip', methods=['POST'])
def upload_assets_zip():
    """
    Accept a ZIP file containing both music and/or background videos.
    Automatically extracts and classifies files into:
      - uploads/assets/music/
      - uploads/assets/bg_video/
    Registers each in the database (Asset table).
    Returns a JSON summary of imported files.
    """
    if 'zip' not in request.files:
        return jsonify({'error': 'no zip file uploaded'}), 400
    f = request.files['zip']
    if f.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    if not f.filename.lower().endswith('.zip'):
        return jsonify({'error': 'only zip files allowed'}), 400

    # Create a temp extraction folder
    token = uuid.uuid4().hex
    temp_folder = os.path.join(UPLOAD_FOLDER, f"temp_assets_{token}")
    os.makedirs(temp_folder, exist_ok=True)
    zip_path = os.path.join(temp_folder, secure_filename(f.filename))
    f.save(zip_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_folder)
    except zipfile.BadZipFile:
        shutil.rmtree(temp_folder)
        return jsonify({'error': 'invalid zip file'}), 400

    added_music = []
    added_bg = []

    # Walk through extracted files
    for root, _, files in os.walk(temp_folder):
        for name in files:
            ext = name.rsplit('.', 1)[-1].lower()
            src_path = os.path.join(root, name)
            if ext in ALLOWED_MUSIC_EXT:
                asset_type = 'music'
                dest_dir = os.path.join(ASSETS_FOLDER, 'music')
            elif ext in ALLOWED_VIDEO_EXT:
                asset_type = 'bg_video'
                dest_dir = os.path.join(ASSETS_FOLDER, 'bg_video')
            else:
                continue  # skip non-media files

            os.makedirs(dest_dir, exist_ok=True)
            new_filename = secure_filename(f"{uuid.uuid4().hex}_{name}")
            dest_path = os.path.join(dest_dir, new_filename)
            shutil.move(src_path, dest_path)

            rel_path = os.path.join(asset_type, new_filename)
            asset = Asset(filename=rel_path, asset_type=asset_type, original_name=name)
            db.session.add(asset)

            if asset_type == 'music':
                added_music.append(name)
            else:
                added_bg.append(name)

    db.session.commit()
    shutil.rmtree(temp_folder, ignore_errors=True)

    return jsonify({
        'ok': True,
        'added': {
            'music_files': added_music,
            'bg_videos': added_bg
        },
        'summary': f"Added {len(added_music)} music files and {len(added_bg)} background videos."
    })
# 🔼 NEW ROUTE ENDS HERE 🔼

@app.route('/api/delete_asset/<int:asset_id>', methods=['DELETE'])
def delete_asset(asset_id):
    """
    Deletes the asset record and removes the file from disk.
    """
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({'error': 'asset not found'}), 404

    file_path = os.path.join(ASSETS_FOLDER, asset.filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        return jsonify({'error': f'failed removing file: {str(e)}'}), 500

    db.session.delete(asset)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/upload_images_zip', methods=['POST'])
def upload_images_zip():
    """
    Accept zip that contains images. Extract to unique folder and return folder name.
    """
    if 'zip' not in request.files:
        return jsonify({'error': 'no zip file'}), 400
    f = request.files['zip']
    if f.filename == '':
        return jsonify({'error': 'empty filename'}), 400
    if not f.filename.lower().endswith('.zip'):
        return jsonify({'error': 'only zip allowed'}), 400

    token = uuid.uuid4().hex
    folder = os.path.join(IMAGES_FOLDER, token)
    os.makedirs(folder, exist_ok=True)
    zip_path = os.path.join(folder, secure_filename(f.filename))
    f.save(zip_path)
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(folder)
    except zipfile.BadZipFile:
        shutil.rmtree(folder)
        return jsonify({'error': 'bad zip file'}), 400

    # count images and return path token
    images = [n for n in os.listdir(folder) if n.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return jsonify({'ok': True, 'token': token, 'image_count': len(images)})

@app.route('/api/create_video', methods=['POST'])
def create_video():
    """
    Single video creation (keeps compatibility).
    POST fields:
     - mode: 'full' or 'short'
     - images_token: token returned by upload_images_zip
     - music_id (optional) or auto_assign checkbox (default true)
     - bg_id (optional)
    """
    start_time = time.time()
    mode = request.form.get('mode')
    token = request.form.get('images_token')
    auto_assign = request.form.get('auto_assign', 'true').lower() == 'true'
    music_id = request.form.get('music_id')
    bg_id = request.form.get('bg_id')

    if mode not in ('full', 'short'):
        return jsonify({'error': 'invalid mode'}), 400

    images_folder = os.path.join(IMAGES_FOLDER, token) if token else None
    if not images_folder or not os.path.exists(images_folder):
        return jsonify({'error': 'images not found'}), 400

    # choose assets
    if music_id:
        music_asset = Asset.query.get(int(music_id))
    elif auto_assign:
        music_asset = get_next_asset('music')
    else:
        music_asset = None

    if bg_id:
        bg_asset = Asset.query.get(int(bg_id))
    elif auto_assign:
        bg_asset = get_next_asset('bg_video')
    else:
        bg_asset = None

    if not music_asset or not bg_asset:
        return jsonify({'error': 'music or background video not available; upload assets first'}), 400

    music_path = os.path.join(ASSETS_FOLDER, music_asset.filename)
    bg_path = os.path.join(ASSETS_FOLDER, bg_asset.filename)

    # prepare output filename
    out_name = f"{mode}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.mp4"
    out_path = os.path.join(OUTPUT_FULL_FOLDER if mode == 'full' else OUTPUT_SHORT_FOLDER, out_name)
    try:
        if mode == 'full':
            img_files = sorted([f for f in os.listdir(images_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            if len(img_files) != 15:
                return jsonify({'error': 'Full video requires exactly 15 images in the zip'}), 400
            create_full_video(images_folder, music_path, bg_path, out_path)
        else:
            img_files = sorted([os.path.join(images_folder, f) for f in os.listdir(images_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            if len(img_files) != 2:
                return jsonify({'error': 'Short video requires exactly 2 images in the zip'}), 400
            create_short_video(img_files, music_path, bg_path, out_path)
    except Exception as e:
        return jsonify({'error': f'video creation failed: {str(e)}'}), 500

    elapsed = round(time.time() - start_time, 2)

    notification.notify(
        title="Video Generation Complete",
        message=f"Your {mode} video has been created in {elapsed}s and is ready.",
        timeout=10
    )

    return jsonify({
        'ok': True,
        'output': out_name,
        'download_url': f'/outputs/{mode}/{out_name}',
        'elapsed_time': elapsed
    })

@app.route('/api/start_batch', methods=['POST'])
def start_batch():
    """
    Async batch: validates inputs, kicks off background thread, returns job_id immediately.
    """
    mode        = request.form.get('mode')
    token       = request.form.get('images_token')
    auto_assign = request.form.get('auto_assign', 'true').lower() == 'true'
    music_id    = request.form.get('music_id')
    bg_id       = request.form.get('bg_id')

    if mode not in ('full', 'short'):
        return jsonify({'error': 'invalid mode'}), 400
    if not token:
        return jsonify({'error': 'images_token missing'}), 400

    images_folder = os.path.join(IMAGES_FOLDER, token)
    if not os.path.exists(images_folder):
        return jsonify({'error': 'images folder not found'}), 400

    images = sorted([n for n in os.listdir(images_folder)
                     if n.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if not images:
        return jsonify({'error': 'no images found in uploaded folder'}), 400

    group_size = 15 if mode == 'full' else 2
    if len(images) % group_size != 0:
        return jsonify({'error': f'Number of images ({len(images)}) is not a multiple of {group_size} for mode {mode}'}), 400

    job_id  = uuid.uuid4().hex
    job_q   = queue_module.Queue()
    jobs[job_id] = {'queue': job_q, 'mode': mode, 'status': 'running'}

    t = threading.Thread(
        target=_run_batch_job,
        args=(job_id, mode, images_folder, images, group_size, auto_assign, music_id, bg_id, token),
        daemon=True
    )
    t.start()

    return jsonify({'ok': True, 'job_id': job_id, 'total': len(images) // group_size})


def _run_batch_job(job_id, mode, images_folder, images, group_size, auto_assign, music_id_str, bg_id_str, token):
    """Background thread: processes batch and pushes SSE events to job queue."""
    job   = jobs[job_id]
    q     = job['queue']
    start = time.time()
    num_videos = len(images) // group_size
    outputs    = []

    def push(event_type, **kwargs):
        q.put({'type': event_type, **kwargs})

    try:
        push('log', msg=f'🚀 Job started — {num_videos} video(s) queued')
        push('log', msg=f'📂 Mode: {mode.upper()} | Group size: {group_size} images')

        with app.app_context():
            for i in range(num_videos):
                video_start = time.time()
                chunk_names = images[i * group_size:(i + 1) * group_size]

                part_folder = os.path.join(images_folder, f"{token}_part_{i}")
                os.makedirs(part_folder, exist_ok=True)
                for idx, fname in enumerate(chunk_names):
                    shutil.copy2(
                        os.path.join(images_folder, fname),
                        os.path.join(part_folder, f"{idx:03d}_{fname}")
                    )

                push('log', msg=f'🎬 [{i+1}/{num_videos}] Selecting assets...')

                if not auto_assign and music_id_str:
                    music_asset = Asset.query.get(int(music_id_str))
                else:
                    music_asset = get_next_asset('music')

                if not auto_assign and bg_id_str:
                    bg_asset = Asset.query.get(int(bg_id_str))
                else:
                    bg_asset = get_next_asset('bg_video')

                if not music_asset or not bg_asset:
                    shutil.rmtree(part_folder, ignore_errors=True)
                    push('error', msg='Music or background asset missing — upload assets first')
                    return

                push('log', msg=f'🎵 Music: {music_asset.original_name}')
                push('log', msg=f'🖼️  Background: {bg_asset.original_name}')
                push('log', msg=f'⚙️  [{i+1}/{num_videos}] Rendering video...')

                music_path = os.path.join(ASSETS_FOLDER, music_asset.filename)
                bg_path    = os.path.join(ASSETS_FOLDER, bg_asset.filename)
                out_name   = f"{mode}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{i+1}_{uuid.uuid4().hex[:6]}.mp4"
                out_path   = os.path.join(OUTPUT_FULL_FOLDER if mode == 'full' else OUTPUT_SHORT_FOLDER, out_name)
                dl_url     = f'/outputs/{mode}/{out_name}'

                if mode == 'full':
                    create_full_video(part_folder, music_path, bg_path, out_path)
                else:
                    img_paths = sorted([
                        os.path.join(part_folder, f)
                        for f in os.listdir(part_folder)
                        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                    ])
                    create_short_video(img_paths, music_path, bg_path, out_path,
                                       duration=10, fps=30, target_size=(1080, 1920))

                shutil.rmtree(part_folder, ignore_errors=True)
                video_elapsed = round(time.time() - video_start, 2)

                push('log',       msg=f'✅ [{i+1}/{num_videos}] Done in {video_elapsed}s → {out_name}')
                push('video_done', filename=out_name, download_url=dl_url, elapsed=video_elapsed)
                outputs.append({'filename': out_name, 'download_url': dl_url})

        total_elapsed = round(time.time() - start, 2)
        push('log', msg=f'🎉 All {num_videos} video(s) complete! Total time: {total_elapsed}s')
        push('done', elapsed=total_elapsed, count=len(outputs), outputs=outputs)

        job['status'] = 'done'
        notification.notify(
            title='All Videos Ready',
            message=f'All {len(outputs)} {mode} videos created in {total_elapsed}s and are ready.',
            timeout=10
        )

    except Exception as e:
        push('log', msg=f'❌ Error: {str(e)}')
        push('error', msg=str(e))
        job['status'] = 'error'


@app.route('/api/job_stream/<job_id>')
def job_stream(job_id):
    """SSE endpoint — streams live progress events for a batch job."""
    def generate():
        if job_id not in jobs:
            yield f'data: {json.dumps({"type": "error", "msg": "Job not found"})}\n\n'
            return
        q = jobs[job_id]['queue']
        while True:
            try:
                msg = q.get(timeout=60)
                yield f'data: {json.dumps(msg)}\n\n'
                if msg.get('type') in ('done', 'error'):
                    break
            except queue_module.Empty:
                yield f'data: {json.dumps({"type": "ping"})}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@app.route('/api/docs')
def get_docs():
    """Reads README.md and returns it as text."""
    readme_path = os.path.join(BASE_DIR, 'README.md')
    content = ""
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    return jsonify({'ok': True, 'content': content})

@app.route('/outputs/<mode>/<path:filename>')
def outputs(mode, filename):
    folder = OUTPUT_FULL_FOLDER if mode == 'full' else OUTPUT_SHORT_FOLDER
    return send_from_directory(folder, filename, as_attachment=True)

@app.route('/uploads/assets/<path:subpath>')
def serve_asset(subpath):
    return send_from_directory(ASSETS_FOLDER, subpath, as_attachment=True)



if __name__ == '__main__':
    app.run(debug=True)
