# create_sqlite_demo.py
import sqlite3
import os

def create_sqlite_demo():
    """Create a comprehensive SQLite demo database"""
    print("🗄️ Creating SQLite demo database...")
    
    # Remove existing if exists
    if os.path.exists('demo_company.db'):
        os.remove('demo_company.db')
    
    conn = sqlite3.connect('demo_company.db')
    
    # Create tables with more realistic structure
    conn.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            salary REAL,
            hire_date TEXT,
            city TEXT,
            country TEXT DEFAULT 'USA'
        )
    ''')
    
    conn.execute('''
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            manager_id INTEGER,
            budget REAL,
            location TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            sale_amount REAL,
            sale_date TEXT,
            product TEXT,
            quantity INTEGER,
            customer_name TEXT
        )
    ''')
    
    conn.execute('''
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            city TEXT,
            country TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            order_date TEXT,
            total_amount REAL,
            status TEXT,
            product_category TEXT
        )
    ''')
    
    # Insert comprehensive sample data
    employees_data = [
        ('John Smith', 'john@company.com', 'Sales', 50000, '2023-01-15', 'London', 'UK'),
        ('Sarah Johnson', 'sarah@company.com', 'Engineering', 75000, '2022-06-20', 'New York', 'USA'),
        ('Mike Brown', 'mike@company.com', 'Sales', 48000, '2023-03-10', 'London', 'UK'),
        ('Lisa Davis', 'lisa@company.com', 'Marketing', 52000, '2022-11-05', 'Paris', 'France'),
        ('David Wilson', 'david@company.com', 'Engineering', 80000, '2022-01-10', 'Tokyo', 'Japan'),
        ('Emma Thompson', 'emma@company.com', 'Sales', 52000, '2023-07-15', 'Berlin', 'Germany'),
        ('James Miller', 'james@company.com', 'Marketing', 48000, '2023-09-20', 'Sydney', 'Australia')
    ]
    
    for emp in employees_data:
        conn.execute(
            'INSERT INTO employees (name, email, department, salary, hire_date, city, country) VALUES (?, ?, ?, ?, ?, ?, ?)', 
            emp
        )
    
    departments_data = [
        ('Sales', 1, 1000000, 'New York'),
        ('Engineering', 2, 1500000, 'San Francisco'),
        ('Marketing', 4, 800000, 'Chicago')
    ]
    
    for dept in departments_data:
        conn.execute('INSERT INTO departments (name, manager_id, budget, location) VALUES (?, ?, ?, ?)', dept)
    
    sales_data = [
        (1, 1500.00, '2024-01-10', 'Product A', 5, 'Alice Brown'),
        (1, 2000.00, '2024-01-15', 'Product B', 3, 'Bob Green'),
        (3, 1200.00, '2024-01-12', 'Product A', 2, 'Carol White'),
        (2, 3000.00, '2024-01-08', 'Product C', 1, 'Daniel Black'),
        (1, 1800.00, '2024-01-20', 'Product A', 4, 'Eva Purple'),
        (6, 2500.00, '2024-01-18', 'Product B', 3, 'Frank Gray')
    ]
    
    for sale in sales_data:
        conn.execute(
            'INSERT INTO sales (employee_id, sale_amount, sale_date, product, quantity, customer_name) VALUES (?, ?, ?, ?, ?, ?)', 
            sale
        )
    
    customers_data = [
        ('Alice Brown', 'alice@email.com', 'London', 'UK'),
        ('Bob Green', 'bob@email.com', 'New York', 'USA'),
        ('Carol White', 'carol@email.com', 'Paris', 'France'),
        ('Daniel Black', 'daniel@email.com', 'Tokyo', 'Japan'),
        ('Eva Purple', 'eva@email.com', 'London', 'UK'),
        ('Frank Gray', 'frank@email.com', 'Berlin', 'Germany')
    ]
    
    for cust in customers_data:
        conn.execute('INSERT INTO customers (name, email, city, country) VALUES (?, ?, ?, ?)', cust)
    
    orders_data = [
        (1, '2024-01-05', 250.00, 'completed', 'Electronics'),
        (2, '2024-01-06', 180.50, 'completed', 'Books'),
        (1, '2024-01-08', 320.75, 'pending', 'Clothing'),
        (3, '2024-01-10', 150.00, 'completed', 'Electronics'),
        (4, '2024-01-12', 275.25, 'shipped', 'Home'),
        (5, '2024-01-14', 420.00, 'completed', 'Electronics')
    ]
    
    for order in orders_data:
        conn.execute('INSERT INTO orders (customer_id, order_date, total_amount, status, product_category) VALUES (?, ?, ?, ?, ?)', order)
    
    conn.commit()
    conn.close()
    
    print("✅ SQLite demo database created: demo_company.db")
    
    # Verify and show stats
    conn = sqlite3.connect('demo_company.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM employees")
    emp_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sales")
    sales_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM customers")
    cust_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Demo data created:")
    print(f"   👥 {emp_count} employees")
    print(f"   💰 {sales_count} sales")
    print(f"   👤 {cust_count} customers")
    print(f"   📦 {orders_count} orders")
    print("\n💡 You can now connect using SQLite in your Streamlit app!")

if __name__ == "__main__":
    create_sqlite_demo()