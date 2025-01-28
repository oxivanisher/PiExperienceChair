from piexpchair import PiExpChair, check_config_for_webui, config_schema, read_config

import time
import datetime


from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)


# Main routes
@app.route('/')
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


# Routes for controlling PiExpChair
@app.route('/play')
def play():
    pxc.send_play()
    return redirect(url_for("index"))


@app.route('/play_single/<int:scene_index>')
def play_single(scene_index):
    pxc.mqtt_client.publish("%s/videoplayer/play_single" % pxc.mqtt_config['base_topic'], scene_index)
    return redirect(url_for("index"))


@app.route('/stop')
def stop():
    pxc.send_stop()
    return redirect(url_for("index"))


@app.route('/next')
def next():
    pxc.send_next()
    return redirect(url_for("index"))


@app.route('/prev')
def prev():
    pxc.send_prev()
    return redirect(url_for("index"))


@app.route('/quit')
def quit():
    pxc.send_quit()
    alert_message = "Please wait, all services (excluding WebUi and VLC) are being restarted."
    return render_template('wait.html', alert_message=alert_message)


@app.route('/force_restart')
def force_restart():
    pxc.send_stop()
    with open("tmp/force_restart", "w") as text_file:
        text_file.write("Force restart requested %s" % time.time())
    alert_message = "Please wait, all services (including WebUi and VLC) are being restarted."
    return render_template('wait.html', alert_message=alert_message)


@app.route('/reboot_computer')
def reboot_computer():
    pxc.send_reboot()
    with open("tmp/reboot_computer", "w") as text_file:
        text_file.write("Force system reboot from webui at %s" % time.time())
    alert_message = "Please wait, the computer is rebooting"
    return render_template('wait.html', alert_message=alert_message)


@app.route('/shutdown_computer')
def shutdown_computer():
    pxc.send_shutdown()
    with open("tmp/shutdown_computer", "w") as text_file:
        text_file.write("Force system shutdown from webui at %s" % time.time())
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


# Add this new route for the player interface
@app.route('/player')
def player():
    result, message = check_config_for_webui()
    if result:
        current_config_content = read_config('config/config.yaml', pxc.logger, config_schema)
        alert_message = None
    else:
        alert_message = message
        current_config_content = {}

    return render_template('player.html',
                           config_content=current_config_content)


# Add this route for getting the current scene state
@app.route('/get_current_scene')
def get_current_scene():
    current_scene = "Idle"
    scene_index = None

    if not hasattr(pxc, 'last_messages'):
        return jsonify({'scene': current_scene, 'scene_index': scene_index})

    last_idle = 0.0
    last_scene_date = 0.0
    last_scene_index = None

    for topic in pxc.last_messages:
        if topic == "%s/videoplayer/scene" % pxc.mqtt_config['base_topic']:
            for date in pxc.last_messages[topic]:
                if date > last_scene_date:
                    last_scene_date = date
                    last_scene_index = int(pxc.last_messages[topic][date])
        if topic == "%s/videoplayer/idle" % pxc.mqtt_config['base_topic']:
            for date in pxc.last_messages[topic]:
                if date > last_idle:
                    last_idle = date

    if last_idle > last_scene_date:
        current_scene = "Idle"
        scene_index = None
    else:
        current_config_content = read_config('config/config.yaml', pxc.logger, config_schema)
        current_scene = current_config_content['scenes'][last_scene_index]['name']
        scene_index = last_scene_index

    return jsonify({'scene': current_scene, 'scene_index': scene_index})

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