import sqlite3
from config import Config


def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password TEXT NOT NULL,
            account_type TEXT NOT NULL CHECK(account_type IN ('user', 'provider')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_name TEXT NOT NULL,
            category TEXT NOT NULL,
            experience TEXT,
            description TEXT,
            city TEXT NOT NULL,
            area TEXT NOT NULL,
            address TEXT,
            phone TEXT NOT NULL,
            profile_image TEXT,
            views INTEGER DEFAULT 0,
            is_subscribed INTEGER DEFAULT 0,
            subscription_started_at DATETIME,
            subscription_expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provider_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (provider_id) REFERENCES providers(id),
            UNIQUE(user_id, provider_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            user_id INTEGER,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (provider_id) REFERENCES providers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    migrate_tables()


def migrate_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE providers ADD COLUMN views INTEGER DEFAULT 0')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE providers ADD COLUMN is_subscribed INTEGER DEFAULT 0')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE providers ADD COLUMN subscription_expires_at DATETIME')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE providers ADD COLUMN subscription_started_at DATETIME')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


def insert_default_categories():
    categories = [
        'Doctor', 'Dentist', 'Physiotherapist', 'Plumber', 'Electrician', 
        'Beautician', 'Hair Salon', 'Carpenter', 'Mechanic', 'Tutor', 
        'Mobile Repair', 'AC Repair', 'Laptop Repair', 'Taxi Driver',
        'Packers & Movers', 'Caterer', 'Event Photographer', 'Fitness Trainer',
        'Water Supplier', 'Grocery Store', 'Restaurant', 'Hotel', 'Pharmacy',
        'Laundry Service', 'Interior Designer', 'Legal Consultant', 'Chartered Accountant'
    ]
    conn = get_db_connection()
    cursor = conn.cursor()
    for cat in categories:
        cursor.execute('INSERT OR IGNORE INTO categories (category_name) VALUES (?)', (cat.strip(),))
    conn.commit()
    conn.close()


def ensure_category_exists(category_name):
    cleaned_name = category_name.strip()
    if not cleaned_name:
        return "Other"
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO categories (category_name) VALUES (?)', (cleaned_name,))
    conn.commit()
    conn.close()
    return cleaned_name


# ── User functions ──

