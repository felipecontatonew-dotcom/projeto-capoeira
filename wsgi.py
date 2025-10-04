from app import create_app
from extensions import socketio

# Cria a aplicação usando a fábrica
app = create_app()

# O objeto 'application' é o que o Gunicorn vai procurar e executar
application = socketio

# Bloco para rodar localmente (python wsgi.py)
if __name__ == "__main__":
    socketio.run(app, debug=True)