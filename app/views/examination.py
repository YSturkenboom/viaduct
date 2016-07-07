import os
import json

from flask import Blueprint
from flask import abort, flash, session, redirect, render_template, request, \
    url_for, jsonify
from flask_login import login_required
from flask_babel import _

from sqlalchemy import func

from app import app, db

from app.forms import CourseForm
from app.utils.forms import flash_form_errors
from app.forms import EducationForm
from app.utils import serialize_sqla

from app.models.examination import Examination, test_types, test_type_default
from app.models.course import Course
from app.models.education import Education
from app.models.degree import Degree

from app.utils.module import ModuleAPI

from werkzeug import secure_filename

from fuzzywuzzy import fuzz

blueprint = Blueprint('examination', __name__)

UPLOAD_FOLDER = app.config['EXAMINATION_UPLOAD_FOLDER']
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

REDIR_PAGES = {'view': 'examination.view_examination',
               'add': 'examination.upload_file',
               'educations': 'examination.view_educations',
               'courses': 'examination.view_courses'
               }

DATE_FORMAT = app.config['DATE_FORMAT']


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def file_exists(filename):
    return os.path.exists(os.path.join(UPLOAD_FOLDER, filename))


def create_unique_file(filename):
    temp_filename = filename

    i = 0
    while file_exists(temp_filename):
        split = filename.split('.')
        split[0] = split[0] + "(" + str(i) + ")"
        temp_filename = split[0] + "." + split[len(split) - 1]
        i += 1
    return temp_filename


def get_education_id(education):
    education_object = db.session.query(Education)\
        .filter(Education.name == education).first()

    if not education_object:
        return None
    return education_object[0].id


def get_course_id(course):
    course_object = db.session.query(Course).filter(Course.name == course)\
        .first()

    if not course_object:
        return None
    return course_object.id


def upload_file_real(file, old_path='1'):
    if file and (file.filename is not ''):
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = create_unique_file(filename)

            if old_path != '1':
                os.remove(os.path.join(UPLOAD_FOLDER, old_path))

            file.save(os.path.join(UPLOAD_FOLDER, filename))

            return filename
        else:
            return None
    else:
        return False


@blueprint.route('/examination/add/', methods=['GET', 'POST'])
def upload_file():
    if not ModuleAPI.can_write('examination', True):
        session['prev'] = 'examination.upload_file'
        return abort(403)

    courses = Course.query.order_by(Course.name).all()
    educations = Education.query.order_by(Education.name).all()
    degrees = Degree.query.order_by(Degree.name).all()

    if request.method == 'POST':
        file = request.files.get('file', None)
        answers = request.files.get('answers', None)
        title = request.form.get("title", None)
        course_id = request.form.get("course", None)
        education_id = request.form.get("education", None)
        test_type = request.form.get("test_type", None)

        error = False

        if not title:
            flash(_('No title given.'), 'danger')
            error = True

        filename = upload_file_real(file)
        if file:
            if not filename:
                flash(_('Wrong format examination.'), 'danger')
                error = True

            answer_path = upload_file_real(answers)
            if answer_path is False:
                flash(_('No answers uploaded.'), 'warning')
                answer_path = 1
            elif answer_path is None:
                flash(_('Wrong format answers.'), 'danger')
                error = True
        else:
            flash(_('No examination uploaded.'), 'danger')
            error = True

        if error:
            dummy_exam = Examination(filename, title, int(course_id),
                                     int(education_id), answers=answer_path,
                                     test_type=test_type)

            return render_template('examination/edit.htm', courses=courses,
                                   educations=educations,
                                   examination=dummy_exam,
                                   title=_('Examinations'), degrees=degrees,
                                   test_types=test_types, new_exam=False)

        exam = Examination(filename, title, course_id, education_id,
                           answers=answer_path, test_type=test_type)
        db.session.add(exam)
        db.session.commit()

        flash(_('Examination successfully uploaded.'), 'success')

        return render_template('examination/edit.htm', courses=courses,
                               educations=educations, examination=exam,
                               title=_('Examinations'), degrees=degrees,
                               test_types=test_types, new_exam=False)

    return render_template('examination/edit.htm', courses=courses,
                           educations=educations,
                           title=_('Examinations'), degrees=degrees,
                           test_types=test_types, new_exam=True,
                           test_type_default=test_type_default)


