from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from extensions import db
from models import Document, LigneDocument, Client
from forms import DocumentForm

bp = Blueprint('avoirs', __name__)

@bp.route('/')
def index():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        documents = Document.query.join(Client).filter(
            (Document.type == 'avoir') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        documents = Document.query.filter_by(type='avoir').order_by(Document.date.desc()).all()
    return render_template('avoirs/index.html', documents=documents)

@bp.route('/add', methods=['GET', 'POST'])
def add():
    form = DocumentForm()
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if form.validate_on_submit():
        year = datetime.now().year
        count = Document.query.filter(Document.numero.like(f'A-{year}-%')).count()
        numero = f'A-{year}-{count + 1:04d}'

        document = Document(
            type='avoir',
            numero=numero,
            date=datetime.strptime(form.date.data, '%Y-%m-%d'),
            client_id=form.client_id.data,
            autoliquidation=form.autoliquidation.data
        )
        
        total_ht = 0
        for ligne_form in form.lignes:
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=ligne_form.quantite.data,
                prix_unitaire=ligne_form.prix_unitaire.data,
                total_ligne=ligne_form.quantite.data * ligne_form.prix_unitaire.data
            )
            total_ht += l.total_ligne
            document.lignes.append(l)
        
        document.montant_ht = total_ht
        if document.autoliquidation:
            document.tva = 0
        else:
            document.tva = total_ht * 0.20
        document.montant_ttc = document.montant_ht + document.tva
        
        db.session.add(document)
        db.session.commit()
        flash(f'Avoir {numero} créé avec succès.', 'success')
        return redirect(url_for('avoirs.index'))
    
    if not form.date.data:
        form.date.data = datetime.now().strftime('%Y-%m-%d')
        
    return render_template('factures/form.html', form=form, title="Nouvel Avoir")

@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        flash('Document invalide.', 'danger')
        return redirect(url_for('avoirs.index'))

    form = DocumentForm(obj=document)
    form.client_id.choices = [(c.id, c.raison_sociale) for c in Client.query.order_by(Client.raison_sociale).all()]

    if request.method == 'GET':
        if document.date:
            form.date.data = document.date.strftime('%Y-%m-%d')

    if form.validate_on_submit():
        # Supprimer l'ancien PDF car le document va être modifié
        from services.pdf_generator import delete_old_pdf
        delete_old_pdf(document)
        
        document.client_id = form.client_id.data
        document.date = datetime.strptime(form.date.data, '%Y-%m-%d')
        document.autoliquidation = form.autoliquidation.data
        
        document.lignes = []
        
        total_ht = 0
        for ligne_form in form.lignes:
            l = LigneDocument(
                designation=ligne_form.designation.data,
                quantite=ligne_form.quantite.data,
                prix_unitaire=ligne_form.prix_unitaire.data,
                total_ligne=ligne_form.quantite.data * ligne_form.prix_unitaire.data
            )
            total_ht += l.total_ligne
            document.lignes.append(l)
        
        document.montant_ht = total_ht
        if document.autoliquidation:
            document.tva = 0
        else:
            document.tva = total_ht * 0.20
        document.montant_ttc = document.montant_ht + document.tva
        
        db.session.commit()
        flash(f'Avoir {document.numero} modifié avec succès.', 'success')
        return redirect(url_for('avoirs.index'))

    return render_template('factures/form.html', form=form, title=f"Modifier Avoir {document.numero}")


@bp.route('/convert/choose')
def choose_facture():
    q = request.args.get('q')
    if q:
        search = f"%{q}%"
        facture_list = Document.query.join(Client).filter(
            (Document.type == 'facture') &
            ((Document.numero.ilike(search)) |
            (Client.raison_sociale.ilike(search)) |
            (db.cast(Document.date, db.String).ilike(search)))
        ).order_by(Document.date.desc()).all()
    else:
        facture_list = Document.query.filter_by(type='facture').order_by(Document.date.desc()).all()
        
    return render_template('avoirs/choose_facture.html', documents=facture_list)

@bp.route('/convert/<int:id>')
def convert_from_facture(id):
    facture = Document.query.get_or_404(id)
    if facture.type != 'facture':
         flash('Document non valide pour conversion.', 'danger')
         return redirect(url_for('factures.index'))
         
    year = datetime.now().year
    count = Document.query.filter(Document.numero.like(f'A-{year}-%')).count()
    numero = f'A-{year}-{count + 1:04d}'
    
    avoir = Document(
        type='avoir',
        numero=numero,
        date=datetime.now(),
        client_id=facture.client_id,
        autoliquidation=facture.autoliquidation,
        montant_ht=facture.montant_ht,
        tva=facture.tva,
        montant_ttc=facture.montant_ttc,
        source_document_id=facture.id
    )
    
    # Clone lines
    for ligne in facture.lignes:
        new_ligne = LigneDocument(
             designation=ligne.designation,
             quantite=ligne.quantite,
             prix_unitaire=ligne.prix_unitaire,
             total_ligne=ligne.total_ligne
        )
        avoir.lignes.append(new_ligne)
    
    db.session.add(avoir)
    db.session.commit()
    flash(f'Facture convertie en Avoir {numero}.', 'success')
    return redirect(url_for('avoirs.index'))

@bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    document = Document.query.get_or_404(id)
    if document.type != 'avoir':
        flash('Opération non autorisée.', 'danger')
        return redirect(url_for('avoirs.index'))
        
    db.session.delete(document)
    db.session.commit()
    flash('Avoir supprimé.', 'info')
    return redirect(url_for('avoirs.index'))
