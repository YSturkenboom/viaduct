from flask.ext.login import current_user
from app.models.page import Page, PageRevision, PagePermission

from app import db

from flask import render_template


class PageAPI:
    @staticmethod
    def remove_page(path):
        page = Page.get_by_path(path)
        if not page:
            return False

        db.session.delete(page)
        db.session.commit()

        return True

    @staticmethod
    def get_footer():
        footer = Page.query.filter(Page.path == 'footer').first()

        if not footer:
            footer = Page('footer')

        revision = footer.get_latest_revision()

        if revision:
            exists = True
        else:
            revision = PageRevision(footer, 'Footer', '', current_user,
                                    '<strong>No footer found</strong>')
            exists = False

        return render_template('page/get_footer.htm', footer_revision=revision,
                               footer=footer, exists=exists)

    @staticmethod
    def can_read(page):
        if page.needs_payed and (not current_user or
                                 not current_user.has_payed):
            return False

        return PagePermission.get_user_rights(current_user, page.id) > 0

    @staticmethod
    def can_write(page):
        return PagePermission.get_user_rights(current_user, page.id) > 1