def create_user(name, email, phone, password, account_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (name, email, phone, password, account_type) VALUES (?, ?, ?, ?, ?)',
            (name, email, phone, password, account_type)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def login_user(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def update_user_profile(user_id, name, phone, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET name = ?, phone = ?, email = ? WHERE id = ?', (name, phone, email, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_user_password(user_id, new_password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password = ? WHERE id = ?', (new_password_hash, user_id))
    conn.commit()
    conn.close()


def delete_user_account(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM providers WHERE user_id = ?', (user_id,))
        provider = cursor.fetchone()
        if provider:
            provider_id = provider['id']
            cursor.execute('DELETE FROM provider_images WHERE provider_id = ?', (provider_id,))
            cursor.execute('DELETE FROM reviews WHERE provider_id = ?', (provider_id,))
            cursor.execute('DELETE FROM inquiries WHERE provider_id = ?', (provider_id,))
            cursor.execute('DELETE FROM favorites WHERE provider_id = ?', (provider_id,))
            cursor.execute('DELETE FROM providers WHERE id = ?', (provider_id,))
        cursor.execute('DELETE FROM favorites WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM reviews WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM inquiries WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ── Provider functions ──

def create_provider(user_id, business_name, category, experience, description, city, area, address, phone, profile_image, business_images=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO providers (user_id, business_name, category, experience, description, city, area, address, phone, profile_image, is_subscribed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (user_id, business_name, category, experience, description, city, area, address, phone, profile_image))
    provider_id = cursor.lastrowid

    if business_images:
        for idx, img_path in enumerate(business_images):
            cursor.execute(
                'INSERT INTO provider_images (provider_id, image_path, sort_order) VALUES (?, ?, ?)',
                (provider_id, img_path, idx)
            )

    conn.commit()
    conn.close()
    return provider_id


def update_provider(user_id, business_name, category, experience, description, city, area, address, phone):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE providers
        SET business_name = ?, category = ?, experience = ?, description = ?, city = ?, area = ?, address = ?, phone = ?
        WHERE user_id = ?
    ''', (business_name, category, experience, description, city, area, address, phone, user_id))
    conn.commit()
    conn.close()


def activate_provider_subscription(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE providers 
        SET is_subscribed = 1, 
            subscription_started_at = datetime('now', 'localtime'),
            subscription_expires_at = datetime('now', '+30 days', 'localtime') 
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()


def update_provider_image(user_id, image_path):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE providers SET profile_image = ? WHERE user_id = ?', (image_path, user_id))
    conn.commit()
    conn.close()


# ── Provider Images functions ──

def add_provider_image(provider_id, image_path, sort_order=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if sort_order is None:
        cursor.execute('SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM provider_images WHERE provider_id = ?', (provider_id,))
        sort_order = cursor.fetchone()['next_order']
    cursor.execute(
        'INSERT INTO provider_images (provider_id, image_path, sort_order) VALUES (?, ?, ?)',
        (provider_id, image_path, sort_order)
    )
    conn.commit()
    conn.close()


def get_provider_images(provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM provider_images WHERE provider_id = ? ORDER BY sort_order ASC, id ASC', (provider_id,))
    images = cursor.fetchall()
    conn.close()
    return images


def delete_provider_image(image_id, provider_user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if provider_user_id:
        cursor.execute('''
            DELETE FROM provider_images WHERE id = ? AND provider_id IN (
                SELECT id FROM providers WHERE user_id = ?
            )
        ''', (image_id, provider_user_id))
    else:
        cursor.execute('DELETE FROM provider_images WHERE id = ?', (image_id,))
    conn.commit()
    conn.close()


def reorder_provider_images(provider_id, image_ids_ordered):
    conn = get_db_connection()
    cursor = conn.cursor()
    for idx, img_id in enumerate(image_ids_ordered):
        cursor.execute(
            'UPDATE provider_images SET sort_order = ? WHERE id = ? AND provider_id = ?',
            (idx, img_id, provider_id)
        )
    conn.commit()
    conn.close()


# ── Category functions ──

def get_all_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY category_name ASC')
    categories = cursor.fetchall()
    conn.close()
    return categories


# ── Provider query functions ──

def get_all_providers(category=None, limit=None, offset=0, sort='newest'):
    conn = get_db_connection()
    cursor = conn.cursor()
    where_clause = " WHERE p.is_subscribed = 1"
    params = []
    if category:
        where_clause += " AND p.category = ?"
        params.append(category)
        
    if sort == 'views':
        order_clause = " ORDER BY p.views DESC, p.created_at DESC"
    elif sort == 'name':
        order_clause = " ORDER BY p.business_name ASC"
    elif sort == 'rating':
        order_clause = " ORDER BY avg_rating DESC, review_count DESC"
    else:
        order_clause = " ORDER BY p.created_at DESC"
        
    limit_clause = ""
    if limit is not None:
        limit_clause = " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
    query = f'''
        SELECT p.*, u.name AS owner_name, u.email AS owner_email,
               COALESCE(AVG(r.rating), 0.0) AS avg_rating,
               COUNT(r.id) AS review_count
        FROM providers p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN reviews r ON p.id = r.provider_id
        {where_clause}
        GROUP BY p.id
        {order_clause}{limit_clause}
    '''
    cursor.execute(query, params)
    providers = cursor.fetchall()
    conn.close()
    return providers


def get_recent_providers(limit=8):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.name AS owner_name, u.email AS owner_email,
               COALESCE(AVG(r.rating), 0.0) AS avg_rating,
               COUNT(r.id) AS review_count
        FROM providers p
        JOIN users u ON p.user_id = u.id 
        LEFT JOIN reviews r ON p.id = r.provider_id
        WHERE p.is_subscribed = 1 
        GROUP BY p.id
        ORDER BY p.created_at DESC LIMIT ?
    ''', (limit,))
    providers = cursor.fetchall()
    conn.close()
    return providers


def get_provider_by_id(provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.name AS owner_name, u.email AS owner_email,
               COALESCE(AVG(r.rating), 0.0) AS avg_rating,
               COUNT(r.id) AS review_count
        FROM providers p
        JOIN users u ON p.user_id = u.id 
        LEFT JOIN reviews r ON p.id = r.provider_id
        WHERE p.id = ?
        GROUP BY p.id
    ''', (provider_id,))
    provider = cursor.fetchone()
    conn.close()
    return provider


def get_provider_by_user_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.email AS owner_email, 
               COALESCE(AVG(r.rating), 0.0) AS avg_rating, 
               COUNT(r.id) AS review_count
        FROM providers p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN reviews r ON p.id = r.provider_id
        WHERE p.user_id = ?
        GROUP BY p.id
    ''', (user_id,))
    provider = cursor.fetchone()
    conn.close()
    return provider


def search_providers(query, limit=None, offset=0, sort='newest'):
    conn = get_db_connection()
    cursor = conn.cursor()
    term = f'%{query}%'
    if sort == 'views':
        order_clause = " ORDER BY p.views DESC, p.created_at DESC"
    elif sort == 'name':
        order_clause = " ORDER BY p.business_name ASC"
    elif sort == 'rating':
        order_clause = " ORDER BY avg_rating DESC, review_count DESC"
    else:
        order_clause = " ORDER BY p.created_at DESC"
        
    limit_clause = ""
    params = [term, term, term, term, term]
    if limit is not None:
        limit_clause = " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
    cursor.execute(f'''
        SELECT p.*, u.name AS owner_name, u.email AS owner_email,
               COALESCE(AVG(r.rating), 0.0) AS avg_rating,
               COUNT(r.id) AS review_count
        FROM providers p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN reviews r ON p.id = r.provider_id
        WHERE p.is_subscribed = 1 AND (p.business_name LIKE ? OR u.name LIKE ? OR p.category LIKE ? OR p.city LIKE ? OR p.area LIKE ?)
        GROUP BY p.id
        {order_clause}{limit_clause}
    ''', params)
    providers = cursor.fetchall()
    conn.close()
    return providers


def get_providers_count(category=None, search_query=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        term = f'%{search_query}%'
        cursor.execute('''
            SELECT COUNT(DISTINCT p.id) as cnt FROM providers p
            JOIN users u ON p.user_id = u.id
            WHERE p.is_subscribed = 1 AND (p.business_name LIKE ? OR u.name LIKE ? OR p.category LIKE ? OR p.city LIKE ? OR p.area LIKE ?)
        ''', (term, term, term, term, term))
    elif category:
        cursor.execute('SELECT COUNT(*) as cnt FROM providers WHERE is_subscribed = 1 AND category = ?', (category,))
    else:
        cursor.execute('SELECT COUNT(*) as cnt FROM providers WHERE is_subscribed = 1')
    count = cursor.fetchone()['cnt']
    conn.close()
    return count


def increment_provider_views(provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE providers SET views = views + 1 WHERE id = ?', (provider_id,))
    conn.commit()
    conn.close()


def get_provider_stats(provider_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT views, id FROM providers WHERE user_id = ?', (provider_user_id,))
    provider = cursor.fetchone()
    stats = {'views': 0, 'reviews': 0, 'inquiries': 0, 'favorites': 0}
    if provider:
        stats['views'] = provider['views'] or 0
        cursor.execute('SELECT COUNT(*) as cnt FROM reviews WHERE provider_id = ?', (provider['id'],))
        stats['reviews'] = cursor.fetchone()['cnt']
        cursor.execute('''
            SELECT COUNT(*) as cnt FROM inquiries i
            JOIN providers p ON i.provider_id = p.id WHERE p.user_id = ?
        ''', (provider_user_id,))
        stats['inquiries'] = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) as cnt FROM favorites WHERE provider_id = ?', (provider['id'],))
        stats['favorites'] = cursor.fetchone()['cnt']
    conn.close()
    return stats


# ── Favorites ──

def toggle_favorite(user_id, provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM favorites WHERE user_id = ? AND provider_id = ?', (user_id, provider_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute('DELETE FROM favorites WHERE id = ?', (existing['id'],))
        conn.commit()
        conn.close()
        return False
    else:
        cursor.execute('INSERT INTO favorites (user_id, provider_id) VALUES (?, ?)', (user_id, provider_id))
        conn.commit()
        conn.close()
        return True


def is_favorited(user_id, provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM favorites WHERE user_id = ? AND provider_id = ?', (user_id, provider_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_user_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.name AS owner_name, u.email AS owner_email,
               COALESCE(AVG(r.rating), 0.0) AS avg_rating,
               COUNT(r.id) AS review_count
        FROM favorites f
        JOIN providers p ON f.provider_id = p.id
        JOIN users u ON p.user_id = u.id
        LEFT JOIN reviews r ON p.id = r.provider_id
        WHERE f.user_id = ? AND p.is_subscribed = 1 
        GROUP BY p.id
        ORDER BY f.created_at DESC
    ''', (user_id,))
    providers = cursor.fetchall()
    conn.close()
    return providers


def get_favorite_ids(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT provider_id FROM favorites WHERE user_id = ?', (user_id,))
    ids = [row['provider_id'] for row in cursor.fetchall()]
    conn.close()
    return ids


# ── Reviews ──

def submit_review(provider_id, user_id, rating, comment):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM reviews WHERE provider_id = ? AND user_id = ?', (provider_id, user_id))
    if cursor.fetchone():
        cursor.execute('UPDATE reviews SET rating = ?, comment = ?, created_at = CURRENT_TIMESTAMP WHERE provider_id = ? AND user_id = ?',
                       (rating, comment, provider_id, user_id))
    else:
        cursor.execute('INSERT INTO reviews (provider_id, user_id, rating, comment) VALUES (?, ?, ?, ?)',
                       (provider_id, user_id, rating, comment))
    conn.commit()
    conn.close()


def get_provider_reviews(provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, u.name AS reviewer_name FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.provider_id = ? ORDER BY r.created_at DESC
    ''', (provider_id,))
    reviews = cursor.fetchall()
    conn.close()
    return reviews


def get_review_stats(provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as total, COALESCE(AVG(rating),0.0) as average FROM reviews WHERE provider_id = ?', (provider_id,))
    stats = cursor.fetchone()
    cursor.execute('''
        SELECT rating, COUNT(*) as count FROM reviews WHERE provider_id = ?
        GROUP BY rating ORDER BY rating DESC
    ''', (provider_id,))
    breakdown = {row['rating']: row['count'] for row in cursor.fetchall()}
    conn.close()
    return stats, breakdown


def get_user_review_for_provider(user_id, provider_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reviews WHERE user_id = ? AND provider_id = ?', (user_id, provider_id))
    row = cursor.fetchone()
    conn.close()
    return row


# ── Inquiries ──

def send_inquiry(provider_id, user_id, name, phone, message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO inquiries (provider_id, user_id, name, phone, message) VALUES (?, ?, ?, ?, ?)
    ''', (provider_id, user_id, name, phone, message))
    conn.commit()
    conn.close()


def get_provider_inquiries(provider_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.* FROM inquiries i
        JOIN providers p ON i.provider_id = p.id
        WHERE p.user_id = ? ORDER BY i.created_at DESC
    ''', (provider_user_id,))
    inquiries = cursor.fetchall()
    conn.close()
    return inquiries


def mark_inquiry_read(inquiry_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inquiries SET is_read = 1 WHERE id = ?', (inquiry_id,))
    conn.commit()
    conn.close()


def get_unread_inquiry_count(provider_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) as cnt FROM inquiries i
        JOIN providers p ON i.provider_id = p.id
        WHERE p.user_id = ? AND i.is_read = 0
    ''', (provider_user_id,))
    row = cursor.fetchone()
    count = row['cnt'] if row else 0
    conn.close()
    return count