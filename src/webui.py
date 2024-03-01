from piexpchair import PiExpChair

import os
import signal
import time

from flask import Flask, request, render_template

app = Flask(__name__)

# Load config.yaml content
with open('config/config.yaml', 'r') as file:
    config_content = file.read()


def shutdown_server():
    return os.kill(os.getpid(), signal.SIGINT)


# Routes for controlling PiExpChair
@app.route('/')
def index():
    return render_template('index.html', config_content=config_content)


@app.route('/quit')
def quit():
    pxc.send_quit()
    shutdown_server()
    return render_template('index.html', config_content=config_content)


@app.route('/play')
def play():
    pxc.send_play()
    return render_template('index.html', config_content=config_content)


@app.route('/stop')
def stop():
    pxc.send_stop()
    return render_template('index.html', config_content=config_content)


@app.route('/next')
def next():
    pxc.send_next()
    return render_template('index.html', config_content=config_content)


@app.route('/prev')
def prev():
    pxc.send_prev()
    return render_template('index.html', config_content=config_content)


@app.route('/force_restart')
def force_restart():
    with open("tmp/force_restart", "w") as text_file:
        text_file.write("Force restart requested %s" % time.time())
    return render_template('index.html', config_content=config_content)

# Routes for managing YAML configuration file
@app.route('/save_config', methods=['POST'])
def save_config():
    # Save modified config content
    new_config_content = request.form['config']
    with open('config/config.yaml', 'w') as file:
        file.write(new_config_content)
    # Call quit method
    return quit()


if __name__ == '__main__':
    pxc = PiExpChair()
    pxc.__init__()
    pxc.mqtt_client.loop_start()
    pxc.logger.info(f"Starting flask app in {app.root_path}")

    app.run(debug=True, host="0.0.0.0")
