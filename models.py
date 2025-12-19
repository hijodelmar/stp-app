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

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False) # 'devis', 'facture', 'avoir'
    numero = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    montant_ht = db.Column(db.Float, default=0.0)
    tva = db.Column(db.Float, default=0.0)
    montant_ttc = db.Column(db.Float, default=0.0)
    
    autoliquidation = db.Column(db.Boolean, default=False)
    paid = db.Column(db.Boolean, default=False)  # Payment status for invoices
    client_reference = db.Column(db.String(30))  # Référence client (max 30 chars)
    chantier_reference = db.Column(db.String(50)) # Référence du chantier (max 50 chars)
    pdf_path = db.Column(db.String(200)) # Chemin vers le fichier PDF archivé
    
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
    
    # Relation avec les lignes
    lignes = db.relationship('LigneDocument', backref='document', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Document {self.numero}>'

class LigneDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    
    designation = db.Column(db.String(200), nullable=False)
    quantite = db.Column(db.Float, default=1.0)
    prix_unitaire = db.Column(db.Float, default=0.0)
    total_ligne = db.Column(db.Float, default=0.0)

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

    def __repr__(self):
        return f'<CompanyInfo {self.nom}>'
