
## USER

SQLite is actually pre-installed on Ubuntu 24.04 LTS, but let me show you how to verify, set up the Python interface, and install useful tools for managing your paper database.

---

## Kimi K2.5

  SQLite is actually **pre-installed** on Ubuntu 24.04 LTS, but let me show you how to verify, set up the Python interface, and install useful tools for managing your paper database.

## 1. Verify SQLite Installation

```bash
# Check if sqlite3 command line tool is installed
sqlite3 --version
# Output: 3.45.1 2024-01-30 16:01:20 e876e51a0ed5c5b3126f52e532044363a014fc74...

# Check Python sqlite3 module (built-in)
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

If for some reason it's missing:
```bash
sudo apt update
sudo apt install sqlite3 libsqlite3-dev
```

## 2. Install Python Database Libraries

In your **ML venv**:

```bash
# Activate your environment
source ~/venvs/ML/bin/activate

# Core libraries (most are already included)
pip install sqlite3-bro  # Enhanced SQLite browser for Python

# For the paper pipeline features we discussed
pip install pdf2doi bibtexparser pdfplumber requests

# Optional: Better SQLite REPL
pip install litecli
```

## 3. Install GUI Database Browser (Optional but Recommended)

```bash
# Option 1: DB Browser for SQLite (GUI tool)
sudo apt install sqlitebrowser

# Option 2: DBeaver (more powerful, supports multiple DBs)
sudo snap install dbeaver-ce

# Option 3: TablePlus (modern UI, proprietary but free tier)
wget -qO - https://deb.tableplus.com/apt.tableplus.com.gpg.key | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://deb.tableplus.com/$(lsb_release -cs) tableplus"
sudo apt update
sudo apt install tableplus
```

## 4. Quick Setup Test

Create a test database to verify everything works:

```bash
# Create test database
sqlite3 ~/test_papers.db <<EOF
CREATE TABLE papers (
    id INTEGER PRIMARY KEY,
    title TEXT,
    doi TEXT,
    year INTEGER
);
INSERT INTO papers (title, doi, year) VALUES ('Test Paper', '10.1000/test', 2024);
SELECT * FROM papers;
EOF
```

Or in Python:

```python
#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# Test database creation
db_path = Path.home() / "test_papers.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stem TEXT UNIQUE,
        title TEXT,
        doi TEXT,
        pdf_path TEXT,
        md_path TEXT,
        bibtex TEXT
    )
''')

# Test insert
cursor.execute('''
    INSERT OR REPLACE INTO papers (stem, title, doi) 
    VALUES (?, ?, ?)
