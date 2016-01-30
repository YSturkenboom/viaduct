from viaduct import db, application
from flask import render_template, Markup, redirect, url_for, abort,\
    flash
from flask.ext.login import current_user
from unidecode import unidecode
import datetime
import re
import baas32 as b32

from fuzzywuzzy.process import extractOne

from viaduct.api.module import ModuleAPI
from viaduct.api.user import UserAPI
from viaduct.models import Group, User
from viaduct.models import Minute, Task
from viaduct.models.pimpy import TaskUserRel

from viaduct.api import copernica

DATE_FORMAT = application.config['DATE_FORMAT']


class PimpyAPI:
    @staticmethod
    def commit_minute_to_db(content, date, group_id):
        """
        Enter minute into the database.
        Return succes (boolean, message (string). Message is the new minute.id
        if succes is true, otherwise it contains an error message.
        """
        if not ModuleAPI.can_write('pimpy'):
            abort(403)

        try:
            date = datetime.datetime.strptime(date, DATE_FORMAT)
        except:
            if date != "":
                return False, "De datum kon niet worden verwerkt."
            date = None

        minute = Minute(content, group_id, date)
        db.session.add(minute)
        db.session.commit()

        return True, minute.id

    @staticmethod
    def commit_task_to_db(name, content, group_id, filled_in_users,
                          line, minute_id, status):
        """
        Enter task into the database.
        Return succes (boolean), message (string). Message is the new task.id
        if succes is true, otherwise it contains an error message.
        """
        if not ModuleAPI.can_write('pimpy'):
            abort(403)

        if group_id == 'all':
            return False, "Groep kan niet 'All' zijn"
        group = Group.query.filter(Group.id == group_id).first()
        if group is None:
            return False, "Er is niet een groep die voldoet opgegeven."

        users, message = PimpyAPI.get_list_of_users_from_string(
            group_id, filled_in_users)
        if not users:
            return False, message

        if minute_id <= 0:
            minute_id = 1

        group_id = int(group_id)

        task = Task.query.filter(
            Task.title == name,
            Task.content == content,
            Task.group_id == group_id).first()

        if task:
            return False, "Deze taak bestaat al in de database"
        else:
            task = Task(name, content, group_id,
                        users, minute_id, line, status)

        db.session.add(task)
        db.session.commit()

        # Add task to Copernica
        data = {
            "Groep": task.group.name,
            "viaductID": task.base32_id(),
            "Actiepunt": task.title,
            "Status": task.get_status_string()
        }
        for user in users:
            copernica.add_subprofile(copernica.SUBPROFILE_TASK,
                                     user.copernica_id, data)
        return True, task.id

    @staticmethod
    def edit_task(task_id, name, content, group_id,
                  filled_in_users, line):
        """
        Returns succes (boolean), message (string). Message is irrelevant if
        succes is true, otherwise it contains what exactly went wrong.

        In case of succes the task is edited in the database.
        """
        if not ModuleAPI.can_write('pimpy'):
            abort(403)

        if task_id == -1:
            return False, "Geen taak ID opgegeven."

        task = Task.query.filter(Task.id == task_id).first()

        users, message = PimpyAPI.get_list_of_users_from_string(
            group_id, filled_in_users)
        if not users:
            return False, message

        if name:
            task.title = name
        if content:
            task.content = content
        if group_id:
            task.group_id = group_id
        if line:
            task.line = line
        if users:
            task.users = users
    #   if status:
    #       task.status = status

        db.session.commit()

        for user in users:
            copernica.update_subprofile(copernica.SUBPROFILE_TASK,
                                        user.copernica_id,
                                        task.base32_id(),
                                        {"Status": task.get_status_string()})

        return True, "Taak bewerkt."

    @staticmethod
    def parse_minute(content, group_id, minute_id):
        """
        Parse the specified minutes for tasks and return them in a list.
        Same for DONE tasks and REMOVED tasks

        syntax within the content:
        ACTIE <name_1>, <name_2>, name_n>: <title of task>
        or
        TODO <name_1>, <name_2>, name_n>: <title of task>
        this creates a single task for one or multiple users

        ACTIES <name_1>, <name_2>, name_n>: <title of task>
        or
        TODOS <name_1>, <name_2>, name_n>: <title of task>
        this creates one or multiple tasks for one or multiple users

        DONE <task1>, <task2, <taskn>
        this sets the given tasks on 'done'

        usage:
        tasks, dones, removes = parse_minute(content, group_id, minute_id)
        where content is a string with the entire minute
        """

        tasks_found = []
        dones_found = []
        removes_found = []

        regex = re.compile("\s*(?:ACTIE|TODO) ([^\n\r]*)")
        for i, line in enumerate(content.splitlines()):
            matches = regex.findall(line)

            for action in matches:
                try:
                    listed_users, title = action.split(":", 1)
                except:
                    print("could not split the line on ':'.\nSkipping hit.")
                    flash("Kon niet verwerken: " + action, 'danger')
                    continue

                users, message = PimpyAPI.get_list_of_users_from_string(
                    group_id, listed_users)
                if not users:
                    print(message)
                    continue

                try:
                    task = Task(title, "", group_id, users,
                                minute_id, i, 0)
                except:
                    print("wasnt given the right input to create a task")
                    continue
                tasks_found.append(task)

        regex = re.compile("\s*(?:ACTIES|TODOS) ([^\n\r]*)")
        for i, line in enumerate(content.splitlines()):
            matches = regex.findall(line)

            for action in matches:
                try:
                    listed_users, title = action.split(":", 1)
                except:
                    print("could not split the line on ':'.\nSkipping hit.")
                    flash("Kon niet verwerken: " + action, 'danger')
                    continue

                users, message = PimpyAPI.get_list_of_users_from_string(
                    group_id, listed_users)
                if not users:
                    print(message)
                    continue

                for user in users:
                    try:
                        task = Task(title, "", group_id, [user],
                                    minute_id, i, 0)
                    except:
                        print("wasnt given the right input to create a task")
                        continue
                    tasks_found.append(task)

        regex = re.compile("\s*(?:DONE) ([^\n\r]*)")
        matches = regex.findall(content)
        for match in matches:
            done_ids = filter(None, match.split(","))

            for b32_id in done_ids:
                done_id = b32.decode(b32_id.strip())
                try:
                    done_task = Task.query.filter(Task.id == done_id).first()
                except:
                    print("could not find the given task")
                    flash("Kan DONE niet vinden, id: " + done_id, "danger")
                    continue
                if done_task is not None:
                    dones_found.append(done_task)

        regex = re.compile("\s*(?:REMOVE) ([^\n\r]*)")
        matches = regex.findall(content)
        for match in matches:
            remove_ids = filter(None, match.split(","))

            for b32_id in remove_ids:
                remove_id = b32.decode(b32_id.strip())
                try:
                    remove_task = Task.query\
                        .filter(Task.id == remove_id).first()
                except:
                    print("could not find the given task")
                    flash("Kan REMOVE niet vinden, id: " + remove_id, "danger")
                    continue
                if remove_task is not None:
                    removes_found.append(remove_task)

        return tasks_found, dones_found, removes_found

    @staticmethod
    def get_list_of_users_from_string(group_id, comma_sep):
        """
        Parses a string which is a list of comma separated user names
        to a list of users, searching only within the group given

        Returns users, message. Users is false if there is something wrong,
        in which case the message is stated in message, otherwise message
        equals "" and users is the list of matched users

        usage:
        get_list_of_users_from_string(group_id, comma_sep)
        where group_id is the group's id
        and comma_sep is a string with comma seperated users.
        """
        if not ModuleAPI.can_read('pimpy'):
            abort(403)

        group = Group.query.filter(Group.id == group_id).first()
        if group is None:
            return False, "Kan groep niet vinden."

        if comma_sep is None:
            return False,
        "Geen komma gescheiden lijst met gebruikers gevonden."

        if not comma_sep:
            return group.users.all(), ''

        comma_sep = map(lambda x: x.lower().strip(), comma_sep.split(','))

        found_users = []

        users = group.users.all()

        user_names = map(lambda x: "%s %s" % (x.first_name.lower().strip(),
                                              x.last_name.lower().strip()),
                         users)
        user_names = [unidecode(x) for x in user_names]

        for comma_sep_user in comma_sep:
            match = extractOne(comma_sep_user, user_names)
            found = False

            if not match:
                return False, \
                    'Kon geen gebruiker vinden voor: %s' % (comma_sep_user)

            for i in range(len(users)):
                # could use a filter here, but meh
                if user_names[i] == match[0]:
                    found_users.append(users[i])
                    found = True
                    break

            if not found:
                return False, \
                    'Kon geen gebruiker vinden voor %s' % (comma_sep_user)

        return found_users, ""

    @staticmethod
    def get_navigation_menu(group_id, personal, type):
        if not ModuleAPI.can_read('pimpy'):
            abort(403)
        if not current_user:
            flash('Huidige gebruiker niet gevonden!', 'danger')
            return redirect(url_for('pimpy.view_minutes'))

        groups = current_user.groups\
            .filter(Group.name != 'all').order_by(Group.name.asc()).all()

        if not type:
            type = 'minutes'
        endpoint = 'pimpy.view_' + type
        endpoints = {'view_chosentype': endpoint,
                     'view_chosentype_personal': endpoint + '_personal',
                     'view_chosentype_chosenpersonal': endpoint +
                     ('_personal' if personal and type != 'minutes' else ''),
                     'view_tasks': 'pimpy.view_tasks',
                     'view_tasks_personal': 'pimpy.view_tasks_personal',
                     'view_tasks_chosenpersonal': 'pimpy.view_tasks',
                     'view_minutes': 'pimpy.view_minutes'}
        if personal:
            endpoints['view_tasks_chosenpersonal'] += '_personal'

        if not group_id:
            group_id = 'all'
        if group_id != 'all':
            group_id = int(group_id)

        return Markup(render_template('pimpy/api/side_menu.htm', groups=groups,
                                      group_id=group_id, personal=personal,
                                      type=type, endpoints=endpoints,
                                      title='PimPy'))

    @staticmethod
    def get_all_tasks(group_id):
        """
        Shows all tasks ever made.
        Can specify specific group.
        No internal permission system made yet.
        Do not make routes to this module yet.
        """
        if not ModuleAPI.can_read('pimpy'):
            abort(403)
        if not current_user:
            flash('Huidige gebruiker niet gevonden.', 'danger')
            return redirect(url_for('pimpy.view_tasks'))

        status_meanings = Task.get_status_meanings()

        list_items = {}
        if group_id == 'all':
            for group in UserAPI.get_groups_for_current_user():
                list_users = {}
                list_users['Iedereen'] = group.tasks
                list_items[group.name] = list_users
        else:
            list_users = {}
            tasks = Task.query.filter(Task.group_id == group_id).all()
            group = Group.query.filter(Group.id == group_id).first()
            if not group:
                abort(404)
            if group not in UserAPI.get_groups_for_current_user():
                abort(403)
            list_users['Iedereen'] = tasks
            list_items[group.name] = list_users

        return Markup(render_template('pimpy/api/tasks.htm',
                                      list_items=list_items, type='tasks',
                                      group_id=group_id, personal=False,
                                      status_meanings=status_meanings,
                                      title='PimPy'))

    @staticmethod
    def get_tasks(group_id, personal):
        if not ModuleAPI.can_read('pimpy'):
            abort(403)
        if not current_user:
            flash('Huidige gebruiker niet gevonden', 'danger')
            return redirect(url_for('pimpy.view_tasks'))

        status_meanings = Task.get_status_meanings()

        tasks_rel = TaskUserRel.query.join(Task).join(User)

        groups = UserAPI.get_groups_for_current_user()
        groups = map(lambda x: x.id, groups)

        if group_id == 'all':
            tasks_rel = tasks_rel.filter(Task.group_id.in_(groups))

        else:
            group_id = int(group_id)
            if group_id not in groups:
                abort(403)

            tasks_rel = tasks_rel.filter(Task.group_id == group_id)

        if personal:
            tasks_rel = tasks_rel.filter(User.id == current_user.id)

        tasks_rel = tasks_rel.filter(~Task.status.in_((4, 5))).join(Group)
        tasks_rel = tasks_rel.order_by(Group.name.asc(), User.first_name.asc(),
                                       User.last_name.asc(), Task.id.asc())

        return Markup(render_template('pimpy/api/tasks.htm',
                                      personal=personal,
                                      group_id=group_id,
                                      tasks_rel=tasks_rel,
                                      type='tasks',
                                      status_meanings=status_meanings,
                                      title='PimPy'))

    @staticmethod
    def get_minutes(group_id):
        """
        Load all minutes in the given group
        """
        if not ModuleAPI.can_read('pimpy'):
            abort(403)
        if not current_user:
            flash('Huidige gebruiker niet gevonden', 'danger')
            return redirect(url_for('pimpy.view_minutes'))

        list_items = {}

        if group_id != 'all':
            query = Minute.query.filter(Minute.group_id == group_id).\
                order_by(Minute.minute_date.desc())
            list_items[Group.query.filter(Group.id == group_id).first().name]\
                = query.all()
        # this should be done with a sql in statement, or something, but meh
        else:
            for group in current_user.groups:
                query = Minute.query.filter(Minute.group_id == group.id)
                query = query.order_by(Minute.minute_date.desc())
                list_items[group.name] = query.all()

        return Markup(render_template('pimpy/api/minutes.htm',
                                      list_items=list_items, type='minutes',
                                      group_id=group_id, line_number=-1,
                                      title='PimPy'))

    @staticmethod
    def get_minute(group_id, minute_id, line_number):
        """
        Load (and thus view) specifically one minute
        """
        if not ModuleAPI.can_read('pimpy'):
            abort(403)
        if not current_user:
            flash('Huidige gebruiker niet gevonden', 'danger')
            return redirect(url_for('pimpy.view_minutes'))

        list_items = {}
        query = Minute.query.filter(Minute.id == minute_id)
        group = Group.query.filter(Group.id == group_id).first()
        list_items[group.name] = query.all()
        tag = "%dln%d" % (list_items[group.name][0].id, int(line_number))

        return render_template('pimpy/api/minutes.htm', list_items=list_items,
                               type='minutes', group_id=group_id,
                               line_number=line_number, tag=tag,
                               title='PimPy')

    @staticmethod
    def update_content(task_id, content):
        """
        Update the content of the task with the given id
        """
        task = Task.query.filter(Task.id == task_id).first()
        task.content = content
        db.session.commit()
        return True, "De taak is succesvol aangepast."

    @staticmethod
    def update_title(task_id, title):
        """
        Update the title of the task with the given id
        """
        task = Task.query.filter(Task.id == task_id).first()
        task.title = title
        db.session.commit()
        for user in task.users:
            copernica.update_subprofile(copernica.SUBPROFILE_TASK,
                                        user.copernica_id,
                                        task.base32_id(),
                                        {"Actiepunt": title})
        return True, "De taak is succesvol aangepast."

    @staticmethod
    def update_users(task_id, comma_sep_users):
        """
        Update the users of the task with the given id
        """
        task = Task.query.filter(Task.id == task_id).first()
        old_users = task.users
        users, message = PimpyAPI.get_list_of_users_from_string(
            task.group_id, comma_sep_users)
        if not users:
            return False, message

        # Sync to Copernica
        for user in old_users:
            if user not in users:
                copernica.update_subprofile(copernica.SUBPROFILE_TASK,
                                            user.copernica_id,
                                            task.base32_id(),
                                            {"Status": "Removed"})
        for user in users:
            if user not in old_users:
                data = {
                    "Groep": task.group.name,
                    "viaductID": task.base32_id(),
                    "Actiepunt": task.title,
                    "Status": task.get_status_string()
                }
                copernica.add_subprofile(copernica.SUBPROFILE_TASK,
                                         user.copernica_id, data)

        task.users = users
        db.session.commit()
        return True, "De taak is succesvol aangepast."
