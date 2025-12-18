# GUIDE D'INSTALLATION ET D'UTILISATION - APPLICATION STP

## 1. Installation

### Prérequis
- Python 3 installé sur la machine.
- Un navigateur web.

### Étapes d'installation
1. **Ouvrir un terminal** dans le dossier du projet (`d:\websites\stp`).
2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
   *Note : Le générateur PDF (xhtml2pdf) est inclus et compatible Windows.*
3. **Initialiser la base de données** :
   ```bash
   python init_db.py
   ```
   (Cela crée `instance/app.db`).

### Lancement
Exécutez :
```bash
python app.py
```
Accédez à `http://127.0.0.1:5001`

---

## 2. Utilisation
- **Clients**: Créez vos clients ici.
- **Devis**: Créez des devis. Une fois validé, transformez un devis en facture via le bouton vert ($).
- **Factures / Avoirs**: Créez directement ou visualisez vos factures.
- **PDF**: Cliquez sur "PDF" pour télécharger/imprimer vos documents.
- **Recherche**: Utilisez la barre de recherche en haut de chaque liste pour filtrer par client, numéro ou année.
- **Conversion Devis -> Facture**: Cochez l'icône "Transformer en Facture" sur la liste des devis, ou allez dans "Factures > Créer depuis Devis" pour chercher et convertir un devis.
- **Paramètres**: Configurez les infos de votre société (Adresse, IBAN, Logo...) via le menu "Paramètres" (Roue crantée).

## 3. Maintenance
- Sauvegardez régulièrement le fichier `instance/app.db` et le dossier `archives/`.
