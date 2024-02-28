from piexpchair import PiExpChair

from flask import Flask, request, render_template

app = Flask(__name__)

# Load config.yaml content
with open('config/config.yaml', 'r') as file:
    config_content = file.read()


# Routes for controlling PiExpChair
@app.route('/')
def index():
    return render_template('index.html', config_content=config_content)


@app.route('/quit')
def quit():
    return render_template('index.html', config_content=config_content)


@app.route('/play')
def play():
    piexpchair.send_play()
    return render_template('index.html', config_content=config_content)


@app.route('/stop')
def stop():
    piexpchair.send_stop()
    return render_template('index.html', config_content=config_content)


@app.route('/next')
def next():
    piexpchair.send_next()
    return render_template('index.html', config_content=config_content)


@app.route('/prev')
def prev():
    piexpchair.send_prev()
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
    piexpchair = PiExpChair()
    piexpchair.__init__()

    piexpchair.mqtt_client.loop_start()

    app.run(debug=True, host="0.0.0.0")
