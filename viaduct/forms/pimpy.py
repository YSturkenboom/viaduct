from flask.ext.wtf import Form, TextField, TextAreaField, FileField,\
    DateTimeField, Required, validators, IntegerField, SelectField,\
    BooleanField

import datetime

from viaduct.models.pimpy import Minute, Task
from viaduct import application


DATE_FORMAT = application.config['DATE_FORMAT']


class AddTaskForm(Form):
    name = TextField('Name', validators=[Required()])
    content = TextAreaField('Content', validators=[validators.optional()])
    deadline = DateTimeField('Deadline', format=DATE_FORMAT,
                             default=datetime.date.today())
    # timestamp
    line = IntegerField(
        'Line', default=-1,
        description='Fill in -1 if this is unknown or impossible.')

    minute_id = IntegerField(
        'Minute ID', default=-1,
        description='Fill in -1 if this is unknown or impossible.')

    group = SelectField('Group')
    users = TextAreaField(
        'Users',
        description='Type comma separated names for whom this task is, in a '
                    'similar manner as you are familiar with whilst taking '
                    'minutes.',
        validators=[Required()])

    status = SelectField(
        'Status',
        choices=map(lambda x, y: (x, y),
                    range(0, len(Task.status_meanings)),
                    Task.status_meanings), validators=[])

    def load_groups(self, groups):
        self.group.choices = map(lambda x: (x.id, x.name), groups)

    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        kwargs.setdefault('group', kwargs.get('default', -1))

        Form.__init__(self, formdata, obj, prefix, **kwargs)


class EditTaskForm(Form):
    name = TextField('Name', validators=[Required()])
    content = TextAreaField('Content', validators=[validators.optional()])
    deadline = DateTimeField('Deadline',
                             format=DATE_FORMAT, default=datetime.date.today())
    # timestamp
    line = IntegerField('Line', default=-1,
                        description='Fill in -1 if this is '
                                    'unknown or impossible.')
    minute_id = IntegerField('Minute ID', default=-1,
                             description='Fill in -1 if this is unknown or '
                                         'impossible.')
    group = SelectField('Group')
    users = TextAreaField('Users',
                          description='Type comma separated names for whom '
                                      'this task is, in a similar manner as '
                                      'you are familiar with whilst taking '
                                      'minutes.', validators=[Required()])

    def load_groups(self, groups, default=-1):
        self.group.choices = map(lambda x: (x.id, x.name), groups)
        self.group.default = default

    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        kwargs.setdefault('group', kwargs.get('default', -1))

        Form.__init__(self, formdata, obj, prefix, **kwargs)


class AddMinuteForm(Form):
    # TODO: should try and resize stuff, especially the content field
    content = TextAreaField('Content', [validators.required()])
    group = SelectField('Group', [validators.required()])
    # FIXME: datetime is now printed badly in the actual form!!! :( :(
    date = DateTimeField('Deadline', format=DATE_FORMAT,
                         default=datetime.date.today())
    parse_tasks = BooleanField('Parse', default=True)

    def load_groups(self, groups, default=-1):
        self.group.choices = map(lambda x: (x.id, x.name), groups)
        self.group.default = default

    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        kwargs.setdefault('group', kwargs.get('default', -1))

        Form.__init__(self, formdata, obj, prefix, **kwargs)
