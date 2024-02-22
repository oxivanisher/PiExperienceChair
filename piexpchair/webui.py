from piexpchair import PiExpChair

from flask import Flask, request

app = Flask(__name__)


class MCP23017Controller(PiExpChair):
    def __init__(self):
        super().__init__()

    # Routes for controlling OMXPlayer
    @app.route('/quit')
    def quit(self):
        self.send_quit()
        return "OK"

    @app.route('/play')
    def play(self):
        self.send_play()
        return "OK"

    @app.route('/stop')
    def stop(self):
        self.send_stop()
        return "OK"

    @app.route('/next')
    def next(self):
        self.send_next()
        return "OK"

    @app.route('/prev')
    def prev(self):
        self.send_prev()
        return "OK"

    # Routes for managing YAML configuration file
    @app.route('/config')
    def get_config(self):
        # Read YAML configuration file and return it as JSON
        # Example implementation:
        with open('config/config.yaml', 'r') as file:
            pass
        return None

    @app.route('/config', methods=['POST'])
    def update_config(self):
        # Update YAML configuration file based on POST request data
        # Example implementation:
        new_config = request.json
        with open('config/config.yaml', 'w') as file:
            pass
        return None


if __name__ == '__main__':
    app.run(debug=True)  # Set debug=True for development
