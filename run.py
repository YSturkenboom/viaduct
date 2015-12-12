#!venv/bin/python2.7

from flask_failsafe import failsafe


@failsafe
def create_app():
    from viaduct import application

    return application

if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=5555)
