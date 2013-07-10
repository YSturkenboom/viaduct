from flask import Blueprint, flash, redirect, render_template, request, \
		url_for, jsonify

from viaduct import db
from viaduct.models.contact import Contact
from viaduct.models.location import Location
from viaduct.utilities import validate_form
from viaduct.forms import ContactForm

blueprint = Blueprint('contact', __name__)

@blueprint.route('/contacts/', methods=['GET', 'POST'])
@blueprint.route('/contacts/<int:page>/', methods=['GET', 'POST'])
def list(page=1):
	'''
	Show a paginated list of contacts.
	'''
	contacts = Contact.query.paginate(page, 15, False)
	return render_template('contact/list.htm', contacts=contacts)

@blueprint.route('/contacts/create/', methods=['GET'])
@blueprint.route('/contacts/edit/<int:contact_id>/', methods=['GET'])
def edit(contact_id=None):
	'''
	Create or edit a contact, frontend.
	'''
	if contact_id:
		contact = Contact.query.get(contact_id)
	else:
		contact = Contact()

	form = ContactForm(request.form, contact)

	locations = Location.query.order_by('address').order_by('city')
	form.location_id.choices = \
			[(l.id, '%s, %s' % (l.address, l.city)) for l in locations]

	return render_template('contact/edit.htm', contact=contact, form=form)

@blueprint.route('/contacts/create/', methods=['POST'])
@blueprint.route('/contacts/edit/<int:contact_id>/', methods=['POST'])
def update(contact_id=None):
	'''
	Create or edit a contact, backend.
	'''
	if contact_id:
		contact = Contact.query.get(contact_id)
	else:
		contact = Contact()

	form = ContactForm(request.form, contact)
	if not validate_form(form, ['name', 'email', 'phone_nr', 'location_id']):
		return redirect(url_for('contact.edit', contact_id=contact_id))

	form.populate_obj(contact)
	db.session.add(contact)
	db.session.commit()

	if contact_id:
		flash('Contactpersoon opgeslagen', 'success')
	else:
		contact_id = contact.id
		flash('Contactpersoon aangemaakt', 'success')

	return redirect(url_for('contact.edit', contact_id=contact_id))

@blueprint.route('/contacts/delete/<int:contact_id>/', methods=['POST'])
def delete(contact_id):
	'''
	Delete a contact.
	'''
	contact = Contact.query.get(contact_id)
	if not contact:
		return abort(404)

	db.session.delete(contact)
	db.session.commit()
	flash('Contactpersoon verwijderd', 'success')

	return redirect(url_for('contact.list'))
