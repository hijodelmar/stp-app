import os
from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Table d'association pour les rôles multiples
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    # Note: La colonne 'role' est conservée temporairement pour la migration mais sera ignorée dans le code
    
    last_active = db.Column(db.DateTime)
    current_session_id = db.Column(db.String(36))
    force_logout_at = db.Column(db.DateTime, nullable=True) # Timestamp before which all sessions are invalid
    
    # Relation vers les rôles multiples
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
        backref=db.backref('users', lazy=True))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(r.name == role_name for r in self.roles)

    def has_any_role(self, roles_list):
        if self.has_role('admin'):
            return True
        return any(r.name in roles_list for r in self.roles)

    def __repr__(self):
        return f'<User {self.username}>'

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    raison_sociale = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True)
    siret = db.Column(db.String(50))
    tva_intra = db.Column(db.String(50))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    
    # Relation avec les documents
    documents = db.relationship('Document', backref='client', lazy=True)

    def __repr__(self):
        return f'<Client {self.raison_sociale}>'

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    raison_sociale = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    siret = db.Column(db.String(50))
    tva_intra = db.Column(db.String(50))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    
    # Relation avec les documents
    documents = db.relationship('Document', backref='supplier', lazy=True)

    def __repr__(self):
        return f'<Supplier {self.raison_sociale}>'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False) # 'devis', 'facture', 'avoir', 'bon_de_commande'
    numero = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    
    montant_ht = db.Column(db.Float, default=0.0)
    tva = db.Column(db.Float, default=0.0)
    montant_ttc = db.Column(db.Float, default=0.0)
    
    autoliquidation = db.Column(db.Boolean, default=False)
    tva_rate = db.Column(db.Float, default=20.0) # Taux de TVA appliqué (en %)
    paid = db.Column(db.Boolean, default=False)  # Payment status for invoices
    client_reference = db.Column(db.String(50)) # Référence client (optionnel)
    chantier_reference = db.Column(db.String(100)) # Référence chantier (optionnel)
    validity_duration = db.Column(db.Integer, default=1) # Durée de validité en mois (pour devis)
    pdf_path = db.Column(db.String(200)) # Chemin vers le fichier PDF archivé
    sent_at = db.Column(db.DateTime, nullable=True) # Date du dernier envoi par email
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    
    # Lien vers le document source (ex: Devis pour une Facture)
    source_document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    source_document = db.relationship('Document', remote_side=[id], backref='generated_documents')
    
    # Token de sécurité pour vérification publique (QR Code)
    secure_token = db.Column(db.String(36), unique=True, nullable=True)
    
    # Relation avec les lignes
    lignes = db.relationship('LigneDocument', backref='document', lazy=True, cascade="all, delete-orphan")

    # Relation avec le contact principal
    contact_id = db.Column(db.Integer, db.ForeignKey('client_contact.id'), nullable=True)
    contact = db.relationship('ClientContact', foreign_keys=[contact_id])

    # Relation Many-to-Many pour les contacts en copie (CC)
    cc_contacts = db.relationship('ClientContact', secondary='document_cc', lazy='subquery',
        backref=db.backref('cc_in_documents', lazy=True))

    def __repr__(self):
        return f'<Document {self.numero}>'

# Table d'association pour les CC
document_cc = db.Table('document_cc',
    db.Column('document_id', db.Integer, db.ForeignKey('document.id'), primary_key=True),
    db.Column('contact_id', db.Integer, db.ForeignKey('client_contact.id'), primary_key=True)
)

class ClientContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    nom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    telephone = db.Column(db.String(20), nullable=True)
    fonction = db.Column(db.String(100), nullable=True)
    
    client = db.relationship('Client', backref=db.backref('contacts', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Contact {self.nom}>'

class LigneDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    
    designation = db.Column(db.String(200), nullable=False)
    quantite = db.Column(db.Float, default=1.0)
    prix_unitaire = db.Column(db.Float, default=0.0)
    total_ligne = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(20), default='fourniture') # 'prestation', 'main_doeuvre', 'fourniture'

    def __repr__(self):
        return f'<Ligne {self.designation}>'

class CompanyInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, default="Service Température Plomberie")
    adresse = db.Column(db.String(200), nullable=False)
    cp = db.Column(db.String(10), nullable=False)
    ville = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    ville_signature = db.Column(db.String(100), nullable=False)
    conditions_reglement = db.Column(db.String(200), nullable=True)
    iban = db.Column(db.String(50), nullable=True)
    footer_info = db.Column(db.Text, nullable=True)
    logo_path = db.Column(db.String(200), nullable=True)
    tva_default = db.Column(db.Float, default=20.0) # Taux de TVA par défaut 

    # Configuration Email (SMTP)
    smtp_server = db.Column(db.String(100), nullable=True)
    smtp_port = db.Column(db.Integer, nullable=True, default=587)
    smtp_user = db.Column(db.String(100), nullable=True)
    smtp_password = db.Column(db.String(100), nullable=True)
    smtp_use_tls = db.Column(db.Boolean, default=True)
    smtp_use_ssl = db.Column(db.Boolean, default=False)
    mail_default_sender = db.Column(db.String(100), nullable=True)
    email_signature = db.Column(db.Text, nullable=True)
    
    # Theme settings
    theme = db.Column(db.String(50), default='default')
    brand_icon = db.Column(db.String(50), default='fas fa-tools')

class AISettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=True)
    provider = db.Column(db.String(20), default='google') # 'google' or 'openai'
    api_key = db.Column(db.String(200), nullable=True)
    model_name = db.Column(db.String(100), nullable=True)
    
    # Audit trail
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AISettings {self.provider} ({"Enabled" if self.enabled else "Disabled"})>'

    @staticmethod
    def get_settings():
        settings = AISettings.query.first()
        if not settings:
            settings = AISettings(
                enabled=True,
                provider='google',
                api_key=os.environ.get('GOOGLE_API_KEY'),
                model_name='gemini-1.5-flash-latest'
            )
            db.session.add(settings)
            db.session.commit()
        return settings

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200), nullable=False)
    amount_ht = db.Column(db.Float, default=0.0)
    tva = db.Column(db.Float, default=0.0)
    amount_ttc = db.Column(db.Float, default=0.0)
    
    # Categorization
    category = db.Column(db.String(50), nullable=False) # 'restaurant', 'transport', 'material', 'urssaf', 'salary', 'other'
    
    # Payment
    payment_method = db.Column(db.String(50), nullable=False) # 'company_card', 'personal_funds', 'transfer'
    is_reimbursed = db.Column(db.Boolean, default=False) # Only relevant for personal_funds
    
    # Proof / Receipt
    proof_path = db.Column(db.String(300), nullable=True) # Path to uploaded file
    
    # Links
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    supplier = db.relationship('Supplier', backref='expenses')
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relation with created_by (User)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    # Relation with attachments
    attachments = db.relationship('ExpenseAttachment', backref='expense', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Expense {self.description} - {self.amount_ttc}€>'

class ExpenseAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False)
    file_path = db.Column(db.String(300), nullable=False) # Relative path
    filename = db.Column(db.String(300), nullable=False) # Original filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ExpenseAttachment {self.filename}>'
