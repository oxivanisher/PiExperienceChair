from piexpchair import PiExpChair, check_config_for_webui

import os
import signal
import time

from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

# Load config.yaml content
with open('config/config.yaml', 'r') as file:
    config_content = file.read()


def shutdown_server():
    return os.kill(os.getpid(), signal.SIGINT)


# Routes for controlling PiExpChair
@app.route('/')
def index():
    result, message = check_config_for_webui()
    if result:
        alert_message = None
    else:
        alert_message = message
    return render_template('index.html', config_content=config_content, alert_message=alert_message)


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
    with open("tmp/force_restart", "w") as text_file:
        text_file.write("Force restart requested %s" % time.time())
    return redirect(url_for("index"))

@app.route('/shutdown_computer')
def shutdown_computer():
    with open("tmp/shutdown_computer", "w") as text_file:
        text_file.write("Force system shutdown at %s" % time.time())
    return redirect(url_for("index"))

# Routes for managing YAML configuration file
@app.route('/save_config', methods=['POST'])
def save_config():
    # Save modified config content
    new_config_content = request.form['config']
    with open('config/config.yaml', 'w') as file:
        file.write(new_config_content)
    return redirect(url_for("index"))


if __name__ == '__main__':
    pxc = PiExpChair()
    pxc.__init__()
    pxc.mqtt_client.loop_start()
    pxc.logger.info(f"Starting flask app in {app.root_path}")

    app.run(debug=False, host="0.0.0.0")
