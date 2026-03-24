#!/usr/bin/env python3
"""
Test script to verify the loan appraiser system database structure.
This script validates that all required tables and columns are created correctly.
"""

import sqlite3
import sys

def test_database_structure():
    """Test that the database structure matches the loan appraiser requirements."""
    
    print("=" * 60)
    print("Loan Appraiser System - Database Structure Test")
    print("=" * 60)
    
    # Initialize database
    from App import init_db, DB
    
    try:
        init_db()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # Test 1: Check users table has role column
    print("\n--- Test 1: Users Table ---")
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns: {', '.join(columns)}")
    
    if 'role' in columns:
        print("✓ Users table has 'role' column")
    else:
        print("✗ Users table missing 'role' column")
        return False
    
    # Test 2: Check loan_applications table exists
    print("\n--- Test 2: Loan Applications Table ---")
    cursor.execute("PRAGMA table_info(loan_applications)")
    app_columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    if not app_columns:
        print("✗ Loan applications table does not exist")
        return False
    
    print(f"Columns: {', '.join(app_columns.keys())}")
    
    required_app_columns = [
        'id', 'user_id', 'applicant_name', 'email', 'phone',
        'loan_amount', 'loan_type', 'employment_status', 'monthly_income',
        'status', 'appraisal_status', 'appraiser_id', 'validity_flag',
        'ltv_ratio', 'dti_ratio', 'submitted_at'
    ]
    
    missing = [col for col in required_app_columns if col not in app_columns]
    if missing:
        print(f"✗ Missing columns: {', '.join(missing)}")
        return False
    else:
        print("✓ All required columns present")
    
    # Test 3: Check appraisal_activities table exists
    print("\n--- Test 3: Appraisal Activities Table ---")
    cursor.execute("PRAGMA table_info(appraisal_activities)")
    activity_columns = [row[1] for row in cursor.fetchall()]
    
    if not activity_columns:
        print("✗ Appraisal activities table does not exist")
        return False
    
    print(f"Columns: {', '.join(activity_columns)}")
    
    required_activity_columns = [
        'id', 'loan_application_id', 'appraiser_id', 
        'activity_type', 'description', 'performed_at'
    ]
    
    missing = [col for col in required_activity_columns if col not in activity_columns]
    if missing:
        print(f"✗ Missing columns: {', '.join(missing)}")
        return False
    else:
        print("✓ All required columns present")
    
    # Test 4: Check document_requests table exists
    print("\n--- Test 4: Document Requests Table ---")
    cursor.execute("PRAGMA table_info(document_requests)")
    doc_columns = [row[1] for row in cursor.fetchall()]
    
    if not doc_columns:
        print("✗ Document requests table does not exist")
        return False
    
    print(f"Columns: {', '.join(doc_columns)}")
    
    required_doc_columns = [
        'id', 'loan_application_id', 'appraiser_id', 
        'document_type', 'request_message', 'status', 'requested_at'
    ]
    
    missing = [col for col in required_doc_columns if col not in doc_columns]
    if missing:
        print(f"✗ Missing columns: {', '.join(missing)}")
        return False
    else:
        print("✓ All required columns present")
    
    # Test 5: Insert sample data
    print("\n--- Test 5: Sample Data Insertion ---")
    try:
        # Insert test appraiser
        cursor.execute("""
            INSERT INTO users (name, email, password, role, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, ('Test Appraiser', 'appraiser@test.com', 'hashed_password', 'appraiser'))
        
        appraiser_id = cursor.lastrowid
        
        # Insert test applicant
        cursor.execute("""
            INSERT INTO users (name, email, password, role, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, ('Test Applicant', 'applicant@test.com', 'hashed_password', 'applicant'))
        
        applicant_id = cursor.lastrowid
        
        # Insert test loan application
        cursor.execute("""
            INSERT INTO loan_applications 
            (user_id, applicant_name, email, phone, loan_amount, loan_type, 
             employment_status, monthly_income, status, appraisal_status, 
             ltv_ratio, dti_ratio, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (applicant_id, 'Test Applicant', 'applicant@test.com', '1234567890',
              50000.00, 'Personal', 'Employed', 5000.00, 'pending', 'not_started',
              0.0, 0.83))
        
        app_id = cursor.lastrowid
        
        # Insert test activity
        cursor.execute("""
            INSERT INTO appraisal_activities 
            (loan_application_id, appraiser_id, activity_type, description, performed_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (app_id, appraiser_id, 'test_activity', 'Test activity log'))
        
        # Insert test document request
        cursor.execute("""
            INSERT INTO document_requests 
            (loan_application_id, appraiser_id, document_type, request_message, status, requested_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (app_id, appraiser_id, 'ID Proof', 'Please provide ID', 'pending'))
        
        conn.commit()
        print("✓ Sample data inserted successfully")
        
        # Verify data
        cursor.execute("SELECT COUNT(*) FROM loan_applications")
        count = cursor.fetchone()[0]
        print(f"✓ Loan applications count: {count}")
        
        cursor.execute("SELECT COUNT(*) FROM appraisal_activities")
        count = cursor.fetchone()[0]
        print(f"✓ Appraisal activities count: {count}")
        
        cursor.execute("SELECT COUNT(*) FROM document_requests")
        count = cursor.fetchone()[0]
        print(f"✓ Document requests count: {count}")
        
    except Exception as e:
        print(f"✗ Sample data insertion failed: {e}")
        return False
    finally:
        conn.close()
    
    print("\n" + "=" * 60)
    print("✓ All tests passed! Database structure is correct.")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_database_structure()
    sys.exit(0 if success else 1)
