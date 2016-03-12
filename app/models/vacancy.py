from viaduct import db
from datetime import datetime

from viaduct.models.company import Company
from viaduct.models import BaseEntity


class Vacancy(db.Model, BaseEntity):
    __tablename__ = 'vacancy'

    title = db.Column(db.String(200), unique=True)
    description = db.Column(db.String(1024))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    contract_of_service = db.Column(db.Enum('voltijd', 'deeltijd',
                                            'bijbaan', 'stage'))
    workload = db.Column(db.String(256))
    date = db.Column(db.DateTime)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))

    company = db.relationship(Company, backref=db.backref('vacancies',
                              lazy='dynamic'))

    def __init__(self, title='', description='', start_date=None,
                 end_date=None, contract_of_service=None, workload='',
                 company=None):
        self.title = title
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.contract_of_service = contract_of_service
        self.workload = workload
        self.date = datetime.now()
        self.company = company
