from flask import Flask, render_template
import logging

from api.routes import api_bp


HOST = "0.0.0.0"
PORT = 80

# disable logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

app = Flask(__name__, template_folder='templates', static_folder='static')

# web client
@app.route('/')
def index():
    return render_template('index.html')

#app.register_blueprint(dkms_v1_bp, url_prefix='/service/v1')
app.register_blueprint(api_bp, url_prefix='/api')


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True, use_reloader=True)
