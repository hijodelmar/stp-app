from app import create_app, db
from models import CompanyInfo
import sqlalchemy

app = create_app()

def migrate():
    with app.app_context():
        # Create table if not exists using sqlalchemy inspector or just create_all
        # create_all deals with tables that don't exist
        db.create_all()
        
        # Check if we need to insert default row
        info = CompanyInfo.query.first()
        if not info:
            print("Creating default CompanyInfo...")
            default_info = CompanyInfo(
                nom="Service Température Plomberie",
                adresse="95 av du président Wilson",
                cp="93100",
                ville="Montreuil",
                telephone="06 23 74 10 41",
                email="stp93100@gmail.com",
                ville_signature="MONTREUIL",
                conditions_reglement="Conditions de règlement : par chèque à réception de facture",
                iban="FR7610207000172221037768278",
                footer_info="Service Temperature Plomberie, Capital: 6000 Euros – RCS BOBIGNY 820266450\nsiren: 82026645000015 – TVA: FR 57820266450 – NAF: 4322A\nAssurances N°193370566 M 001"
            )
            db.session.add(default_info)
            db.session.commit()
            print("Default CompanyInfo created.")
        else:
            print("CompanyInfo already exists.")

if __name__ == '__main__':
    migrate()
