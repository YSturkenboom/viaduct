from datetime import date, datetime
from flask import Blueprint, render_template, abort
from sqlalchemy import desc

from viaduct import db
from viaduct.models import News
from viaduct.models.page import Page, PageRevision
from viaduct.models.activity import Activity

blueprint = Blueprint('home', __name__)


@blueprint.route('/', methods=['GET'])
def home():
    data = ['activities',
            'contact']

    pages = []
    revisions = []

    for path in data:
        if path == 'activities':
            revision = PageRevision(None, None, None, None, None)

            activities = Activity.query \
                .filter(Activity.end_time > datetime.now()) \
                .order_by(Activity.start_time.asc())
            revision.activity = \
                render_template('activity/view_simple.htm',
                                activities=activities.paginate(1, 4, False))

            revisions.append(revision)

            continue

        page = Page.get_by_path(Page.strip_path(path))
        pages.append(page)

        if not page:
            revision = PageRevision(None, None, None, None, None)
            revision.title = 'Not found!'
            revision.content = 'Page not found'

            revisions.append(revision)

            continue

        revision = page.get_latest_revision()
        revision.test = path
        if not revision:
            return abort(500)

        revisions.append(revision)

    news = News.query.filter(
        db.and_(
            db.or_(
                News.archive_date >= date.today(), News.archive_date == None),
            News.publish_date >= date.today())).order_by(desc(News.created))\
        .limit(8).all()  # noqa

    print(news)

    return render_template('home/home.htm', revisions=revisions,
                           title='Homepage', news=news)
