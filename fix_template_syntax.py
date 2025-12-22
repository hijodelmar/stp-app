"""
Fix the Jinja2 template syntax error in devis/form.html and factures/form.html
"""
import re

def fix_file(filepath):
    """Fix the malformed Jinja2 template in the specified file"""
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match the broken block:
    # let lineIndex = {{ form.lignes| length
    #             }
    #         };
    
    # Replace with: let lineIndex = {{ form.lignes|length }};
    
    # Use regex to find and replace the broken pattern
    # This pattern matches across multiple lines
    pattern = r'let lineIndex = \{\{ form\.lignes\|\s*length\s*\n\s*\}\s*\n\s*\};'
    replacement = r'let lineIndex = {{ form.lignes|length }};'
    
    content_fixed = re.sub(pattern, replacement, content)
    
    # Check if any changes were made
    if content == content_fixed:
        print(f"  No changes needed (or pattern didn't match)")
        # Try a simpler pattern
        pattern2 = r'\{\{ form\.lignes\|\s*length[^}]*$'
        matches = re.findall(pattern2, content, re.MULTILINE)
        if matches:
            print(f"  Found unclosed Jinja2 tags: {matches}")
            # Manual fix: replace the specific broken lines
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '{{ form.lignes| length' in line and '}}' not in line:
                    print(f"  Found broken line at {i+1}: {line[:80]}")
                    # Fix this line and the next few
                    if i + 2 < len(lines):
                        # Check if next lines are the closing braces
                        if '}' in lines[i+1] and '};' in lines[i+2]:
                            # Replace these 3 lines with the correct single line
                            indent = len(line) - len(line.lstrip())
                            lines[i] = ' ' * indent + 'let lineIndex = {{ form.lignes|length }};'
                            lines[i+1] = ''  # Remove
                            lines[i+2] = ''  # Remove
                            print(f"  Fixed lines {i+1} to {i+3}")
            
            content_fixed = '\n'.join(line for line in lines if line is not None)
    else:
        print(f"  Changes applied successfully")
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content_fixed)
    
    print(f"  Done!\n")

if __name__ == '__main__':
    fix_file('d:/websites/stp/templates/devis/form.html')
    fix_file('d:/websites/stp/templates/factures/form.html')
    print("All files processed. Please restart your Flask server.")
