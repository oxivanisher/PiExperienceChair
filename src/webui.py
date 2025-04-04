
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, jsonify, Response, session
import os
from piexpchair import PiExpChair, check_config_for_webui, config_schema, read_config
import time
import datetime
import secrets

import logging

log_level = logging.INFO
if os.getenv('DEBUG', False):
    logging.getLogger('werkzeug').setLevel(logging.DEBUG)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Auth methods
def check_auth(username, password):
    """Check if the username and password match the config."""
    try:
        config = read_config('config/config.yaml', pxc.logger, config_schema)
        if 'webui' in config and 'user' in config['webui'] and 'password' in config['webui']:
            pxc.logger.debug(f"Config contains webui settings: user={config['webui']['user']}")  # Log the admin username (be careful with password logging)
            return username == config['webui']['user'] and password == config['webui']['password']
    except Exception as e:
        pxc.logger.error(f"Error checking authentication: {str(e)}")
    return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already authenticated, redirect to index
    if session.get('authenticated'):
        pxc.logger.info("User already authenticated, redirecting to index")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        pxc.logger.info(f"Login attempt for user: {username}")

        # Add debug logging for config reading
        try:
            config = read_config('config/config.yaml', pxc.logger, config_schema)
            if 'webui' in config:
                pxc.logger.debug("Found webui section in config")
                if 'user' in config['webui']:
                    pxc.logger.debug(f"Found admin user in config: {config['webui']['user']}")
                if 'password' in config['webui']:
                    pxc.logger.debug("Found password in config")
        except Exception as e:
            pxc.logger.error(f"Error reading config during login: {str(e)}")

        if check_auth(username, password):
            pxc.logger.info("Authentication successful")
            session['authenticated'] = True
            return redirect(request.args.get('next') or url_for('index'))
        else:
            pxc.logger.warning("Authentication failed")
    return render_template('login.html')

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # List of paths that don't require authentication
        public_paths = [
            '/player',
            '/get_current_scene',
            '/play_single',
            '/stop',
            '/play',
            '/static',
            '/login',  # Add login to public paths
        ]

        # Check if the current path starts with any of the public paths
        if any(request.path.startswith(path) for path in public_paths):
            return f(*args, **kwargs)

        if not session.get('authenticated'):
            return redirect(url_for('login', next=request.url))

        return f(*args, **kwargs)
    return decorated

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@requires_auth
def index():
    last_scenes = {}
    current_scene = "¯\\_(ツ)_/¯"

    result, message = check_config_for_webui()
    if result:
        current_config_content = read_config('config/config.yaml', pxc.logger, config_schema)
        alert_message = None
        extracted_scenes = []
        last_idle = 0.0
        last_scene_date = 0.0
        last_scene_index = 0
        for topic in pxc.last_messages.keys():
            if topic == "%s/videoplayer/scene" % pxc.mqtt_config['base_topic']:
                for date in pxc.last_messages[topic]:
                    extracted_scenes.append((date, pxc.last_messages[topic][date]))
            if topic == "%s/videoplayer/idle" % pxc.mqtt_config['base_topic']:
                for date in pxc.last_messages[topic]:
                    last_idle = date

        for date, scene_index in reversed(extracted_scenes):
            last_scenes[date] = current_config_content['scenes'][int(scene_index)]['name']
            if date > last_scene_date:
                last_scene_date = date
                last_scene_index = int(scene_index)

        if last_idle > last_scene_date:
            current_scene = "Idle"
        elif last_idle == last_scene_date:
            pass
        else:
            current_scene = current_config_content['scenes'][last_scene_index]['name']
    else:
        alert_message = message
        current_config_content = {}

    return render_template('control.html',
                           last_scenes=last_scenes,
                           current_scene=current_scene,
                           alert_message=alert_message,
                           config_content=current_config_content)

@app.route('/status')
@requires_auth
def status():
    result, message = check_config_for_webui()
    if result:
        alert_message = None
        current_config_content = read_config('config/config.yaml', pxc.logger, config_schema)
    else:
        alert_message = message
        current_config_content = {}

    return render_template('status.html',
                           config_content=current_config_content,
                           mqtt_messages=pxc.last_messages,
                           alert_message=alert_message)

@app.route('/config')
@requires_auth
def config():
    result, message = check_config_for_webui()
    if result:
        alert_message = None
    else:
        alert_message = message

    with open('config/config.yaml', 'r') as file:
        current_config_content = file.read()

    return render_template('config.html',
                           config_content=current_config_content,
                           alert_message=alert_message)

# Player routes (no auth required)
@app.route('/player')
def player():
    result, message = check_config_for_webui()
    if result:
        current_config_content = read_config('config/config.yaml', pxc.logger, config_schema)
        alert_message = None
    else:
        alert_message = message
        current_config_content = {}

    sorted_scenes = sorted(enumerate(current_config_content["scenes"]), key=lambda x: x[1]["webplayer_ordering"])
    return render_template('player.html',
                           sorted_scenes=sorted_scenes,
                           # config_content=current_config_content,
                           alert_message=alert_message)

