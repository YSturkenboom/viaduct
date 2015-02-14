from flask_wtf import Form
from wtforms import BooleanField, StringField, TextAreaField, FieldList, \
    SelectField, SubmitField, RadioField, FormField

from wtforms.validators import InputRequired, Regexp, Optional

from wtforms import Form as UnsafeForm


class EditGroupPagePermissionEntry(UnsafeForm):
    select = SelectField(None, coerce=int, choices=[(0, 'Geen'), (1, 'Lees'),
                                                    (2, 'Lees/Schrijf')])


class SuperPageForm(Form):
    """TODO"""
    needs_payed = BooleanField('Betaling vereist')

    title = StringField('Titel', [InputRequired()])
    comment = StringField('Reden van wijziging', [Optional()])

    save_page = SubmitField('Opslaan')


class PageForm(SuperPageForm):
    content = TextAreaField('Inhoud', [InputRequired()])
    filter_html = BooleanField('Sta HTML tags toe')
    custom_form_id = SelectField('Formulier', coerce=int)
    permissions = FieldList(FormField(EditGroupPagePermissionEntry))


class HistoryPageForm(Form):
    previous = RadioField('Previous', coerce=int)
    current = RadioField('Current', coerce=int)
    compare = SubmitField('Compare')


class ChangePathForm(Form):
    path = StringField('Path',
                       [InputRequired(), Regexp(r'^ */?[\w-]+(/[\w-]+)*/? *$',
                                                message='You suck at typing '
                                                        'URL paths')])
    move_only_this = SubmitField('Only this page')
    move_children = SubmitField('This and its children ')
