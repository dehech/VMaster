import subprocess
import sys
import os
import sqlite3
from typing import Optional

class VirtualBoxVMCreator:
    def __init__(self):
        self.vboxmanage_path = self._find_vboxmanage()
        
    def _find_vboxmanage(self) -> str:
        
        possible_paths = [
            "C:\\Program Files\\Oracle\\VirtualBox\\VBoxManage.exe"
        ]
        
        for path in possible_paths:
            try:
                subprocess.run([path, "--version"], capture_output=True, check=True)
                return path
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        raise Exception("VBoxManage non trouvé. Assurez-vous que VirtualBox est installé.")
    
    def _get_os_template(self, os_type: str) -> dict:
        """Retourne les paramètres par défaut selon l'OS"""
        templates = {
            "ubuntu": {"ostype": "Ubuntu_64"},
            "debian": {"ostype": "Debian_64"},
            "centos": {"ostype": "RedHat_64"},
            "fedora": {"ostype": "Fedora_64"},
            "archlinux": {"ostype": "ArchLinux_64"},
            "opensuse": {"ostype": "openSUSE_64"},
            "gentoo": {"ostype": "Gentoo_64"},
            "linux": {"ostype": "Linux_64"},
            "windows": {"ostype": "Windows2019_64"},
            "windows10": {"ostype": "Windows10_64"},
            "windows11": {"ostype": "Windows11_64"},
            "freebsd": {"ostype": "FreeBSD_64"},
            "solaris": {"ostype": "Solaris_64"},
            "oracle": {"ostype": "Oracle_64"},
        }
        return templates.get(os_type.lower(), templates["ubuntu"])
    
    def _run_command(self, command: list) -> bool:
        """Exécute une commande VBoxManage"""
        try:
            result = subprocess.run(
                [self.vboxmanage_path] + command,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ {' '.join(command)}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ {' '.join(command)}")
            print(f"Erreur: {e.stderr}")
            return False
    
    def _vm_exists(self, vm_name: str) -> bool:
        """Vérifie si une VM existe"""
        try:
            result = subprocess.run(
                [self.vboxmanage_path, "list", "vms"],
                capture_output=True, text=True
            )
            return f'"{vm_name}"' in result.stdout
        except:
            return False

    def _is_vm_running(self, vm_name: str) -> bool:
        """Vérifie si une VM est en cours d'exécution"""
        try:
            result = subprocess.run(
                [self.vboxmanage_path, "list", "runningvms"],
                capture_output=True, text=True
            )
            return f'"{vm_name}"' in result.stdout
        except:
            return False

    def create_vm(self, vm_name: str, os_type: str, cpu_count: int, ram_gb: int, 
                  storage_gb: int, iso_path: Optional[str] = None,
                  network_type: Optional[str] = None, graphics_controller: Optional[str] = None,
                  vram_mb: Optional[str] = None) -> bool:
        """
        Crée une machine virtuelle dans VirtualBox
        """
        
        print(f"\n🎯 Création VM: {vm_name}")
        print(f"📋 {os_type}, {cpu_count} CPU, {ram_gb} Go RAM, {storage_gb} Go stockage")
        print(f"⚙️  Config: {network_type} network, {graphics_controller} graphics, {vram_mb} MB VRAM")

        # Vérifier si la VM existe déjà
        if self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' existe déjà"
            print(f"⚠️  {error_msg}")
            return False
        
        template = self._get_os_template(os_type)
        
        try:
            # 1. Créer la VM
            if not self._run_command(["createvm", "--name", vm_name, "--register"]):
                raise Exception("Échec création VM")
            
            # 2. Configurer l'OS
            if not self._run_command(["modifyvm", vm_name, "--ostype", template["ostype"]]):
                raise Exception("Échec configuration OS")
            
            # 3. Configurer la mémoire
            ram_mb = ram_gb * 1024
            if not self._run_command(["modifyvm", vm_name, "--memory", str(ram_mb)]):
                raise Exception("Échec configuration mémoire")
            
            # 4. Configurer les CPUs
            if not self._run_command(["modifyvm", vm_name, "--cpus", str(cpu_count)]):
                raise Exception("Échec configuration CPU")
            
            # 5. Configurer la carte réseau (NAT par défaut)
            if not self._run_command(["modifyvm", vm_name, "--nic1", network_type]):
                raise Exception("Échec configuration réseau")
            
            # 6. Créer le disque dur
            storage_mb = storage_gb * 1024
            vdi_path = os.path.join(os.getcwd(), f"{vm_name}.vdi")
            
            if not self._run_command(["createmedium", "disk", "--filename", vdi_path, 
                                    "--size", str(storage_mb), "--format", "VDI"]):
                raise Exception("Échec création disque")
            
            # 7. Attacher le contrôleur SATA
            if not self._run_command(["storagectl", vm_name, "--name", "SATA Controller", 
                                    "--add", "sata", "--controller", "IntelAHCI"]):
                raise Exception("Échec configuration contrôleur SATA")
            
            # 8. Attacher le disque dur
            if not self._run_command(["storageattach", vm_name, "--storagectl", "SATA Controller",
                                    "--port", "0", "--device", "0", "--type", "hdd", 
                                    "--medium", vdi_path]):
                raise Exception("Échec attachement disque")
            
            # 9. Gérer l'ISO si fourni
            if iso_path and os.path.exists(iso_path):
                if not self._run_command(["storagectl", vm_name, "--name", "IDE Controller", 
                                        "--add", "ide", "--controller", "PIIX4"]):
                    raise Exception("Échec configuration contrôleur IDE")
                
                if not self._run_command(["storageattach", vm_name, "--storagectl", "IDE Controller",
                                        "--port", "0", "--device", "0", "--type", "dvddrive", 
                                        "--medium", iso_path]):
                    raise Exception("Échec attachement ISO")
                
                if not self._run_command(["modifyvm", vm_name, "--boot1", "dvd", "--boot2", "disk"]):
                    raise Exception("Échec configuration boot")
            else:
                if not self._run_command(["modifyvm", vm_name, "--boot1", "disk"]):
                    raise Exception("Échec configuration boot")
            
            # 10. Configurations supplémentaires
            self._run_command(["modifyvm", vm_name, "--graphicscontroller", graphics_controller])
            self._run_command(["modifyvm", vm_name, "--vram", str(vram_mb)])
            self._run_command(["modifyvm", vm_name, "--usb", "on", "--usbehci", "on"])
            self._run_command(["modifyvm", vm_name, "--audio", "none"])
            # 11. Activer l'accès distant VNC
            self._run_command(["modifyvm", vm_name, "--vrde", "on"])
            self._run_command(["modifyvm", vm_name, "--vrdeproperty", "Security/Method="])
            self._run_command(["modifyvm", vm_name, "--vrdeproperty", "VNCPassword=vmaster123"])
            self._run_command(["modifyvm", vm_name, "--vrdeport", "5900"])

            # Démarrer le proxy Websockify
            try:
                subprocess.Popen(["python", "-m", "websockify", "6080", "localhost:5900"])
                print("✓ Websockify démarré sur le port 6080")
            except Exception as e:
                print(f"✗ Erreur websockify: {e}")
            
            print(f"\n✅ VM '{vm_name}' créée avec succès!")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erreur création VM: {error_msg}")
            return False

    def start_vm(self, vm_name: str) -> bool:
        """Démarre une VM"""
        print(f"\n🚀 Démarrage de la VM: {vm_name}")
        
        if not self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' n'existe pas"
            print(f"❌ {error_msg}")
            return False
        
        try:
            if self._run_command(["startvm", vm_name, "--type", "headless"]):
                print(f"✅ VM '{vm_name}' démarrée avec succès!")
                return True
            else:
                raise Exception("Échec du démarrage")
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erreur démarrage VM: {error_msg}")
            return False

    def stop_vm(self, vm_name: str) -> bool:
        """Arrête une VM"""
        print(f"\n🛑 Arrêt de la VM: {vm_name}")
        
        if not self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' n'existe pas"
            print(f"❌ {error_msg}")
            return False
        
        try:
            # Essayer d'arrêter proprement d'abord
            if self._run_command(["controlvm", vm_name, "acpipowerbutton"]):
                print("✓ Signal d'arrêt envoyé (ACPI)")
                # Attendre un peu puis forcer l'arrêt si nécessaire
                import time
                time.sleep(10)
                
                # Vérifier si la VM est toujours en cours d'exécution
                if self._is_vm_running(vm_name):
                    print("⚠️  Forçage de l'arrêt...")
                    if self._run_command(["controlvm", vm_name, "poweroff"]):
                        print("✓ Arrêt forcé réussi")
            
            print(f"✅ VM '{vm_name}' arrêtée avec succès!")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erreur arrêt VM: {error_msg}")
            return False

    def delete_vm(self, vm_name: str) -> bool:
        """Supprime une VM"""
        print(f"\n🗑️  Suppression de la VM: {vm_name}")
        
        if not self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' n'existe pas"
            print(f"❌ {error_msg}")
            return False
        
        try:
            # Arrêter la VM si elle est en cours d'exécution
            if self._is_vm_running(vm_name):
                print("🛑 Arrêt de la VM en cours...")
                self._run_command(["controlvm", vm_name, "poweroff"])
                import time
                time.sleep(5)
            
            # Supprimer la VM
            if self._run_command(["unregistervm", vm_name, "--delete"]):
                # Supprimer aussi le fichier VDI s'il existe
                vdi_file = f"{vm_name}.vdi"
                if os.path.exists(vdi_file):
                    os.remove(vdi_file)
                    print(f"✓ Fichier {vdi_file} supprimé")
                
                print(f"✅ VM '{vm_name}' supprimée avec succès!")
                return True
            else:
                raise Exception("Échec de la suppression")
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erreur suppression VM: {error_msg}")
            return False

    def get_vm_info(self, vm_name: str):
        """Affiche les informations d'une VM"""
        print(f"\n📊 Informations de la VM: {vm_name}")
        if self._vm_exists(vm_name):
            self._run_command(["showvminfo", vm_name])
        else:
            print(f"❌ La VM '{vm_name}' n'existe pas")

    def list_vms(self):
        """Liste toutes les VMs"""
        print("\n📋 Liste des VMs:")
        self._run_command(["list", "vms"])
        
        print("\n🏃 VMs en cours d'exécution:")
        self._run_command(["list", "runningvms"])

def main():
    """Point d'entrée principal"""
    try:
        creator = VirtualBoxVMCreator()
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "create" and len(sys.argv) >= 7:
            # Format: python vm_creator.py create <name> <os> <cpu> <ram> <storage> [iso] [network] [graphics] [vram]
            vm_name = sys.argv[2]
            os_type = sys.argv[3]
            cpu_count = int(sys.argv[4])
            ram_gb = int(sys.argv[5])
            storage_gb = int(sys.argv[6])
    
            iso_path = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] else None
            network_type = sys.argv[8] if len(sys.argv) > 8 and sys.argv[8] != "" else None
            graphics_controller = sys.argv[9] if len(sys.argv) > 9 and sys.argv[9] != "" else None
            vram_mb = int(sys.argv[10]) if len(sys.argv) > 10 and sys.argv[10] != "" else None
            
            success = creator.create_vm(
                vm_name, os_type, cpu_count, ram_gb, storage_gb,
                iso_path, network_type, graphics_controller, vram_mb
            )
            sys.exit(0 if success else 1)
            
        elif action == "start" and len(sys.argv) >= 3:
            vm_name = sys.argv[2]
            success = creator.start_vm(vm_name)
            sys.exit(0 if success else 1)
            
        elif action == "stop" and len(sys.argv) >= 3:
            vm_name = sys.argv[2]
            success = creator.stop_vm(vm_name)
            sys.exit(0 if success else 1)
            
        elif action == "delete" and len(sys.argv) >= 3:
            vm_name = sys.argv[2]
            success = creator.delete_vm(vm_name)
            sys.exit(0 if success else 1)
            
        elif action == "info" and len(sys.argv) >= 3:
            creator.get_vm_info(sys.argv[2])
            
        elif action == "list":
            creator.list_vms()
            
        else:
            print("Usage:")
            print("  Créer: python vm_creator.py create <name> <os> <cpu> <ram> <storage> [iso]")
            print("  Démarrer: python vm_creator.py start <vm_name>")
            print("  Arrêter: python vm_creator.py stop <vm_name>")
            print("  Supprimer: python vm_creator.py delete <vm_name>")
            print("  Info: python vm_creator.py info <vm_name>")
            print("  Lister: python vm_creator.py list")
            sys.exit(1)
    else:
        print("VM Creator - Utilisez --help pour voir les commandes disponibles")

if __name__ == "__main__":
    main()