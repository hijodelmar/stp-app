from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, IntegerField, FloatField, BooleanField, SelectField, FieldList, FormField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, InputRequired

class ClientForm(FlaskForm):
    raison_sociale = StringField('Raison Sociale / Nom', validators=[DataRequired(), Length(max=100)])
    adresse = StringField('Adresse', validators=[Optional(), Length(max=200)])
    code_postal = StringField('Code Postal', validators=[Optional(), Length(max=10)])
    ville = StringField('Ville', validators=[Optional(), Length(max=100)])
    telephone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    siret = StringField('SIRET', validators=[Optional(), Length(max=50)])
    tva_intra = StringField('TVA Intracommunautaire', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Enregistrer')

    submit = SubmitField('Enregistrer')

class SupplierForm(FlaskForm):
    raison_sociale = StringField('Raison Sociale / Nom', validators=[DataRequired(), Length(max=100)])
    adresse = StringField('Adresse', validators=[Optional(), Length(max=200)])
    code_postal = StringField('Code Postal', validators=[Optional(), Length(max=10)])
    ville = StringField('Ville', validators=[Optional(), Length(max=100)])
    telephone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    siret = StringField('SIRET', validators=[Optional(), Length(max=50)])
    tva_intra = StringField('TVA Intracommunautaire', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Enregistrer')

class LigneDocumentForm(FlaskForm):
    # FormField needs 'clss' not 'form', but we use it in a FieldList in DocumentForm
    # We actually need a meta class or just standard WTForms setup
    class Meta:
        csrf = False # Embedded forms usually don't need independent CSRF

    category = SelectField('Type', choices=[
        ('fourniture', 'Fourniture'),
        ('prestation', 'Prestation'),
        ('main_doeuvre', "Main d'oeuvre")
    ], default='fourniture')
    designation = StringField('Désignation', validators=[DataRequired()])
    quantite = FloatField('Quantité', default=1.0, validators=[InputRequired()])
    prix_unitaire = FloatField('Prix Unitaire HT', default=0.0, validators=[InputRequired()])
    # Total ligne calculated separately or in JS

from wtforms import StringField, SubmitField, IntegerField, FloatField, BooleanField, SelectField, FieldList, FormField, TextAreaField, SelectMultipleField

class DocumentForm(FlaskForm):
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    # Contacts en Copie (CC)
    # Destinataires (Anciennement CC, maintenant destinataires directs)
    cc_contacts = SelectMultipleField('Destinataires', coerce=int, validators=[Optional()], validate_choice=False)
    
    date = StringField('Date', validators=[DataRequired()]) # We'll use a date picker
    validity_duration = IntegerField('Durée de validité (mois)', default=1)
    tva_rate = FloatField('Taux TVA (%)', default=20.0, validators=[InputRequired()])
    autoliquidation = BooleanField('Auto-liquidation (Pas de TVA)')
    paid = BooleanField('Facture Réglée')
    client_reference = StringField('Référence Client', validators=[Optional(), Length(max=30)])
    chantier_reference = StringField('Référence Chantier', validators=[Optional(), Length(max=50)])
    lignes = FieldList(FormField(LigneDocumentForm), min_entries=1)
    submit = SubmitField('Enregistrer')

class BonCommandeForm(FlaskForm):
    supplier_id = SelectField('Fournisseur', coerce=int, validators=[DataRequired()])
    date = StringField('Date', validators=[DataRequired()])
    tva_rate = FloatField('Taux TVA (%)', default=20.0, validators=[InputRequired()])
    autoliquidation = BooleanField('Auto-liquidation (Pas de TVA)')
    client_reference = StringField('Référence Devis Client', validators=[Optional(), Length(max=30)])
    chantier_reference = StringField('Référence Chantier', validators=[Optional(), Length(max=50)])
    lignes = FieldList(FormField(LigneDocumentForm), min_entries=1)
    submit = SubmitField('Enregistrer')

class CompanyInfoForm(FlaskForm):
    nom = StringField('Nom Société', validators=[DataRequired()])
    adresse = StringField('Adresse', validators=[DataRequired()])
    cp = StringField('Code Postal', validators=[DataRequired()])
    ville = StringField('Ville', validators=[DataRequired()])
    telephone = StringField('Téléphone')
    email = StringField('Email', validators=[Optional(), Email()])
    ville_signature = StringField('Ville de Signature (Fait à)', validators=[DataRequired()])
    conditions_reglement = TextAreaField('Conditions de Règlement')
    iban = StringField('IBAN')
    tva_default = FloatField('Taux TVA par défaut (%)', default=20.0)
    footer_info = TextAreaField('Pied de page (Mentions Légales)', render_kw={"rows": 4})
    logo = FileField('Logo (PNG/JPG)', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement!')])
    
    # Email Config
    smtp_server = StringField('Serveur SMTP (ex: smtp.gmail.com)')
    smtp_port = IntegerField('Port SMTP (ex: 587)', validators=[Optional()])
    smtp_user = StringField('Utilisateur SMTP (Email)', validators=[Optional(), Email()])
    smtp_password = StringField('Mot de passe SMTP', render_kw={"type": "password"})
    smtp_use_tls = BooleanField('Utiliser TLS (STARTTLS)', default=True)
    smtp_use_ssl = BooleanField('Utiliser SSL', default=False)
    mail_default_sender = StringField('Nom de l\'expéditeur (ex: STP Gestion)')
    email_signature = TextAreaField('Signature Email (HTML)')
    
    submit = SubmitField('Enregistrer')
