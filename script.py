import re

with open('Rangtsok_app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix Update Title overlap
title_old = '''        btn_save_hdr = ttk.Button(frame_hdr, text="Update Title", command=self.save_title_settings)
        btn_save_hdr.grid(row=0, column=2, padx=(15, 0), pady=5)
        lbl_info_title = tk.Label(frame_hdr, text="\u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_title.grid(row=0, column=2, sticky="e", padx=(0, 5))
        ToolTip(lbl_info_title, "Updates the Office Title displayed\\nat the very top of the application window.")'''
title_new = '''        f_title_btn = ttk.Frame(frame_hdr)
        f_title_btn.grid(row=0, column=2, padx=15, pady=5, sticky="w")
        btn_save_hdr = ttk.Button(f_title_btn, text="Update Title", command=self.save_title_settings)
        btn_save_hdr.pack(side="left")
        lbl_info_title = tk.Label(f_title_btn, text=" \u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_title.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_title, "Updates the Office Title displayed\\nat the very top of the application window.")'''
text = text.replace(title_old, title_new)


# 2. Fix Apply Period overlap
period_old = '''        ttk.Button(frame_other, text="Apply Period", command=self.apply_period_setting).grid(
            row=0, column=4, padx=(10, 0), pady=5, sticky="w"
        )
        lbl_info_period = tk.Label(frame_other, text="\u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_period.grid(row=0, column=4, sticky="e", padx=(0, 10))
        ToolTip(lbl_info_period, "Sets the default Financial Year Period.\\nWhen you add new contributions in the Entry Form,\\nthey will automatically use these dates.")'''
period_new = '''        f_per_btn = ttk.Frame(frame_other)
        f_per_btn.grid(row=0, column=4, sticky="w", padx=10, pady=5)
        btn_per = ttk.Button(f_per_btn, text="Apply Period", command=self.apply_period_setting)
        btn_per.pack(side="left")
        lbl_info_period = tk.Label(f_per_btn, text=" \u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_period.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_period, "Sets the default Financial Year Period.\\nWhen you add new contributions in the Entry Form,\\nthey will automatically use these dates.")'''
text = text.replace(period_old, period_new)


# 3. Fix Add Currency overlap
curr_old = '''        ttk.Button(frame_other, text="\U0001f4b5 Add Currency", command=self.insert_currency).grid(
            row=2, column=2, sticky="w", padx=(5, 0), pady=5
        )
        lbl_info_curr = tk.Label(frame_other, text="\u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_curr.grid(row=2, column=2, sticky="e")
        ToolTip(lbl_info_curr, "Type a currency symbol or code (e.g. USD, EUR)\\nin the box and click Add to make it\\navailable in the dropdowns.")'''
curr_new = '''        f_curr_btn = ttk.Frame(frame_other)
        f_curr_btn.grid(row=2, column=2, sticky="w", padx=5, pady=5)
        btn_curr = ttk.Button(f_curr_btn, text="\U0001f4b5 Add Currency", command=self.insert_currency)
        btn_curr.pack(side="left")
        lbl_info_curr = tk.Label(f_curr_btn, text=" \u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_curr.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_curr, "Type a currency symbol or code (e.g. USD, EUR)\\nin the box and click Add to make it\\navailable in the dropdowns.")'''
text = text.replace(curr_old, curr_new)


# 4. Fix Add Location overlap
loc_old = '''        ttk.Button(frame_other, text="\U0001f4cd Add Location", command=self.add_location).grid(
            row=4, column=4, padx=(5, 0), pady=5, sticky="w"
        )
        lbl_info_loc = tk.Label(frame_other, text="\u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_loc.grid(row=4, column=4, sticky="e")
        ToolTip(lbl_info_loc, "Add a new Place/City to the selected Country.\\nUseful for categorizing contributors\\nby region or chapter.")'''
loc_new = '''        f_loc_btn = ttk.Frame(frame_other)
        f_loc_btn.grid(row=4, column=4, sticky="w", padx=5, pady=5)
        btn_loc = ttk.Button(f_loc_btn, text="\U0001f4cd Add Location", command=self.add_location)
        btn_loc.pack(side="left")
        lbl_info_loc = tk.Label(f_loc_btn, text=" \u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_loc.pack(side="left", padx=(5, 0))
        ToolTip(lbl_info_loc, "Add a new Place/City to the selected Country.\\nUseful for categorizing contributors\\nby region or chapter.")'''
text = text.replace(loc_old, loc_new)


# 5. Add the GB database tooltips correctly this time (my regex failed previously)
gb_new = '''        btn_clipboard.pack(side="left", padx=(5, 0))
        lbl_info_clip = tk.Label(frame_controls, text=" \u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_clip.pack(side="left", padx=(0, 15))
        ToolTip(lbl_info_clip, "How to import:\\n1. Open your Excel file\\n2. Copy two columns: GB Number (left) and Name (right)\\n3. Click this button to paste them instantly into the database!")

        btn_clean = ttk.Button(
            frame_controls, text="\U0001f9f9 Clean Database", command=self.cleanse_gb_database
        )
        btn_clean.pack(side="left", padx=(5, 0))
        lbl_info_clean = tk.Label(frame_controls, text=" \u24d8", fg="#007bff", cursor="hand2", font=("Segoe UI", 10, "bold"))
        lbl_info_clean.pack(side="left", padx=(0, 15))
        ToolTip(lbl_info_clean, "Clean Database:\\nThis scans the entire database for duplicates.\\nIf someone has multiple entries, it merges them, keeping the longest name.\\nIt also removes blank rows and fixes formatting issues.")'''

text = re.sub(r'        btn_clipboard\.pack\(side=\"left\", padx=5\).*?btn_clean\.pack\(side=\"left\", padx=15\)', gb_new, text, flags=re.DOTALL)


with open('Rangtsok_app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done')
