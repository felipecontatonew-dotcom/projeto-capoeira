import os
from flask import Flask, render_template, request, redirect, url_for, flash
from extensions import db, login_manager
from models import User, Responsavel, Presenca, Mensagem, Aula
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from functools import wraps
from sqlalchemy import or_
from flask_socketio import SocketIO, join_room, leave_room, send, emit

# --- CONFIGURAÇÃO DA APLICAÇÃO ---
app = Flask(__name__)
base_dir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(base_dir, 'capoeira_palmares.db')
app.config['SECRET_KEY'] = 'sua-chave-secreta-incrivelmente-segura-2024'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SocketIO com o app
socketio = SocketIO(app)

# Inicializa as outras extensões com o app original do Flask
db.init_app(app)
login_manager.init_app(app)
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

# --- ROTA DE DEBUG PARA CRIAR O BANCO DE DADOS EM PRODUÇÃO ---
@app.route('/debug-criar-banco/secreto-9876')
def init_db_route_debug():
    try:
        with app.app_context():
            # Este comando cria as tabelas se elas não existirem. É mais seguro.
            db.create_all()

            # Verifica se o admin já existe, se não, cria ele.
            if not User.query.filter_by(email='admin@capoeira.com').first():
                admin = User(nome='Administrador', matricula='ADMIN001', email='admin@capoeira.com', role='admin', graduacao='Mestre')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                return "SUCESSO: Tabelas e usuário admin foram criados!"
            else:
                return "AVISO: As tabelas já existiam. O usuário admin já está cadastrado."
    except Exception as e:
        # Retorna o erro exato para a tela do navegador para podermos ver o que aconteceu.
        return f"ERRO AO INICIALIZAR O BANCO: {str(e)}"
        
