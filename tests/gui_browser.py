import sys
import os
import sqlite3
import subprocess
from pathlib import Path

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
                                 QTableWidget, QTableWidgetItem, QSplitter, 
                                 QLabel, QTextEdit, QPushButton, QLineEdit, 
                                 QInputDialog, QMessageBox, QHeaderView, QComboBox, QScrollArea,
                                 QTreeWidgetItemIterator)
    from PyQt5.QtCore import Qt
except ImportError:
    print("PyQt5 is not installed. Please install it using: pip install PyQt5")
    sys.exit(1)

DB_PATH = "/home/prokop/git/AutoCrunchCoder/tests/paper_pipeline_out/consolidated.db"

class PaperBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paper Browser & Organizer")
        self.resize(1400, 900)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.current_paper_stem = None
        self.init_ui()
        self.load_tree_data()
        self.search_papers() # Initial load of all papers
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Top Panel: Search and Filters
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Title, Authors, Essence...")
        self.search_input.returnPressed.connect(self.search_papers)
        top_layout.addWidget(self.search_input)
        
        self.tag_logic_combo = QComboBox()
        self.tag_logic_combo.addItems(["OR (Any selected tag)", "AND (All selected tags)"])
        top_layout.addWidget(self.tag_logic_combo)
        
        self.btn_search = QPushButton("Search / Apply Filters")
        self.btn_search.clicked.connect(self.search_papers)
        top_layout.addWidget(self.btn_search)
        
        main_layout.addLayout(top_layout)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Panel: Trees (Runs and Tags)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Categories / Runs / Tags"])
        self.tree.itemChanged.connect(self.on_tree_item_changed)
        left_layout.addWidget(self.tree)
        
        splitter.addWidget(left_widget)
        
        # Center Panel: Paper List
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0,0,0,0)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Stem", "Title", "Year", "Authors"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        center_layout.addWidget(self.table)
        
        splitter.addWidget(center_widget)
        
        # Right Panel: Details (using ScrollArea for better fit)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Basic Info
        self.lbl_title = QLabel("<b>Title:</b> ")
        self.lbl_title.setWordWrap(True)
        right_layout.addWidget(self.lbl_title)
        
        self.lbl_authors = QLabel("<b>Authors:</b> ")
        self.lbl_authors.setWordWrap(True)
        right_layout.addWidget(self.lbl_authors)
        
        self.lbl_year = QLabel("<b>Year:</b> ")
        right_layout.addWidget(self.lbl_year)
        
        # Tags
        self.lbl_tags = QLabel("<b>Tags:</b> ")
        self.lbl_tags.setWordWrap(True)
        right_layout.addWidget(self.lbl_tags)
        
        tag_btn_layout = QHBoxLayout()
        self.btn_add_tag = QPushButton("Add Tag")
        self.btn_add_tag.clicked.connect(self.add_tag)
        self.btn_remove_tag = QPushButton("Remove Tag")
        self.btn_remove_tag.clicked.connect(self.remove_tag)
        tag_btn_layout.addWidget(self.btn_add_tag)
        tag_btn_layout.addWidget(self.btn_remove_tag)
        tag_btn_layout.addStretch()
        right_layout.addLayout(tag_btn_layout)
        
        # Copyable Links & Open Buttons
        links_layout = QVBoxLayout()
        
        def make_link_row(label_text, btn_text, attr_name):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label_text}:</b>"))
            le = QLineEdit()
            le.setReadOnly(True)
            btn = QPushButton(btn_text)
            btn.clicked.connect(lambda: self.open_file(attr_name))
            row.addWidget(le)
            row.addWidget(btn)
            return row, le

        row_pdf, self.le_pdf = make_link_row("PDF", "Open PDF", "original_pdf_path")
        row_md, self.le_md = make_link_row("MD", "Open MD", "md_path")
        row_bib, self.le_bib = make_link_row("Bib", "Open Bib", "bibtex_path")
        
        links_layout.addLayout(row_pdf)
        links_layout.addLayout(row_md)
        links_layout.addLayout(row_bib)
        right_layout.addLayout(links_layout)
        
        # Text Areas Splitting
        text_splitter = QSplitter(Qt.Vertical)
        
        # Essence
        essence_w = QWidget()
        el = QVBoxLayout(essence_w)
        el.setContentsMargins(0,0,0,0)
        el.addWidget(QLabel("<b>Essence:</b>"))
        self.txt_essence = QTextEdit()
        self.txt_essence.setReadOnly(True)
        el.addWidget(self.txt_essence)
        text_splitter.addWidget(essence_w)
        
        # BibTeX
        bib_w = QWidget()
        bl = QVBoxLayout(bib_w)
        bl.setContentsMargins(0,0,0,0)
        bl.addWidget(QLabel("<b>BibTeX:</b>"))
        self.txt_bibtex = QTextEdit()
        self.txt_bibtex.setReadOnly(True)
        bl.addWidget(self.txt_bibtex)
        text_splitter.addWidget(bib_w)
        
        # Markdown
        md_w = QWidget()
        ml = QVBoxLayout(md_w)
        ml.setContentsMargins(0,0,0,0)
        ml.addWidget(QLabel("<b>Markdown:</b>"))
        self.txt_markdown = QTextEdit()
        self.txt_markdown.setReadOnly(True)
        ml.addWidget(self.txt_markdown)
        text_splitter.addWidget(md_w)
        
        # Adjust proportions: Essence(20%), Bib(20%), MD(60%)
        text_splitter.setSizes([100, 100, 400])
        right_layout.addWidget(text_splitter)
        
        scroll_area.setWidget(right_widget)
        splitter.addWidget(scroll_area)
        
        # Main splitter proportions
        splitter.setSizes([250, 450, 700])

    def load_tree_data(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        
        # 1. Runs (Folders) - Checkable
        runs_root = QTreeWidgetItem(self.tree, ["Runs (Folders)"])
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT run_name FROM papers WHERE run_name IS NOT NULL ORDER BY run_name DESC")
        for row in cur.fetchall():
            run_name = row["run_name"]
            item = QTreeWidgetItem(runs_root, [run_name])
            item.setCheckState(0, Qt.Unchecked)
            item.setData(0, Qt.UserRole, {"type": "run", "value": run_name})
            
        # 2. Tags - Checkable
        tags_root = QTreeWidgetItem(self.tree, ["Tags (Virtual Folders)"])
        cur.execute("SELECT DISTINCT category FROM tags WHERE category IS NOT NULL")
        categories = [r["category"] for r in cur.fetchall()]
        if "uncategorized" not in categories:
            categories.append("uncategorized")
        
        cat_items = {}
        for cat in categories:
            cat_item = QTreeWidgetItem(tags_root, [cat])
            cat_items[cat] = cat_item
            
        cur.execute("SELECT id, name, category FROM tags ORDER BY name")
        for row in cur.fetchall():
            cat = row["category"] or "uncategorized"
            tag_name = row["name"]
            item = QTreeWidgetItem(cat_items.get(cat, tags_root), [tag_name])
            item.setCheckState(0, Qt.Unchecked)
            item.setData(0, Qt.UserRole, {"type": "tag", "value": tag_name, "id": row["id"]})
            
        self.tree.expandItem(runs_root)
        self.tree.expandItem(tags_root)
        self.tree.blockSignals(False)

    def on_tree_item_changed(self, item, column):
        # Auto-trigger search when a checkbox changes
        self.search_papers()

    def get_checked_items(self):
        checked_runs = []
        checked_tags = []
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.checkState(0) == Qt.Checked:
                data = item.data(0, Qt.UserRole)
                if data:
                    if data["type"] == "run":
                        checked_runs.append(data["value"])
                    elif data["type"] == "tag":
                        checked_tags.append(data["id"])
            iterator += 1
            
        return checked_runs, checked_tags

    def search_papers(self):
        checked_runs, checked_tags = self.get_checked_items()
        search_text = self.search_input.text().strip()
        is_and = self.tag_logic_combo.currentIndex() == 1
        
        query = "SELECT DISTINCT p.stem, p.title, p.year, p.authors FROM papers p"
        joins = []
        wheres = []
        params = []
        
        # Tags logic
        if checked_tags:
            if is_and:
                # Must have ALL selected tags
                for i, tid in enumerate(checked_tags):
                    joins.append(f"JOIN article_tags at{i} ON p.stem = at{i}.article_id")
                    wheres.append(f"at{i}.tag_id = ?")
                    params.append(tid)
            else:
                # Must have ANY selected tag
                joins.append("JOIN article_tags at ON p.stem = at.article_id")
                placeholders = ",".join(["?"] * len(checked_tags))
                wheres.append(f"at.tag_id IN ({placeholders})")
                params.extend(checked_tags)
                
        # Runs logic
        if checked_runs:
            placeholders = ",".join(["?"] * len(checked_runs))
            wheres.append(f"p.run_name IN ({placeholders})")
            params.extend(checked_runs)
            
        # Text search logic
        if search_text:
            search_pattern = f"%{search_text}%"
            # we want to search title, authors, essence
            # and potentially tag names
            search_clause = "(p.title LIKE ? OR p.authors LIKE ? OR p.essence LIKE ? OR p.stem LIKE ?)"
            params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            wheres.append(search_clause)
            
        full_query = query + " " + " ".join(joins)
        if wheres:
            full_query += " WHERE " + " AND ".join(wheres)
            
        cur = self.conn.cursor()
        cur.execute(full_query, params)
        rows = cur.fetchall()
        
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["stem"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(row["title"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(row["year"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(row["authors"] or ""))

    def on_table_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.current_paper_stem = None
            return
            
        row = selected[0].row()
        stem = self.table.item(row, 0).text()
        self.current_paper_stem = stem
        
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM papers WHERE stem = ?", (stem,))
        paper = cur.fetchone()
        if not paper:
            return
            
        self.lbl_title.setText(f"<b>Title:</b> {paper['title']}")
        self.lbl_authors.setText(f"<b>Authors:</b> {paper['authors']}")
        self.lbl_year.setText(f"<b>Year:</b> {paper['year']}")
        self.txt_essence.setText(paper['essence'] or "")
        
        # Fill Links
        self.le_pdf.setText(paper['original_pdf_path'] or "")
        self.le_md.setText(paper['md_path'] or "")
        self.le_bib.setText(paper['bibtex_path'] or "")
        
        # Load File contents
        def safe_read(path):
            if path and os.path.exists(path):
                try:
                    return Path(path).read_text(encoding='utf-8', errors='replace')
                except Exception as e:
                    return f"Error reading file: {e}"
            return ""
            
        self.txt_bibtex.setText(paper['bibtex_text'] or safe_read(paper['bibtex_path']))
        self.txt_markdown.setText(safe_read(paper['md_path']))
        
        # Get tags
        cur.execute("""
            SELECT t.name FROM tags t
            JOIN article_tags at ON t.id = at.tag_id
            WHERE at.article_id = ?
        """, (stem,))
        tags = [r["name"] for r in cur.fetchall()]
        self.lbl_tags.setText(f"<b>Tags:</b> {', '.join(tags)}")

    def add_tag(self):
        if not self.current_paper_stem:
            return
        tag_name, ok = QInputDialog.getText(self, "Add Tag", "Tag name:")
        if ok and tag_name:
            tag_name = tag_name.strip().lower()
            cur = self.conn.cursor()
            cur.execute("INSERT OR IGNORE INTO tags (name, category) VALUES (?, ?)", (tag_name, "manual"))
            cur.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            tag_id = cur.fetchone()["id"]
            cur.execute("INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)", (self.current_paper_stem, tag_id))
            self.conn.commit()
            self.on_table_selection_changed() # Refresh details
            self.load_tree_data() # Refresh tree to show new tag if needed

    def remove_tag(self):
        if not self.current_paper_stem:
            return
        cur = self.conn.cursor()
        cur.execute("""
            SELECT t.name FROM tags t
            JOIN article_tags at ON t.id = at.tag_id
            WHERE at.article_id = ?
        """, (self.current_paper_stem,))
        tags = [r["name"] for r in cur.fetchall()]
        
        if not tags:
            return
            
        tag_name, ok = QInputDialog.getItem(self, "Remove Tag", "Select tag to remove:", tags, 0, False)
        if ok and tag_name:
            cur.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            tag_row = cur.fetchone()
            if tag_row:
                cur.execute("DELETE FROM article_tags WHERE article_id = ? AND tag_id = ?", (self.current_paper_stem, tag_row["id"]))
                self.conn.commit()
                self.on_table_selection_changed()

    def open_file(self, path_col):
        if not self.current_paper_stem:
            return
        cur = self.conn.cursor()
        cur.execute(f"SELECT {path_col} FROM papers WHERE stem = ?", (self.current_paper_stem,))
        row = cur.fetchone()
        if not row or not row[path_col]:
            QMessageBox.warning(self, "Not Found", f"No {path_col} found for this paper.")
            return
            
        filepath = row[path_col]
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "Not Found", f"File does not exist:\n{filepath}")
            return
            
        try:
            subprocess.Popen(["xdg-open", filepath])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Consolidated DB not found at {DB_PATH}. Please run consolidate_dbs.py first.")
        sys.exit(1)
        
    app = QApplication(sys.argv)
    window = PaperBrowser()
    window.show()
    sys.exit(app.exec_())

