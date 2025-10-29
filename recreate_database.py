# recreate_database.py
from app import app
from database import db
from models import User, VM

def recreate_database():
    """Supprime et recrée la base de données avec le nouveau schéma"""
    with app.app_context():
        try:
            # Supprimer toutes les tables
            db.drop_all()
            print("✓ Anciennes tables supprimées")
            
            # Recréer toutes les tables avec le nouveau schéma
            db.create_all()
            print("✓ Nouvelles tables créées avec le schéma mis à jour")
            
            print("✅ Base de données recréée avec succès!")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    recreate_database()