# --- ROTAS DE AUTENTICAÇÃO E GERAIS ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard') if current_user.role == 'admin' else url_for('aluno_dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_password(request.form.get('senha')):
            if not user.ativo:
                flash('Sua conta está inativa.', 'danger')
                return redirect(url_for('login'))
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                if request.form.get('senha') == '123':
                    flash('Por favor, altere sua senha inicial.', 'warning')
                    return redirect(url_for('trocar_senha'))
                return redirect(url_for('aluno_dashboard'))
        else:
            flash('E-mail ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'success')
    return redirect(url_for('login'))

@app.route('/trocar_senha', methods=['GET', 'POST'])
@login_required
def trocar_senha():
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        if not nova_senha or len(nova_senha) < 5:
            flash('A senha deve ter no mínimo 5 caracteres.', 'danger')
        else:
            current_user.set_password(nova_senha)
            db.session.commit()
            flash('Senha alterada com sucesso! Faça login novamente.', 'success')
            logout_user()
            return redirect(url_for('login'))
    return render_template('trocar_senha.html')

@app.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        flash(f'Se o e-mail "{request.form.get("email")}" estiver cadastrado, um link será enviado.', 'info')
        return redirect(url_for('login'))
    return render_template('esqueci_senha.html')

# --- ROTAS DO PAINEL DE ADMIN ---
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    total_alunos = User.query.filter_by(role='aluno', ativo=True).count()
    alunos_inativos = User.query.filter_by(role='aluno', ativo=False).count()
    alunos_recentes = User.query.filter_by(role='aluno').order_by(User.created_at.desc()).limit(5).all()
    mensagens = Mensagem.query.order_by(Mensagem.timestamp.desc()).limit(5).all()
    return render_template('admin.html', total_alunos=total_alunos, alunos_inativos=alunos_inativos, alunos_recentes=alunos_recentes, mensagens=mensagens)

@app.route('/gerenciar_aulas', methods=['GET', 'POST'])
@login_required
@admin_required
def gerenciar_aulas():
    if request.method == 'POST':
        nova_aula = Aula(nome_aula=request.form.get('nome_aula'), data_hora=datetime.fromisoformat(request.form.get('data_hora')), local=request.form.get('local'), tipo=request.form.get('tipo'))
        db.session.add(nova_aula)
        db.session.commit()
        flash(f'{nova_aula.tipo} cadastrado com sucesso!', 'success')
        return redirect(url_for('gerenciar_aulas'))
    aulas_futuras = Aula.query.filter(Aula.data_hora >= datetime.now()).order_by(Aula.data_hora.asc()).all()
    return render_template('aulas_admin.html', aulas=aulas_futuras)

@app.route('/deletar_aula/<int:aula_id>', methods=['POST'])
@login_required
@admin_required
def deletar_aula(aula_id):
    aula = Aula.query.get_or_404(aula_id)
    db.session.delete(aula)
    db.session.commit()
    flash('Aula/Evento deletado com sucesso!', 'success')
    return redirect(url_for('gerenciar_aulas'))

@app.route('/cadastro', methods=['GET', 'POST'])
@login_required
@admin_required
def cadastro_aluno():
    if request.method == 'POST':
        form = request.form
        matricula_auto = datetime.now().strftime('%Y%m%d%H%M%S')
        if User.query.filter(User.email == form['emailAluno']).first():
            flash('Este e-mail já foi cadastrado.', 'danger')
            return redirect(url_for('cadastro_aluno'))
        new_user = User(matricula=matricula_auto, nome=form['nomeAluno'], idade=int(form['idadeAluno']), etnia=form['etnia'], cpf=form['cpfAluno'], email=form['emailAluno'], data_entrada=datetime.strptime(form['dataEntrada'], '%Y-%m-%d').date(), graduacao=form['graduacaoAluno'], rg=form.get('rgAluno'), contato=form.get('contatoAluno'), role='admin' if form.get('tipo_usuario') == 'adm' else 'aluno')
        new_user.set_password(form['senhaAluno'])
        db.session.add(new_user)
        db.session.flush()
        if new_user.idade < 18 and form.get('nomeResp1'):
            db.session.add(Responsavel(aluno_id=new_user.id, nome=form['nomeResp1'], cpf=form.get('cpfResp1'), parentesco=form.get('parentescoResp1')))
        db.session.commit()
        flash(f'Usuário cadastrado com sucesso! Matrícula: {matricula_auto}', 'success')
        return redirect(url_for('cadastro_aluno'))
    return render_template('cadastro_aluno.html', data_atual=datetime.now().strftime('%Y-%m-%d'))

@app.route('/consultar')
@login_required
@admin_required
def consultar_alunos():
    query = request.args.get('busca', '')
    base_query = User.query.filter_by(role='aluno')
    if query:
        search_term = f'%{query}%'
        base_query = base_query.filter(or_(User.nome.like(search_term), User.matricula.like(search_term)))
    alunos = base_query.order_by(User.nome).all()
    return render_template('consultar_alunos.html', alunos=alunos)

@app.route('/ficha_aluno/<int:aluno_id>')
@login_required
@admin_required
def ficha_aluno(aluno_id):
    aluno = User.query.get_or_404(aluno_id)
    resp1 = Responsavel.query.filter_by(aluno_id=aluno.id).first()
    return render_template('ficha_aluno.html', aluno=aluno, resp1=resp1)

@app.route('/atualizar_status_aluno', methods=['POST'])
@login_required
@admin_required
def atualizar_status_aluno():
    aluno = User.query.get_or_404(request.form.get('aluno_id'))
    aluno.ativo = (request.form.get('status') == 'ativo')
    db.session.commit()
    flash('Status do aluno atualizado.', 'success')
    return redirect(url_for('consultar_alunos'))

@app.route('/deletar_aluno/<int:aluno_id>', methods=['POST'])
@login_required
@admin_required
def deletar_aluno(aluno_id):
    aluno = User.query.get_or_404(aluno_id)
    db.session.delete(aluno)
    db.session.commit()
    flash(f'Aluno "{aluno.nome}" excluído com sucesso!', 'success')
    return redirect(url_for('consultar_alunos'))

@app.route('/graduacao', methods=['GET', 'POST'])
@login_required
@admin_required
def graduacao():
    if request.method == 'POST':
        aluno = User.query.get_or_404(request.form.get('aluno_id'))
        aluno.graduacao = request.form.get('graduacao')
        db.session.commit()
        flash('Graduação atualizada com sucesso!', 'success')
        return redirect(url_for('graduacao'))
    alunos = User.query.filter_by(role='aluno').order_by(User.nome).all()
    return render_template('graduacao.html', alunos=alunos)

@app.route('/presenca', methods=['GET', 'POST'])
@login_required
@admin_required
def presenca():
    if request.method == 'POST':
        nova_presenca = Presenca(aluno_id=request.form['aluno_id'], data_aula=datetime.strptime(request.form['data_aula'], '%Y-%m-%d').date(), aula=request.form['aula'], status=request.form['status'])
        db.session.add(nova_presenca)
        db.session.commit()
        flash('Presença registrada com sucesso!', 'success')
        return redirect(url_for('presenca'))
    alunos = User.query.filter_by(role='aluno', ativo=True).order_by(User.nome).all()
    presencas = db.session.query(Presenca, User.nome).join(User, Presenca.aluno_id == User.id).order_by(Presenca.data_aula.desc()).limit(50).all()
    return render_template('presenca.html', alunos=alunos, presencas=presencas, data_hoje=datetime.now().strftime('%Y-%m-%d'))

@app.route('/mensagens')
@login_required
@admin_required
def mensagens():
    alunos = User.query.filter_by(role='aluno').order_by(User.nome).all()
    return render_template('mensagens_admin.html', alunos=alunos)

@app.route('/usuarios')
@login_required
@admin_required
def usuarios():
    users = User.query.order_by(User.nome).all()
    return render_template('usuarios.html', usuarios=users)

@app.route('/resetar_senha', methods=['POST'])
@login_required
@admin_required
def resetar_senha():
    user = User.query.get_or_404(request.form.get('user_id'))
    user.set_password("capoeira123")
    db.session.commit()
    flash(f'Senha de {user.nome} resetada para "capoeira123".', 'success')
    return redirect(url_for('usuarios'))

# --- ROTAS DE CHAT E ALUNO ---
@app.route('/chat/<int:destinatario_id>')
@login_required
def chat(destinatario_id):
    destinatario = User.query.get_or_404(destinatario_id)
    if current_user.role == 'aluno' and destinatario.role != 'admin':
        flash('Alunos só podem conversar com administradores.', 'danger')
        return redirect(url_for('aluno_dashboard'))
    
    Mensagem.query.filter_by(remetente_id=destinatario.id, destinatario_id=current_user.id, lida=False).update({'lida': True})
    db.session.commit()

    room_name = f"chat_{min(current_user.id, destinatario.id)}_{max(current_user.id, destinatario.id)}"
    mensagens = Mensagem.query.filter(or_((Mensagem.remetente_id == current_user.id) & (Mensagem.destinatario_id == destinatario.id), (Mensagem.remetente_id == destinatario.id) & (Mensagem.destinatario_id == current_user.id))).order_by(Mensagem.timestamp.asc()).all()
    return render_template('chat.html', mensagens=mensagens, destinatario=destinatario, room=room_name)

@app.route('/aluno/dashboard')
@login_required
def aluno_dashboard():
    if current_user.role != 'aluno': return redirect(url_for('login'))
    admins = User.query.filter_by(role='admin').all()
    mensagens = Mensagem.query.filter(or_(Mensagem.destinatario_id == None, Mensagem.destinatario_id == current_user.id, Mensagem.remetente_id == current_user.id)).order_by(Mensagem.timestamp.desc()).limit(10).all()
    presencas = Presenca.query.filter_by(aluno_id=current_user.id).order_by(Presenca.data_aula.desc()).limit(10).all()
    aulas_futuras = Aula.query.filter(Aula.data_hora >= datetime.now()).order_by(Aula.data_hora.asc()).limit(5).all()
    return render_template('aluno.html', aluno=current_user, presencas=presencas, mensagens=mensagens, aulas=aulas_futuras, admins=admins)

# --- EVENTOS DE SOCKET.IO ---
@socketio.on('join')
def on_join(data):
    join_room(data['room'])

@socketio.on('send_message')
def handle_send_message(json_data):
    nova_mensagem = Mensagem(remetente_id=current_user.id, destinatario_id=json_data['destinatario_id'], conteudo=json_data['conteudo'], lida=False)
    db.session.add(nova_mensagem)
    db.session.commit()
    dados_para_emitir = {'id': nova_mensagem.id, 'conteudo': nova_mensagem.conteudo, 'remetente_id': nova_mensagem.remetente_id, 'timestamp': nova_mensagem.timestamp.strftime('%H:%M')}
    emit('receive_message', dados_para_emitir, to=json_data['room'])
    emit('new_message_notification', {'remetente_nome': current_user.nome}, to=f"user_{json_data['destinatario_id']}")

@socketio.on('delete_message')
def handle_delete_message(json_data):
    msg = Mensagem.query.get(json_data['message_id'])
    if msg and (current_user.role == 'admin' or msg.remetente_id == current_user.id):
        db.session.delete(msg)
        db.session.commit()
        emit('message_deleted', {'message_id': json_data['message_id']}, to=json_data['room'])

@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")

# --- COMANDO E EXECUÇÃO ---
@app.cli.command("init-db")
def init_db_command():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@capoeira.com').first():
            admin = User(nome='Administrador', matricula='ADMIN001', email='admin@capoeira.com', role='admin', graduacao='Mestre')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Admin criado com sucesso!')
        print("Banco de dados inicializado.")

if __name__ == '__main__':
    socketio.run(app, debug=True)