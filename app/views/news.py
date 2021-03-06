from datetime import date

from flask import Blueprint, abort, render_template, request, flash, redirect,\
    url_for
from flask_login import current_user
from flask_babel import _  # gettext

from sqlalchemy import desc

from app import db
from app.forms import NewsForm
from app.models import News
from app.utils import ModuleAPI
from app.utils.forms import flash_form_errors

blueprint = Blueprint('news', __name__, url_prefix='/news')


@blueprint.route('/', methods=['GET'])
@blueprint.route('/<int:page_nr>/', methods=['GET'])
def list(page_nr=1):
    if not ModuleAPI.can_read('news'):
        return abort(403)

    items = News.query.filter(
        db.and_(
            db.or_(
                News.archive_date >= date.today(), News.archive_date == None),
            News.publish_date <= date.today()))\
        .order_by(desc(News.publish_date))  # noqa

    return render_template('news/list.htm',
                           items=items.paginate(page_nr, 10, False),
                           archive=False)


@blueprint.route('/all/', methods=['GET'])
@blueprint.route('/all/<int:page_nr>/', methods=['GET'])
def all(page_nr=1):
    if not ModuleAPI.can_read('news'):
        return abort(403)

    return render_template('news/list.htm',
                           items=News.query.paginate(page_nr, 10, False),
                           archive=False)


@blueprint.route('/archive/', methods=['GET'])
@blueprint.route('/archive/<int:page_nr>/', methods=['GET'])
def archive(page_nr=1):
    if not ModuleAPI.can_read('news'):
        return abort(403)

    items = News.query.filter(db.and_(News.archive_date < date.today(),
                                     News.archive_date != None))  # noqa

    return render_template('news/list.htm',
                           items=items.paginate(page_nr, 10, False),
                           archive=True)


@blueprint.route('/create/', methods=['GET', 'POST'])
@blueprint.route('/edit/<int:news_id>/', methods=['GET', 'POST'])
def edit(news_id=None):
    if not ModuleAPI.can_write('news'):
        return abort(403)

    if news_id:
        news_item = News.query.get_or_404(news_id)
    else:
        news_item = News()

    form = NewsForm(request.form, news_item)

    if request.method == 'POST':
        if form.validate_on_submit():

            # fill the news_item with the form entries.
            form.populate_obj(news_item)

            # Only set writer if post is brand new
            if not news_item.id:
                news_item.user_id = current_user.id

            db.session.add(news_item)
            db.session.commit()

            news_id = news_item.id
            flash(_('News item saved'), 'success')

            return redirect(url_for('news.view', news_id=news_id))

        else:
            flash_form_errors(form)

    return render_template('news/edit.htm', form=form, news_id=news_id)


@blueprint.route('/view/', methods=['GET'])
@blueprint.route('/view/<int:news_id>/', methods=['GET'])
def view(news_id=None):
    if not ModuleAPI.can_read('news'):
        return abort(403)

    if not news_id:
        flash(_('This news item does not exist'), 'danger')
        return redirect(url_for('news.list'))

    news = News.query.get_or_404(news_id)

    return render_template('news/view_single.htm', news=news)


@blueprint.route('/delete/', methods=['GET'])
@blueprint.route('/delete/<int:news_id>/', methods=['GET'])
def delete(news_id=None):
    if not ModuleAPI.can_write('news'):
        return abort(403)

    if not news_id:
        flash(_('This news item does not exist'), 'danger')
        return redirect(url_for('news.list'))

    news = News.query.get_or_404(news_id)
    db.session.delete(news)
    db.session.commit()

    flash(_('News item succesfully deleted'), 'success')

    return redirect(url_for('news.list'))
