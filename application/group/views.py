from flask import Blueprint, flash, redirect, render_template, request, url_for

from application import db
from application.group.models import user_group, Group
from application.user.models import User

group = Blueprint('group', __name__)

@group.route('/groups/', methods=['GET', 'POST'])
@group.route('/groups/<int:page>/', methods=['GET', 'POST'])
def view(page=1):
	if request.method == 'POST':
		group_ids = request.form.getlist('select')

		groups = Group.query.filter(Group.id.in_(group_ids)).all()

		for group in groups:
			db.session.delete(group)

		db.session.commit()

		if len(groups) > 1:
			flash('The selected groups have been deleted.', 'success')
		else:
			flash('The selected group has been deleted.', 'success')

		redirect(url_for('group.view'))

	groups = Group.query.paginate(page, 15, False)

	return render_template('group/view.htm', groups=groups)

@group.route('/groups/create/', methods=['GET', 'POST'])
def create():
	if request.method == 'POST':
		name = request.form['name'].strip()
		valid_form = True

		if not name:
			flash('No group name has been specified.', 'error')
			valid_form = False
		elif Group.query.filter(Group.name==name).count() > 0:
			flash('The group name that has been specified is in use already.', 'error')
			valid_form = False

		if valid_form:
			group = Group(name)

			db.session.add(group)
			db.session.commit()

			flash('The group has been created.', 'success')

			return redirect(url_for('group.view'))

	return render_template('group/create.htm')

@group.route('/groups/<int:group_id>/users/', methods=['GET', 'POST'])
@group.route('/groups/<int:group_id>/users/<int:page>/', methods=['GET', 'POST'])
def view_users(group_id, page=1):
	group = Group.query.filter(Group.id==group_id).first()

	if not group:
		flash('There is no such group.')

		return redirect(url_for('group.view'))

	if request.method == 'POST':
		user_ids = request.form.getlist('select')

		users = group.get_users().filter(User.id.in_(user_ids)).all()

		for user in users:
			group.delete_user(user)

		db.session.add(group)
		db.session.commit()

		if len(user_ids) > 1:
			flash('The selected users have been deleted.', 'success')
		else:
			flash('The selected user has been deleted.', 'success')

		return redirect(url_for('group.view_users', group_id=group_id))

	users = group.get_users().paginate(page, 15, False)

	return render_template('group/view_users.htm', group=group, users=users)

@group.route('/groups/<int:group_id>/users/add/', methods=['GET', 'POST'])
@group.route('/groups/<int:group_id>/users/add/<int:page_id>', methods=['GET', 'POST'])
def add_users(group_id, page=1):
	group = Group.query.filter(Group.id==group_id).first()

	if not group:
		flash('There is no such group.')

		return redirect(url_for('group.view'))

	if request.method == 'POST':
		user_ids = request.form.getlist('select')

		users = User.query.filter(User.id.in_(user_ids)).all()

		for user in users:
			group.add_user(user)

		db.session.add(group)
		db.session.commit()

		if len(user_ids) > 1:
			flash('The selected users have been added to the group.', 'success')
		else:
			flash('The selected user has been added to the group.', 'success')

		return redirect(url_for('group.view_users', group_id=group_id))

	users = User.query.paginate(page, 15, False)

	return render_template('group/add_users.htm', group=group, users=users)
