from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, IntegerField, FloatField, BooleanField, SelectField, FieldList, FormField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

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

class LigneDocumentForm(FlaskForm):
    # FormField needs 'clss' not 'form', but we use it in a FieldList in DocumentForm
    # We actually need a meta class or just standard WTForms setup
    class Meta:
        csrf = False # Embedded forms usually don't need independent CSRF

    designation = StringField('Désignation', validators=[DataRequired()])
    quantite = FloatField('Quantité', default=1.0, validators=[DataRequired()])
    prix_unitaire = FloatField('Prix Unitaire HT', default=0.0, validators=[DataRequired()])
    # Total ligne calculated separately or in JS

class DocumentForm(FlaskForm):
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    date = StringField('Date', validators=[DataRequired()]) # We'll use a date picker
    autoliquidation = BooleanField('Auto-liquidation (Pas de TVA)')
    paid = BooleanField('Facture Réglée')
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
    footer_info = TextAreaField('Pied de page (Mentions Légales)', render_kw={"rows": 4})
    logo = FileField('Logo (PNG/JPG)', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images uniquement!')])
    submit = SubmitField('Enregistrer')
