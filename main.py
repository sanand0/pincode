import os
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import users

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '0.96')
from django.utils import simplejson as json


class PostalCode(db.Model):
    # See format at http://download.geonames.org/export/zip/
    # key = country_code/postal_code
    place_name  = db.StringProperty()
    admin_name1 = db.StringProperty()
    latitude    = db.StringProperty()
    longitude   = db.StringProperty()
    accuracy    = db.IntegerProperty()
    history     = db.TextProperty()

    created     = db.DateTimeProperty(auto_now_add=True)
    author      = db.UserProperty()


class HomePage(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render('template/index.html', locals()))

class CodePage(webapp.RequestHandler):
    def get(self, code):
        data = PostalCode.get_by_key_name(code)
        if not data: data = PostalCode(
            key_name    = code,
            place_name  = '',
            admin_name1 = '',
            latitude    = '22',
            longitude   = '78',
            accuracy    = -1
        )
        self.response.out.write(template.render('template/postcode.html', locals()))

    def post(self, code):
        old_data = PostalCode.get_by_key_name(code)
        data = PostalCode(
            key_name    = code,
            place_name  = self.request.get('place_name'),
            admin_name1 = self.request.get('admin_name1'),
            latitude    = self.request.get('latitude'),
            longitude   = self.request.get('longitude'),
            accuracy    = 3,
        )
        data.put()
        self.redirect('/')

class LoginPage(webapp.RequestHandler):
    def get(self):
        self.redirect(users.create_login_url(self.request.get('continue', '/')))

class LogoutPage(webapp.RequestHandler):
    def get(self):
        self.redirect(users.create_logout_url(self.request.get('continue', '/')))


application = webapp.WSGIApplication([
    ('/',                   HomePage),
    ('/([A-Z][A-Z]/\d+)',   CodePage),
    ('/login',              LoginPage),
    ('/logout',             LogoutPage),
], debug=(os.name=='nt'))

if __name__ == '__main__':
    webapp.util.run_wsgi_app(application)
