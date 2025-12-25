import logging
from datetime import datetime
from flask import url_for, request
from flask_login import current_user
from extensions import db
from models import Client, Supplier, Document, LigneDocument, CompanyInfo, ClientContact
from sqlalchemy import func

logger = logging.getLogger(__name__)

class ChatExecutor:
    def __init__(self):
        self.actions = {
            'create_client': self.create_client,
            'list_clients': self.list_clients,
            'create_supplier': self.create_supplier,
            'list_suppliers': self.list_suppliers,
            'create_document': self.create_document,
            'list_documents': self.list_documents,
            'add_line': self.add_line,
            'get_stats': self.get_stats,
            'calculate_totals': self.calculate_totals,
            'delete_client': self.delete_client,
            'delete_supplier': self.delete_supplier,
            'delete_document': self.delete_document,
            'convert_document': self.convert_document,
            'send_email': self.send_email,
            'get_recent_activity': self.get_recent_activity,
            'reset': self.reset_context,
            'add_contact': self.add_contact
        }

    def reset_context(self, data=None):
        return {"status": "success", "message": "Context reset triggered."}

    def execute(self, command_json, context=None):
        """
        Executes a command based on the JSON payload.
        Expected format: { "action": "action_name", "data": { ... } }
        """
        if not command_json:
            return {"status": "error", "message": "No command provided."}
        
        action = command_json.get('action')
        data = command_json.get('data', {})
        self.context = context or {}
        
        if action not in self.actions:
            return {"status": "error", "message": f"Unknown action: {action}"}
        
        try:
            return self.actions[action](data)
        except Exception as e:
            logger.error(f"Error executing {action}: {e}")
            return {"status": "error", "message": str(e)}

    def create_client(self, data):
        if not data.get('raison_sociale'):
            return {"status": "error", "message": "Raison sociale is required."}
        
        client = Client(
            raison_sociale=data['raison_sociale'],
            email=data.get('email'),
            telephone=data.get('telephone'),
            adresse=data.get('adresse'),
            ville=data.get('ville'),
            code_postal=data.get('code_postal'),
            created_by_id=current_user.id
        )
        db.session.add(client)
        db.session.commit()
        return {
            "status": "success", 
            "message": f"Client {client.raison_sociale} created.", 
            "data": {"id": client.id, "type": "client", "name": client.raison_sociale}
        }

    def list_clients(self, data):
        limit = data.get('limit', 10)
        clients = Client.query.order_by(Client.raison_sociale).limit(limit).all()
        result = [{"id": c.id, "name": c.raison_sociale, "email": c.email} for c in clients]
        return {"status": "success", "data": result}

    def add_contact(self, data):
        client_id = data.get('client_id') or self.context.get('last_client_id')
        if not client_id and data.get('client_name'):
            client = Client.query.filter(Client.raison_sociale.ilike(f"%{data['client_name']}%")).first()
            if client:
                client_id = client.id

        if not client_id:
            return {"status": "error", "message": "Client ID ou nom requis pour ajouter un contact."}

        # Model uses 'nom' only, and 'fonction' instead of 'poste'
        first = data.get('prenom', '')
        last = data.get('nom', '')
        full_name = f"{first} {last}".strip() or last or first or "Contact"

        contact = ClientContact(
            client_id=client_id,
            nom=full_name,
            email=data.get('email'),
            telephone=data.get('telephone'),
            fonction=data.get('poste') or data.get('fonction', 'Contact')
        )
        db.session.add(contact)
        db.session.commit()
        return {
            "status": "success", 
            "message": f"Contact {full_name} ajouté.",
            "data": {"id": contact.id, "name": full_name, "email": contact.email}
        }

    def create_supplier(self, data):
        if not data.get('raison_sociale'):
            return {"status": "error", "message": "Raison sociale is required."}
            
        supplier = Supplier(
            raison_sociale=data['raison_sociale'],
            email=data.get('email'),
            telephone=data.get('telephone'),
            created_by_id=current_user.id
        )
        db.session.add(supplier)
        db.session.commit()
        return {
            "status": "success", 
            "message": f"Supplier {supplier.raison_sociale} created.", 
            "data": {"id": supplier.id, "type": "supplier", "name": supplier.raison_sociale}
        }

    def list_suppliers(self, data):
        limit = data.get('limit', 10)
        suppliers = Supplier.query.order_by(Supplier.raison_sociale).limit(limit).all()
        result = [{"id": s.id, "name": s.raison_sociale} for s in suppliers]
        return {"status": "success", "data": result}

    def _generate_document_number(self, doc_type):
        year = datetime.now().year
        # Prefixes: Devis=D, Facture=F, Avoir=A, Commande=BC?
        prefix_map = {'devis': 'D', 'facture': 'F', 'avoir': 'A', 'bon_de_commande': 'BC'}
        prefix = prefix_map.get(doc_type, 'DOC')
        
        count = Document.query.filter(Document.numero.like(f'{prefix}-{year}-%')).count()
        return f'{prefix}-{year}-{count + 1:04d}'

    def create_document(self, data):
        """
        Creates a document (Devis, Facture, Avoir).
        Requires: client_id or client_name (fuzzy search), type
        """
        doc_type = data.get('type')
        if doc_type not in ['devis', 'facture', 'avoir', 'bon_de_commande']:
            return {"status": "error", "message": "Invalid document type."}
            
        # Resolve Client
        client_id = data.get('client_id') or self.context.get('last_client_id')
        if not client_id and data.get('client_name'):
            client = Client.query.filter(Client.raison_sociale.ilike(f"%{data['client_name']}%")).first()
            if not client:
                return {"status": "error", "message": f"Client '{data['client_name']}' not found."}
            client_id = client.id
        
        if not client_id:
             return {"status": "error", "message": "Client is required."}

        # Generate Number
        numero = self._generate_document_number(doc_type)
        
        date_str = data.get('date')
        doc_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()

        # Defaults
        info = CompanyInfo.query.first()
        default_tva = info.tva_default if info else 20.0
        
        doc = Document(
            type=doc_type,
            numero=numero,
            date=doc_date,
            client_id=client_id,
            tva_rate=data.get('tva_rate', default_tva),
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        db.session.add(doc)
        db.session.commit()
        return {
            "status": "success", 
            "message": f"{doc_type.capitalize()} {numero} créé.", 
            "data": {
                "id": doc.id, 
                "document_number": numero, 
                "type": doc_type,
                "pdf_url": f"{request.host_url.rstrip('/')}{url_for('documents.view_pdf', id=doc.id)}?v={int(doc.updated_at.timestamp())}"
            }
        }

    def add_line(self, data):
        """
        Adds a line to a document.
        Requires: document_id or document_number, designation, quantite, prix_unitaire
        """
        doc_id = data.get('document_id') or self.context.get('last_document_id')
        if not doc_id and data.get('document_number'):
            doc = Document.query.filter_by(numero=data['document_number']).first()
            if not doc:
                return {"status": "error", "message": f"Document {data['document_number']} not found."}
            doc_id = doc.id
            
        if not doc_id:
            return {"status": "error", "message": "Document ID or Number required."}
            
        doc = Document.query.get(doc_id)
        if not doc:
             return {"status": "error", "message": "Document not found."}

        if not data.get('designation') or not data.get('prix_unitaire'):
             return {"status": "error", "message": "Designation and Price are required."}

        qty = float(data.get('quantite', 1))
        price = float(data.get('prix_unitaire'))
        
        line = LigneDocument(
            document_id=doc.id,
            designation=data['designation'],
            quantite=qty,
            prix_unitaire=price,
            total_ligne=qty * price,
            category=data.get('category', 'fourniture')
        )
        db.session.add(line)
        
        # Recalculate Document Totals
        self._recalculate_document(doc)
        
        db.session.commit()
        return {
            "status": "success", 
            "message": "Line added.", 
            "data": {
                "id": doc.id,
                "document_number": doc.numero,
                "total_ht": doc.montant_ht, 
                "total_ttc": doc.montant_ttc,
                "pdf_url": f"{request.host_url.rstrip('/')}{url_for('documents.view_pdf', id=doc.id)}?v={int(doc.updated_at.timestamp())}"
            }
        }

    def _recalculate_document(self, doc):
        total_ht = sum(l.total_ligne for l in doc.lignes)
        doc.montant_ht = total_ht
        if doc.autoliquidation:
            doc.tva = 0
        else:
            doc.tva = total_ht * (doc.tva_rate / 100)
        doc.montant_ttc = doc.montant_ht + doc.tva

    def calculate_totals(self, data):
         return self.add_line(data)

    def list_documents(self, data):
        doc_type = data.get('type')
        query = Document.query
        if doc_type:
            query = query.filter_by(type=doc_type)
        
        # Date filtering
        timeframe = data.get('timeframe')
        if timeframe:
            from datetime import datetime as dt
            if timeframe == 'this_month':
                start_date = dt.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(Document.date >= start_date)
            elif timeframe == 'this_year':
                start_date = dt.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(Document.date >= start_date)

        limit = data.get('limit', 10)
        docs = query.order_by(Document.date.desc()).limit(limit).all()
        
        result = [{
            "id": d.id, 
            "numero": d.numero, 
            "client": d.client.raison_sociale if d.client else "?",
            "total_ttc": d.montant_ttc,
            "date": d.date.strftime('%Y-%m-%d')
        } for d in docs]
        return {"status": "success", "data": result}
        
    def get_stats(self, data):
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # Determine timeframe
        timeframe = data.get('timeframe', 'this_month')
        start_date = None
        end_date = datetime.now() + timedelta(days=1)
        
        if timeframe == 'this_month':
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'this_year':
            start_date = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default to all time if not specified or unrecognized
            start_date = datetime(2000, 1, 1)

        # 1. Handle Credit Notes (Avoirs) exclusion like in app.py
        avoir_sources = db.session.query(Document.source_document_id).filter(
            Document.type == 'avoir', 
            Document.source_document_id.isnot(None)
        ).subquery()

        # 2. Main Queries
        def get_totals(doc_type, filters=None):
            q_ht = db.session.query(func.sum(Document.montant_ht)).filter(Document.type == doc_type)
            q_tva = db.session.query(func.sum(Document.tva)).filter(Document.type == doc_type)
            q_ttc = db.session.query(func.sum(Document.montant_ttc)).filter(Document.type == doc_type)
            q_count = db.session.query(func.count(Document.id)).filter(Document.type == doc_type)
            
            if start_date:
                q_ht = q_ht.filter(Document.date >= start_date)
                q_tva = q_tva.filter(Document.date >= start_date)
                q_ttc = q_ttc.filter(Document.date >= start_date)
                q_count = q_count.filter(Document.date >= start_date)

            if doc_type == 'facture':
                q_ht = q_ht.filter(~Document.id.in_(avoir_sources))
                q_tva = q_tva.filter(~Document.id.in_(avoir_sources))
                q_ttc = q_ttc.filter(~Document.id.in_(avoir_sources))
                q_count = q_count.filter(~Document.id.in_(avoir_sources))
            
            if filters == 'paid':
                q_ttc = q_ttc.filter(Document.paid == True)
            
            return {
                "ht": q_ht.scalar() or 0.0,
                "tva": q_tva.scalar() or 0.0,
                "ttc": q_ttc.scalar() or 0.0,
                "count": q_count.scalar() or 0
            }

        factures = get_totals('facture')
        factures_paid = get_totals('facture', filters='paid')
        devis = get_totals('devis')
        bons_commande = get_totals('bon_de_commande')
        
        # Performance Commerciale (Conversion)
        # Using the same logic as app.py: how many Devis in this period became a Facture
        converted_ids = db.session.query(Document.source_document_id).filter(
            Document.type == 'facture',
            Document.source_document_id.isnot(None)
        ).subquery()
        
        q_converted = db.session.query(func.count(Document.id)).filter(
            Document.type == 'devis',
            Document.id.in_(converted_ids)
        )
        if start_date:
            q_converted = q_converted.filter(Document.date >= start_date)
        
        converted_count = q_converted.scalar() or 0
        conversion_rate = (converted_count / devis['count'] * 100) if devis['count'] > 0 else 0.0

        # Stats par Client
        client_stats = db.session.query(
            Client.raison_sociale,
            func.sum(Document.montant_ht).label('total_ht')
        ).join(Document, Document.client_id == Client.id).filter(
            Document.type == 'facture',
            ~Document.id.in_(avoir_sources)
        )
        if start_date:
            client_stats = client_stats.filter(Document.date >= start_date)
        
        top_clients = client_stats.group_by(Client.raison_sociale).order_by(func.sum(Document.montant_ht).desc()).limit(10).all()

        return {
            "status": "success", 
            "data": {
                "timeframe": timeframe,
                "factures": {
                    "count": factures['count'],
                    "total_ht": factures['ht'],
                    "total_tva": factures['tva'],
                    "total_ttc": factures['ttc'],
                    "encaissements": factures_paid['ttc'],
                    "impayes": factures['ttc'] - factures_paid['ttc']
                },
                "devis": {
                    "count": devis['count'],
                    "total_ht": devis['ht']
                },
                "bons_de_commande": {
                    "count": bons_commande['count'],
                    "total_ht": bons_commande['ht'],
                    "total_tva": bons_commande['tva'],
                    "total_ttc": bons_commande['ttc']
                },
                "top_clients": [{"name": c[0], "total_ht": c[1]} for c in top_clients],
                "performance": {
                    "devis_convertis": converted_count,
                    "taux_conversion": round(conversion_rate, 2)
                }
            }
        }

    def delete_client(self, data):
        client_name = data.get('client_name')
        client_id = data.get('client_id')
        
        if not client_id and client_name:
            client = Client.query.filter(Client.raison_sociale.ilike(f"%{client_name}%")).first()
            if not client:
                return {"status": "error", "message": f"Client '{client_name}' non trouvé."}
            client_id = client.id
            
        if not client_id:
            return {"status": "error", "message": "ID ou nom du client requis."}
            
        client = Client.query.get(client_id)
        if not client:
            return {"status": "error", "message": "Client non trouvé."}
            
        name = client.raison_sociale
        db.session.delete(client)
        db.session.commit()
        return {"status": "success", "message": f"Client '{name}' supprimé avec succès."}

    def delete_supplier(self, data):
        name = data.get('supplier_name')
        if not name:
            return {"status": "error", "message": "Nom du fournisseur requis."}
            
        supplier = Supplier.query.filter(Supplier.raison_sociale.ilike(f"%{name}%")).first()
        if not supplier:
            return {"status": "error", "message": f"Fournisseur '{name}' non trouvé."}
            
        real_name = supplier.raison_sociale
        db.session.delete(supplier)
        db.session.commit()
        return {"status": "success", "message": f"Fournisseur '{real_name}' supprimé avec succès."}

    def delete_document(self, data):
        numero = data.get('document_number') or self.context.get('last_document_number')
        if not numero:
            return {"status": "error", "message": "Numéro du document requis."}
            
        doc = Document.query.filter_by(numero=numero).first()
        if not doc:
            return {"status": "error", "message": f"Document '{numero}' non trouvé."}
            
        doc_type = doc.type
        db.session.delete(doc)
        db.session.commit()
        return {"status": "success", "message": f"{doc_type.capitalize()} '{numero}' supprimé avec succès."}

    def convert_document(self, data):
        """
        Converts a document:
        - Devis -> Facture
        - Facture -> Avoir (Credit Note)
        """
        source_number = data.get('source_number') or self.context.get('last_document_number')
        if not source_number:
            return {"status": "error", "message": "Numéro du document source requis."}
            
        source_doc = Document.query.filter_by(numero=source_number).first()
        if not source_doc:
            return {"status": "error", "message": f"Document '{source_number}' non trouvé."}

        target_type = 'facture' if source_doc.type == 'devis' else 'avoir'
        
        # Restriction: Facture -> Avoir only if NOT paid
        if source_doc.type == 'facture' and source_doc.paid:
             return {"status": "error", "message": f"Impossible de créer un avoir pour la facture {source_number} car elle est déjà payée."}

        # Check if already converted
        existing = Document.query.filter_by(type=target_type, source_document_id=source_doc.id).first()
        if existing:
            return {"status": "error", "message": f"Ce document a déjà été converti ({existing.numero})."}
            
        numero = self._generate_document_number(target_type)
        new_doc = Document(
            type=target_type,
            numero=numero,
            date=datetime.now(),
            client_id=source_doc.client_id,
            autoliquidation=source_doc.autoliquidation,
            montant_ht=source_doc.montant_ht,
            tva_rate=source_doc.tva_rate,
            tva=source_doc.tva,
            montant_ttc=source_doc.montant_ttc,
            source_document_id=source_doc.id,
            chantier_reference=source_doc.chantier_reference,
            client_reference=data.get('client_reference', source_doc.client_reference or "REF-CHRONO"),
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        if source_doc.cc_contacts:
            new_doc.cc_contacts = list(source_doc.cc_contacts)
            
        for ligne in source_doc.lignes:
            new_ligne = LigneDocument(
                 designation=ligne.designation,
                 quantite=ligne.quantite,
                 prix_unitaire=ligne.prix_unitaire,
                 total_ligne=ligne.total_ligne,
                 category=ligne.category
            )
            new_doc.lignes.append(new_ligne)
            
        db.session.add(new_doc)
        db.session.commit()
        
        display_name = "Facture" if target_type == 'facture' else "Avoir"
        source_name = "Devis" if source_doc.type == 'devis' else "Facture"
        
        return {
            "status": "success", 
            "message": f"{source_name} {source_number} converti en {display_name} {numero}.",
            "data": {"id": new_doc.id, "document_number": numero, "type": target_type, "pdf_url": f"{request.host_url.rstrip('/')}{url_for('documents.view_pdf', id=new_doc.id)}?v={int(new_doc.updated_at.timestamp())}"}
        }

    def send_email(self, data):
        """
        Sends a document PDF via email.
        """
        doc_number = data.get('document_number') or self.context.get('last_document_number')
        if not doc_number:
            return {"status": "error", "message": "Numéro du document requis."}
            
        doc = Document.query.filter_by(numero=doc_number).first()
        if not doc:
            return {"status": "error", "message": f"Document '{doc_number}' non trouvé."}
            
        # Determine recipients
        recipient_emails = []
        
        # 1. Check for explicit email in data
        if data.get('recipient_email'):
            recipient_emails = [data['recipient_email']]
        
        # 2. Check for recipient_name (fuzzy match in contacts)
        elif data.get('recipient_name'):
            name = data['recipient_name']
            # Search in current document's client contacts
            contact = ClientContact.query.filter(
                ClientContact.client_id == doc.client_id,
                ClientContact.nom.ilike(f"%{name}%")
            ).first()
            if contact and contact.email:
                recipient_emails = [contact.email]
            else:
                return {"status": "error", "message": f"Contact '{name}' non trouvé ou sans email pour ce client."}

        # 3. Fallback to default (CC contacts then client main email)
        if not recipient_emails:
            recipient_emails = [c.email for c in doc.cc_contacts if c.email]
            if not recipient_emails and doc.client and doc.client.email:
                recipient_emails = [doc.client.email]
             
        if not recipient_emails:
            return {"status": "error", "message": "Aucune adresse email spécifiée et aucune adresse par défaut trouvée."}
            
        from services.pdf_generator import generate_pdf_bytes
        from services.mail_service import send_email_with_attachment
        import os
        
        try:
            pdf_bytes = generate_pdf_bytes(doc)
            info = CompanyInfo.query.first()
            doc_type_display = "Bon de Commande" if doc.type == 'bon_de_commande' else doc.type.title()
            subject = f"{doc_type_display} n°{doc.numero} - {info.nom if info else 'STP'}"
            
            body = f"Bonjour,<br><br>Veuillez trouver ci-joint votre {doc_type_display.lower()} n°{doc.numero}.<br><br>Cordialement,"
            filename = f"{doc.type}_{doc.numero}.pdf"
            
            send_email_with_attachment(recipient_emails, subject, body, pdf_bytes, filename)
            
            doc.sent_at = datetime.utcnow()
            db.session.commit()
            
            return {"status": "success", "message": f"Email envoyé à {', '.join(recipient_emails)}"}
        except Exception as e:
            return {"status": "error", "message": f"Erreur d'envoi : {str(e)}"}

    def get_recent_activity(self, data=None):
        """
        Fetches last few changes across documents and clients to 'learn' from UI.
        """
        recent_docs = Document.query.order_by(Document.updated_at.desc()).limit(3).all()
        recent_clients = Client.query.order_by(Client.updated_at.desc()).limit(3).all()
        
        activity = []
        for d in recent_docs:
            activity.append(f"Document {d.numero} ({d.type}) mis à jour le {d.updated_at.strftime('%H:%M')}")
        for c in recent_clients:
            activity.append(f"Client {c.raison_sociale} mis à jour le {c.updated_at.strftime('%H:%M')}")
            
        return {"status": "success", "data": activity}
