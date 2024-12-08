from main import db
from datetime import datetime

class PharmacyItem(db.Model):
    __tablename__ = 'pharmacy_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Medicine' or 'Equipment'
    description = db.Column(db.Text)
    unit = db.Column(db.String(20), nullable=False)  # e.g., 'Tablets', 'Pieces', 'Boxes'
    quantity = db.Column(db.Integer, nullable=False, default=0)
    cost_per_unit = db.Column(db.Float, nullable=False)
    reorder_level = db.Column(db.Integer, default=10)  # Minimum quantity before reorder
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PharmacyItem {self.name}>'
