from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        # Logo could be added here if available
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Voluntary Contribution Recording System - User Manual', border=0, align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, 'Comprehensive Guide & Frequently Asked Questions', border=0, align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, num, title):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, f'{num}. {title}', align='L', fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('helvetica', '', 11)
        self.multi_cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def sub_title(self, title):
        self.set_font('helvetica', 'B', 11)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

pdf = PDF()
pdf.add_page()

# 1. Introduction
pdf.chapter_title(1, 'Introduction')
text = ("Welcome to the Voluntary Contribution Recording System! This application is designed to securely and efficiently "
        "manage voluntary contributions, maintain a database of Green Book (GB) holders, and generate detailed reports. "
        "The application provides a seamless experience for data entry, bulk Excel imports/exports, and customizable settings.")
pdf.chapter_body(text)

# 2. Entry Form Tab
pdf.chapter_title(2, 'Entry Form Tab')
text = ("The Entry Form is where you record new contributions. It is divided into three sections:\n\n"
        "- Transaction Details: Enter Receipt Number, Country, Place, Currency, and Transaction Date. The FY Period From/To "
        "fields dictate the default period for the payment.\n"
        "- Green Book Holder Verification: Type the GB Number and press Enter (or click Lookup) to automatically pull the name "
        "from your database. If the record doesn't exist, enter the name manually and click 'Update Name in DB'.\n"
        "- Contribution Amounts: Input the amounts for various account heads (Chatrel, Meal Strike, etc.). The TOTAL AMOUNT is "
        "automatically calculated as you type.\n\n"
        "Click 'Save Contribution Entry' when finished. The Receipt Number will automatically increment for your next entry.")
pdf.chapter_body(text)

# 3. GB Database Tab
pdf.chapter_title(3, 'GB Database Tab')
text = ("This tab manages your master list of Green Book holders.\n\n"
        "- Paste from Excel: You can instantly import GB holders by copying two columns (GB Number and Name) from Excel and "
        "clicking 'Paste directly from Excel Clipboard'.\n"
        "- Clean Database: A powerful tool that automatically scans your database, reformats GB numbers (lowercase, no spaces), "
        "capitalizes names correctly, and removes any duplicate entries.\n"
        "- Backup Database: Always click this button periodically to securely save a copy of your database file (.db) to your computer.")
pdf.chapter_body(text)

# 4. Reports & Filters Tab
pdf.chapter_title(4, 'Reports & Filters Tab')
text = ("The Reports tab lets you analyze and export your data.\n\n"
        "- Search & Filter: Filter contributions by Date Range, Country, Place, Currency, Name, GB Number, or Account Head. "
        "Click 'Run Report' to view the results.\n"
        "- Editing Entries: Double-click any row in the generated report to instantly load it into the Entry Form for editing.\n"
        "- Export & Import: Click 'Export Excel' to save your filtered report. You can also 'Import Excel' to batch import entries. "
        "Tip: Always export a blank report first to use as an exact template for importing!\n"
        "- Total Row: A styled 'TOTAL' row appears at the bottom of your report, automatically summing all amounts for easy reading.")
pdf.chapter_body(text)

# 5. Settings Tab
pdf.chapter_title(5, 'Settings Tab')
text = ("Customize the application to fit your exact needs.\n\n"
        "- Form Title & Theme: Change the Office Heading Name or toggle the 'Dark Mode' (Superhero theme).\n"
        "- Periods & Geographies: Set your default Financial Year period, manage default Currencies, and add new Places to Countries.\n"
        "- Manage Account Heads: You can add new fields for contributions. Set the 'Type' to 'Amount' or 'Date', and provide a "
        "default value. You can even click on an existing head to edit it, or drag and drop to reorder how they appear on the Entry Form!")
pdf.chapter_body(text)

pdf.add_page()
# 6. Frequently Asked Questions (FAQ)
pdf.chapter_title(6, 'Frequently Asked Questions (FAQ)')

faqs = [
    ("Q: How do I edit an existing transaction?", 
     "A: Go to the 'Reports & Filters' tab, run a report to find your transaction, and double-click the row. The application will immediately switch to the Entry Form with all details loaded. Once edited, click 'Update Contribution Entry'."),
    
    ("Q: Do I need to worry about Excel changing my date formats when importing?",
     "A: Not at all! The application has a built-in date converter. Whether your dates in Excel are formatted as text or actual Date objects, the system will automatically convert and read them correctly when you click 'Import Excel'."),
     
    ("Q: How do I add a completely new Account Head (like a special donation fund)?",
     "A: Go to the 'Settings' tab. Under 'Manage Account Heads', type the Head Name (e.g., 'Special Donation'), select Type as 'Amount', provide a default amount (usually 0.0), and click 'Save / Edit Head'. It will immediately appear on your Entry Form!"),
     
    ("Q: What does the 'Clean Database' button actually do?",
     "A: It performs maintenance on your Green Book records. If you have accidental duplicates (e.g., 'IN123' and 'in-123'), it merges them, standardizes the formatting, and cleans up capitalization."),
     
    ("Q: Why is my 'TOTAL' row missing when I export to Excel?",
     "A: The 'TOTAL' row is displayed in the application UI for quick visual reading and is intentionally omitted from the Excel export. This ensures that if you re-import that Excel file later, the app doesn't accidentally treat 'TOTAL' as a real person's contribution!"),
     
    ("Q: How do I back up my database?",
     "A: Go to the 'GB Database' tab and click 'Backup Database'. You can choose where to save the .db file on your computer. It is highly recommended to do this regularly!")
]

for q, a in faqs:
    pdf.set_font('helvetica', 'B', 11)
    pdf.multi_cell(0, 7, q, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 7, a, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

pdf.output('User_Manual.pdf')
