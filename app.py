# app.py
import os
import json
from functools import wraps
from flask import Flask, request, render_template, jsonify, abort
from dotenv import load_dotenv

# --- Carga .env ---
load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "") # Carga el env o si no encuentra en el env, usa cadena vacía
SECRET_KEY   = os.getenv("FLASK_SECRET", "change-me")
BIND_HOST    = os.getenv("BIND_HOST", "0.0.0.0")
BIND_PORT    = int(os.getenv("BIND_PORT", "5003"))

# Pines BCM de relé (lista de enteros)
RELAYS = [int(x) for x in os.getenv("RELAYS", "17,27,22,23").split(",") if x.strip()]

# --- GPIO ---
try:
    from gpiozero import LED
    RELAY_PINS = {pin: LED(pin) for pin in RELAYS}
    RELAY_ACTIVE_LOW = False  # ajusta según tu módulo
except Exception as e:
    RELAY_PINS = {}
    print(f"[WARN] GPIO no disponible: {e}")

# --- App ---
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# Estado en memoria para consulta rápida
relay_state = {pin: False for pin in RELAYS}  # False=OFF, True=ON

# --- Helpers ---
def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Token en cabecera "X-Access-Token" o en query ?token=
        token = request.headers.get("X-Access-Token") or request.args.get("token")
        if ACCESS_TOKEN and token != ACCESS_TOKEN:
            abort(401)
        return f(*args, **kwargs)
    return wrapper

def set_relay(pin: int, on: bool):
    if pin not in RELAY_PINS:
        relay_state[pin] = on
        return
    if RELAY_ACTIVE_LOW:
        RELAY_PINS[pin].off() if on else RELAY_PINS[pin].on()
    else:
        RELAY_PINS[pin].on() if on else RELAY_PINS[pin].off()
    relay_state[pin] = on

# --- Rutas Web ---
@app.route("/")
@require_token
def index():
    return render_template("index.html", pins=RELAYS, states=relay_state)

# --- API REST ---
@app.route("/api/relays", methods=["GET"])
@require_token
def api_list():
    return jsonify({
        "pins": RELAYS,
        "state": relay_state
    })

@app.route("/api/relay/<int:pin>/<action>", methods=["POST"])
@require_token
def api_toggle(pin, action):
    if pin not in RELAYS:
        return jsonify({"error": "Pin no admitido"}), 400
    if action not in ("on", "off", "toggle"):
        return jsonify({"error": "Acción inválida"}), 400

    if action == "toggle":
        desired = not relay_state[pin]
    else:
        desired = (action == "on")

    try:
        set_relay(pin, desired)
        return jsonify({"ok": True, "pin": pin, "state": relay_state[pin]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# --- Shutdown GPIO limpio ---
@app.route("/_shutdown", methods=["POST"])
def _shutdown():
    # sin token a propósito no exponer esto
    func = request.environ.get("werkzeug.server.shutdown")
    if func:
        func()
    return "Shutting down..."

# --- Main ---
if __name__ == "__main__":
    # Producción real la haremos con systemd; esto es para test local
    app.run(host=BIND_HOST, port=BIND_PORT, debug=False)
