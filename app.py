import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime, timedelta
import time
import uuid

# Database setup and initialization
def init_database():
    conn = sqlite3.connect('campus_food_system.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        user_type TEXT DEFAULT 'customer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Vendors table
    c.execute('''CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        location TEXT NOT NULL,
        contact_phone TEXT,
        contact_email TEXT,
        operating_hours TEXT,
        rating REAL DEFAULT 0.0,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Food items table
    c.execute('''CREATE TABLE IF NOT EXISTS food_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor_id INTEGER,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        category TEXT,
        image_url TEXT,
        is_available BOOLEAN DEFAULT 1,
        preparation_time INTEGER DEFAULT 15,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vendor_id) REFERENCES vendors (id)
    )''')
    
    # Orders table
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        vendor_id INTEGER,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        delivery_location TEXT,
        special_instructions TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES users (id),
        FOREIGN KEY (vendor_id) REFERENCES vendors (id)
    )''')
    
    # Order items table
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        food_item_id INTEGER,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (food_item_id) REFERENCES food_items (id)
    )''')
    
    # Insert default admin user
    admin_password = hashlib.sha256("admin".encode()).hexdigest()
    c.execute('''INSERT OR IGNORE INTO users (username, password, email, full_name, user_type) 
                 VALUES (?, ?, ?, ?, ?)''', 
              ("admin", admin_password, "admin@fss.edu.ng", "System Administrator", "admin"))
    
    # Insert sample vendors
    sample_vendors = [
        ("Campus Cafeteria", "Main campus dining hall", "Block A, Ground Floor", "08012345678", "cafeteria@fss.edu.ng", "7:00 AM - 9:00 PM"),
        ("Quick Bites", "Fast food and snacks", "Student Center", "08098765432", "quickbites@fss.edu.ng", "8:00 AM - 8:00 PM"),
        ("Healthy Meals", "Nutritious and organic food", "Faculty Building", "08055566677", "healthy@fss.edu.ng", "9:00 AM - 6:00 PM")
    ]
    
    for vendor in sample_vendors:
        c.execute('''INSERT OR IGNORE INTO vendors (name, description, location, contact_phone, contact_email, operating_hours) 
                    VALUES (?, ?, ?, ?, ?, ?)''', vendor)
    
    # Insert sample food items
    sample_foods = [
        (1, "Jollof Rice", "Spicy Nigerian rice dish", 800.00, "Main Course", "", 1, 20),
        (1, "Fried Rice", "Delicious fried rice with vegetables", 750.00, "Main Course", "", 1, 18),
        (1, "Chicken Stew", "Tender chicken in tomato stew", 1200.00, "Main Course", "", 1, 25),
        (2, "Meat Pie", "Savory pastry with meat filling", 200.00, "Snacks", "", 1, 5),
        (2, "Sausage Roll", "Crispy pastry with sausage", 150.00, "Snacks", "", 1, 5),
        (2, "Soft Drinks", "Assorted soft drinks", 100.00, "Beverages", "", 1, 2),
        (3, "Grilled Fish", "Fresh grilled fish with vegetables", 1500.00, "Main Course", "", 1, 30),
        (3, "Vegetable Salad", "Fresh mixed vegetable salad", 600.00, "Salads", "", 1, 10),
        (3, "Fruit Juice", "Fresh fruit juice", 300.00, "Beverages", "", 1, 5)
    ]
    
    for food in sample_foods:
        c.execute('''INSERT OR IGNORE INTO food_items (vendor_id, name, description, price, category, image_url, is_available, preparation_time) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', food)
    
    conn.commit()
    conn.close()

# Authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def authenticate_user(username, password):
    conn = sqlite3.connect('campus_food_system.db')
    c = conn.cursor()
    c.execute("SELECT id, username, password, user_type, full_name FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and verify_password(password, user[2]):
        return {"id": user[0], "username": user[1], "user_type": user[3], "full_name": user[4]}
    return None

# Database query functions
def get_vendors():
    conn = sqlite3.connect('campus_food_system.db')
    df = pd.read_sql_query("SELECT * FROM vendors WHERE is_active = 1", conn)
    conn.close()
    return df

def get_food_items(vendor_id=None):
    conn = sqlite3.connect('campus_food_system.db')
    if vendor_id:
        query = """SELECT fi.*, v.name as vendor_name 
                   FROM food_items fi 
                   JOIN vendors v ON fi.vendor_id = v.id 
                   WHERE fi.vendor_id = ? AND fi.is_available = 1"""
        df = pd.read_sql_query(query, conn, params=(vendor_id,))
    else:
        query = """SELECT fi.*, v.name as vendor_name 
                   FROM food_items fi 
                   JOIN vendors v ON fi.vendor_id = v.id 
                   WHERE fi.is_available = 1"""
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def search_food_items(search_term):
    conn = sqlite3.connect('campus_food_system.db')
    query = """SELECT fi.*, v.name as vendor_name 
               FROM food_items fi 
               JOIN vendors v ON fi.vendor_id = v.id 
               WHERE (fi.name LIKE ? OR fi.description LIKE ? OR v.name LIKE ?) 
               AND fi.is_available = 1"""
    search_pattern = f"%{search_term}%"
    df = pd.read_sql_query(query, conn, params=(search_pattern, search_pattern, search_pattern))
    conn.close()
    return df

def create_order(customer_id, vendor_id, items, total_amount, delivery_location, special_instructions=""):
    conn = sqlite3.connect('campus_food_system.db')
    c = conn.cursor()
    
    # Generate unique order number
    order_number = f"FSS{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    # Insert order
    c.execute('''INSERT INTO orders (order_number, customer_id, vendor_id, total_amount, delivery_location, special_instructions) 
                 VALUES (?, ?, ?, ?, ?, ?)''', 
              (order_number, customer_id, vendor_id, total_amount, delivery_location, special_instructions))
    
    order_id = c.lastrowid
    
    # Insert order items
    for item in items:
        c.execute('''INSERT INTO order_items (order_id, food_item_id, quantity, unit_price, subtotal) 
                    VALUES (?, ?, ?, ?, ?)''', 
                  (order_id, item['id'], item['quantity'], item['price'], item['subtotal']))
    
    conn.commit()
    conn.close()
    return order_number

def get_orders(customer_id=None):
    conn = sqlite3.connect('campus_food_system.db')
    if customer_id:
        query = """SELECT o.*, v.name as vendor_name, u.full_name as customer_name
                   FROM orders o 
                   JOIN vendors v ON o.vendor_id = v.id 
                   JOIN users u ON o.customer_id = u.id
                   WHERE o.customer_id = ? 
                   ORDER BY o.created_at DESC"""
        df = pd.read_sql_query(query, conn, params=(customer_id,))
    else:
        query = """SELECT o.*, v.name as vendor_name, u.full_name as customer_name
                   FROM orders o 
                   JOIN vendors v ON o.vendor_id = v.id 
                   JOIN users u ON o.customer_id = u.id
                   ORDER BY o.created_at DESC"""
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_order_details(order_id):
    conn = sqlite3.connect('campus_food_system.db')
    query = """SELECT oi.*, fi.name as food_name, fi.description
               FROM order_items oi
               JOIN food_items fi ON oi.food_item_id = fi.id
               WHERE oi.order_id = ?"""
    df = pd.read_sql_query(query, conn, params=(order_id,))
    conn.close()
    return df

def update_order_status(order_id, status):
    conn = sqlite3.connect('campus_food_system.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()

# Streamlit app
def main():
    st.set_page_config(
        page_title="FSS Campus Food Ordering System",
        page_icon="🍽️",
        layout="wide"
    )
    
    # Initialize database
    init_database()
    
    # Session state initialization
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'page' not in st.session_state:
        st.session_state.page = 'main'
    
    # Header
    st.title("🍽️ Federal School of Statistics - Campus Food Ordering System")
    
    if not st.session_state.logged_in:
        show_login_page()
    else:
        if st.session_state.user['user_type'] == 'admin':
            show_admin_dashboard()
        else:
            show_customer_dashboard()

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 Login to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.success(f"Welcome, {user['full_name']}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        st.info("**Admin Credentials:** Username: admin, Password: admin")
        
        with st.expander("📝 Register New Account"):
            with st.form("register_form"):
                reg_username = st.text_input("Choose Username")
                reg_email = st.text_input("Email Address")
                reg_full_name = st.text_input("Full Name")
                reg_phone = st.text_input("Phone Number")
                reg_password = st.text_input("Password", type="password")
                reg_confirm_password = st.text_input("Confirm Password", type="password")
                register = st.form_submit_button("Register")
                
                if register:
                    if reg_password != reg_confirm_password:
                        st.error("Passwords do not match")
                    elif not all([reg_username, reg_email, reg_full_name, reg_password]):
                        st.error("Please fill in all required fields")
                    else:
                        try:
                            conn = sqlite3.connect('campus_food_system.db')
                            c = conn.cursor()
                            hashed_password = hash_password(reg_password)
                            c.execute('''INSERT INTO users (username, password, email, full_name, phone) 
                                         VALUES (?, ?, ?, ?, ?)''', 
                                      (reg_username, hashed_password, reg_email, reg_full_name, reg_phone))
                            conn.commit()
                            conn.close()
                            st.success("Account created successfully! Please login.")
                        except sqlite3.IntegrityError:
                            st.error("Username or email already exists")

def show_admin_dashboard():
    st.sidebar.title(f"👨‍💼 Admin Panel")
    st.sidebar.write(f"Welcome, {st.session_state.user['full_name']}")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🏪 Vendors", "🍽️ Food Items", "📋 Orders", "👥 Users"])
    
    with tab1:
        show_admin_dashboard_stats()
    
    with tab2:
        show_vendor_management()
    
    with tab3:
        show_food_management()
    
    with tab4:
        show_order_management()
    
    with tab5:
        show_user_management()

def show_admin_dashboard_stats():
    st.header("📊 System Overview")
    
    # Get statistics
    conn = sqlite3.connect('campus_food_system.db')
    
    # Total counts
    total_users = pd.read_sql_query("SELECT COUNT(*) as count FROM users WHERE user_type != 'admin'", conn).iloc[0]['count']
    total_vendors = pd.read_sql_query("SELECT COUNT(*) as count FROM vendors WHERE is_active = 1", conn).iloc[0]['count']
    total_orders = pd.read_sql_query("SELECT COUNT(*) as count FROM orders", conn).iloc[0]['count']
    total_revenue = pd.read_sql_query("SELECT COALESCE(SUM(total_amount), 0) as revenue FROM orders WHERE status != 'cancelled'", conn).iloc[0]['revenue']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", total_users)
    with col2:
        st.metric("Active Vendors", total_vendors)
    with col3:
        st.metric("Total Orders", total_orders)
    with col4:
        st.metric("Total Revenue", f"₦{total_revenue:,.2f}")
    
    # Recent orders
    st.subheader("📋 Recent Orders")
    recent_orders = pd.read_sql_query("""
        SELECT o.order_number, o.created_at, o.status, o.total_amount, 
               v.name as vendor_name, u.full_name as customer_name
        FROM orders o 
        JOIN vendors v ON o.vendor_id = v.id 
        JOIN users u ON o.customer_id = u.id
        ORDER BY o.created_at DESC LIMIT 10
    """, conn)
    
    if not recent_orders.empty:
        st.dataframe(recent_orders, use_container_width=True)
    else:
        st.info("No orders yet")
    
    conn.close()

def show_vendor_management():
    st.header("🏪 Vendor Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        vendors = get_vendors()
        if not vendors.empty:
            st.dataframe(vendors, use_container_width=True)
        else:
            st.info("No vendors found")
    
    with col2:
        st.subheader("Add New Vendor")
        with st.form("add_vendor_form"):
            name = st.text_input("Vendor Name")
            description = st.text_area("Description")
            location = st.text_input("Location")
            phone = st.text_input("Contact Phone")
            email = st.text_input("Contact Email")
            hours = st.text_input("Operating Hours")
            
            if st.form_submit_button("Add Vendor"):
                if name and location:
                    conn = sqlite3.connect('campus_food_system.db')
                    c = conn.cursor()
                    c.execute('''INSERT INTO vendors (name, description, location, contact_phone, contact_email, operating_hours) 
                                 VALUES (?, ?, ?, ?, ?, ?)''', 
                              (name, description, location, phone, email, hours))
                    conn.commit()
                    conn.close()
                    st.success("Vendor added successfully!")
                    st.rerun()
                else:
                    st.error("Name and location are required")

def show_food_management():
    st.header("🍽️ Food Items Management")
    
    vendors = get_vendors()
    if vendors.empty:
        st.warning("Please add vendors first")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        food_items = get_food_items()
        if not food_items.empty:
            st.dataframe(food_items[['name', 'vendor_name', 'price', 'category', 'is_available']], use_container_width=True)
        else:
            st.info("No food items found")
    
    with col2:
        st.subheader("Add Food Item")
        with st.form("add_food_form"):
            vendor_id = st.selectbox("Select Vendor", 
                                     options=vendors['id'].tolist(),
                                     format_func=lambda x: vendors[vendors['id'] == x]['name'].iloc[0])
            name = st.text_input("Food Name")
            description = st.text_area("Description")
            price = st.number_input("Price (₦)", min_value=0.0, step=50.0)
            category = st.selectbox("Category", ["Main Course", "Snacks", "Beverages", "Salads", "Desserts"])
            prep_time = st.number_input("Preparation Time (minutes)", min_value=1, value=15)
            
            if st.form_submit_button("Add Food Item"):
                if name and price > 0:
                    conn = sqlite3.connect('campus_food_system.db')
                    c = conn.cursor()
                    c.execute('''INSERT INTO food_items (vendor_id, name, description, price, category, preparation_time) 
                                 VALUES (?, ?, ?, ?, ?, ?)''', 
                              (vendor_id, name, description, price, category, prep_time))
                    conn.commit()
                    conn.close()
                    st.success("Food item added successfully!")
                    st.rerun()
                else:
                    st.error("Name and valid price are required")

def show_order_management():
    st.header("📋 Order Management")
    
    orders = get_orders()
    
    if not orders.empty:
        for idx, order in orders.iterrows():
            with st.expander(f"Order #{order['order_number']} - {order['status'].title()} - ₦{order['total_amount']:,.2f}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Customer:** {order['customer_name']}")
                    st.write(f"**Vendor:** {order['vendor_name']}")
                    st.write(f"**Total:** ₦{order['total_amount']:,.2f}")
                
                with col2:
                    st.write(f"**Status:** {order['status'].title()}")
                    st.write(f"**Created:** {order['created_at']}")
                    st.write(f"**Location:** {order['delivery_location']}")
                
                with col3:
                    if order['special_instructions']:
                        st.write(f"**Instructions:** {order['special_instructions']}")
                    
                    new_status = st.selectbox(
                        "Update Status",
                        ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"],
                        index=["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"].index(order['status']),
                        key=f"status_{order['id']}"
                    )
                    
                    if st.button(f"Update", key=f"update_{order['id']}"):
                        update_order_status(order['id'], new_status)
                        st.success("Status updated!")
                        st.rerun()
                
                # Show order details
                order_details = get_order_details(order['id'])
                if not order_details.empty:
                    st.write("**Order Items:**")
                    for _, item in order_details.iterrows():
                        st.write(f"- {item['food_name']} x {item['quantity']} = ₦{item['subtotal']:,.2f}")
    else:
        st.info("No orders found")

def show_user_management():
    st.header("👥 User Management")
    
    conn = sqlite3.connect('campus_food_system.db')
    users = pd.read_sql_query("SELECT id, username, email, full_name, phone, user_type, created_at FROM users", conn)
    conn.close()
    
    if not users.empty:
        st.dataframe(users, use_container_width=True)
    else:
        st.info("No users found")

def show_customer_dashboard():
    st.sidebar.title(f"👋 Welcome, {st.session_state.user['full_name']}")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.cart = []
        st.session_state.page = 'main'
        st.rerun()
    
    # Cart summary in sidebar
    if st.session_state.cart:
        st.sidebar.subheader("🛒 Your Cart")
        total = sum(item['subtotal'] for item in st.session_state.cart)
        st.sidebar.write(f"Items: {len(st.session_state.cart)}")
        st.sidebar.write(f"Total: ₦{total:,.2f}")
        
        if st.sidebar.button("View Cart & Checkout"):
            st.session_state.page = 'cart'
            st.rerun()
    
    # Clear cart button
    if st.session_state.cart and st.sidebar.button("Clear Cart"):
        st.session_state.cart = []
        st.rerun()
    
    # Page navigation
    if st.session_state.page == 'cart':
        show_cart_page()
    else:
        st.session_state.page = 'main'
        tab1, tab2, tab3 = st.tabs(["🍽️ Browse Food", "🔍 Search", "📋 My Orders"])
        
        with tab1:
            show_browse_food()
        
        with tab2:
            show_search_food()
        
        with tab3:
            show_customer_orders()

def show_browse_food():
    st.header("🍽️ Browse Food by Vendor")
    
    vendors = get_vendors()
    
    if vendors.empty:
        st.info("No vendors available at the moment")
        return
    
    for idx, vendor in vendors.iterrows():
        with st.expander(f"🏪 {vendor['name']} - {vendor['location']}", expanded=True):
            st.write(vendor['description'])
            st.write(f"📍 **Location:** {vendor['location']}")
            st.write(f"⏰ **Hours:** {vendor['operating_hours']}")
            
            food_items = get_food_items(vendor['id'])
            
            if not food_items.empty:
                cols = st.columns(3)
                for i, (idx, item) in enumerate(food_items.iterrows()):
                    with cols[i % 3]:
                        st.subheader(item['name'])
                        st.write(item['description'])
                        st.write(f"💰 **₦{item['price']:,.2f}**")
                        st.write(f"⏱️ {item['preparation_time']} mins")
                        
                        quantity = st.number_input(f"Quantity", min_value=0, max_value=10, key=f"qty_{item['id']}")
                        
                        if st.button(f"Add to Cart", key=f"add_{item['id']}"):
                            if quantity > 0:
                                add_to_cart(item, quantity)
                                st.success(f"Added {quantity}x {item['name']} to cart!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("Please select quantity")
            else:
                st.info("No food items available from this vendor")

def show_search_food():
    st.header("🔍 Search Food Items")
    
    search_term = st.text_input("Search for food, vendor, or category...")
    
    if search_term:
        results = search_food_items(search_term)
        
        if not results.empty:
            st.subheader(f"Found {len(results)} results for '{search_term}'")
            
            cols = st.columns(3)
            for i, (idx, item) in enumerate(results.iterrows()):
                with cols[i % 3]:
                    st.subheader(item['name'])
                    st.write(f"🏪 {item['vendor_name']}")
                    st.write(item['description'])
                    st.write(f"💰 **₦{item['price']:,.2f}**")
                    st.write(f"⏱️ {item['preparation_time']} mins")
                    
                    quantity = st.number_input(f"Quantity", min_value=0, max_value=10, key=f"search_qty_{item['id']}")
                    
                    if st.button(f"Add to Cart", key=f"search_add_{item['id']}"):
                        if quantity > 0:
                            add_to_cart(item, quantity)
                            st.success(f"Added {quantity}x {item['name']} to cart!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Please select quantity")
        else:
            st.info("No results found. Try different keywords.")

def add_to_cart(item, quantity):
    cart_item = {
        'id': item['id'],
        'name': item['name'],
        'vendor_id': item['vendor_id'],
        'vendor_name': item['vendor_name'],
        'price': item['price'],
        'quantity': quantity,
        'subtotal': item['price'] * quantity
    }
    
    # Check if item already in cart
    existing_item = next((x for x in st.session_state.cart if x['id'] == item['id']), None)
    if existing_item:
        existing_item['quantity'] += quantity
        existing_item['subtotal'] = existing_item['price'] * existing_item['quantity']
    else:
        st.session_state.cart.append(cart_item)

def show_cart_page():
    st.header("🛒 Your Cart")
    
    if not st.session_state.cart:
        st.info("Your cart is empty")
        if st.button("Continue Shopping"):
            st.session_state.page = 'main'
            st.rerun()
        return
    
    # Back to shopping button
    if st.button("← Continue Shopping"):
        st.session_state.page = 'main'
        st.rerun()
    
    # Group items by vendor
    vendors_in_cart = {}
    for item in st.session_state.cart:
        vendor_id = item['vendor_id']
        if vendor_id not in vendors_in_cart:
            vendors_in_cart[vendor_id] = {
                'name': item['vendor_name'],
                'items': [],
                'total': 0
            }
        vendors_in_cart[vendor_id]['items'].append(item)
        vendors_in_cart[vendor_id]['total'] += item['subtotal']
    
    if len(vendors_in_cart) > 1:
        st.warning("⚠️ You have items from multiple vendors. Please place separate orders for each vendor.")
    
    for vendor_id, vendor_info in vendors_in_cart.items():
        st.subheader(f"🏪 {vendor_info['name']}")
        
        # Display cart items
        for item in vendor_info['items']:
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            
            with col1:
                st.write(f"**{item['name']}**")
            with col2:
                st.write(f"₦{item['price']:,.2f}")
            with col3:
                new_quantity = st.number_input(
                    "Qty", 
                    min_value=1, 
                    max_value=10, 
                    value=item['quantity'], 
                    key=f"cart_qty_{item['id']}"
                )
                if new_quantity != item['quantity']:
                    item['quantity'] = new_quantity
                    item['subtotal'] = item['price'] * new_quantity
                    st.rerun() # Rerun to update totals
            with col4:
                st.write(f"₦{item['subtotal']:,.2f}")
            with col5:
                if st.button("Remove", key=f"remove_{item['id']}"):
                    st.session_state.cart.remove(item)
                    st.success(f"{item['name']} removed from cart.")
                    time.sleep(0.5)
                    st.rerun()
        
        st.markdown("---")
        st.markdown(f"**Vendor Total: ₦{vendor_info['total']:,.2f}**")
        
        st.subheader(f"Place Order for {vendor_info['name']}")
        delivery_location = st.text_input("Delivery Location (e.g., Your Hostel, Department)", key=f"loc_{vendor_id}")
        special_instructions = st.text_area("Special Instructions (optional)", key=f"inst_{vendor_id}")
        
        if st.button(f"Place Order from {vendor_info['name']}", key=f"checkout_{vendor_id}"):
            if delivery_location:
                try:
                    order_number = create_order(
                        st.session_state.user['id'], 
                        vendor_id, 
                        vendor_info['items'], 
                        vendor_info['total'], 
                        delivery_location, 
                        special_instructions
                    )
                    st.success(f"Order #{order_number} placed successfully! You will be redirected to My Orders.")
                    # Remove ordered items from cart
                    st.session_state.cart = [
                        cart_item for cart_item in st.session_state.cart 
                        if cart_item['vendor_id'] != vendor_id
                    ]
                    time.sleep(2)
                    st.session_state.page = 'orders'
                    st.rerun()
                except Exception as e:
                    st.error(f"Error placing order: {e}")
            else:
                st.error("Please enter a delivery location.")
        st.markdown("---") # Separator between vendors

def show_customer_orders():
    st.header("📋 My Orders")
    
    customer_orders = get_orders(st.session_state.user['id'])
    
    if not customer_orders.empty:
        for idx, order in customer_orders.iterrows():
            with st.expander(f"Order #{order['order_number']} - {order['status'].title()} - ₦{order['total_amount']:,.2f}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Vendor:** {order['vendor_name']}")
                    st.write(f"**Total Amount:** ₦{order['total_amount']:,.2f}")
                    st.write(f"**Status:** {order['status'].title()}")
                with col2:
                    st.write(f"**Order Date:** {order['created_at']}")
                    st.write(f"**Delivery Location:** {order['delivery_location']}")
                    if order['special_instructions']:
                        st.write(f"**Instructions:** {order['special_instructions']}")
                
                # Show order items
                order_details = get_order_details(order['id'])
                if not order_details.empty:
                    st.write("**Order Items:**")
                    for _, item in order_details.iterrows():
                        st.write(f"- {item['food_name']} x {item['quantity']} @ ₦{item['unit_price']:,.2f} = ₦{item['subtotal']:,.2f}")
                
                # Add a cancellation option for pending orders
                if order['status'] == 'pending':
                    if st.button("Cancel Order", key=f"cancel_order_{order['id']}"):
                        update_order_status(order['id'], 'cancelled')
                        st.success(f"Order #{order['order_number']} has been cancelled.")
                        st.rerun()
    else:
        st.info("You haven't placed any orders yet.")

if __name__ == "__main__":
    main()
