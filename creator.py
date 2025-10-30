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
        try:
            result = subprocess.run(
                [self.vboxmanage_path, "list", "vms"],
                capture_output=True, text=True
            )
            return f'"{vm_name}"' in result.stdout
        except:
            return False

    def _is_vm_running(self, vm_name: str) -> bool:
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
                  secondary_network_type: Optional[str] = None, 
                  graphics_controller: Optional[str] = None,
                  vram_mb: Optional[str] = None,
                  vm_db_id: Optional[int] = None) -> bool:
        """
        Crée une machine virtuelle dans VirtualBox
        """
        
        print(f"\n🎯 Création VM: {vm_name}")
        print(f"📋 {os_type}, {cpu_count} CPU, {ram_gb} Go RAM, {storage_gb} Go stockage")
        print(f"⚙️  Config: nat (obligatoire) + {secondary_network_type} (optionnel)")

        if self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' existe déjà"
            print(f"⚠️  {error_msg}")
            return False
        
        template = self._get_os_template(os_type)
        
        graphics = graphics_controller or "vmsvga"
        vram = vram_mb or "128"
        
        # ✅ CALCUL SIMPLE : Port = 2200 + ID_VM
        base_ssh_port = 2200
        
        if vm_db_id:
            # Utiliser l'ID de la base de données
            ssh_host_port = base_ssh_port + vm_db_id
            port_source = f"ID base de données ({vm_db_id})"
        else:
            # Fallback : calcul simple basé sur le nom
            simple_id = sum(ord(c) for c in vm_name) % 100 + 10
            ssh_host_port = base_ssh_port + simple_id
            port_source = f"calcul du nom ({simple_id})"
        
        vm_ip = "10.0.2.15"
        
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
            
            # 5. INTERFACE RÉSEAU 1: NAT OBLIGATOIRE
            print(f"\n📡 Configuration interface réseau 1 (NAT obligatoire)")
            if not self._run_command(["modifyvm", vm_name, "--nic1", "nat"]):
                raise Exception("Échec configuration interface nat")
            
            # 6. REDIRECTION PORT SSH
            print(f"🔗 Configuration SSH: 127.0.0.1:{ssh_host_port} → {vm_ip}:22")
            print(f"   - Source: {port_source}")
            if not self._run_command(["modifyvm", vm_name, "--natpf1", f"ssh,tcp,127.0.0.1,{ssh_host_port},{vm_ip},22"]):
                print("⚠️  Impossible de configurer la redirection SSH")
            
            # 7. INTERFACE RÉSEAU 2: OPTIONNELLE
            if secondary_network_type and secondary_network_type != "none":
                print(f"\n📡 Configuration interface réseau 2 ({secondary_network_type} optionnel)")
                if not self._run_command(["modifyvm", vm_name, "--nic2", secondary_network_type]):
                    print(f"⚠️  Impossible de configurer l'interface {secondary_network_type}")
                
                if secondary_network_type == "bridged":
                    if not self._run_command(["modifyvm", vm_name, "--bridgeadapter2", "en0"]):
                        print("⚠️  Impossible de configurer l'adaptateur bridge")
                
                elif secondary_network_type == "hostonly":
                    if not self._run_command(["modifyvm", vm_name, "--hostonlyadapter2", "VirtualBox Host-Only Ethernet Adapter"]):
                        print("⚠️  Impossible de configurer l'adaptateur host-only")
                
                elif secondary_network_type == "natnetwork":
                    if not self._run_command(["modifyvm", vm_name, "--nat-network2", "NatNetwork"]):
                        print("⚠️  Impossible de configurer NatNetwork")
            
            # 8. Créer le disque dur
            storage_mb = storage_gb * 1024
            vdi_path = os.path.join(os.getcwd(), f"{vm_name}.vdi")
            
            if not self._run_command(["createmedium", "disk", "--filename", vdi_path, 
                                    "--size", str(storage_mb), "--format", "VDI"]):
                raise Exception("Échec création disque")
            
            # 9. Attacher le contrôleur SATA
            if not self._run_command(["storagectl", vm_name, "--name", "SATA Controller", 
                                    "--add", "sata", "--controller", "IntelAHCI"]):
                raise Exception("Échec configuration contrôleur SATA")
            
            # 10. Attacher le disque dur
            if not self._run_command(["storageattach", vm_name, "--storagectl", "SATA Controller",
                                    "--port", "0", "--device", "0", "--type", "hdd", 
                                    "--medium", vdi_path]):
                raise Exception("Échec attachement disque")
            
            # 11. Gérer l'ISO si fourni
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
            
            # 12. Configurations supplémentaires
            self._run_command(["modifyvm", vm_name, "--graphicscontroller", graphics])
            self._run_command(["modifyvm", vm_name, "--vram", str(vram)])
            self._run_command(["modifyvm", vm_name, "--usb", "on", "--usbehci", "on"])
            self._run_command(["modifyvm", vm_name, "--audio", "none"])
            self._run_command(["modifyvm", vm_name, "--vrde", "off"])
            
            print(f"\n✅ VM '{vm_name}' créée avec succès!")
            print(f"📊 Configuration réseau:")
            print(f"   - Interface 1: NAT (obligatoire)")
            print(f"   - IP VM: {vm_ip}")
            print(f"   - SSH: 127.0.0.1:{ssh_host_port} → {vm_ip}:22")
            print(f"   - Port source: {port_source}")
            
            if secondary_network_type and secondary_network_type != "none":
                print(f"   - Interface 2: {secondary_network_type} (optionnel)")
            else:
                print(f"   - Interface 2: Aucune")
            
            print(f"🔧 Autres paramètres:")
            print(f"   - CPU: {cpu_count}, RAM: {ram_gb}GB, Stockage: {storage_gb}GB")
            print(f"   - Graphics: {graphics}, VRAM: {vram}MB")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erreur création VM: {error_msg}")
            return False

    def start_vm(self, vm_name: str) -> bool:
        print(f"\n🚀 Démarrage de la VM: {vm_name}")
        
        if not self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' n'existe pas"
            print(f"❌ {error_msg}")
            return False
        
        try:
            # Calcul simple du port pour l'affichage
            simple_id = sum(ord(c) for c in vm_name) % 100 + 10
            ssh_port = 2200 + simple_id
            
            if self._run_command(["startvm", vm_name, "--type", "headless"]):
                print(f"✅ VM '{vm_name}' démarrée!")
                print(f"📡 Accès SSH: ssh utilisateur@127.0.0.1 -p {ssh_port}")
                print(f"🌐 IP VM: 10.0.2.15 (NAT)")
                print(f"🔢 Port SSH estimé: {ssh_port}")
                
                import time
                time.sleep(60)
                
                return True
            else:
                raise Exception("Échec du démarrage")
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erreur démarrage VM: {error_msg}")
            return False

    def stop_vm(self, vm_name: str) -> bool:
        print(f"\n🛑 Arrêt de la VM: {vm_name}")
        
        if not self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' n'existe pas"
            print(f"❌ {error_msg}")
            return False
        
        try:
            if self._run_command(["controlvm", vm_name, "acpipowerbutton"]):
                print("✓ Signal d'arrêt envoyé (ACPI)")
                import time
                time.sleep(10)
                
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
        print(f"\n🗑️  Suppression de la VM: {vm_name}")
        
        if not self._vm_exists(vm_name):
            error_msg = f"La VM '{vm_name}' n'existe pas"
            print(f"❌ {error_msg}")
            return False
        
        try:
            if self._is_vm_running(vm_name):
                print("🛑 Arrêt de la VM en cours...")
                self._run_command(["controlvm", vm_name, "poweroff"])
                import time
                time.sleep(5)
            
            if self._run_command(["unregistervm", vm_name, "--delete"]):
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
        print(f"\n📊 Informations de la VM: {vm_name}")
        if self._vm_exists(vm_name):
            simple_id = sum(ord(c) for c in vm_name) % 100 + 10
            ssh_port = 2200 + simple_id
            
            print(f"🔗 Accès réseau:")
            print(f"   - Interface 1: NAT (obligatoire)")
            print(f"   - IP VM: 10.0.2.15")
            print(f"   - SSH: 127.0.0.1:{ssh_port} → 10.0.2.15:22")
            
            self._run_command(["showvminfo", vm_name])
        else:
            print(f"❌ La VM '{vm_name}' n'existe pas")

    def list_vms(self):
        print("\n📋 Liste des VMs:")
        self._run_command(["list", "vms"])
        
        print("\n🏃 VMs en cours d'exécution:")
        self._run_command(["list", "runningvms"])

    def get_ssh_info(self, vm_name: str):
        if self._vm_exists(vm_name):
            simple_id = sum(ord(c) for c in vm_name) % 100 + 10
            ssh_port = 2200 + simple_id
            
            print(f"\n🔗 Informations SSH pour '{vm_name}':")
            print(f"   - Port SSH: {ssh_port}")
            print(f"   - Commande: ssh utilisateur@127.0.0.1 -p {ssh_port}")
            print(f"   - IP VM: 10.0.2.15")
        else:
            print(f"❌ La VM '{vm_name}' n'existe pas")

