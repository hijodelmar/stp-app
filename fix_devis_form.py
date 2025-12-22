import re

# Read the file
with open('d:/websites/stp/templates/devis/form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the broken Jinja2 expression on line ~244
# Replace the incomplete expression with the complete one
content = content.replace(
    '{{ form.lignes| length\n            }\n        };',
    '{{ form.lignes|length }};'
)

# Remove duplicate template declaration (should only appear once in addButton block)
lines = content.split('\n')
in_addbutton_block = False
first_template_seen = False
fixed_lines = []

for i, line in enumerate(lines):
    if 'const template = document.getElementById' in line:
        if not first_template_seen:
            first_template_seen = True
            fixed_lines.append(line)
        else:
            # Skip duplicate
            continue
    else:
        fixed_lines.append(line)

content = '\n'.join(fixed_lines)

# Write back
with open('d:/websites/stp/templates/devis/form.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed devis form.html")
