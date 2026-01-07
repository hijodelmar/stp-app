from xhtml2pdf import pisa
from datetime import datetime
import os

def generate_pdf():
    output_filename = "documentation_dashboard.pdf"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4 portrait;
                margin: 2cm;
            }}
            body {{
                font-family: Helvetica, sans-serif;
                font-size: 12px;
                color: #333;
            }}
            h1 {{
                color: #002366;
                font-size: 24px;
                margin-bottom: 10px;
                text-align: center;
            }}
            h2 {{
                color: #D4AF37;
                font-size: 16px;
                margin-top: 25px;
                margin-bottom: 10px;
                border-bottom: 2px solid #D4AF37;
                padding-bottom: 5px;
            }}
            p {{
                margin-bottom: 10px;
                line-height: 1.5;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                margin-bottom: 20px;
            }}
            th {{
                background-color: #002366;
                color: #ffffff;
                padding: 10px;
                text-align: left;
                font-weight: bold;
                border: 1px solid #002366;
            }}
            td {{
                padding: 8px;
                border: 1px solid #ccc;
                vertical-align: top;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .footer {{
                position: fixed;
                bottom: 0;
                width: 100%;
                text-align: center;
                font-size: 10px;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <h1>Schéma Logique du Tableau de Bord</h1>
        <p style="text-align: center; color: #666;">Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>

        <h2>1. Indicateurs de Performance (KPIs)</h2>
        <table>
            <thead>
                <tr>
                    <th width="25%">Étiquette</th>
                    <th width="25%">Source de Données</th>
                    <th width="50%">Formule de Calcul</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>Chiffre d'Affaires HT</b></td>
                    <td>Factures</td>
                    <td>Somme(montant_ht) des factures (hors avoirs)</td>
                </tr>
                <tr>
                    <td><b>Total Dépenses HT</b></td>
                    <td>Bons de Commande</td>
                    <td>Somme(montant_ht) des bons de commande fournisseur</td>
                </tr>
                <tr>
                    <td><b>Bénéfice Net HT</b></td>
                    <td>Calculé</td>
                    <td>Chiffre d'Affaires HT - Total Dépenses HT</td>
                </tr>
                <tr>
                    <td><b>Taux Transformation</b></td>
                    <td>Devis</td>
                    <td>(Devis signés / Total Devis) * 100<br/><i>(Un devis est "signé" s'il a généré une facture)</i></td>
                </tr>
            </tbody>
        </table>

        <h2>2. Trésorerie & Statut</h2>
        <table>
            <thead>
                <tr>
                    <th width="25%">Étiquette</th>
                    <th width="25%">Source de Données</th>
                    <th width="50%">Formule de Calcul</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>CA TTC Encaissé</b></td>
                    <td>Factures (Payées)</td>
                    <td>Somme(montant_ttc) des factures marquées comme "Payées"</td>
                </tr>
                <tr>
                    <td><b>Total Impayé</b></td>
                    <td>Calculé</td>
                    <td>Total TTC Facturé - CA TTC Encaissé</td>
                </tr>
                <tr>
                    <td><b>CA Auto-liquidation</b></td>
                    <td>Factures (Spécial)</td>
                    <td>Somme(montant_ht) des factures avec l'option "Auto-liquidation" activée</td>
                </tr>
            </tbody>
        </table>

        <h2>3. Analyse TVA (Nouveau)</h2>
        <table>
            <thead>
                <tr>
                    <th width="25%">Étiquette</th>
                    <th width="25%">Source de Données</th>
                    <th width="50%">Formule de Calcul</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>TVA Collectée</b></td>
                    <td>Factures</td>
                    <td>Somme(tva) de toutes les factures émises</td>
                </tr>
                <tr>
                    <td><b>TVA Déductible</b></td>
                    <td>Bons de Commande</td>
                    <td>Somme(tva) de tous les bons de commande fournisseurs</td>
                </tr>
                <tr>
                    <td><b>TVA Nette à Payer</b></td>
                    <td>Calculé</td>
                    <td>TVA Collectée - TVA Déductible</td>
                </tr>
            </tbody>
        </table>
        
        <div class="footer">
            Document Interne - STP Gestion
        </div>
    </body>
    </html>
    """

    with open(output_filename, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

    if pisa_status.err:
        print(f"Error generating PDF: {pisa_status.err}")
    else:
        print(f"PDF successfully generated: {os.path.abspath(output_filename)}")

if __name__ == "__main__":
    generate_pdf()
