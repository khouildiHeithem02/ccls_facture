import sqlite3
import os
import hashlib

def init_db():
    """Initializes the SQLite database with necessary tables."""
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    
    # Main Invoices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decompte TEXT,
            date TEXT,
            farmer_name TEXT,
            farmer_address TEXT,
            farmer_nif TEXT,
            farmer_id_piece TEXT,
            total_brut REAL,
            total_retenues REAL,
            total_net REAL,
            total_avant_taxes REAL DEFAULT 0.0,
            total_bonification REAL DEFAULT 0.0,
            total_refaction REAL DEFAULT 0.0,
            pdf_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration: Check for new columns in invoices table
    cursor.execute("PRAGMA table_info(invoices)")
    columns = [row[1] for row in cursor.fetchall()]
    
    new_cols = [
        ("total_avant_taxes", "REAL DEFAULT 0.0"),
        ("total_bonification", "REAL DEFAULT 0.0"),
        ("total_refaction", "REAL DEFAULT 0.0"),
        ("wilaya", "TEXT"),
        ("payment_status", "TEXT DEFAULT 'Non Payé'"),
        ("created_by", "TEXT")
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_type}")
    
    # Products table (links to invoices)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            nature TEXT,
            quantite REAL,
            prix_u REAL,
            bon REAL,
            refac REAL,
            montant_brut REAL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    ''')
    
    # Product Receipts table (links to products)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            receipt_ref TEXT,
            receipt_date TEXT,
            quantity REAL,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Retenues/Taxes table (links to invoices)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS retenues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            name TEXT,
            nbre REAL,
            pu REAL,
            amount REAL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    ''')
    
    # Users table for login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # Products metadata table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            price REAL
        )
    ''')
    
    # Migration: Add role to users if it doesn't exist
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cursor.fetchall()]
    if "role" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Initialize default settings
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('max_products_per_invoice', '5')")
    
    # Check if admin user exists, if not create default
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        # Default password 'admin' hashed with SHA-256
        admin_pass = hashlib.sha256("admin".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", admin_pass, "admin"))
    else:
        # Ensure default admin has admin role
        cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")

    # Seed products metadata if empty
    cursor.execute("SELECT COUNT(*) FROM products_metadata")
    if cursor.fetchone()[0] == 0:
        initial_products = [
            ("Blé Dur", 6000),
            ("Blé Tendre", 5000),
            ("Orge", 3400),
            ("Tretical", 4300)
        ]
        cursor.executemany("INSERT INTO products_metadata (name, price) VALUES (?, ?)", initial_products)

    # --- PERFORMANCE INDEXES (Lag Fix) ---
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_wilaya ON invoices(wilaya)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(payment_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_farmer ON invoices(farmer_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_nature ON products(nature)")

    conn.commit()
    conn.close()


def save_invoice(data, pdf_path):
    """Saves a complete invoice and its related products/taxes to the database."""
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    
    try:
        ident = data.get('identity', {})
        totals = data.get('totals', {})
        products_list = data.get('products', [])
        retenues_list = data.get('retenues', [])
        
        # Calculate Financial Breakdowns for the invoice record
        total_brut = sum(float(p.get('montant_brut', 0)) for p in products_list)
        total_avant = sum(float(p.get('quantite', 0)) * float(p.get('prix_u', 0)) for p in products_list)
        total_bon = sum(float(p.get('quantite', 0)) * float(p.get('bon', 0)) for p in products_list)
        total_refac = sum(float(p.get('quantite', 0)) * float(p.get('refac', 0)) for p in products_list)
        
        # 1. Insert Main Invoice Record
        cursor.execute('''
            INSERT INTO invoices (
                decompte, date, farmer_name, farmer_address, wilaya,
                farmer_nif, farmer_id_piece, total_brut, 
                total_retenues, total_net, total_avant_taxes,
                total_bonification, total_refaction, pdf_path, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ident.get('decompte'),
            ident.get('date'),
            ident.get('farmer'),
            ident.get('adresse'),
            ident.get('wilaya'),
            ident.get('nif'),
            ident.get('piece_identite'),
            total_brut,
            totals.get('total_retenues', 0),
            totals.get('montant_net', 0),
            total_avant,
            total_bon,
            total_refac,
            pdf_path,
            ident.get('user_account_name')
        ))
        
        invoice_id = cursor.lastrowid
        
        # 2. Insert all products for this invoice
        for p in products_list:
            cursor.execute('''
                INSERT INTO products (
                    invoice_id, nature, quantite, prix_u, bon, refac, montant_brut
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id,
                p.get('nature'),
                p.get('quantite'),
                p.get('prix_u'),
                p.get('bon'),
                p.get('refac'),
                p.get('montant_brut')
            ))
            
            product_id = cursor.lastrowid
            # 2b. Insert receipts for this product
            receipts = p.get('receipts', [])
            for r in receipts:
                cursor.execute('''
                    INSERT INTO product_receipts (
                        product_id, receipt_ref, receipt_date, quantity
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    product_id,
                    r.get('ref'),
                    r.get('date'),
                    r.get('qte')
                ))
            
        # 3. Insert all retenues for this invoice
        for r in retenues_list:
            # We only store if there was an amount or a name
            if r.get('amount', 0) > 0 or r.get('nbre'):
                cursor.execute('''
                    INSERT INTO retenues (
                        invoice_id, name, nbre, pu, amount
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    invoice_id,
                    r.get('name'),
                    r.get('nbre'),
                    r.get('pu'),
                    r.get('amount')
                ))
            
        conn.commit()
    finally:
        conn.close()

def delete_invoice_related_data(cursor, invoice_id):
    """Internal helper to clear related products/receipts/retenues before update."""
    # 1. Get product IDs to delete receipts
    cursor.execute("SELECT id FROM products WHERE invoice_id = ?", (invoice_id,))
    product_ids = [row[0] for row in cursor.fetchall()]
    
    if product_ids:
        # Delete receipts for these products
        placeholders = ', '.join(['?'] * len(product_ids))
        cursor.execute(f"DELETE FROM product_receipts WHERE product_id IN ({placeholders})", product_ids)
    
    # 2. Delete products
    cursor.execute("DELETE FROM products WHERE invoice_id = ?", (invoice_id,))
    
    # 3. Delete retenues
    cursor.execute("DELETE FROM retenues WHERE invoice_id = ?", (invoice_id,))

def update_invoice_full(invoice_id, data, pdf_path):
    """Updates an existing invoice by replacing all related data and updating totals."""
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    
    try:
        ident = data.get('identity', {})
        totals = data.get('totals', {})
        products_list = data.get('products', [])
        retenues_list = data.get('retenues', [])
        
        # Calculate Financial Breakdowns
        total_brut = sum(float(p.get('montant_brut', 0)) for p in products_list)
        total_avant = sum(float(p.get('quantite', 0)) * float(p.get('prix_u', 0)) for p in products_list)
        total_bon = sum(float(p.get('quantite', 0)) * float(p.get('bon', 0)) for p in products_list)
        total_refac = sum(float(p.get('quantite', 0)) * float(p.get('refac', 0)) for p in products_list)
        
        # 1. Update Main Invoice Record
        cursor.execute('''
            UPDATE invoices SET 
                date = ?, farmer_name = ?, farmer_address = ?, wilaya = ?,
                farmer_nif = ?, farmer_id_piece = ?, total_brut = ?, 
                total_retenues = ?, total_net = ?, total_avant_taxes = ?,
                total_bonification = ?, total_refaction = ?, pdf_path = ?
            WHERE id = ?
        ''', (
            ident.get('date'),
            ident.get('farmer'),
            ident.get('adresse'),
            ident.get('wilaya'),
            ident.get('nif'),
            ident.get('piece_identite'),
            total_brut,
            totals.get('total_retenues', 0),
            totals.get('montant_net', 0),
            total_avant,
            total_bon,
            total_refac,
            pdf_path,
            invoice_id
        ))
        
        # 2. Clear old related data
        delete_invoice_related_data(cursor, invoice_id)
        
        # 3. Insert new products and receipts
        for p in products_list:
            cursor.execute('''
                INSERT INTO products (
                    invoice_id, nature, quantite, prix_u, bon, refac, montant_brut
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id,
                p.get('nature'),
                p.get('quantite'),
                p.get('prix_u'),
                p.get('bon'),
                p.get('refac'),
                p.get('montant_brut')
            ))
            
            product_id = cursor.lastrowid
            receipts = p.get('receipts', [])
            for r in receipts:
                cursor.execute('''
                    INSERT INTO product_receipts (
                        product_id, receipt_ref, receipt_date, quantity
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    product_id,
                    r.get('ref'),
                    r.get('date'),
                    r.get('qte')
                ))
            
        # 4. Insert new retenues
        for r in retenues_list:
            if r.get('amount', 0) > 0 or r.get('nbre'):
                cursor.execute('''
                    INSERT INTO retenues (
                        invoice_id, name, nbre, pu, amount
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    invoice_id,
                    r.get('name'),
                    r.get('nbre'),
                    r.get('pu'),
                    r.get('amount')
                ))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] Full update failed: {e}")
        return False
    finally:
        conn.close()