@blueprint.route('/examination/', methods=['GET', 'POST'])
@blueprint.route('/examination/<int:page_nr>/', methods=['GET', 'POST'])
@login_required
def view_examination(page_nr=1):
    if not ModuleAPI.can_read('examination', True):
        flash(_('Valid membership is required for the examination module'),
              'warning')
        session['prev'] = 'examination.view_examination'
        return abort(403)

    # First check if the delete argument is set before loading
    # the search results
    if request.args.get('delete'):
        exam_id = request.args.get('delete')
        examination = Examination.query.filter(Examination.id == exam_id)\
            .first()

        if not examination:
            flash(_('Specified examination does not exist'), 'danger')
        else:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, examination.path))
            except:
                flash(_('File does not exist, examination deleted.'), 'info')

            db.session.delete(examination)
            db.session.commit()
            flash(_('Examination successfully deleted.'))

    # After deletion, do the search.
    if request.args.get('search'):
        search = request.args.get('search')

        exams = Examination.query.all()
        exam_matches_per_course = {}
        course_max_scores = {}

        search_lower = search.lower().strip()

        for exam in exams:
            course = exam.course.name.lower()
            title_ratio = fuzz.partial_ratio(search_lower, exam.title.lower())
            course_ratio = fuzz.partial_ratio(search_lower, course)
            education_ratio = fuzz.partial_ratio(search_lower,
                                                 exam.education.name.lower())
            if title_ratio > 75 or course_ratio > 75 or education_ratio > 75:
                # Calculate the score for the exam
                # TODO: maybe use a weighted mean instead of max
                score = max(title_ratio, course_ratio, education_ratio)

                exam_tuple = (score, exam.id)

                # If the course did not occur before, add it
                # to the dictionaries and set the max score
                # to the score of this exam
                if course not in exam_matches_per_course:
                    exam_matches_per_course[course] = [exam_tuple]
                    course_max_scores[course] = score

                # Otherwise, add the exam to the list of the course
                # and update the maximum course score
                else:
                    exam_matches_per_course[course].append(exam_tuple)
                    course_max_scores[course] = max(score,
                                                    course_max_scores[course])
        if len(course_max_scores) == 0:
            examinations = None
        else:
            # Sort the courses by their max score
            courses_sorted = sorted(course_max_scores,
                                    key=course_max_scores.get, reverse=True)

            # Create the list of exam ids. These are ordered by course with
            # their maximum score, and for each course ordered by exam score
            exam_matches = []
            for course in courses_sorted:
                exam_matches.extend(list(zip(*sorted(
                    exam_matches_per_course[course], reverse=True)))[1])

            # Query the exams. The order_by clause keeps them in the same
            # order as the exam_matches list
            examinations = Examination.query \
                .filter(Examination.id.in_(exam_matches)) \
                .order_by(func.field(Examination.id, *exam_matches)) \
                .paginate(page_nr, 15, True)
    else:
        search = ""
        examinations = Examination.query.join(Course)\
            .order_by(Course.name).paginate(page_nr, 15, True)

    path = '/static/uploads/examinations/'

    return render_template('examination/view.htm', path=path,
                           examinations=examinations, search=search,
                           title=_('Examinations'), test_types=test_types)


@blueprint.route('/examination/edit/<int:exam_id>/', methods=['GET', 'POST'])
@login_required
def edit(exam_id):
    if not ModuleAPI.can_write('examination', True):
        session['prev'] = 'examination.edit_examination'
        return abort(403)

    exam = Examination.query.get(exam_id)

    if not exam:
        flash(_('Examination could not be found.'), 'danger')
        return redirect(url_for('examination.view_examination'))

    session['examination_edit_id'] = exam_id

    if request.method == 'POST':
        file = request.files['file']
        answers = request.files['answers']
        title = request.form.get("title", None)
        course_id = request.form.get("course", None)
        education_id = request.form.get("education", None)
        test_type = request.form.get("test_type", None)

        if not title:
            flash(_('No title given.'), 'danger')
        elif not education_id:
            flash(_('No education given.'), 'danger')
        else:
            exam.title = title
            exam.course_id = course_id
            exam.education_id = education_id
            exam.test_type = test_type

            new_path = upload_file_real(file, exam.path)
            if new_path:
                exam.path = new_path
            elif new_path is None:
                flash(_('Wrong format examination.'), 'danger')

            if not new_path:
                flash(_('Old examination preserved.'), 'info')

            new_answer_path = upload_file_real(answers, exam.answer_path)
            if new_answer_path:
                exam.answer_path = new_answer_path
            elif new_answer_path is None:
                flash(_('Wrong format answers.'), 'danger')

            if not new_answer_path:
                flash(_('Old answers preserved.'), 'info')

            db.session.commit()
            flash(_('Examination succesfully changed.'), 'success')

            return redirect(url_for('examination.edit', exam_id=exam_id))

    path = '/static/uploads/examinations/'
    courses = Course.query.order_by(Course.name).all()
    educations = Education.query.order_by(Education.name).all()

    return render_template(
        'examination/edit.htm', path=path, examination=exam,
        title=_('Examinations'), courses=courses, educations=educations,
        test_types=test_types, new_exam=False)


