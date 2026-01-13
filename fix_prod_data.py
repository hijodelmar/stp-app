from app import create_app
from extensions import db
from models import Document
from datetime import timedelta
import sys

# Script para corregir el estado "Mise à jour" de un Devis específico
# Para usarlo: python fix_prod_data.py
# testomar

def fix_devis(numero_devis):
    app = create_app()
    with app.app_context():
        print(f"--- Reparando Devis: {numero_devis} ---")
        
        # 1. Buscar el Devis
        devis = Document.query.filter_by(numero=numero_devis).first()
        
        if not devis:
            print(f"❌ Error: No se encontró el Devis {numero_devis}")
            return

        # 2. Buscar la Factura asociada (la más reciente)
        invoices = [d for d in devis.generated_documents if d.type == 'facture']
        
        if not invoices:
             print(f"❌ Error: El Devis {numero_devis} no tiene facturas enlazadas.")
             return
             
        # Ordenar por fecha para coger la última
        invoices.sort(key=lambda x: x.created_at, reverse=True)
        latest_inv = invoices[0]
        
        print(f"Devis encontrado (ID: {devis.id})")
        print(f"Factura encontrada: {latest_inv.numero} (ID: {latest_inv.id})")
        print(f"Fecha Modificación Devis: {devis.updated_at}")
        print(f"Fecha Creación Factura:   {latest_inv.created_at}")
        
        # 3. Comprobar y Corregir
        if devis.updated_at > latest_inv.created_at:
            print("⚠️ DETECTADO: El Devis es más reciente que la Factura (Por eso sale 'Mise à jour').")
            print("🔧 Corrigiendo fechas...")
            
            # Poner la fecha del Devis 1 minuto ANTES de la factura
            new_date = latest_inv.created_at - timedelta(minutes=1)
            devis.updated_at = new_date
            
            db.session.commit()
            print(f"✅ ¡ÉXITO! Nueva fecha Devis: {devis.updated_at}")
            print("El estado debería ser ahora 'Facturé'.")
        else:
            print("ℹ️ Todo correcto: El Devis ya es más antiguo que la Factura. No se necesita corrección.")

if __name__ == "__main__":
    # Puedes cambiar el número aquí si necesitas arreglar otro
    target_devis = "D-2026-003"
    
    if len(sys.argv) > 1:
        target_devis = sys.argv[1]
        
    fix_devis(target_devis)
