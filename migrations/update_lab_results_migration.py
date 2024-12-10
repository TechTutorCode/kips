from main import db
from models.lab_results import LabResult
from models.billing import BillItem
from models.patients import Patient
from sqlalchemy import text

def migrate_lab_results():
    """
    Migrate existing lab results to include patient_id
    """
    try:
        # Start a transaction
        with db.session.begin():
            # Find all lab results
            lab_results = LabResult.query.all()
            
            print(f"Total Lab Results to Migrate: {len(lab_results)}")
            
            # Track migration details
            migration_details = []
            
            for lab_result in lab_results:
                # Try to get patient through bill item
                try:
                    patient = lab_result.bill_item.bill.patient if lab_result.bill_item and lab_result.bill_item.bill else None
                    
                    if patient:
                        # Update patient_id
                        lab_result.patient_id = patient.id
                        
                        migration_details.append({
                            'lab_result_id': lab_result.id,
                            'bill_item_id': lab_result.bill_item_id,
                            'patient_id': patient.id,
                            'patient_name': f"{patient.first_name} {patient.last_name}"
                        })
                    else:
                        print(f"WARNING: Could not find patient for Lab Result {lab_result.id}")
                
                except Exception as inner_e:
                    print(f"ERROR processing Lab Result {lab_result.id}: {str(inner_e)}")
            
            # Commit changes
            db.session.commit()
            
            # Log migration details
            with open('lab_results_migration_log.json', 'w') as f:
                import json
                json.dump(migration_details, f, indent=2)
            
            print("Lab Results Migration Completed Successfully")
    
    except Exception as e:
        db.session.rollback()
        print(f"ERROR during Lab Results Migration: {str(e)}")

def validate_migration():
    """
    Validate the migration process
    """
    # SQL query to check migration results
    sql = text("""
    SELECT 
        lr.id as lab_result_id, 
        lr.patient_id, 
        lr.bill_item_id,
        p.first_name,
        p.last_name
    FROM 
        lab_results lr
    LEFT JOIN 
        patients p ON lr.patient_id = p.id
    WHERE 
        lr.patient_id IS NULL OR p.id IS NULL
    """)

    results = db.session.execute(sql).fetchall()
    
    print("Migration Validation Results:")
    for row in results:
        print(f"Lab Result ID: {row.lab_result_id}")
        print(f"Patient ID: {row.patient_id}")
        print(f"Bill Item ID: {row.bill_item_id}")
        print("---")

def main():
    migrate_lab_results()
    validate_migration()

if __name__ == '__main__':
    main()
