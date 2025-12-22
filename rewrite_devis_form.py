
content = r"""{% extends 'base.html' %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-10">
        <div class="card shadow">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h3 class="mb-0">{{ title }}</h3>
                <a href="{{ url_for('devis.index') }}" class="btn btn-outline-light btn-sm">Retour</a>
            </div>
            <div class="card-body">
                <form method="POST" action="">
                    {{ form.hidden_tag() }}

                    <div class="card mb-4">
                        <div class="card-header bg-light">Informations Client & Chantier</div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    {{ form.client_id.label(class="form-label") }}
                                    {{ form.client_id(class="form-select") }}
                                    {% for error in form.client_id.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                                <div class="col-md-6 mb-3">
                                    {{ form.date.label(class="form-label") }}
                                    {{ form.date(class="form-control", type="date") }}
                                    {% for error in form.date.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                            <!-- Références -->
                            <div class="row">
                                <div class="col-md-12 mb-3">
                                    {{ form.chantier_reference.label(class="form-label") }}
                                    {{ form.chantier_reference(class="form-control") }}
                                    {% for error in form.chantier_reference.errors %}
                                    <div class="text-danger">{{ error }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="card mb-4">
                        <div class="card-body">
                            <div class="form-check form-switch">
                                {{ form.autoliquidation(class="form-check-input") }}
                                {{ form.autoliquidation.label(class="form-check-label") }}
                            </div>
                        </div>
                    </div>

                    <div class="card mb-4">
                        <div class="card-header bg-light d-flex justify-content-between align-items-center">
                            <span>Lignes du devis</span>
                            <button type="button" class="btn btn-sm btn-success" id="add-line">
                                <i class="fas fa-plus"></i> Ajouter une ligne
                            </button>
                        </div>
                        <div class="card-body">
                            <div id="lignes-container">
                                {% for ligne in form.lignes %}
                                <div class="row mb-2 align-items-end ligne-item">
                                    <div class="col-md-2">
                                        {{ ligne.category.label(class="form-label small") }}
                                        {{ ligne.category(class="form-select form-select-sm category-select") }}
                                    </div>
                                    <div class="col-md-4">
                                        {{ ligne.designation.label(class="form-label small") }}
                                        {{ ligne.designation(class="form-control form-control-sm") }}
                                    </div>
                                    <div class="col-md-2 full-fields">
                                        {{ ligne.quantite.label(class="form-label small") }}
                                        {{ ligne.quantite(class="form-control form-control-sm text-end") }}
                                    </div>
                                    <div class="col-md-2 full-fields">
                                        {{ ligne.prix_unitaire.label(class="form-label small") }}
                                        {{ ligne.prix_unitaire(class="form-control form-control-sm text-end") }}
                                    </div>
                                    <div class="col-md-2">
                                        <button type="button" class="btn btn-sm btn-outline-danger w-100 remove-line"
                                            tabindex="-1">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>

                    <!-- Summary Section -->
                    <div class="card mt-3">
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-8"></div>
                                <div class="col-md-4">
                                    <table class="table table-sm">
                                        <tr>
                                            <td class="text-end"><strong>Total HT :</strong></td>
                                            <td class="text-end" id="display-total-ht">0.00 €</td>
                                        </tr>
                                        <tr>
                                            <td class="text-end"><strong>TVA (Autoliquidation) :</strong></td>
                                            <td class="text-end">0.00 €</td>
                                        </tr>
                                        <tr class="table-active">
                                            <td class="text-end"><strong>NET à Payer (HT) :</strong></td>
                                            <td class="text-end" id="display-net-payer">0.00 €</td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="text-end mt-3">
                        <button type="submit" class="btn btn-primary btn-lg">
                            <i class="fas fa-save me-2"></i> Enregistrer
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<div id="ligne-template" class="d-none">
    <div class="row mb-2 align-items-end ligne-item">
        <div class="col-md-2">
            <label class="form-label small">Type</label>
            <select class="form-select form-select-sm category-select" name="lignes-__index__-category">
                <option value="fourniture" selected>Fourniture</option>
                <option value="prestation">Prestation</option>
                <option value="main_doeuvre">Main d'oeuvre</option>
            </select>
        </div>
        <div class="col-md-4">
            <label class="form-label small">Désignation</label>
            <input type="text" class="form-control form-control-sm" name="lignes-__index__-designation">
        </div>
        <div class="col-md-2 full-fields">
            <label class="form-label small">Quantité</label>
            <input type="number" step="0.01" class="form-control form-control-sm text-end"
                name="lignes-__index__-quantite" value="1.0">
        </div>
        <div class="col-md-2 full-fields">
            <label class="form-label small">Prix Unitaire</label>
            <input type="number" step="0.01" class="form-control form-control-sm text-end"
                name="lignes-__index__-prix_unitaire" value="0.0">
        </div>
        <div class="col-md-2">
            <button type="button" class="btn btn-sm btn-outline-danger w-100 remove-line" tabindex="-1">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function() {
        console.log("DOM Loaded - Devis Form Script Init");
        
        function calculateTotals() {
            let totalHT = 0;
            const rows = document.querySelectorAll('.ligne-item');
            
            rows.forEach(row => {
                const categorySelect = row.querySelector('.category-select');
                const qteInput = row.querySelector('input[name*="quantite"]');
                const prixInput = row.querySelector('input[name*="prix_unitaire"]');
                
                if (categorySelect && qteInput && prixInput) {
                    const category = categorySelect.value;
                    const qte = parseFloat(qteInput.value) || 0;
                    const prix = parseFloat(prixInput.value) || 0;
                    
                    if (category === 'main_doeuvre') {
                        totalHT += prix;
                    } else if (category !== 'prestation') {
                        totalHT += qte * prix;
                    }
                }
            });
            
            const totalEl = document.getElementById('display-total-ht');
            const netEl = document.getElementById('display-net-payer');
            if(totalEl) totalEl.textContent = totalHT.toFixed(2) + ' €';
            if(netEl) netEl.textContent = totalHT.toFixed(2) + ' €';
        }
        
        function updateLineVisibility(row) {
            const select = row.querySelector('.category-select');
            const qteInput = row.querySelector('input[name*="quantite"]');
            const prixInput = row.querySelector('input[name*="prix_unitaire"]');
            const desInput = row.querySelector('input[name*="designation"]'); 
            
            if(!select || !qteInput || !prixInput) return;

            const qteWrapper = qteInput.closest('.full-fields'); 
            const prixWrapper = prixInput.closest('.full-fields');
            const desWrapper = row.querySelector('.col-md-4') || desInput?.parentElement;

            if(!qteWrapper || !prixWrapper || !desWrapper) return;

            const prixLabel = prixWrapper.querySelector('label');
            const category = select.value;
            
            // Reset visibility (display) and classes
            qteWrapper.style.display = 'block';
            prixWrapper.style.display = 'block';
            desWrapper.className = 'col-md-4'; // Reset to default width

            if (category === 'prestation') {
                qteWrapper.style.display = 'none';
                prixWrapper.style.display = 'none';
                desWrapper.className = 'col-md-8';
                
                qteInput.value = '';
                prixInput.value = '';

            } else if (category === 'main_doeuvre') {
                qteWrapper.style.display = 'none';
                qteInput.value = 1; 
                
                if(prixLabel) prixLabel.textContent = "Montant Total";
                desWrapper.className = 'col-md-6';

            } else {
                if(prixLabel) prixLabel.textContent = "Prix Unitaire";
            }
            
            calculateTotals();
        }

        const container = document.getElementById('lignes-container');
        if(container){
            container.addEventListener('change', function(e) {
                if (e.target.classList.contains('category-select')) {
                    updateLineVisibility(e.target.closest('.ligne-item'));
                }
            });
            
            container.addEventListener('input', function(e) {
                if (e.target.name && (e.target.name.includes('quantite') || e.target.name.includes('prix_unitaire'))) {
                    calculateTotals();
                }
            });
            
            document.querySelectorAll('.ligne-item').forEach(updateLineVisibility);
            calculateTotals();

            const addButton = document.getElementById('add-line');
            if (addButton) {
                let lineIndex = {{ form.lignes|length }};
                const template = document.getElementById('ligne-template').innerHTML;
                
                addButton.addEventListener('click', function() {
                    const newHtml = template.replace(/__index__/g, lineIndex);
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = newHtml;
                    const newRow = tempDiv.firstElementChild;
                    container.appendChild(newRow);
                    updateLineVisibility(newRow);
                    lineIndex++;
                });
            }
            
            container.addEventListener('click', function(e) {
                if (e.target.closest('.remove-line')) {
                    const row = e.target.closest('.ligne-item');
                    if (document.querySelectorAll('.ligne-item').length > 1) {
                        row.remove();
                        calculateTotals();
                    } else {
                        alert('Le document doit contenir au moins une ligne.');
                    }
                }
            });
        }
    });
</script>
{% endblock %}
"""

with open('d:/websites/stp/templates/devis/form.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Rewrite complete")
