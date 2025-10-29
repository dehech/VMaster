from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
#from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from database import db
from models import User, VM
import subprocess
import sys
#from app import app

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # à changer pour la production

# Configuration base de données SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

#db = SQLAlchemy(app)
'''
# ------------------ Modèle utilisateur ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
# ------------------ Modèle Machine Virtuelle ------------------
class VM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    os = db.Column(db.String(50), nullable=False)
    cpu = db.Column(db.Integer, nullable=False)
    ram = db.Column(db.Integer, nullable=False)  # en Go
    storage = db.Column(db.Integer, nullable=False)  # en Go
    script = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='creating')  # creating, running, stopped
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('vms', lazy=True))
'''
# Crée la base si elle n'existe pas
with app.app_context():
    db.create_all()

# ------------------ Routes ------------------

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            #flash('Connexion réussie ✅')
            return redirect(url_for('home'))
        else:
            flash('Nom d’utilisateur ou mot de passe incorrect ❌')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Ce nom d’utilisateur existe déjà ⚠️')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Compte créé avec succès ✅ Connecte-toi maintenant.')
        return redirect(url_for('login'))
        # ✅ Connecter automatiquement après inscription
        #session['user_id'] = new_user.id
        #session['username'] = new_user.username

    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        db.session.commit()
        flash('Profil mis à jour ✅')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/vms')
def my_vms():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    vms = VM.query.filter_by(user_id=session['user_id']).all()
    return render_template('vms.html', vms=vms)


@app.route('/vms/<int:vm_id>/start', methods=['POST'])
def start_vm(vm_id):
    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        flash("Action non autorisée ❌")
        return redirect(url_for('my_vms'))

    try:
        subprocess.Popen([sys.executable, "creator.py", "start", vm.name])
        vm.status = 'running'
        db.session.commit()
        flash(f"✅ La machine {vm.name} est en cours de démarrage.", "success")
    except Exception as e:
        flash(f"⚠️ Erreur lors du démarrage : {e}", "danger")

    return redirect(request.referrer or url_for('my_vms'))

# Route : Stopper une VM
@app.route('/vms/<int:vm_id>/stop', methods=['POST'])
def stop_vm(vm_id):
    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        flash("Action non autorisée ❌")
        return redirect(url_for('my_vms'))

    try:
        subprocess.Popen([sys.executable, "creator.py", "stop", vm.name])
        vm.status = 'stopped'
        db.session.commit()
        flash(f"🛑 La machine {vm.name} est en cours d'arrêt.", "success")
    except Exception as e:
        flash(f"⚠️ Erreur lors de l'arrêt : {e}", "danger")

    return redirect(request.referrer or url_for('my_vms'))

# Route : Supprimer une VM
@app.route('/vms/<int:vm_id>/delete', methods=['POST'])
def delete_vm(vm_id):
    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        flash("Action non autorisée ❌")
        return redirect(url_for('my_vms'))

    try:
        subprocess.Popen([sys.executable, "creator.py", "delete", vm.name])
        db.session.delete(vm)
        db.session.commit()
        flash(f"🗑 La machine {vm.name} est en cours de suppression.", "success")
    except Exception as e:
        flash(f"⚠️ Erreur lors de la suppression : {e}", "danger")

    return redirect(url_for('my_vms'))

# Route : Détails d'une VM
@app.route('/vms/<int:vm_id>')
def vm_details(vm_id):
    if 'user_id' not in session:
        flash("Veuillez vous connecter.", "warning")
        return redirect(url_for('login'))

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        flash("Accès non autorisé ❌")
        return redirect(url_for('my_vms'))

    return render_template('vm_details.html', vm=vm)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    #flash('Déconnexion réussie 👋')
    return redirect(url_for('login'))

# ------------------ Route création de VM (simulation pour le moment) ------------------

