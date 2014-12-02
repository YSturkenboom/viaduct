from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SelectField, \
    IntegerField, FileField
from wtforms.validators import InputRequired, Email, EqualTo, ValidationError
from config import LANGUAGES


class SignUpForm(Form):
    email = StringField('E-mailadres',
                        validators=[InputRequired(message='Geen e-mailadres '
                                                  'opgegeven'),
                                    Email(message='Ongelding e-mailadres '
                                          'opgegeven')])
    password = PasswordField('Wachtwoord',
                             validators=[InputRequired(message='Geen '
                                                       'wachtwoord opgegeven')]
                             )
    repeat_password = PasswordField('Herhaal wachtwoord',
                                    validators=[InputRequired(message='Wacht'
                                                              'woorden komen '
                                                              'niet overeen'),
                                                EqualTo('password',
                                                        message='Wachtwoorden '
                                                                'komen niet '
                                                                'overeen')])
    first_name = StringField('Voornaam',
                             validators=[InputRequired(message='Geen voornaam '
                                                       'opgegeven')])
    last_name = StringField('Achternaam',
                            validators=[InputRequired(message='Geen achternaam'
                                                      ' opgegeven')])
    student_id = StringField('Studentnummer',
                             validators=[InputRequired(message='Geen '
                                                       'studentnummer '
                                                       'opgegeven')])
    education_id = SelectField('Opleiding', coerce=int)
    avatar = FileField('Avatar')


class EditUserForm(Form):
    """ Edit a user as administrator """
    id = IntegerField('ID')
    email = StringField('E-mailadres',
                        validators=[InputRequired(message='Geen e-mailadres '
                                                  'opgegeven'),
                                    Email(message='Ongeldig e-mailadres '
                                          'opgegeven')])
    password = PasswordField('Wachtwoord')
    repeat_password = PasswordField('Herhaal wachtwoord')
    first_name = StringField('Voornaam',
                             validators=[InputRequired(message='Geen voornaam '
                                                       'opgegeven')])
    last_name = StringField('Achternaam',
                            validators=[InputRequired(message='Geen achternaam'
                                                      ' opgegeven')])
    has_payed = BooleanField('Heeft betaald')
    honorary_member = BooleanField('Erelid')
    locale = SelectField('Taal', choices=LANGUAGES.items())
    favourer = BooleanField('Begunstiger')
    student_id = StringField('Studentnummer',
                             validators=[InputRequired(message='Geen '
                                                       'studentnummer '
                                                       'opgegeven')])
    education_id = SelectField('Opleiding', coerce=int)
    avatar = FileField('Avatar')

    def validate_password(form, field):
        """Providing a password is only required when creating a new user."""
        if form.id.data == 0 and len(field.data) == 0:
            raise ValidationError('Geen wachtwoord opgegeven')

    def validate_repeat_password(form, field):
        """Only validate the repeat password if a password is set."""
        if len(form.password.data) > 0 and field.data != form.password.data:
            raise ValidationError('Wachtwoorden komen niet overeen')


class EditUserInfoForm(Form):
    """ Edit your own user information """
    id = IntegerField('ID')
    email = StringField('E-mailadres',
                        validators=[InputRequired(message='Geen e-mailadres '
                                                  'opgegeven'),
                                    Email(message='Ongeldig e-mailadres '
                                          'opgegeven')])
    password = PasswordField('Wachtwoord')
    repeat_password = PasswordField('Herhaal wachtwoord')
    first_name = StringField('Voornaam',
                             validators=[InputRequired(message='Geen voornaam '
                                                       'opgegeven')])
    last_name = StringField('Achternaam',
                            validators=[InputRequired(message='Geen achternaam'
                                                      ' opgegeven')])
    student_id = StringField('Studentnummer',
                             validators=[InputRequired(message='Geen '
                                                       'studentnummer '
                                                       'opgegeven')])
    locale = SelectField('Taal', choices=LANGUAGES.items())
    education_id = SelectField('Opleiding', coerce=int)
    avatar = FileField('Avatar')

    def validate_password(form, field):
        """Providing a password is only required when creating a new user."""
        if form.id.data == 0 and len(field.data) == 0:
            raise ValidationError('Geen wachtwoord opgegeven')

    def validate_repeat_password(form, field):
        """Only validate the repeat password if a password is set."""
        if len(form.password.data) > 0 and field.data != form.password.data:
            raise ValidationError('Wachtwoorden komen niet overeen')


class SignInForm(Form):
    email = StringField('E-mailadres',
                        validators=[InputRequired(message='Geen e-mailadres '
                                                  'opgegeven'),
                                    Email(message='Ongeldig e-mailadres '
                                          'opgegeven')])
    password = PasswordField('Wachtwoord',
                             validators=[InputRequired(message='Geen '
                                                       'wachtwoord opgegeven')]
                             )
    remember_me = BooleanField('Onthouden', default=False)


class RequestPassword(Form):
    email = StringField('E-mailadres',
                        validators=[InputRequired(message='Geen e-mailadres '
                                                  'opgegeven'),
                                    Email(message='Ongeldig e-mailadres '
                                          'opgegeven')])
    student_id = StringField('Studentnummer',
                             validators=[InputRequired(message='Geen '
                                                       'studentnummer '
                                                       'opgegeven')])


class ResetPassword(Form):
    password = PasswordField('Wachtwoord',
                             validators=[InputRequired(message='Geen '
                                                       'wachtwoord opgegeven')]
                             )
    password_repeat = PasswordField('Herhaal wachtwoord',
                                    validators=[InputRequired(message='Wacht'
                                                              'woorden komen '
                                                              'niet overeen'),
                                                EqualTo('password',
                                                        message='Wachtwoorden '
                                                                'komen niet '
                                                                'overeen')])
