from viaduct import db
from viaduct.models.location import Location
from viaduct.models.contact import Contact

class Company(db.Model):
	__tablename__ = 'company'

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(256), unique=True)
	description = db.Column(db.String(1024))
	website = db.Column(db.String(256))
	contract_start_date = db.Column(db.Date)
	contract_end_date = db.Column(db.Date)
	location_id = db.Column(db.Integer, db.ForeignKey('location.id'))
	contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'))
	rank = db.Column(db.Integer)
	location = db.relationship('Location', backref=db.backref('companies',
			lazy='dynamic'))
	contact = db.relationship('Contact', backref=db.backref('companies',
			lazy='dynamic'))

	def __init__(self, name='', description='', contract_start_date=None,
			contract_end_date=None, location=None, contact=None, website=None, rank=1000):
		self.name = name
		self.description = description
		self.contract_start_date = contract_start_date
		self.contract_end_date = contract_end_date
		self.location = location
		self.contact = contact
		self.website = website
		self.rank = rank