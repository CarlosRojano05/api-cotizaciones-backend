from flask import Flask
from flask_cors import CORS
from controllers.cliente_controllers import cliente_bp
from controllers.item_controllers import item_bp
from controllers.cotizacion_controllers import cotizacion_bp

app = Flask(__name__)
CORS(app)

# Se Registra el blueprint de los controllers
app.register_blueprint(cliente_bp)
app.register_blueprint(item_bp)
app.register_blueprint(cotizacion_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)