@app.route('/create', methods=['GET', 'POST'])
def create_vm():
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour créer une machine virtuelle.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Champs obligatoires
            name = request.form['name']
            os_type = request.form['os']  # Changé 'os' en 'os_type' pour éviter conflit
            cpu = request.form['cpu']
            ram = request.form['ram']
            storage = request.form['storage']
            
            # Nouveaux champs optionnels
            script = request.form.get('script', '')
            network_type = request.form.get('network_type', 'nat')
            graphics_controller = request.form.get('graphics_controller', 'vmsvga')
            vram = request.form.get('vram', '128')

            # ✅ Validation des champs obligatoires
            if not all([name, os_type, cpu, ram, storage]):
                flash("Tous les champs marqués comme obligatoires sont requis ⚠️", "error")
                return redirect(url_for('create_vm'))

            # ✅ Validation numérique
            try:
                cpu_int = int(cpu)
                ram_int = int(ram)
                storage_int = int(storage)
                vram_int = int(vram)
                
                if not (1 <= cpu_int <= 32):
                    flash("Le nombre de CPU doit être entre 1 et 32 ⚠️", "error")
                    return redirect(url_for('create_vm'))
                    
                if not (1 <= ram_int <= 128):
                    flash("La RAM doit être entre 1 et 128 Go ⚠️", "error")
                    return redirect(url_for('create_vm'))
                    
                if not (10 <= storage_int <= 1000):
                    flash("Le stockage doit être entre 10 et 1000 Go ⚠️", "error")
                    return redirect(url_for('create_vm'))
                    
                if not (16 <= vram_int <= 256):
                    flash("La mémoire vidéo doit être entre 16 et 256 MB ⚠️", "error")
                    return redirect(url_for('create_vm'))
                    
            except ValueError:
                flash("Veuillez entrer des valeurs numériques valides ⚠️", "error")
                return redirect(url_for('create_vm'))

            # ✅ Validation du nom
            import re
            if not re.match(r'^[a-zA-Z0-9-_ ]+$', name):
                flash("Le nom de la VM ne peut contenir que des lettres, chiffres, espaces, tirets et underscores ⚠️", "error")
                return redirect(url_for('create_vm'))
            
            # ✅ Déterminer automatiquement le chemin ISO selon l'OS
            iso_paths = {
                'ubuntu': r'D:\programs\ubuntu-22.04.4-desktop-amd64.iso',
                'windows': r'D:\programs\win_server_release_amd64fre_SERVER_LOF_PACKAGES_OEM.iso',
                'windows10': r'D:\programs\Win10_21H2_French_x64.iso',
                'windows11': r'D:\programs\Win11_22H2_EnglishInternational_x64v2.iso'
            }
            
            iso_path = iso_paths.get(os_type)  # Utiliser os_type ici
            import os
            # Vérifier si le fichier ISO existe
            if iso_path:
                if os.path.exists(iso_path):
                    print(f"✓ ISO trouvé: {iso_path}")
                else:
                    print(f"⚠️ ISO non trouvé: {iso_path}")
                    flash(f"⚠️ Le fichier ISO pour {os_type} n'a pas été trouvé: {iso_path}", "warning")
                    iso_path = None  # Continuer sans ISO
            else:
                print(f"ℹ️ Aucun ISO automatique pour: {os_type}")

            # ✅ Création de la VM avec tous les champs
            new_vm = VM(
                user_id=session['user_id'],
                name=name,
                os=os_type,  # Utiliser os_type ici
                cpu=cpu_int,
                ram=ram_int,
                storage=storage_int,
                script=script,
                network_type=network_type,
                graphics_controller=graphics_controller,
                vram=vram_int,
                status='creating'
            )
            
            db.session.add(new_vm)
            db.session.commit()
            vm_id = new_vm.id

            # ✅ Appel du script Python pour créer la VM
            try:
                command = [
                    sys.executable,
                    "creator.py",  # Corrigé: "creator.py" → "vm_creator.py"
                    "create",
                    name,
                    os_type,  # Utiliser os_type ici
                    str(cpu_int),
                    str(ram_int),
                    str(storage_int),
                    iso_path if iso_path else "",
                    network_type,
                    graphics_controller,
                    str(vram_int),
                    str(vm_id)# - le script ne l'utilise pas
                ]

                # Nettoyer les arguments vides
                command = [arg for arg in command if arg != ""]
                
                # Lancer le script en arrière-plan
                subprocess.Popen(command)
                
                if iso_path:
                    flash(f"✅ Votre machine virtuelle {os_type} est en cours de création avec l'ISO automatique...", "success")
                else:
                    flash(f"✅ Votre machine virtuelle {os_type} est en cours de création (sans ISO)...", "success")
                
                print(f"🚀 Lancement création VM: {name} (ID: {vm_id})")
                print(f"📋 Configuration: {os_type}, {cpu_int} CPU, {ram_int} Go RAM, {storage_int} Go stockage")
                if iso_path:
                    print(f"📀 ISO: {iso_path}")

            except Exception as e:
                # En cas d'erreur, mettre à jour le statut
                new_vm.status = 'error'
                db.session.commit()
                flash(f"❌ Erreur lors du lancement du script: {e}", "danger")
                print(f"❌ Erreur script VM: {e}")

            return redirect('/vms')

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur lors de la création: {e}", "danger")
            print(f"❌ Erreur création VM: {e}")
            return redirect(url_for('create_vm'))

    # Méthode GET - Afficher le formulaire
    return render_template('create.html')

# --------------- Dashboard ----------------------------------------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# -----------------------------VNC----------------------------------------------
@app.route('/api/vms/<int:vm_id>/vnc-info')
def get_vnc_info(vm_id):
    """Retourne les informations de connexion VNC pour la VM"""
    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        # Configuration VNC (à adapter selon votre setup)
        # Ces valeurs peuvent venir de la base de données ou d'un fichier de config
        vnc_config = {
            'host': 'localhost',          # Votre serveur VNC/Websockify
            'port': 6080,                 # Port du proxy Websockify
            'password': 'vmaster123',     # Mot de passe VNC
            'success': True
        }
        
        return jsonify(vnc_config)
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erreur: {str(e)}'
        })

