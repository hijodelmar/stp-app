from datetime import datetime

class MockClient:
    raison_sociale = "Client Exemple SARL"
    adresse = "12 Rue de la Démonstration"
    code_postal = "75001"
    ville = "Paris"
    tva_intra = "FR12345678901"

class MockLigne:
    def __init__(self, designation, qte, pu):
        self.designation = designation
        self.quantite = qte
        self.prix_unitaire = pu
        self.total_ligne = qte * pu

class MockDocument:
    numero = "FACT-2025-001"
    type = "facture"
    date = datetime.now()
    client = MockClient()
    lignes = [
        MockLigne("Installation Chaudière XYZ", 1, 1500.00),
        MockLigne("Kit Raccordement", 2, 45.50),
        MockLigne("Main d'oeuvre (Heures)", 4, 60.00)
    ]
    montant_ht = 1831.00
    tva = 366.20
    montant_ttc = 2197.20
    autoliquidation = False

def get_mock_document():
    return MockDocument()
