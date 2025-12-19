// Custom JS
document.addEventListener('DOMContentLoaded', function () {

    // Dynamic Devis/Facture Lines
    const container = document.getElementById('lignes-container');
    const addBtn = document.getElementById('add-ligne-btn');
    const template = document.getElementById('ligne-template');
    const form = document.getElementById('devisForm');

    if (container && addBtn && template) {
        // Initial calculation
        calculateTotals();

        // Event listener for inputs to recalculate
        container.addEventListener('input', function (e) {
            if (e.target.classList.contains('calc-input')) {
                calculateRowTotal(e.target.closest('.ligne-item'));
                calculateTotals();
            }
        });

        // Add new line
        addBtn.addEventListener('click', function () {
            const index = container.children.length;
            const newHtml = template.innerHTML.replace(/__idx__/g, index);
            container.insertAdjacentHTML('beforeend', newHtml);
        });

        // Auto-liquidation toggle
        const autoliqCheckbox = document.getElementById('autoliquidation');
        if (autoliqCheckbox) {
            autoliqCheckbox.addEventListener('change', calculateTotals);
        }
    }

    function calculateRowTotal(row) {
        const qtyInput = row.querySelector('input[name*="quantite"]');
        const priceInput = row.querySelector('input[name*="prix_unitaire"]');
        const totalInput = row.querySelector('.total-ligne');

        const qty = parseFloat(qtyInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;
        const total = qty * price;

        totalInput.value = total.toFixed(2);
        return total;
    }

    function calculateTotals() {
        let totalHT = 0;
        const rows = document.querySelectorAll('.ligne-item');

        rows.forEach(row => {
            // Ensure row total is updated
            totalHT += calculateRowTotal(row);
        });

        const autoliqCheckbox = document.getElementById('autoliquidation');
        const autoliq = autoliqCheckbox ? autoliqCheckbox.checked : false;
        const tva = autoliq ? 0 : totalHT * 0.20;
        const totalTTC = totalHT + tva;

        document.getElementById('total-ht').textContent = totalHT.toFixed(2) + ' €';
        document.getElementById('total-tva').textContent = tva.toFixed(2) + ' €';
        document.getElementById('total-ttc').textContent = totalTTC.toFixed(2) + ' €';

        const rowTva = document.getElementById('row-tva');
        const ttcLabel = document.querySelector('td[id="total-ttc"]').previousElementSibling.querySelector('strong');

        if (autoliq) {
            if (rowTva) rowTva.classList.add('d-none');
            if (ttcLabel) ttcLabel.textContent = 'Total HT (Autoliq) :';
        } else {
            if (rowTva) rowTva.classList.remove('d-none');
            if (ttcLabel) ttcLabel.textContent = 'Total TTC :';
        }
    }
});