@blueprint.route('/courses/', methods=['GET'])
def view_courses():
    if not ModuleAPI.can_write('examination', True):
        return abort(403)

    return render_template('course/view.htm')


@blueprint.route('/courses/api/get/', methods=['GET'])
def get_courses():
    if not ModuleAPI.can_write('examination', True):
        return abort(403)

    courses = Course.query.all()
    courses_list = []

    for course in courses:
        courses_list.append(
            [course.id,
             course.name,
             course.description if course.description != "" else "N/A"
             ])

    return json.dumps({"data": courses_list})


@blueprint.route('/course/add/', methods=['GET', 'POST'])
def add_course():
    r = request.args.get('redir')
    if r in REDIR_PAGES:
        session['origin'] = url_for(REDIR_PAGES[r])
    elif r == 'edit' and 'examination_edit_id' in session:
        session['origin'] = '/examination/edit/{}'.format(
            session['examination_edit_id'])

    if not ModuleAPI.can_write('examination', True):
        session['prev'] = 'examination.add_course'
        return abort(403)

    form = CourseForm(request.form)

    if request.method == 'POST':
        if form.validate_on_submit():
            title = form.title.data
            course = Course.query.filter(Course.name == title).first()
            if not course:
                description = form.description.data
                new_course = Course(title, description)
                db.session.add(new_course)
                db.session.commit()
                flash("'%s': " % title + _('Course succesfully added.'),
                      'success')
            else:
                flash("'%s': " % title + _('Already exists in the database'),
                      'danger')

                return render_template('course/edit.htm', new=True, form=form)

            if 'origin' in session:
                redir = session['origin']
            else:
                redir = url_for('examination.upload_file')
            return redirect(redir)
        else:
            flash_form_errors(form)

    return render_template('course/edit.htm', new=True, form=form)


