from flask import render_template, request
# -*- coding: utf-8 -*-
import datetime
import re

from viaduct import db, application
from viaduct.helpers import get_login_form
from viaduct.models.activity import Activity
from viaduct.models.navigation import NavigationEntry
from viaduct.models.page import Page
from viaduct.api.group import GroupPermissionAPI
from viaduct.api.user import UserAPI


class NavigationAPI:
    @staticmethod
    def get_navigation_bar():
        entries = NavigationAPI.get_entries(True)
        entries = NavigationAPI.remove_unauthorized(entries)
        login_form = get_login_form()

        return render_template('navigation/view_bar.htm', bar_entries=entries,
                               login_form=login_form)

    @staticmethod
    def get_navigation_menu():
        my_path = request.path

        my_path = re.sub(r'(/[0-9]+)?/$', '', my_path)

        me = db.session.query(NavigationEntry).filter_by(url=my_path)\
            .first()

        if me:
            parent = me.parent

        else:
            parent_path = my_path.rsplit('/', 1)[0]
            parent = db.session.query(NavigationEntry)\
                .filter_by(url=parent_path).first()

        if parent:
            entries = db.session.query(NavigationEntry)\
                .filter_by(parent_id=parent.id)\
                .order_by(NavigationEntry.position).all()
        else:
            entries = [me] if me else []

        entries = NavigationAPI.remove_unauthorized(entries)

        return render_template('navigation/view_sidebar.htm', back=parent,
                               pages=entries, current=me)

    @staticmethod
    def current_entry():
        my_path = request.path

        temp_strip = my_path.rstrip('0123456789')
        if temp_strip.endswith('/'):
            my_path = temp_strip

        my_path = my_path.rstrip('/')

        return db.session.query(NavigationEntry).filter_by(url=my_path)\
            .first()

    @staticmethod
    def parent_entry():
        my_path = request.path

        temp_strip = my_path.rstrip('0123456789')
        if temp_strip.endswith('/'):
            my_path = temp_strip

        my_path = my_path.rstrip('/')

        return db.session.query(NavigationEntry).filter_by(url=my_path)\
            .first()

    @staticmethod
    def order(entries, parent):
        position = 1

        for entry in entries:
            db_entry = db.session.query(NavigationEntry)\
                .filter_by(id=entry['id']).first()

            db_entry.parent_id = parent.id if parent else None
            db_entry.position = position

            NavigationAPI.order(entry['children'], db_entry)

            position += 1

            db.session.add(db_entry)
            db.session.commit()

    @staticmethod
    def get_entries(inc_activities=False):
        entries = db.session.query(NavigationEntry).filter_by(parent_id=None)\
            .order_by(NavigationEntry.position).all()

        # Fill in activity lists.
        if inc_activities:
            for entry in entries:
                if entry.activity_list:
                    entry.activities = []
                    activities = db.session.query(Activity)\
                        .filter(Activity.end_time > datetime.datetime.now())\
                        .order_by("activity_start_time").all()

                    for activity in activities:
                        entry_title = '%s %s' % (activity.start_time
                                                 .strftime('%Y-%m-%d'),
                                                 activity.name)
                        entry.activities.append(
                            NavigationEntry(entry, entry_title,
                                            '/activities/' + str(activity.id),
                                            False, False, 0))

        return entries

    @staticmethod
    def can_view(entry):
        '''
        Check whether the current user can view the entry, so if not it can be
        removed from the navigation.
        '''
        blueprints = [(name, b.url_prefix) for name, b in
                      application.blueprints.iteritems()]

        if entry.external or entry.activity_list:
            return True

        url = entry.url
        if not url[-1:] == '/':
            path = url
            url += '/'
        else:
            path = url[:-1]

        for blueprint, url_prefix in blueprints:
            if not url_prefix:
                continue

            if url_prefix == url:
                return GroupPermissionAPI.can_read(blueprint)

        page = Page.query.filter_by(path=path).first()
        if not page:
            return True

        return UserAPI.can_read(page)

    @staticmethod
    def remove_unauthorized(entries):
        authorized_entries = list(entries)
        for entry in entries:
            if not NavigationAPI.can_view(entry):
                authorized_entries.remove(entry)

        return authorized_entries

    @staticmethod
    def order_entries(query):
        """Order entries."""
        return query.order_by(NavigationEntry.position)

    @staticmethod
    def get_navigation_backtrack():
        backtrack = []
        tracker = NavigationAPI.current_entry()
        while tracker:
            backtrack.append(tracker)
            tracker = tracker.parent

        backtrack.reverse()
        return render_template('navigation/view_backtrack.htm',
                               backtrack=backtrack)