# ✅ NOUVELLE ROUTE : Informations de connexion SSH
@app.route('/api/vms/<int:vm_id>/ssh-info')
def get_ssh_info(vm_id):
    """Retourne les informations de connexion SSH pour la VM"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'})

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        # ✅ DÉTERMINER LE NOM D'UTILISATEUR SELON L'OS
        os_username_map = {
            'ubuntu': 'ubuntu',
            'debian': 'debian',
            'centos': 'centos',
            'fedora': 'fedora',
            'archlinux': 'arch',
            'opensuse': 'opensuse',
            'gentoo': 'gentoo',
            'linux': 'linux',
            'windows': 'administrator',  # Pour Windows via SSH
            'windows10': 'administrator',
            'windows11': 'administrator',
            'freebsd': 'freebsd',
            'solaris': 'solaris',
            'oracle': 'oracle'
        }
        
        # Utilisateur par défaut basé sur l'OS
        username = os_username_map.get(vm.os.lower(), 'user')
        
        # ✅ GÉNÉRER L'ID DE LA VM POUR LE PORT SSH
        def get_vm_id(vm_name):
            return abs(hash(vm_name)) % 100 + 10  # ID entre 10 et 109
        
        vm_id_number = get_vm_id(vm.name)
        base_ssh_port = 2200
        ssh_port = base_ssh_port + vm_id_number
        
        # ✅ INFORMATIONS DE CONNEXION SSH
        ssh_config = {
            'success': True,
            'vm_name': vm.name,
            'os': vm.os,
            'username': username,
            'password': '123456',  # Mot de passe fixe
            'host': '127.0.0.1',
            'port': ssh_port,
            'vm_ip': '10.0.2.15',  # IP fixe pour NAT VirtualBox
            'vm_id': vm_id_number,
            'base_port': base_ssh_port,
            'command': f'ssh {username}@127.0.0.1 -p {ssh_port}',
            'status': vm.status
        }
        
        return jsonify(ssh_config)
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erreur: {str(e)}'
        })

# ✅ NOUVELLE ROUTE : Test de connexion SSH
@app.route('/api/vms/<int:vm_id>/test-ssh')
def test_ssh_connection(vm_id):
    """Teste la connexion SSH à la VM"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'})

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        import paramiko
        import socket
        
        # Récupérer les infos SSH
        ssh_info_response = get_ssh_info(vm_id)
        ssh_info = ssh_info_response.get_json()
        
        if not ssh_info['success']:
            return jsonify({'success': False, 'message': 'Impossible de récupérer les infos SSH'})
        
        # Tester la connexion SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=ssh_info['host'],
                port=ssh_info['port'],
                username=ssh_info['username'],
                password=ssh_info['password'],
                timeout=10
            )
            
            # Exécuter une commande simple pour vérifier
            stdin, stdout, stderr = ssh.exec_command('whoami')
            user_output = stdout.read().decode().strip()
            
            ssh.close()
            
            return jsonify({
                'success': True,
                'message': f'Connexion SSH réussie! Utilisateur: {user_output}',
                'user': user_output
            })
            
        except paramiko.AuthenticationException:
            return jsonify({
                'success': False,
                'message': 'Échec de l\'authentification SSH - Vérifiez le nom d\'utilisateur/mot de passe'
            })
        except paramiko.SSHException as e:
            return jsonify({
                'success': False,
                'message': f'Erreur SSH: {str(e)}'
            })
        except socket.timeout:
            return jsonify({
                'success': False,
                'message': 'Timeout de connexion - La VM est-elle démarrée?'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Erreur de connexion: {str(e)}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erreur lors du test SSH: {str(e)}'
        })

# ✅ NOUVELLE ROUTE : Lancer une session SSH via le terminal web
@app.route('/api/vms/<int:vm_id>/ssh-session', methods=['POST'])
def start_ssh_session(vm_id):
    """Démarre une session SSH pour le terminal web"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'})

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        # Vérifier que la VM est en cours d'exécution
        if vm.status != 'running':
            return jsonify({
                'success': False, 
                'message': 'La VM doit être en cours d\'exécution pour se connecter en SSH'
            })
        
        # Récupérer les informations SSH
        ssh_info_response = get_ssh_info(vm_id)
        ssh_info = ssh_info_response.get_json()
        
        if not ssh_info['success']:
            return jsonify({'success': False, 'message': 'Impossible de récupérer les infos SSH'})
        
        return jsonify({
            'success': True,
            'message': 'Session SSH prête',
            'ssh_config': ssh_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Erreur lors du démarrage de la session SSH: {str(e)}'
        })

# ------------------ Lancement de l'application ------------------
if __name__ == '__main__':
    app.run(debug=True)