''', ('test_paper', 'Quantum DFT Methods', '10.1000/quantum.2024'))

conn.commit()

# Verify
cursor.execute("SELECT * FROM papers")
print(cursor.fetchall())

conn.close()
print(f"✓ Database created at: {db_path}")
```

## 5. Command Line Usage Tips

```bash
# Open database interactively
sqlite3 ~/papers.db

# Useful SQLite commands:
.help              # Show all commands
.tables            # List tables
.schema papers     # Show table structure
SELECT * FROM papers LIMIT 5;
.mode column       # Pretty print columns
.headers on        # Show column names
.quit              # Exit

# Export to CSV
sqlite3 ~/papers.db -csv "SELECT * FROM papers" > papers.csv

# Import from CSV
sqlite3 ~/papers.db ".import papers.csv papers"
```

## 6. For Your Paper Pipeline

Since SQLite is file-based, no server setup needed. Just ensure your pipeline has write permissions:

```bash
# Create directory for your paper database
mkdir -p ~/paper_library
cd ~/paper_library

# The database file will be created automatically by Python
# Just run your pipeline:
python3 /home/prokop/git/AutoCrunchCoder/tests/test_paper_pipeline.py
```

## 7. Backup Strategy (Important!)

Since SQLite is a single file, backup is trivial:

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="$HOME/paper_library/backups"
DB_FILE="$HOME/paper_library/papers.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
cp "$DB_FILE" "$BACKUP_DIR/papers_backup_$TIMESTAMP.db"

# Keep only last 10 backups
ls -t "$BACKUP_DIR"/*.db | tail -n +11 | xargs -r rm
```

Add to crontab for daily backups:
```bash
crontab -e
# Add line:
0 2 * * * /home/prokop/backup_papers_db.sh
```

## Summary

| Component | Status | Command |
|-----------|--------|---------|
| SQLite CLI | Pre-installed | `sqlite3 --version` |
| Python sqlite3 | Built-in | `import sqlite3` |
| GUI Browser | Optional install | `sudo apt install sqlitebrowser` |
| Enhanced CLI | Optional | `pip install litecli` |

**You're ready to go!** SQLite requires zero configuration—just start using it in Python and the database file will be created automatically.

---

# Grok

**✅ Perfect — here's the cleanest, fastest way to install and set up SQLite on Ubuntu 24.04 LTS** (Noble Numbat).

SQLite is **already installed by default** on almost every Ubuntu 24.04 system (version 3.45.1), but we’ll make sure and add the CLI tools.

### 1. Install SQLite (CLI + library) – 10 seconds

```bash
sudo apt update
sudo apt install sqlite3 -y
```

That’s it. (The `-y` just auto-confirms.)

### 2. Verify installation

```bash
sqlite3 --version
```

You should see something like:
```
3.45.1 2024-... (or newer)
```

### 3. (Optional but highly recommended) Install GUI viewer

```bash
sudo apt install sqlitebrowser -y
```

Now you can open any `.db` file with a nice point-and-click interface:
```bash
sqlitebrowser ~/.autocrunch/papers.db
```

### 4. Quick test – create your paper database

```bash
# Create the directory and DB in one go
mkdir -p ~/.autocrunch
sqlite3 ~/.autocrunch/papers.db "VACUUM;"
```

Now enter the SQLite shell and create the table we talked about earlier:

```bash
sqlite3 ~/.autocrunch/papers.db
```

Inside the shell, paste this:

```sql
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    original_pdf_path TEXT UNIQUE,
    stem TEXT,
    doi TEXT,
    bibtex_ok INTEGER DEFAULT 0,
    bibtex_path TEXT,
    shadow_pdf_path TEXT,
    shadow_md_path TEXT,
    timestamp TEXT
);

-- Test insert
INSERT INTO papers (original_pdf_path, stem, doi, bibtex_ok, timestamp)
VALUES ('/home/prokop/Desktop/PAPERs/2017_05_24/Dircet_CO_CH_hydrogen_Bonc_SI_1603258_e1603258.full.pdf',
        'Dircet_CO_CH_hydrogen_Bonc_SI_1603258_e1603258.full',
        '10.1126/sciadv.1603258', 1, datetime('now'));

.tables
SELECT * FROM papers;
.exit
```

You should see your first row.

### 5. Python side (no extra install needed!)

Your Python 3.12 already has `sqlite3` in the standard library.

Just use the code I gave you earlier in `paper_db.py`:

```python
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".autocrunch" / "papers.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS papers (...)""")  # the table above
    conn.commit()
```

Everything works immediately — no `pip install` required.

### Bonus: One-liner to open your DB anytime

```bash
alias papersdb="sqlite3 ~/.autocrunch/papers.db"
```

Add it to your `~/.bashrc` so you can just type `papersdb` and run queries.

You’re now 100% ready.  
Run the install commands above, then run the `test_bibtex_and_shadow_on_existing_run()` function I gave you earlier — it will automatically call `upsert_paper()` and populate your new SQLite DB.

Want me to give you the **complete `paper_db.py` + updated `process_bibtex_and_shadow_tree()`** function that auto-creates the table on first run? Just say “give me the full db code” and I’ll paste the ready-to-drop files.  

You’ll have a searchable, permanent library of all your papers in under 2 minutes. 🚀