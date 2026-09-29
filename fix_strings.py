import re

with open('Rangtsok_app.py', 'r', encoding='utf-8') as f:
    text = f.read()

def replacer(match):
    s = match.group(0)
    # Convert ToolTip(lbl, "multi\nline") to ToolTip(lbl, \"\"\"multi\nline\"\"\")
    s = s.replace('ToolTip(', 'ToolTip_REPLACEME_')
    
    # We find the string literal inside. It starts with " and ends with ")
    # Actually, simpler:
    return s

# Let's just do direct string replacements for the ones that are broken
text = text.replace('ToolTip(lbl_info_title, "Updates the Office Title displayed\\nat the very top of the application window.")', 'ToolTip(lbl_info_title, \"\"\"Updates the Office Title displayed\\nat the very top of the application window.\"\"\")')
text = text.replace('ToolTip(lbl_info_period, "Sets the default Financial Year Period.\\nWhen you add new contributions in the Entry Form,\\nthey will automatically use these dates.")', 'ToolTip(lbl_info_period, \"\"\"Sets the default Financial Year Period.\\nWhen you add new contributions in the Entry Form,\\nthey will automatically use these dates.\"\"\")')
text = text.replace('ToolTip(lbl_info_curr, "Type a currency symbol or code (e.g. USD, EUR)\\nin the box and click Add to make it\\navailable in the dropdowns.")', 'ToolTip(lbl_info_curr, \"\"\"Type a currency symbol or code (e.g. USD, EUR)\\nin the box and click Add to make it\\navailable in the dropdowns.\"\"\")')
text = text.replace('ToolTip(lbl_info_loc, "Add a new Place/City to the selected Country.\\nUseful for categorizing contributors\\nby region or chapter.")', 'ToolTip(lbl_info_loc, \"\"\"Add a new Place/City to the selected Country.\\nUseful for categorizing contributors\\nby region or chapter.\"\"\")')
text = text.replace('ToolTip(lbl_info_logic, "Date Logic Explanation:\\n\\n1. Start/End Dates are auto-filled from your \'FY Period From/To\' settings.\\n2. If you change a date here, the app assumes you are paying for that specific period.\\n3. This allows you to log Back-Arrears or Advance Payments separate from the current FY.\\n4. Syncs automatically with the main FY fields at the top!")', 'ToolTip(lbl_info_logic, \"\"\"Date Logic Explanation:\\n\\n1. Start/End Dates are auto-filled from your \'FY Period From/To\' settings.\\n2. If you change a date here, the app assumes you are paying for that specific period.\\n3. This allows you to log Back-Arrears or Advance Payments separate from the current FY.\\n4. Syncs automatically with the main FY fields at the top!\"\"\")')

# wait, they have literal newlines in the file, so \n won't match. 
