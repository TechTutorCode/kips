from main import db
from models.lab_results import LabResult
from models.billing import BillItem, Bill
from sqlalchemy import text, and_, or_
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s',
    filename='lab_results_migration.log'
)

def clean_lab_results():
    """
    Clean up lab results with invalid bill_item_id references
    """
    try:
        # Find lab results with no valid bill item
        invalid_results = db.session.query(LabResult).filter(
            or_(
                ~db.exists().where(BillItem.id == LabResult.bill_item_id),
                LabResult.bill_item_id == None
            )
        ).all()

        logging.info(f"Found {len(invalid_results)} invalid lab results")
        print(f"Found {len(invalid_results)} invalid lab results")

        # Detailed tracking of invalid results
        invalid_result_details = []

        # Remove or update invalid results
        for result in invalid_results:
            detail = {
                'lab_result_id': result.id,
                'current_bill_item_id': result.bill_item_id,
                'status': result.status,
                'created_at': result.created_at
            }
            invalid_result_details.append(detail)

            logging.warning(f"Removing Invalid Lab Result - ID: {result.id}, Current Bill Item ID: {result.bill_item_id}")
            db.session.delete(result)

        # Commit the changes
        db.session.commit()
        logging.info("Lab results cleanup completed successfully")
        print("Lab results cleanup completed successfully")

        # Optional: Write detailed log of removed results
        with open('removed_lab_results.log', 'w') as f:
            import json
            json.dump(invalid_result_details, f, default=str, indent=2)

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during lab results cleanup: {str(e)}")
        print(f"Error during lab results cleanup: {str(e)}")

def validate_lab_results():
    """
    Comprehensive validation of lab results integrity
    """
    try:
        # Advanced SQL query to check lab results integrity
        sql = text("""
        SELECT 
            lr.id as lab_result_id, 
            lr.bill_item_id, 
            lr.status as lab_result_status,
            bi.id as bill_item_id, 
            bi.description as bill_item_description,
            bi.bill_id,
            b.id as bill_id,
            b.patient_id,
            b.status as bill_status
        FROM 
            lab_results lr
        LEFT JOIN 
            bill_items bi ON lr.bill_item_id = bi.id
        LEFT JOIN 
            bills b ON bi.bill_id = b.id
        WHERE 
            bi.id IS NULL OR b.id IS NULL OR lr.bill_item_id IS NULL
        """)

        results = db.session.execute(sql).fetchall()
        
        logging.info("Lab Results Integrity Check:")
        print("Lab Results Integrity Check:")
        
        integrity_issues = []
        for row in results:
            issue = {
                'lab_result_id': row.lab_result_id,
                'lab_result_status': row.lab_result_status,
                'bill_item_id': row.bill_item_id,
                'bill_item_description': row.bill_item_description,
                'bill_id': row.bill_id,
                'patient_id': row.patient_id,
                'bill_status': row.bill_status
            }
            integrity_issues.append(issue)
            
            logging.warning(f"""
            Integrity Issue Detected:
            - Lab Result ID: {row.lab_result_id}
            - Lab Result Status: {row.lab_result_status}
            - Bill Item ID: {row.bill_item_id}
            - Bill Item Description: {row.bill_item_description}
            - Bill ID: {row.bill_id}
            - Patient ID: {row.patient_id}
            - Bill Status: {row.bill_status}
            """)
        
        # Optional: Write detailed log of integrity issues
        with open('lab_results_integrity_issues.log', 'w') as f:
            import json
            json.dump(integrity_issues, f, default=str, indent=2)
        
        return integrity_issues

    except Exception as e:
        logging.error(f"Error during lab results integrity check: {str(e)}")
        print(f"Error during lab results integrity check: {str(e)}")
        return []

def main():
    # Validate first
    integrity_issues = validate_lab_results()
    
    if integrity_issues:
        print(f"Found {len(integrity_issues)} integrity issues. Proceeding with cleanup...")
        clean_lab_results()
    else:
        print("No integrity issues found in lab results.")

if __name__ == '__main__':
    main()
