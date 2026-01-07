#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose encoding in PDF template"""

import re

filepath = 'd:/websites/stp/templates/pdf_template.html'

with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Look for NET ... Payer
match = re.search(r'Net .* Payer', content)
if match:
    print(f"Found match: {match.group(0)}")
    print(f"Repr: {repr(match.group(0))}")
else:
    print("Could not find Net ... Payer pattern")

# Also look for TVA Autoliquidation line to verify hardcoded 0.00
match_tva = re.search(r'TVA \(Autoliquidation\)', content)
if match_tva:
    # Print context
    start = max(0, match_tva.start() - 20)
    end = min(len(content), match_tva.end() + 50)
    print(f"TVA Context: {repr(content[start:end])}")
