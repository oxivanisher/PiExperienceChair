from piexpchair import PiExpChair, check_config_for_webui, config_schema, read_config

import os
import signal
import time
import datetime


from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

# Load config.yaml content
with open('config/config.yaml', 'r') as file:
    config_content = file.read()


def shutdown_server():
    return os.kill(os.getpid(), signal.SIGINT)


# Main routes
@app.route('/')
def index():
    last_scenes = {}
    current_scene = "¯\_(ツ)_/¯"

    # try:
    config_content = read_config('config/config.yaml', pxc.logger, config_schema)
    extracted_scenes = []
    last_idle = 0.0
    last_scene_date = 0.0
    last_scene_index = 0
    for topic in pxc.last_messages.keys():
        print("topic", topic)

        if topic == "%s/videoplayer/scene" % pxc.mqtt_config['base_topic']:
            print("aa", pxc.last_messages[topic])
            for date in pxc.last_messages[topic]:
                extracted_scenes.append((date, pxc.last_messages[topic][date]))
        if topic == "%s/videoplayer/idle" % pxc.mqtt_config['base_topic']:
            for key, _ in pxc.last_messages[topic]:
                last_idle = key
                print("last idle", key)

    for date, scene_index in reversed(extracted_scenes):
        print("date/message", date, scene_index)
        last_scenes[date] = config_content['scenes'][int(scene_index)]['name']
        if date > last_scene_date:
            last_scene_date = date
            last_scene_index = int(scene_index)

    if last_idle > last_scene_date:
        current_scene = "Idle"
    elif last_idle == last_scene_date:
        pass
    else:
        current_scene = config_content['scenes'][last_scene_index]['name']

    print("last scenes", last_scenes)
    print("current scene", current_scene)

    # except Exception as e:
    #     pass

    return render_template('control.html', last_scenes=last_scenes, current_scene=current_scene)


@app.route('/status')
def status():
    return render_template('status.html',
                           config_content=read_config('config/config.yaml',
                           pxc.logger, config_schema),
                           mqtt_messages=pxc.last_messages)


@app.route('/config')
def config():
    result, message = check_config_for_webui()
    if result:
        alert_message = None
    else:
        alert_message = message
    return render_template('config.html', config_content=config_content, alert_message=alert_message)


# Routes for controlling PiExpChair
@app.route('/quit')
def quit():
    pxc.send_quit()
    shutdown_server()
    return redirect(url_for("index"))


@app.route('/play')
def play():
    pxc.send_play()
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


@app.route('/force_restart')
def force_restart():
    pxc.send_stop()
    with open("tmp/force_restart", "w") as text_file:
        text_file.write("Force restart requested %s" % time.time())
    return redirect(url_for("index"))


@app.route('/shutdown_computer')
def shutdown_computer():
    pxc.send_shutdown()
    with open("tmp/shutdown_computer", "w") as text_file:
        text_file.write("Force system shutdown from webui at %s" % time.time())
    return redirect(url_for("index"))


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
