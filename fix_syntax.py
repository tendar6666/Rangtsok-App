with open('Rangtsok_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_tooltip = False
for i, line in enumerate(lines):
    if not in_tooltip and 'ToolTip(' in line and '")' not in line:
        # It's a multiline tooltip starting
        lines[i] = line.replace(', "', ', """')
        in_tooltip = True
    elif in_tooltip:
        if '")' in line:
            lines[i] = line.replace('")', '""")')
            in_tooltip = False
        
with open('Rangtsok_app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done syntax fix')
