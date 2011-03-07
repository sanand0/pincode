import os, datetime, csv, StringIO
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import users, taskqueue

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

class Event(db.Model):
    user    = db.UserProperty()
    time    = db.DateTimeProperty(auto_now_add=True)
    text    = db.StringProperty()

class Download(db.Model):
    text    = db.TextProperty()


class HomePage(webapp.RequestHandler):
    def get(self):
        events = Event.all().order('-time').fetch(100)
        self.response.out.write(template.render('template/index.html', locals()))

class FeedPage(webapp.RequestHandler):
    def get(self):
        events = Event.all().order('-time').fetch(100)
        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write(template.render('template/atom.xml', locals()))

class CodePage(webapp.RequestHandler):
    def get(self, code):
        data = PostalCode.get_by_key_name(code)
        user = users.get_current_user()
        if not data: data = PostalCode(
            key_name    = code,
            place_name  = '',
            admin_name1 = '',
            latitude    = '22',
            longitude   = '78',
            accuracy    = -1
        )
        history = json.loads(data.history or '[]')
        self.response.out.write(template.render('template/postcode.html', locals()))

    def post(self, code):
        user = users.get_current_user()
        old_data = PostalCode.get_by_key_name(code)
        if old_data:
            history = json.loads(old_data.history or '[]')
            history.append({
                'u': old_data.author and old_data.author.nickname() or 'None',
                'p': old_data.place_name,
                'a': old_data.admin_name1,
                'x': old_data.latitude,
                'y': old_data.longitude,
                'z': old_data.accuracy
            })
        else:
            history = []
        data = PostalCode(
            key_name    = code,
            place_name  = self.request.get('place_name'),
            admin_name1 = self.request.get('admin_name1'),
            latitude    = self.request.get('latitude'),
            longitude   = self.request.get('longitude'),
            accuracy    = 3,
            author      = user,
            created     = datetime.datetime.now(),
            history     = json.dumps(history)
        )
        data.put()
        Event(user=user,text=code).put()
        self.redirect('/' + code)

class BuildDownload(webapp.RequestHandler):
    def get(self):
        count    = int(self.request.get('count') or 0)
        last_key = self.request.get('last')

        q = PostalCode.all().order('__key__')
        if last_key: q = q.filter('__key__ > ', db.Key(last_key))

        text = StringIO.StringIO()
        out = csv.writer(text)
        codes = q.fetch(500)

        if not codes: return

        for p in codes:
            country, postcode = p.key().name().split('/')
            out.writerow([country, postcode, p.place_name, p.admin_name1,
                p.latitude, p.longitude, p.accuracy])

        Download(key_name = str(count), text=text.getvalue()).put()
        taskqueue.add(url=self.request.path, method='GET', params={
            'count': str(count+1),
            'last': codes[-1].key(),
        })
        self.response.out.write('Download file #' + str(count) + ' built.')


class DownloadPage(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        for data in Download.all().order('__key__'):
            self.response.out.write(data.text)

class LoginPage(webapp.RequestHandler):
    def get(self):
        self.redirect(users.create_login_url(self.request.get('continue', '/')))

class LogoutPage(webapp.RequestHandler):
    def get(self):
        self.redirect(users.create_logout_url(self.request.get('continue', '/')))


application = webapp.WSGIApplication([
    ('/',                   HomePage),
    ('/([A-Z][A-Z]/\d+)',   CodePage),
    ('/feed',               FeedPage),
    ('/_download',          BuildDownload),
    ('/download',           DownloadPage),
    ('/login',              LoginPage),
    ('/logout',             LogoutPage),
], debug=(os.name=='nt'))

if __name__ == '__main__':
    webapp.util.run_wsgi_app(application)
