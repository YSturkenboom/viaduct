from flask import Blueprint
from flask import render_template

from viaduct.models.examination import Examination
from viaduct.models.course import Course
from viaduct.models.education import Education

from viaduct.api.search import SearchAPI


# THIS IS A TEST MODULE, currently testing the searchAPI

blueprint = Blueprint('module_permission', __name__,
                      url_prefix='/module_permission')


@blueprint.route('/', methods=['GET', 'POST'])
def main_view():
    stack = [(Examination, [Examination.title]), (Course, [Course.name]),
             (Education, [Education.name])]
    needle = "inf ku"
    result = SearchAPI.search(stack, needle)
    print 'result from module_permission view: ', result
    return render_template('module_permission/view.htm', result=result)
