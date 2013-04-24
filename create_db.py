import bcrypt

import datetime
from viaduct import db
from viaduct.blueprints.user.models import User, UserPermission
from viaduct.blueprints.group.models import Group, GroupPermission
from viaduct.blueprints.page.models import Page, PagePermission, PageRevision
from viaduct.blueprints.pimpy.models import Minute, Task
from viaduct.models.navigation import NavigationEntry

import os

# Remove the old db.
if os.path.exists('application.db'):
	os.remove('application.db')

# Create the database.
db.create_all()

page = Page('')

db.session.add(page)
db.session.commit()

# Add the anonymous user.
user = User('anonymous', '', 'Anonymous', '')

db.session.add(user)
db.session.commit()

anon = Group('anonymous')

db.session.add(anon)
db.session.commit()

# Add the administrator.
user = User('administrator@svia.nl', bcrypt.hashpw('administrator',
		bcrypt.gensalt()), 'Administrator', '')

db.session.add(user)
db.session.commit()

# Add the administrators group.
group = Group('administrators')

db.session.add(group)
db.session.commit()

# Add the administrator to the administrators group.
group.add_user(user)

db.session.add(group)
db.session.commit()

# Grant the permissions.
permissions = UserPermission(group, view=True, create=True, edit=True,
	delete=True)

db.session.add(permissions)
db.session.commit()

permissions = GroupPermission(group, view=True, create=True, edit=True,
	delete=True)

db.session.add(permissions)
db.session.commit()

permissions = PagePermission(group, page, view=True, create=True, edit=True,
	delete=True)

db.session.add(permissions)
db.session.commit()

#	def __init__(self, title, content, deadline, group_id, users,
#				minute, line):

# Add standard pimpy tasks
minute = Minute("minute content, jaja", 2)
db.session.add(minute)
db.session.commit()

task = Task('test task', 'test content', datetime.date(2020, 10, 10), 2,
		[user], 1, minute.id)
db.session.add(task)
db.session.commit()

# Do some pages.
page = Page('page1')
db.session.add(page)
db.session.commit()

permissions = PagePermission(group, page, view=True, create=True, edit=True,
		delete=True)
db.session.add(permissions)
db.session.commit()

permissions = PagePermission(anon, page, view=True, create=True, edit=True,
		delete=True)
db.session.add(permissions)
db.session.commit()

revision = PageRevision(page, user, 'Page 1', 'herr derr 1', 0)
db.session.add(revision)
db.session.commit()
