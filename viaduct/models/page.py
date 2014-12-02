import sys

from viaduct import db
from viaduct.models import BaseEntity, Group

from sqlalchemy import event


class Page(db.Model, BaseEntity):
    __tablename__ = 'page'

    path = db.Column(db.String(200), unique=True)
    needs_payed = db.Column(db.Boolean)

    type = db.Column(db.String(256))

    def __init__(self, path, type='page'):
        self.path = path.rstrip('/')
        self.type = type

        # Store the page's revision class, based upon its type.
        self.revision_cls = self.get_revision_class()

    def __repr__(self):
        return '<Page(%s, "%s")>' % (self.id, self.path)

    def can_read(self, user):
        if PagePermission.get_user_rights(user, self.id) > 0:
            return True
        else:
            return False

    def can_write(self, user):
        if PagePermission.get_user_rights(user, self.id) > 1:
            return True
        else:
            return False

    def get_latest_revision(self):
        """Get the latest revision of this page."""
        revision = self.revision_cls.get_query()\
            .filter(self.revision_cls.page_id == self.id)\
            .order_by(self.revision_cls.id.desc())\
            .first()

        return revision

    def get_revision_class(self):
        """Turn a page's type into a revision class."""
        if not self.type:
            return None

        class_name = '%sRevision' % (self.type.capitalize())
        revision_class = getattr(
            sys.modules['viaduct.models.%s' % (self.type)], class_name)

        return revision_class

    @staticmethod
    def strip_path(path):
        return path.rstrip('/')

    @staticmethod
    def get_by_path(path):
        return Page.query.filter(Page.path == path).first()


@event.listens_for(Page, 'load')
def set_revision_class(page, context):
    """Calculate revision class."""
    page.revision_cls = page.get_revision_class()


class SuperRevision(db.Model, BaseEntity):
    """Any revision class should inherit from this one. It contains all general
    revision fields, as well as some helper functions.

    NOTE: I am not able to get a relationship to work with page here, so you
    will have to implement that yourself."""
    __abstract__ = True

    title = db.Column(db.String(128))
    comment = db.Column(db.String(1024))

    def __init__(self, title, comment):
        """Any necessary initialization. Don't forget to call
        `super().__init__(title, comment)`!"""
        self.title = title
        self.comment = comment

    def get_comparable(self):
        """As long as no alternative comparable is given, compare titles."""
        return self.title

    @classmethod
    def get_query(cls):
        return cls.query.order_by(cls.id.desc())


class IdRevision(SuperRevision):
    """Class that page types can inherit from to let their pages to work with
    id's instead of paths."""
    __abstract__ = True

    instance_id = db.Column(db.Integer)

    def __init__(self, title, comment, instance_id):
        """Initialization. Don't forget to call
        `super().__init__(title, comment, instance_id)`."""
        super(IdRevision, self).__init__(title, comment)

        self.instance_id = instance_id

    def get_path(self):
        return '/%s/%d/' % (self.page.type, self.instance_id)

    @classmethod
    def get_new_id(cls):
        first = cls.get_query().first()

        return first.instance_id + 1 if first else 1

    @classmethod
    def get_latest(cls, instance_id):
        return cls.get_query().filter(cls.instance_id == instance_id).first()


class PageRevision(SuperRevision):
    __tablename__ = 'page_revision'

    filter_html = db.Column(db.Boolean)
    content = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('page_edits',
                                                      lazy='dynamic'))

    custom_form_id = db.Column(db.Integer, db.ForeignKey('custom_form.id'))
    custom_form = db.relationship('CustomForm',
                                  backref=db.backref('page_revision',
                                                     lazy='dynamic'))

    page_id = db.Column(db.Integer, db.ForeignKey('page.id'))
    page = db.relationship('Page', backref=db.backref('page_revisions',
                                                      lazy='dynamic',
                                                      cascade='all,delete'))

    def __init__(self, page, title, comment, user, content,
                 filter_html=True, custom_form_id=None):
        super(PageRevision, self).__init__(title, comment)

        self.page = page

        self.filter_html = filter_html
        self.custom_form_id = custom_form_id
        self.content = content
        self.user_id = user.id if user else None

    def get_comparable(self):
        return self.content


class PagePermission(db.Model):
    __tablename__ = 'page_permission'

    id = db.Column(db.Integer, primary_key=True)
    permission = db.Column(db.Integer)
    page_id = db.Column(db.Integer, db.ForeignKey('page.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    page = db.relationship('Page', backref=db.backref('permissions',
                           lazy='dynamic'))

    def __init__(self, group_id, page_id, permission=0):
        self.permission = permission
        self.group_id = group_id
        self.page_id = page_id

    @staticmethod
    def get_user_rights(user, page_id):
        rights = 0

        if not user or not user.is_active():
            groups = [Group.query.filter(Group.name == 'all').first()]
        else:
            groups = user.groups.all()

        page = Page.query.filter(Page.id == page_id).first()

        if page:
            for group in groups:
                if group.name == 'administrators':
                    return 2

                permissions = PagePermission.query\
                    .filter(PagePermission.page_id == page.id,
                            PagePermission.group_id == group.id).first()

                if permissions:
                    if (permissions.permission >= 2):
                        return permissions.permission

                    if (permissions.permission > rights):
                        rights = permissions.permission

        return rights
