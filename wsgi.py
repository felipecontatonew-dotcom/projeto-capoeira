import os
from flask import Flask
from extensions import db, login_manager, socketio
from app import register_routes_and_events

# Cria a aplicação Flask
app = Flask(__name__)

# Configura a aplicação
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(base_dir, 'capoeira_palmares.db')
app.config['SECRET_KEY'] = 'sua-chave-secreta-incrivelmente-segura-2024'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa as extensões com o app
db.init_app(app)
login_manager.init_app(app)
socketio.init_app(app)

# Registra todas as rotas e eventos
register_routes_and_events(app)

# Cria o comando 'init-db' para o terminal
@app.cli.command("init-db")
def init_db_command():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@capoeira.com').first():
            from models import User # Importação local para evitar dependência circular
            admin = User(nome='Administrador', matricula='ADMIN001', email='admin@capoeira.com', role='admin', graduacao='Mestre')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Admin criado com sucesso!')
        print("Banco de dados inicializado.")

# O objeto 'application' é o que o Gunicorn vai procurar e executar
application = socketio

# Bloco para rodar localmente (executando 'python wsgi.py')
if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)