@blueprint.route('/course/edit/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    r = request.args.get('redir')
    if r in REDIR_PAGES:
        session['origin'] = url_for(REDIR_PAGES[r])
    elif r == 'edit' and 'examination_edit_id' in session:
        session['origin'] = '/examination/edit/{}'.format(
            session['examination_edit_id'])

    if not ModuleAPI.can_write('examination', True):
        session['prev'] = 'examination.edit_course'
        return abort(403)

    course = Course.query.get(course_id)

    if not course:
        flash(_('Course could not be found.'), 'danger')
        return redirect(url_for('examination.view_courses'))

    exam_count = Examination.query.filter(Examination.course == course).count()
    if 'delete' in request.args:
        if exam_count > 0:
            flash(_('Course still has examinations in the database.'),
                  'danger')
            form = CourseForm(title=course.name,
                              description=course.description)
            return render_template('course/edit.htm', new=False,
                                   form=form,
                                   course=course, redir=r,
                                   exam_count=exam_count)

        Course.query.filter_by(id=course_id).delete()
        db.session.commit()

        flash(_('Course succesfully deleted.'), 'success')
        if 'origin' in session:
            redir = session['origin']
        else:
            redir = url_for('examination.upload_file')
        return redirect(redir)

    if request.method == 'POST':
        form = CourseForm(request.form)
        if form.validate_on_submit():
            title = form.title.data
            if title != course.name and Course.query.filter(
                    Course.name == title).count() >= 1:
                flash("'%s': " % title + _('Already exists in the database'),
                      'danger')
                return render_template('course/edit.htm', new=False,
                                       form=form, redir=r,
                                       course=course,
                                       exam_count=exam_count)
            else:
                description = form.description.data
                course.name = title
                course.description = description

                db.session.commit()
                flash(_('Course succesfully saved.'),
                      'success')

                if 'origin' in session:
                    redir = session['origin']
                else:
                    redir = url_for('examination.upload_file')
                return redirect(redir)
        else:
            flash_form_errors(form)
    else:
        form = CourseForm(title=course.name, description=course.description)

    return render_template('course/edit.htm', new=False,
                           form=form, redir=r, course=course,
                           exam_count=exam_count)


@blueprint.route('/educations/', methods=['GET'])
def view_educations():
    if not ModuleAPI.can_write('examination', True):
        return abort(403)

    return render_template('education/view.htm')


@blueprint.route('/educations/api/get/', methods=['GET'])
def get_educations():
    if not ModuleAPI.can_write('examination', True):
        return abort(403)

    educations = Education.query.all()
    educations_list = []

    for education in educations:
        created = "N/A"
        modified = "N/A"
        if education.created:
            created = education.created.strftime(DATE_FORMAT)

        if education.modified:
            modified = education.modified.strftime(DATE_FORMAT)

        educations_list.append(
            [education.id,
             education.name,
             created,
             modified
             ])

    return json.dumps({"data": educations_list})


@blueprint.route('/education/add/', methods=['GET', 'POST'])
def add_education():
    r = request.args.get('redir', True)
    if r in REDIR_PAGES:
        session['origin'] = url_for(REDIR_PAGES[r])
    elif r == 'edit' and 'examination_edit_id' in session:
        session['origin'] = '/examination/edit/{}'.format(
            session['examination_edit_id'])

    if not ModuleAPI.can_write('examination', True):
        session['prev'] = 'examination.add_education'
        return abort(403)

    form = EducationForm(request.form)

    if request.method == 'POST':
        if form.validate_on_submit():
            title = form.title.data
            education = Education.query.filter(Education.name == title).first()
            if not education:
                new_education = Education(1, title)

                db.session.add(new_education)
                db.session.commit()
                flash("'%s': " % title + _('Education succesfully added.'),
                      'success')
            else:
                flash("'%s': " % title + _('Already exists in the database'),
                      'danger')

            if 'origin' in session:
                redir = session['origin']
            else:
                redir = url_for('examination.upload_file')
            return redirect(redir)

        else:
            flash_form_errors(form)

    return render_template('education/edit.htm',
                           form=form, new=True)


@blueprint.route('/education/edit/<int:education_id>', methods=['GET', 'POST'])
def edit_education(education_id):
    r = request.args.get('redir')
    if r in REDIR_PAGES:
        session['origin'] = url_for(REDIR_PAGES[r])
    elif r == 'edit' and 'examination_edit_id' in session:
        session['origin'] = '/examination/edit/{}'.format(
            session['examination_edit_id'])

    if not ModuleAPI.can_write('examination', True):
        session['prev'] = 'examination.edit_education'
        return abort(403)

    education = Education.query.get(education_id)

    if not education:
        flash(_('Education could not be found.'), 'danger')
        return redirect(url_for('examination.view_educations'))

    exam_count = Examination.query.filter(
        Examination.education == education).count()

    if 'delete' in request.args:
        if exam_count > 0:
            flash(_('Education still has examinations in the database.'),
                  'danger')
            form = CourseForm(title=education.name)
            return render_template('education/edit.htm', new=False,
                                   form=form, education=education,
                                   redir=r, exam_count=exam_count)

        Education.query.filter_by(id=education_id).delete()
        db.session.commit()

        flash(_('Education succesfully deleted.'), 'success')
        if 'origin' in session:
            redir = session['origin']
        else:
            redir = url_for('examination.upload_file')
        return redirect(redir)

    if request.method == 'POST':
        form = EducationForm(request.form)
        if form.validate_on_submit():
            name = form.title.data
            if name != education.name and Education.query.filter(
                    Education.name == name).count() >= 1:
                flash("'%s': " % name + _('Already exists in the database'),
                      'danger')
                return render_template('education/edit.htm', new=False,
                                       form=form, redir=r,
                                       exam_count=exam_count,
                                       education=education)
            else:
                education.name = name

                db.session.commit()
                flash("'%s': " % name + _('Education succesfully saved.'),
                      'success')

                if 'origin' in session:
                    redir = session['origin']
                else:
                    redir = url_for('examination.view_educations')
                return redirect(redir)

        else:
            flash_form_errors(form)
    else:
        form = CourseForm(title=education.name)

    return render_template('education/edit.htm', new=False,
                           form=form, redir=r, exam_count=exam_count,
                           education=education)


@blueprint.route('/examination/api/course/', methods=['POST'])
def examination_api_course_add():
    if not ModuleAPI.can_write('examination', True):
        return abort(403)

    course_name = request.form.get('course_name', '')

    if course_name == '':
        return jsonify(error='Geen vaknaam opgegeven'), 500
    if Course.query.filter(Course.name == course_name).first():
        return jsonify(error=_('There is already a course with this name')), \
            500

    course = Course(course_name, '')
    db.session.add(course)
    db.session.commit()

    courses = Course.query.order_by(Course.name).all()

    return jsonify(course_id=course.id, courses=serialize_sqla(courses))


@blueprint.route('/examination/api/education/', methods=['POST'])
def examination_api_education_add():
    if not ModuleAPI.can_write('examination', True):
        return abort(403)

    education_name = request.form.get('education_name', '')
    degree_id = request.form.get('degree_id', '')

    if education_name == '':
        return jsonify(error=_('No education name specified')), 500
    if degree_id == '':
        return jsonify(error=_('No education degree specified')), 500

    education = Education(degree_id, education_name)
    db.session.add(education)
    db.session.commit()

    educations = Education.query.order_by(Education.name).all()

    return jsonify(education_id=education.id,
                   educations=serialize_sqla(educations))
