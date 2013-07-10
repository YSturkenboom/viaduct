from flask import Blueprint, flash, redirect, render_template, request, \
		url_for, jsonify

from viaduct import db
from viaduct.models.location import Location
from viaduct.utilities import serialize_sqla, validate_form
from viaduct.forms import LocationForm

blueprint = Blueprint('location', __name__)

@blueprint.route('/locations/<int:location_id>/contacts/', methods=['GET'])
def get_contacts(location_id):
	location = Location.query.get(location_id)
	return jsonify(contacts=serialize_sqla(location.contacts.all()))

@blueprint.route('/locations/', methods=['GET', 'POST'])
@blueprint.route('/locations/<int:page>/', methods=['GET', 'POST'])
def list(page=1):
	locations = Location.query.paginate(page, 15, False)
	return render_template('location/list.htm', locations=locations)

@blueprint.route('/locations/create/', methods=['GET'])
@blueprint.route('/locations/edit/<int:location_id>/', methods=['GET'])
def view(location_id=None):
	'''
	FRONTEND
	Create, view or edit a location.
	'''

	# Select location..
	if location_id:
		location = Location.query.get(location_id)
	else:
		location = Location()

	form = LocationForm(request.form, location)
	return render_template('location/view.htm', location=location, form=form)

@blueprint.route('/locations/create/', methods=['POST'])
@blueprint.route('/locations/edit/<int:location_id>/', methods=['POST'])
def update(location_id=None):
	'''
	BACKEND
	Create or edit a location.
	'''

	# Select location.
	if location_id:
		location = Location.query.get(location_id)
	else:
		location = Location()

	form = LocationForm(request.form, location)
	if not validate_form(form, ['city', 'country', 'address', 'zip', 'email',
				'phone_nr']):
		return redirect(url_for('location.view', location_id=location_id))

	form.populate_obj(location)
	db.session.add(location)
	db.session.commit()

	if location_id:
		flash('Locatie opgeslagen', 'success')
	else:
		location_id = location.id
		flash('Locatie aangemaakt', 'success')

	return redirect(url_for('location.view', location_id=location_id))

@blueprint.route('/locations/delete/<int:location_id>/', methods=['POST'])
def delete(location_id):
	'''
	BACKEND
	Delete a location.
	'''
	location = Location.query.get(location_id)
	if not location:
		return abort(404)

	db.session.delete(location)
	db.session.commit()
	flash('Locatie verwijderd', 'success')

	return redirect(url_for('location.list'))
