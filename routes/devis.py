from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from extensions import db
from models import Document, LigneDocument, Client, CompanyInfo, ClientContact

from forms import DocumentForm
from flask_login import login_required, current_user
from utils.auth import role_required

bp = Blueprint('devis', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'reporting', 'devis_admin'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'devis') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        documents = Document.query.filter_by(type='devis').order_by(Document.date.desc()).all()
    return render_template('devis/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def add():
    # ...
    if form.validate_on_submit():
        # ...
        document = Document(
            type='devis',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            # Contacts (Manual handling for dynamic fields)
            contact_id=form.contact_id.data if form.contact_id.data else None,
            autoliquidation=form.autoliquidation.data,
            # ...
        )

        # Handle CC Contacts
        if form.cc_contacts.data:
            # Filter empty strings match IDs
            cc_ids = [int(id) for id in form.cc_contacts.data if id]
            if cc_ids:
                contacts = ClientContact.query.filter(ClientContact.id.in_(cc_ids)).all()
                document.cc_contacts = contacts
        
        # ...

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def edit(id):
    # ...
    if form.validate_on_submit():
        # ...
        document.client_id = form.client_id.data
        if form.contact_id.data:
            document.contact_id = form.contact_id.data
        else:
            document.contact_id = None
            
        # Handle CC Contacts (Update relation)
        if form.cc_contacts.data:
             cc_ids = [int(id) for id in form.cc_contacts.data if id]
             if cc_ids:
                 contacts = ClientContact.query.filter(ClientContact.id.in_(cc_ids)).all()
                 document.cc_contacts = contacts
             else:
                 document.cc_contacts = []
        else:
             document.cc_contacts = []
             
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        # ...
from utils.auth import role_required

bp = Blueprint('devis', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'manager', 'reporting', 'devis_admin'])
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'devis') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        documents = Document.query.filter_by(type='devis').order_by(Document.date.desc()).all()
    return render_template('devis/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def add():
    form = DocumentForm()
    # Populate client choices
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        # Génération numéro (Logique simple pour l'instant: D-{YYYY}-{Count+1})
        year = datetime.now().year
        count = Document.query.filter(Document.numero.like(f'D-{year}-%')).count()
        numero = f'D-{year}-{count + 1:04d}'

        document = Document(
            type='devis',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data,
            tva_rate=form.tva_rate.data,
            client_reference=form.client_reference.data,
            chantier_reference=form.chantier_reference.data,
            validity_duration=form.validity_duration.data,
            created_by_id=current_user.id,
            updated_by_id=current_user.id
        )
        
        # Handle optional Primary Contact - REMOVED
        # if form.contact_id.data:
        #    document.contact_id = form.contact_id.data

        # Handle CC Contacts
        if form.cc_contacts.data:
            # form.cc_contacts.data is already a list of ints because coerce=int
            cc_ids = form.cc_contacts.data
            if cc_ids:
                contacts = ClientContact.query.filter(ClientContact.id.in_(cc_ids)).all()
                document.cc_contacts = contacts
        
        # Calcul des totaux et ajout des lignes
        total_ht = 0
        for ligne_form in form.lignes:
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=ligne_form.quantite.data,
                prix_unitaire=ligne_form.prix_unitaire.data,
                total_ligne=ligne_form.quantite.data * ligne_form.prix_unitaire.data,
                category=ligne_form.category.data
            )
            total_ht += l.total_ligne
            document.lignes.append(l)
        
        document.montant_ht = total_ht
        if document.autoliquidation:
            document.tva = 0
        else:
            document.tva = total_ht * (document.tva_rate / 100)
        document.montant_ttc = document.montant_ht + document.tva
        
        db.session.add(document)
        db.session.commit()
        flash(f'Devis {numero} créé avec succès.', 'success')
        return redirect(url_for('devis.index'))
    
    # Default date today
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    # Default TVA from Company Settings
    if request.method == 'GET' and not form.tva_rate.data:
        info = CompanyInfo.query.first()
        if info:
            form.tva_rate.data = info.tva_default
    
    if form.errors:
        flash(f"Erreur de validation: {form.errors}", 'danger')

    return render_template('devis/form.html', form=form, title="Nouveau Devis")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'devis':
        flash('Document invalide.', 'danger')
        return redirect(url_for('devis.index'))

    form = DocumentForm(obj=document)
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if request.method == 'GET':
        # Pre-populate date correctly (string format for date input)
        if document.date:
            form.date.data = document.date.strftime('%Y-%m-%d')
        
        # Manually populate CC contacts with IDs for the form
        if document.cc_contacts:
            form.cc_contacts.data = [c.id for c in document.cc_contacts]

    if form.validate_on_submit():
        # Supprimer l'ancien PDF car le document va être modifié
        from services.pdf_generator import delete_old_pdf
        delete_old_pdf(document)
        
        document.client_id = form.client_id.data
        
        # Handle optional Primary Contact - REMOVED
        # document.contact_id = form.contact_id.data if form.contact_id.data else None

        # Handle CC Contacts
        document.cc_contacts = [] # Clear old associations
        if form.cc_contacts.data:
            cc_ids = form.cc_contacts.data
            if cc_ids:
                contacts = ClientContact.query.filter(ClientContact.id.in_(cc_ids)).all()
                document.cc_contacts = contacts
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        document.autoliquidation = form.autoliquidation.data
        document.tva_rate = form.tva_rate.data
        document.client_reference = form.client_reference.data
        document.chantier_reference = form.chantier_reference.data
        document.validity_duration = form.validity_duration.data
        document.updated_by_id = current_user.id
        document.updated_at = datetime.utcnow()
        
        # Update lines: Clear old ones and add new ones
        document.lignes = [] 
        
        total_ht = 0
        for ligne_form in form.lignes:
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=ligne_form.quantite.data,
                prix_unitaire=ligne_form.prix_unitaire.data,
                total_ligne=ligne_form.quantite.data * ligne_form.prix_unitaire.data,
                category=ligne_form.category.data
            )
            total_ht += l.total_ligne
            document.lignes.append(l)
        
        document.montant_ht = total_ht
        if document.autoliquidation:
            document.tva = 0
        else:
            document.tva = total_ht * (document.tva_rate / 100)
        document.montant_ttc = document.montant_ht + document.tva
        
        db.session.commit()
        flash(f'Devis {document.numero} modifié avec succès.', 'success')
        return redirect(url_for('devis.index'))

    if form.errors:
        flash(f"Erreur de validation: {form.errors}", 'danger')

    return render_template('devis/form.html', form=form, title=f"Modifier Devis {document.numero}")

@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['admin', 'manager', 'devis_admin'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'devis':
        abort(403)
        
    # Check if a facture was generated from this devis
    if document.generated_documents:
        flash(f"Impossible de supprimer le devis {document.numero} car une facture ou un avoir y est lié.", 'danger')
        return redirect(url_for('devis.index'))
        
    db.session.delete(document)
    db.session.commit()
    flash('Devis supprimé.', 'info')
    return redirect(url_for('devis.index'))
