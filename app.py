import os
from flask import Flask, render_template, request, redirect, url_for, flash
from extensions import db, login_manager, socketio
from models import User, Responsavel, Presenca, Mensagem, Aula
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from functools import wraps
from sqlalchemy import or_
from flask_socketio import join_room, leave_room, send, emit

def create_app():
    app = Flask(__name__)
    
    # --- CONFIGURAÇÃO DA APLICAÇÃO ---
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(base_dir, 'capoeira_palmares.db')
    app.config['SECRET_KEY'] = 'sua-chave-secreta-incrivelmente-segura-2024'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- INICIALIZAÇÃO DAS EXTENSÕES COM O APP ---
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    
    login_manager.login_view = 'login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != 'admin':
                flash('Acesso restrito a administradores.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.context_processor
    def inject_unread_count():
        if current_user.is_authenticated:
            count = Mensagem.query.filter_by(destinatario_id=current_user.id, lida=False).count()
            return dict(unread_messages=count)
        return dict(unread_messages=0)

    # --- REGISTRO DE ROTAS E EVENTOS ---
    with app.app_context():
        
        # --- ROTAS HTTP ---
        @app.route('/', methods=['GET', 'POST'])
        def login():
            # ... (código da rota)
            pass # Mantenha o código completo da sua rota aqui
        
        # ... (COLE AQUI TODAS AS SUAS OUTRAS ROTAS @app.route) ...

        # --- EVENTOS DE SOCKET.IO ---
        @socketio.on('join')
        def on_join(data):
            join_room(data['room'])
        
        # ... (COLE AQUI TODOS OS SEUS OUTROS EVENTOS @socketio.on) ...

        # --- COMANDO CLI ---
        @app.cli.command("init-db")
        def init_db_command():
            db.create_all()
            if not User.query.filter_by(email='admin@capoeira.com').first():
                admin = User(nome='Administrador', matricula='ADMIN001', email='admin@capoeira.com', role='admin', graduacao='Mestre')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print('Admin criado com sucesso!')
            print("Banco de dados inicializado.")
            
    return app

# (Note que não há mais o if __name__ == '__main__' aqui)