def get_all_invoices(query=None, wilaya="Tous", product="Tous", status="Tous", start_date=None, end_date=None):
    """Fetches all invoices, optionally filtered by search text, wilaya, product, status and date range."""
    conn = sqlite3.connect("invoices.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    where_clauses = []
    params = []
    
    if query:
        where_clauses.append("(farmer_name LIKE ? OR farmer_nif LIKE ? OR decompte LIKE ?)")
        params.extend([f"%{query}%"] * 3)
    if wilaya != "Tous":
        where_clauses.append("wilaya = ?")
        params.append(wilaya)
    if product != "Tous":
        where_clauses.append("id IN (SELECT invoice_id FROM products WHERE nature = ?)")
        params.append(product)
    if status != "Tous":
        where_clauses.append("payment_status = ?")
        params.append(status)
        
    # Date Range Filter: Invoices table uses 'date' column in DD / MM / YYYY format
    # For SQLite, we compare strings carefully or convert if needed. 
    # Since we use formatted strings, we'll implement a logic to filter by date.
    # Handles both 'DD/MM/YYYY' and 'DD / MM / YYYY'
    date_sql = "CASE WHEN date LIKE '% / %' THEN substr(date,10,4)||'-'||substr(date,6,2)||'-'||substr(date,1,2) ELSE substr(date,7,4)||'-'||substr(date,4,2)||'-'||substr(date,1,2) END"
    
    if start_date:
        where_clauses.append(f"{date_sql} >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append(f"{date_sql} <= ?")
        params.append(end_date)
        
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    try:
        cursor.execute(f"SELECT * FROM invoices {where_sql} ORDER BY created_at DESC", params)
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch invoices: {e}")
        return []
    finally:
        conn.close()

def get_invoice_details(invoice_id):
    """Reconstructs the full nested dictionary for an invoice from the DB."""
    conn = sqlite3.connect("invoices.db")
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    cursor = conn.cursor()
    
    try:
        # 1. Fetch main invoice data
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        inv_row = cursor.fetchone()
        if not inv_row:
            return None
            
        data = {
            "identity": {
                "adresse": inv_row["farmer_address"],
                "wilaya": inv_row["wilaya"],
                "nif": inv_row["farmer_nif"],
                "piece_identite": inv_row["farmer_id_piece"],
                "date": inv_row["date"],
                "decompte": inv_row["decompte"],
                "farmer": inv_row["farmer_name"],
                "user_account_name": inv_row["created_by"]
            },
            "status": inv_row["payment_status"],
            "totals": {
                "total_retenues": inv_row["total_retenues"],
                "montant_net": inv_row["total_net"]
            }
        }
        
        # 2. Fetch products
        cursor.execute("SELECT * FROM products WHERE invoice_id = ?", (invoice_id,))
        p_rows = cursor.fetchall()
        data["products"] = []
        for pr in p_rows:
            prod_data = {
                "nature": pr["nature"],
                "quantite": pr["quantite"],
                "prix_u": pr["prix_u"],
                "montant_avant_tax": pr["quantite"] * pr["prix_u"], # derived
                "bon": pr["bon"],
                "refac": pr["refac"],
                "montant_brut": pr["montant_brut"],
                "receipts": []
            }
            
            # Fetch receipts for this product
            cursor.execute("SELECT * FROM product_receipts WHERE product_id = ?", (pr["id"],))
            rr_rows = cursor.fetchall()
            for rr in rr_rows:
                prod_data["receipts"].append({
                    "ref": rr["receipt_ref"],
                    "date": rr["receipt_date"],
                    "qte": rr["quantity"]
                })
            data["products"].append(prod_data)
            
        # 3. Fetch retenues
        cursor.execute("SELECT * FROM retenues WHERE invoice_id = ?", (invoice_id,))
        r_rows = cursor.fetchall()
        data["retenues"] = []
        for rr in r_rows:
            data["retenues"].append({
                "name": rr["name"],
                "nbre": rr["nbre"],
                "pu": rr["pu"],
                "amount": rr["amount"]
            })
            
        return data
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch invoice details: {e}")
        return None
    finally:
        conn.close()

def get_filtered_totals(query=None, wilaya="Tous", product="Tous", status="Tous", start_date=None, end_date=None):
    """Calculates grand totals for a set of invoices filtered by search, wilaya, product, and status."""
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    
    where_clauses = []
    params = []
    
    if query:
        where_clauses.append("(farmer_name LIKE ? OR farmer_nif LIKE ? OR decompte LIKE ?)")
        params.extend([f"%{query}%"] * 3)
    if wilaya != "Tous":
        where_clauses.append("wilaya = ?")
        params.append(wilaya)
    if product != "Tous":
        where_clauses.append("id IN (SELECT invoice_id FROM products WHERE nature = ?)")
        params.append(product)
    if status != "Tous":
        where_clauses.append("payment_status = ?")
        params.append(status)
        
    # Handles both 'DD/MM/YYYY' and 'DD / MM / YYYY'
    date_sql = "CASE WHEN date LIKE '% / %' THEN substr(date,10,4)||'-'||substr(date,6,2)||'-'||substr(date,1,2) ELSE substr(date,7,4)||'-'||substr(date,4,2)||'-'||substr(date,1,2) END"
    
    if start_date:
        where_clauses.append(f"{date_sql} >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append(f"{date_sql} <= ?")
        params.append(end_date)
        
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    inner_id_query = f"SELECT id FROM invoices {where_sql}"
    
    try:
        # Get everything from the invoice table (FASTER!)
        cursor.execute(f'''
            SELECT 
                SUM(total_avant_taxes), 
                SUM(total_bonification), 
                SUM(total_refaction),
                SUM(total_retenues), 
                SUM(total_net),
                SUM(CASE WHEN payment_status = 'Payé' THEN total_net ELSE 0 END),
                SUM(CASE WHEN payment_status != 'Payé' THEN total_net ELSE 0 END)
            FROM invoices 
            WHERE id IN ({inner_id_query})
        ''', params)
            
        sums = cursor.fetchone()
        
        return {
            "total_avant": sums[0] or 0.0,
            "total_bon": sums[1] or 0.0,
            "total_refac": sums[2] or 0.0,
            "total_retenues": sums[3] or 0.0,
            "total_net": sums[4] or 0.0,
            "total_net_paye": sums[5] or 0.0,
            "total_net_non_paye": sums[6] or 0.0
        }
    except Exception as e:
        print(f"[DB ERROR] Calc failed: {e}")
        return {k: 0.0 for k in ["total_avant", "total_bon", "total_refac", "total_retenues", "total_net", "total_net_paye", "total_net_non_paye"]}
    finally:
        conn.close()

def get_grouped_accumulation(query=None, wilaya="Tous", product="Tous", status="Tous", start_date=None, end_date=None):
    """Retrieves totals grouped by product nature, respecting all filters."""
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    
    where_clauses = []
    params = []
    
    if query:
        where_clauses.append("(i.farmer_name LIKE ? OR i.farmer_nif LIKE ? OR i.decompte LIKE ?)")
        params.extend([f"%{query}%"] * 3)
    if wilaya != "Tous":
        where_clauses.append("i.wilaya = ?")
        params.append(wilaya)
    if product != "Tous":
        where_clauses.append("i.id IN (SELECT invoice_id FROM products WHERE nature = ?)")
        params.append(product)
    if status != "Tous":
        where_clauses.append("i.payment_status = ?")
        params.append(status)
        
    date_sql = "CASE WHEN i.date LIKE '% / %' THEN substr(i.date,10,4)||'-'||substr(i.date,6,2)||'-'||substr(i.date,1,2) ELSE substr(i.date,7,4)||'-'||substr(i.date,4,2)||'-'||substr(i.date,1,2) END"
    if start_date:
        where_clauses.append(f"{date_sql} >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append(f"{date_sql} <= ?")
        params.append(end_date)
        
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    try:
        cursor.execute(f'''
            SELECT 
                p.nature,
                COUNT(DISTINCT i.farmer_name) as farmer_count,
                SUM(p.quantite) as qte,
                SUM(p.quantite * p.prix_u) as avant,
                SUM(p.quantite * p.bon) as bon,
                SUM(p.quantite * p.refac) as refac,
                SUM(p.montant_brut) as net_prod
            FROM products p
            JOIN invoices i ON i.id = p.invoice_id
            {where_sql}
            GROUP BY p.nature
        ''', params)
        
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "nature": r[0],
                "farmer_count": r[1],
                "qte": r[2] or 0.0,
                "avant": r[3] or 0.0,
                "bon": r[4] or 0.0,
                "refac": r[5] or 0.0,
                "net_prod": r[6] or 0.0
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] Grouped calc failed: {e}")
        return []
    finally:
        conn.close()

def update_payment_status(invoice_id, status):
    """Updates the payment_status of a specific invoice."""
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE invoices SET payment_status = ? WHERE id = ?", (status, invoice_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] Status update failed: {e}")
        return False
    finally:
        conn.close()
def verify_login(username, password):
    """Verifies user credentials and returns (success, role)."""
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    
    try:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, hashed_pw))
        row = cursor.fetchone()
        if row:
            return True, row[0]
        return False, None
    except Exception as e:
        print(f"[DB ERROR] Login verification failed: {e}")
        return False, None
    finally:
        conn.close()

# --- USER MANAGEMENT ---
def get_all_users():
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def add_user(username, password, role):
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    try:
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       (username, hashed_pw, role))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def delete_user(username):
    if username == "admin": return False # Prevent self-delete
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True

def update_user_password(username, new_password):
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    try:
        hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_pw, username))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# --- PRODUCT MANAGEMENT ---
def get_db_products():
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products_metadata")
    rows = cursor.fetchall()
    conn.close()
    return {name: price for name, price in rows}

def add_db_product(name, price):
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO products_metadata (name, price) VALUES (?, ?)", (name, price))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def delete_db_product(name):
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products_metadata WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return True

# --- SETTINGS MANAGEMENT ---
def get_setting(key, default=None):
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect("invoices.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()
