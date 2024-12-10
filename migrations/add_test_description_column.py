from main import db
from sqlalchemy import text

def add_test_description_column():
    """
    Add test_description column to lab_results table
    """
    try:
        # Add column with SQLAlchemy
        db.session.execute(text('''
            ALTER TABLE lab_results 
            ADD COLUMN test_description VARCHAR(255)
        '''))
        
        # Optional: Update existing records with a default description
        db.session.execute(text('''
            UPDATE lab_results 
            SET test_description = 'Unspecified Lab Test'
            WHERE test_description IS NULL
        '''))
        
        db.session.commit()
        print("Successfully added test_description column to lab_results")
    
    except Exception as e:
        db.session.rollback()
        print(f"Error adding test_description column: {str(e)}")

def main():
    add_test_description_column()

if __name__ == '__main__':
    main()