def main():
    try:
        creator = VirtualBoxVMCreator()
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "create" and len(sys.argv) >= 7:
            # Format: python creator.py create <name> <os> <cpu> <ram> <storage> [iso] [network] [graphics] [vram] [vm_db_id]
            vm_name = sys.argv[2]
            os_type = sys.argv[3]
            cpu_count = int(sys.argv[4])
            ram_gb = int(sys.argv[5])
            storage_gb = int(sys.argv[6])
    
            iso_path = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] else None
            network_type = sys.argv[8] if len(sys.argv) > 8 and sys.argv[8] != "" else "nat"
            graphics_controller = sys.argv[9] if len(sys.argv) > 9 and sys.argv[9] != "" else None
            vram_mb = int(sys.argv[10]) if len(sys.argv) > 10 and sys.argv[10] != "" else None
            vm_db_id = int(sys.argv[11]) if len(sys.argv) > 11 and sys.argv[11] != "" else None
            
            success = creator.create_vm(
                vm_name, os_type, cpu_count, ram_gb, storage_gb,
                iso_path, network_type, graphics_controller, vram_mb, vm_db_id
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
            
        elif action == "ssh" and len(sys.argv) >= 3:
            creator.get_ssh_info(sys.argv[2])
            
        elif action == "list":
            creator.list_vms()
            
        else:
            print("Usage:")
            print("  Créer: python creator.py create <name> <os> <cpu> <ram> <storage> [iso] [network] [graphics] [vram] [vm_db_id]")
            print("  Démarrer: python creator.py start <vm_name>")
            print("  Arrêter: python creator.py stop <vm_name>")
            print("  Supprimer: python creator.py delete <vm_name>")
            print("  Info: python creator.py info <vm_name>")
            print("  SSH Info: python creator.py ssh <vm_name>")
            print("  Lister: python creator.py list")
            print("\nCalcul du port SSH:")
            print("  - Port SSH = 2200 + ID_VM (depuis la base de données)")
            sys.exit(1)
    else:
        print("VM Creator - Utilisez --help pour voir les commandes disponibles")

if __name__ == "__main__":
    main()