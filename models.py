from database import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    vms = db.relationship('VM', backref='user', lazy=True)

class VM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    os = db.Column(db.String(50), nullable=False)
    cpu = db.Column(db.Integer, nullable=False)
    ram = db.Column(db.Integer, nullable=False)
    storage = db.Column(db.Integer, nullable=False)
    script = db.Column(db.Text, nullable=True)
    
    # Nouveaux champs ajoutés
    #iso_path = db.Column(db.String(500), nullable=True)  # Chemin vers l'ISO
    network_type = db.Column(db.String(20), default='nat')  # nat, bridged, hostonly, internal
    graphics_controller = db.Column(db.String(20), default='vmsvga')  # vboxsvga, vmsvga, vboxvga
    vram = db.Column(db.Integer, default=128)  # Mémoire vidéo en MB
    
    # Champs existants
    status = db.Column(db.String(20), default='creating')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)