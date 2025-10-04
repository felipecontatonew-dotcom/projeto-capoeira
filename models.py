# models.py (Versão Verificada)
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    matricula = db.Column(db.String(50), unique=True)
    nome = db.Column(db.String(150), nullable=False)
    idade = db.Column(db.Integer)
    data_entrada = db.Column(db.Date, default=datetime.utcnow)
    graduacao = db.Column(db.String(50))
    rg = db.Column(db.String(20))
    cpf = db.Column(db.String(20))
    contato = db.Column(db.String(20))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    etnia = db.Column(db.String(30))
    ativo = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), nullable=False, default='aluno')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    responsaveis = db.relationship('Responsavel', backref='aluno', lazy=True, cascade="all, delete-orphan")
    presencas = db.relationship('Presenca', backref='aluno', lazy=True, cascade="all, delete-orphan")
    
    mensagens_enviadas = db.relationship('Mensagem', foreign_keys='Mensagem.remetente_id', backref='autor', lazy=True)
    mensagens_recebidas = db.relationship('Mensagem', foreign_keys='Mensagem.destinatario_id', backref='destinatario', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Responsavel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    rg = db.Column(db.String(20))
    cpf = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    parentesco = db.Column(db.String(50))
    tipo = db.Column(db.Integer)

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_aula = db.Column(db.Date, nullable=False)
    aula = db.Column(db.String(100))
    status = db.Column(db.String(20), default='presente')

class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    remetente_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    conteudo = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    lida = db.Column(db.Boolean, default=False)

class Aula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_aula = db.Column(db.String(150), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)
    local = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), default='Aula')