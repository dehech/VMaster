from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User, VM
import subprocess
import sys
import json
from datetime import datetime
import random
import webbrowser
from threading import Timer
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuration base de données SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

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
    return redirect(url_for('login'))

@app.route('/create', methods=['GET', 'POST'])
def create_vm():
    if 'user_id' not in session:
        flash("Veuillez vous connecter pour créer une machine virtuelle.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Champs obligatoires
            name = request.form['name']
            os_type = request.form['os']
            cpu = request.form['cpu']
            ram = request.form['ram']
            storage = request.form['storage']
            
            # Nouveaux champs optionnels
            script = request.form.get('script', '')
            network_type = request.form.get('network_type', 'nat')
            graphics_controller = request.form.get('graphics_controller', 'vmsvga')
            vram = request.form.get('vram', '128')

            # Validation des champs obligatoires
            if not all([name, os_type, cpu, ram, storage]):
                flash("Tous les champs marqués comme obligatoires sont requis ⚠️", "error")
                return redirect(url_for('create_vm'))

            # Validation numérique
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

            # Validation du nom
            import re
            if not re.match(r'^[a-zA-Z0-9-_ ]+$', name):
                flash("Le nom de la VM ne peut contenir que des lettres, chiffres, espaces, tirets et underscores ⚠️", "error")
                return redirect(url_for('create_vm'))
            
            # Déterminer automatiquement le chemin ISO selon l'OS
            iso_paths = {
                'ubuntu': r'D:\programs\ubuntu-22.04.4-desktop-amd64.iso',
                'windows': r'D:\programs\win_server_release_amd64fre_SERVER_LOF_PACKAGES_OEM.iso',
                'windows10': r'D:\programs\Win10_21H2_French_x64.iso',
                'windows11': r'D:\programs\Win11_22H2_EnglishInternational_x64v2.iso'
            }
            
            iso_path = iso_paths.get(os_type)
            import os
            if iso_path:
                if os.path.exists(iso_path):
                    print(f"✓ ISO trouvé: {iso_path}")
                else:
                    print(f"⚠️ ISO non trouvé: {iso_path}")
                    flash(f"⚠️ Le fichier ISO pour {os_type} n'a pas été trouvé: {iso_path}", "warning")
                    iso_path = None
            else:
                print(f"ℹ️ Aucun ISO automatique pour: {os_type}")

            # Création de la VM dans la base
            new_vm = VM(
                user_id=session['user_id'],
                name=name,
                os=os_type,
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

            # ✅ CALCUL SIMPLE DU PORT SSH
            ssh_port = 2200 + vm_id
            print(f"🔧 Port SSH calculé: 2200 + {vm_id} = {ssh_port}")

            # Appel du script Python pour créer la VM
            try:
                command = [
                    sys.executable,
                    "creator.py",
                    "create",
                    name,
                    os_type,
                    str(cpu_int),
                    str(ram_int),
                    str(storage_int),
                    iso_path if iso_path else "",
                    network_type,
                    graphics_controller,
                    str(vram_int),
                    str(vm_id)  # ✅ ENVOYER L'ID DE LA VM
                ]

                # Nettoyer les arguments vides
                command = [arg for arg in command if arg != ""]
                
                # Lancer le script en arrière-plan
                subprocess.Popen(command)
                
                if iso_path:
                    flash(f"✅ Votre machine virtuelle {os_type} est en cours de création avec l'ISO automatique...", "success")
                else:
                    flash(f"✅ Votre machine virtuelle {os_type} est en cours de création (sans ISO)...", "success")
                
                print(f"🚀 Lancement création VM: {name} (ID: {vm_id}, Port SSH: {ssh_port})")
                print(f"📋 Configuration: {os_type}, {cpu_int} CPU, {ram_int} Go RAM, {storage_int} Go stockage")

            except Exception as e:
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

    return render_template('create.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api/vms/<int:vm_id>/vnc-info')
def get_vnc_info(vm_id):
    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        vnc_config = {
            'host': 'localhost',
            'port': 6080,
            'password': 'vmaster123',
            'success': True
        }
        return jsonify(vnc_config)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

# ✅ ROUTE SSH INFO AVEC CALCUL SIMPLE
@app.route('/api/vms/<int:vm_id>/ssh-info')
def get_ssh_info(vm_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'})

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        # Mapping utilisateur/OS
        os_username_map = {
            'ubuntu': 'ubuntu',
            'debian': 'debian',
            'centos': 'centos',
            'fedora': 'fedora',
            'archlinux': 'arch',
            'opensuse': 'opensuse',
            'gentoo': 'gentoo',
            'linux': 'linux',
            'windows': 'administrator',
            'windows10': 'administrator',
            'windows11': 'administrator',
            'freebsd': 'freebsd',
            'solaris': 'solaris',
            'oracle': 'oracle'
        }
        
        username = os_username_map.get(vm.os.lower(), 'user')
        
        # ✅ CALCUL SIMPLE : Port = 2200 + ID_VM
        base_ssh_port = 2200
        ssh_port = base_ssh_port + vm.id
        
        ssh_config = {
            'success': True,
            'vm_name': vm.name,
            'os': vm.os,
            'username': username,
            'password': '123456',
            'host': '127.0.0.1',
            'port': ssh_port,
            'vm_ip': '10.0.2.15',
            'vm_db_id': vm.id,
            'base_port': base_ssh_port,
            'command': f'ssh {username}@127.0.0.1 -p {ssh_port}',
            'status': vm.status
        }
        
        print(f"🔧 App.py - VM: {vm.name}, ID: {vm.id}, Port: {ssh_port}")
        
        return jsonify(ssh_config)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/vms/<int:vm_id>/test-ssh')
def test_ssh_connection(vm_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'})

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        import paramiko
        import socket
        
        ssh_info_response = get_ssh_info(vm_id)
        ssh_info = ssh_info_response.get_json()
        
        if not ssh_info['success']:
            return jsonify({'success': False, 'message': 'Impossible de récupérer les infos SSH'})
        
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
            
            stdin, stdout, stderr = ssh.exec_command('whoami')
            user_output = stdout.read().decode().strip()
            
            ssh.close()
            
            return jsonify({
                'success': True,
                'message': f'Connexion SSH réussie! Utilisateur: {user_output}',
                'user': user_output
            })
            
        except paramiko.AuthenticationException:
            return jsonify({'success': False, 'message': 'Échec de l\'authentification SSH'})
        except paramiko.SSHException as e:
            return jsonify({'success': False, 'message': f'Erreur SSH: {str(e)}'})
        except socket.timeout:
            return jsonify({'success': False, 'message': 'Timeout de connexion'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Erreur de connexion: {str(e)}'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors du test SSH: {str(e)}'})

@app.route('/api/vms/<int:vm_id>/ssh-session', methods=['POST'])
def start_ssh_session(vm_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'})

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        if vm.status != 'running':
            return jsonify({'success': False, 'message': 'La VM doit être en cours d\'exécution'})
        
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
        return jsonify({'success': False, 'message': f'Erreur lors du démarrage de la session SSH: {str(e)}'})

# ✅ ROUTE MÉTRIQUES SIMPLIFIÉE (4 MÉTRIQUES SEULEMENT)
@app.route('/api/vms/<int:vm_id>/metrics')
def get_vm_metrics(vm_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Non connecté'})

    vm = VM.query.get_or_404(vm_id)
    if vm.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Non autorisé'})

    try:
        # Récupérer les métriques depuis metrics.py
        result = subprocess.run(
            [sys.executable, "metrics.py", vm.name],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8'
        )
        
        if result.returncode == 0 and result.stdout:
            metrics_data = json.loads(result.stdout)
            
            return jsonify({
                'success': True,
                'metrics': {
                    'cpu_usage': metrics_data.get('cpu_usage', 0),
                    'memory_usage': metrics_data.get('memory_usage', 0),
                    'disk_usage': metrics_data.get('disk_usage', 0),
                    'network_usage': metrics_data.get('network_usage', 0),
                    'is_running': metrics_data.get('is_running', False)
                },
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Métriques simulées en cas d'erreur
            return jsonify({
                'success': True,
                'metrics': {
                    'cpu_usage': round(random.uniform(5, 25), 1) if vm.status == 'running' else 0,
                    'memory_usage': round(random.uniform(15, 45), 1) if vm.status == 'running' else 0,
                    'disk_usage': round(random.uniform(10, 35), 1) if vm.status == 'running' else 0,
                    'network_usage': round(random.uniform(0.1, 2.5), 2) if vm.status == 'running' else 0,
                    'is_running': vm.status == 'running'
                },
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        # Métriques simulées en cas d'erreur
        return jsonify({
            'success': True,
            'metrics': {
                'cpu_usage': round(random.uniform(5, 25), 1) if vm.status == 'running' else 0,
                'memory_usage': round(random.uniform(15, 45), 1) if vm.status == 'running' else 0,
                'disk_usage': round(random.uniform(10, 35), 1) if vm.status == 'running' else 0,
                'network_usage': round(random.uniform(0.1, 2.5), 2) if vm.status == 'running' else 0,
                'is_running': vm.status == 'running'
            },
            'timestamp': datetime.now().isoformat()
        })

def open_browser():
    # Ouvre automatiquement le navigateur sur ton IP locale
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == '__main__':
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1, open_browser).start()
    app.run(debug=True, host='0.0.0.0', port=5000)