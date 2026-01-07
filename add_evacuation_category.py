#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add evacuation_dechets category to templates"""

import re

templates = [
    'd:/websites/stp/templates/devis/form.html',
    'd:/websites/stp/templates/factures/form.html',
    'd:/websites/stp/templates/bons_commande/form.html',
]

for filepath in templates:
    try:
        # Try UTF-8 first, fall back to latin-1 if needed
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Add the new option in the select dropdown after main_doeuvre
        # Pattern: find the main_doeuvre option and add evacuation_dechets after it
        pattern = r"(<option value=\"main_doeuvre\">Main d'oeuvre</option>)"
        replacement = r"\1\n                                        <option value=\"evacuation_dechets\">Évacuation des déchets</option>"
        content = re.sub(pattern, replacement, content)
        
        # Also update the template row (ligne-template)
        pattern2 = r"(<option value=\"main_doeuvre\">Main d'oeuvre</option>)"
        content = re.sub(pattern2, replacement, content)
        
        # Update JavaScript to hide quantity field for evacuation_dechets
        # Find the updateLineVisibility function and update it
        old_visibility_logic = r"(const category = categorySelect\.value;[\s\S]*?)(if \(category === 'main_doeuvre'\) \{)"
        new_visibility_logic = r"\1if (category === 'evacuation_dechets') {\n                    qteField.style.display = 'none';\n                    prixField.classList.remove('col-md-3');\n                    prixField.classList.add('col-md-5');\n                } else \2"
        
        content = re.sub(old_visibility_logic, new_visibility_logic, content)
        
        # Write back as UTF-8
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Updated: {filepath}")
    except Exception as e:
        print(f"✗ Error updating {filepath}: {e}")
        import traceback
        traceback.print_exc()

print("\nTemplates updated for evacuation_dechets category!")
