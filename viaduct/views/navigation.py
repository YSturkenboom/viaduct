from flask import Blueprint, render_template, abort, request, flash, \
    redirect, url_for

from viaduct import db
from viaduct.helpers import flash_form_errors
from viaduct.models.navigation import NavigationEntry
from viaduct.forms import NavigationEntryForm
from viaduct.api.navigation import NavigationAPI
from viaduct.api.group import GroupPermissionAPI
from viaduct.api.page import PageAPI
from viaduct.models.page import Page

import json
import re

blueprint = Blueprint('navigation', __name__, url_prefix='/navigation')


@blueprint.route('/edit/')
def edit_back():
    if not GroupPermissionAPI.can_read('navigation'):
        return abort(403)

    return redirect(url_for('navigation.view'))


@blueprint.route('/')
def view():
    if not GroupPermissionAPI.can_read('navigation'):
        return abort(403)

    entries = NavigationAPI.get_entries()

    return render_template('navigation/view.htm', nav_entries=entries)


@blueprint.route('/create/', methods=['GET', 'POST'])
@blueprint.route('/create/<int:parent_id>/', methods=['GET', 'POST'])
@blueprint.route('/edit/<int:entry_id>/', methods=['GET', 'POST'])
def edit(entry_id=None, parent_id=None):
    if not GroupPermissionAPI.can_read('navigation'):
        return abort(403)

    if entry_id:
        entry = db.session.query(NavigationEntry).filter_by(id=entry_id)\
            .first()
        if not entry:
            return abort(404)
    else:
        entry = None

    form = NavigationEntryForm(request.form, entry)

    if form.is_submitted():
        if form.validate_on_submit():
            url = form.url.data
            pattern = re.compile('^/')
            if not pattern.match(url):
                url = '/' + url

            if entry:
                flash('De navigatie link is opgeslagen.', 'success')
                entry.title = form.title.data
                entry.url = url
                entry.external = form.external.data
                entry.activity_list = form.activity_list.data
            else:
                if not parent_id:
                    parent = None

                    last_entry = db.session.query(NavigationEntry)\
                        .filter_by(parent_id=None)\
                        .order_by(NavigationEntry.position.desc()).first()

                    position = last_entry.position + 1
                else:
                    parent = db.session.query(NavigationEntry) \
                        .filter_by(id=parent_id).first()

                    if not parent:
                        flash('Deze navigatie parent bestaat niet.', 'danger')
                        return redirect(url_for('navigation.edit'))

                    last_entry = db.session.query(NavigationEntry)\
                        .filter_by(parent_id=parent.id)\
                        .order_by(NavigationEntry.position.desc()).first()
                    if last_entry:
                        position = last_entry.position + 1
                    else:
                        position = 0

                entry = NavigationEntry(parent, form.title.data, url,
                                        form.external.data,
                                        form.activity_list.data, position)
                flash('De navigatie link is aangemaakt.', 'success')

            db.session.add(entry)
            db.session.commit()

            if not form.external.data:

                # Check if the page exists, if not redirect to create it
                path = form.url.data.lstrip('/')
                page = Page.get_by_path(path)
                if not page and form.url.data != '/':
                    flash('De link verwijst naar een pagina die niet bestaat, '
                          'maak deze aub aan!', 'alert')
                    return redirect(url_for('page.edit_page', path=path))

            return redirect(url_for('navigation.edit', entry_id=entry.id))

        else:
            known_error = False

            if not form.title.data:
                flash('Geen titel opgegeven.', 'danger')
                known_error = True

            if not form.url.data:
                flash('Geen url opgegeven.', 'danger')
                known_error = True
            if not known_error:
                flash_form_errors(form)

    parents = db.session.query(NavigationEntry).filter_by(parent_id=None)

    if entry:
        parents = parents.filter(NavigationEntry.id != entry.id)

    parents = parents.all()

    return render_template('navigation/edit.htm', entry=entry, form=form,
                           parents=parents)


@blueprint.route('/delete/<int:entry_id>/', methods=['GET'])
@blueprint.route('/delete/<int:entry_id>/<int:inc_page>', methods=['GET'])
def delete(entry_id, inc_page=0):
    if not GroupPermissionAPI.can_write('navigation'):
        return abort(403)

    if inc_page and not GroupPermissionAPI.can_write('page'):
        return abort(403)

    entry = db.session.query(NavigationEntry).filter_by(id=entry_id).first()
    if not entry:
        abort(404)

    if not entry.parent:
        if entry.children.count() > 0:
            flash('Deze item heeft nog subitems.', 'danger')
            return redirect(url_for('navigation.edit', entry_id=entry.id))

    if inc_page:
        if entry.external or entry.activity_list:
            flash('Deze item verwijst niet naar een pagina op deze website.',
                  'danger')
        else:
            path = entry.url.lstrip('/')
            if PageAPI.remove_page(path):
                flash('De pagina is verwijderd.', 'success')
            else:
                flash('De te verwijderen pagina kon niet worden gevonden.',
                      'danger')

    db.session.delete(entry)
    db.session.commit()

    flash('De navigatie-item is verwijderd.', 'success')

    return redirect(url_for('navigation.view'))


@blueprint.route('/navigation/reorder', methods=['POST'])
def reorder():
    if not GroupPermissionAPI.can_write('navigation'):
        return abort(403)

    entries = json.loads(request.form['entries'])
    NavigationAPI.order(entries, None)

    return ""