@app.route('/play')
def play():
    try:
        pxc.logger.info("Starting play all")
        pxc.send_play()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'success'})
        return redirect(url_for("index"))
    except Exception as e:
        pxc.logger.error(f"Error starting play all: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': str(e)}), 500
        return redirect(url_for("index"))

@app.route('/play_single/<int:scene_index>')
def play_single(scene_index):
    try:
        pxc.logger.info(f"Playing single scene {scene_index}")
        pxc.send_play_single(scene_index)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'success', 'scene': scene_index})
        return redirect(url_for("index"))

    except Exception as e:
        pxc.logger.error(f"Error playing scene {scene_index}: {str(e)}")
        import traceback
        pxc.logger.error(f"Traceback: {traceback.format_exc()}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error','message': str(e)}), 500
        return redirect(url_for("index"))

@app.route('/stop')
def stop():
    try:
        pxc.logger.info("Stopping playback")
        pxc.send_stop()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'success'})
        return redirect(url_for("index"))
    except Exception as e:
        pxc.logger.error(f"Error stopping playback: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': str(e)}), 500
        return redirect(url_for("index"))

@app.route('/get_current_scene')
def get_current_scene():
    current_scene = "Idle"
    scene_index = None

    # First check if last_messages exists
    if not hasattr(pxc, 'last_messages'):
        return jsonify({'scene': current_scene, 'scene_index': scene_index})

    last_idle = 0.0
    last_scene_date = 0.0
    last_scene_index = None

    # Get MQTT topic base
    mqtt_base_topic = pxc.mqtt_config.get('base_topic', '')

    # Check scene messages
    scene_topic = f"{mqtt_base_topic}/videoplayer/scene"
    idle_topic = f"{mqtt_base_topic}/videoplayer/idle"

    # Get last scene info
    if scene_topic in pxc.last_messages:
        for date in pxc.last_messages[scene_topic]:
            if date > last_scene_date:
                last_scene_date = date
                last_scene_index = int(pxc.last_messages[scene_topic][date])

    # Get last idle info
    if idle_topic in pxc.last_messages:
        for date in pxc.last_messages[idle_topic]:
            if date > last_idle:
                last_idle = date

    # Determine current state
    if last_idle > last_scene_date:
        # System is idle
        current_scene = "Idle"
        scene_index = None
    elif last_scene_index is not None:
        try:
            # Try to get scene information
            current_config_content = read_config('config/config.yaml', pxc.logger, config_schema)
            if (current_config_content
                and 'scenes' in current_config_content
                and last_scene_index < len(current_config_content['scenes'])):
                current_scene = current_config_content['scenes'][last_scene_index]['name']
                scene_index = last_scene_index
            else:
                current_scene = f"Scene {last_scene_index}"
                scene_index = last_scene_index
        except Exception as e:
            pxc.logger.error(f"Error reading scene information: {str(e)}")
            current_scene = f"Scene {last_scene_index}"
            scene_index = last_scene_index

    return jsonify({'scene': current_scene, 'scene_index': scene_index})

@app.route('/next')
def next():
    pxc.send_next()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success'})
    return redirect(url_for("index"))


@app.route('/prev')
def prev():
    pxc.send_prev()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success'})
    return redirect(url_for("index"))

# Admin routs which require auth
@app.route('/quit')
@requires_auth
def quit():
    pxc.send_quit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'message': "Services are being restarted"})
    alert_message = "Please wait, all services excluding the webinterface and the videoplayer are being restarted."
    return render_template('wait.html', alert_message=alert_message)

@app.route('/force_restart')
@requires_auth
def force_restart():
    pxc.send_stop()
    with open("tmp/force_restart", "w") as text_file:
        text_file.write("Force restart requested %s" % time.time())
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'message': "All services are being restarted"})
    alert_message = "Please wait, all services including the webinterface and the videoplayer are being restarted."
    return render_template('wait.html', alert_message=alert_message)

@app.route('/reboot_computer')
@requires_auth
def reboot_computer():
    pxc.send_reboot()
    with open("tmp/reboot_computer", "w") as text_file:
        text_file.write("Force system reboot from webui at %s" % time.time())
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'message': "System is rebooting"})
    alert_message = "Please wait, the computer is rebooting"
    return render_template('wait.html', alert_message=alert_message)

@app.route('/shutdown_computer')
@requires_auth
def shutdown_computer():
    pxc.send_shutdown()
    with open("tmp/shutdown_computer", "w") as text_file:
        text_file.write("Force system shutdown from webui at %s" % time.time())
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'message': "System is shutting down"})
    alert_message = "The computer is shut down."
    return render_template('wait.html', alert_message=alert_message)

# Routes for managing YAML configuration file
@app.route('/save_config', methods=['POST'])
def save_config():
    # Save modified config content
    new_config_content = request.form['config']
    with open('config/config.yaml', 'w') as file:
        file.write(new_config_content)
    return redirect(url_for("index"))

# Filters
@app.template_filter('strftime')
def _filter_datetime(timestamp, format=None):
    if not format:
        format = '%Y-%m-%d %H:%M:%S'
    return datetime.datetime.fromtimestamp(timestamp).strftime(format)


if __name__ == '__main__':
    pxc = PiExpChair()
    pxc.__init__(subscribe_to_everything=True)
    pxc.mqtt_client.loop_start()
    pxc.logger.info(f"Starting flask app in {app.root_path}")
    app.run(debug=False, host="0.0.0.0")