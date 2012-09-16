#!/usr/bin/python2
# -*- coding: utf-8 -*-

'''
Created on May 3, 2012
views.py
@author: mikoto
'''
from ConfigParser import SafeConfigParser
import hashlib
import tornado.web
import os
import tornado.ioloop
import tornado.locale as user_locale
import db
import re

config = SafeConfigParser()
config.read('config.ini')

class BaseHandler(tornado.web.RequestHandler):
	def initialize(self):
		config.read('config.ini')
		self.title = config.get('main', 'board_title')
		self.help = open('res/help.html').read()
		self.db = db.Database()
	def get_current_user(self):
		user = self.get_user()
		return self.db.check_auth(user)
	def get_user(self):
		user = {}
		login = self.get_secure_cookie('user')
		password = self.get_secure_cookie('pass')
		user['user'] = login
		user['pass'] = password
		return user

class PostHandler(BaseHandler):
	def get(self, post_id):
		user = self.get_user()
		self.db.get_post(int(post_id), user=user, callback = self.on_response, board=None)
	
	def on_response(self, post, boards, board, auth):
		self.render('templates/board/post.html',post=post, boards=boards, board=board, auth=auth, title=self.title)
	
class BoardHandler(BaseHandler):
	@tornado.web.asynchronous
	def get(self, board, page=0):
		if page == '':
			page = 0
		user = self.get_user()
		self.db.get_threads(board, user, int(page), self.on_response)
	
	@tornado.web.asynchronous
	def post(self, _board, page):
		name = self.get_argument('name')
		name = tornado.escape.xhtml_escape(name)
		message = self.get_argument('message')
		#message = tornado.escape.xhtml_escape(message)
		try:
			picture = self.request.files['picture'][0]
		except:
			self.write("<center>Для создания треда необходимо приложить изображение.</center>")
			self.finish()
			return
		ip = self.request.remote_ip
		ext = os.path.splitext(picture['filename'])[1]
		r = re.compile(r'(.jpg|.png|.jpeg|.gif)')
		if r.match(ext):
			self.db.new_thread(ip=ip, name=name, picture=picture, message=message, callback=self.on_new_thread, board=_board)
		else:
			self.write('<center><font color=RED><b>Что-то не так. Скорее всего ошибка, или в качестве изображения указан неподходящий файл. Поробуйте ещё раз.</b></font></center>')
			self.finish()
		
	def on_response(self, response, board, boards, auth, pages, page):
		if board:
			self.render('templates/board/board.html', threads = response, board = board, boards = boards, auth = auth, pages = pages, page = page, help = self.help, title = self.title)
		else:
			self.write('<center><font color=RED>Запрошеной доски не существует</font></center>')
			self.finish()
	
	def on_new_thread(self, thread_id, board_id):
		if thread_id:
			self.redirect('/thread/' + str(thread_id))
		else:
			self.write('<center><font color=RED><b>Что-то не так. Скорее всего ошибка, или в качестве изображения указан неподходящий файл. Поробуйте ещё раз.</b></font></center>')

class MainHandler(BaseHandler):
	@tornado.web.asynchronous
	def get(self):
		self.db.get_main(self.on_response)
	def on_response(self, featured, boards, news):
		self.render('templates/board/index.html', pics = featured, boards = boards, news = news, title=self.title)

class ThreadHandler(BaseHandler):
	@tornado.web.asynchronous
	def get(self, thread_id):
		user = self.get_user()
		self.db.get_posts(int(thread_id), user=user,  board = None, callback=self._on_response)
	
	@tornado.web.asynchronous
	def post(self, thread_id):
		self.tid = thread_id
		name = self.get_argument('name')
		name = tornado.escape.xhtml_escape(name)
		message = self.get_argument('message')
		#message = tornado.escape.xhtml_escape(message)
		try:
			picture = self.request.files['picture'][0]
		except:
			picture = None
		if not picture and message == "":
			self.write('<center>Пустые сообщения запрещены</center>')
			self.finish()
			return
		ip = self.request.remote_ip
		self.db.new_post(name = name, message = message, thread_id = thread_id, picture = picture, callback = self.on_new_post, board=None, ip=ip)
	
	def on_new_post(self, thread_id, post_id, board):
		self.redirect('/thread/'+ str(thread_id) + "#" + str(post_id))
		#self.write(response['filename'])
		#self.finish()
	
	def _on_response(self, response, thread, boards, auth):
		if thread:
			self.render('templates/board/thread.html', posts = response, thread = thread, boards = boards, auth=auth, help=self.help, title=self.title)
		else:
			self.write('<center><span style="color: red;">Запрошеного вами треда не существует</span>')
			self.finish()

class LoginHandler(BaseHandler):
	def get(self):
		self.render('templates/admin/login.html')
	@tornado.web.asynchronous
	def post(self):
		login = self.get_argument('login')
		pwd = hashlib.sha256(self.get_argument('password')).hexdigest()
		user = {'user': login, 'pass': pwd}
		self.db.check_auth(user, callback=self.on_auth)
	def on_auth(self, auth, user=None):
		if auth:
			self.set_secure_cookie('user', user['user'])
			self.set_secure_cookie('pass', user['pass'])
			self.redirect('/admin/users')
		else:
			self.redirect('/admin/login')

class LogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie('user')
		self.clear_cookie('pass')
		self.redirect('/')

class PerkelHandler(BaseHandler):
	def get(self):
		self.render('templates/board/perkel/perkel.html')

class AdminHandler(BaseHandler):
	@tornado.web.authenticated
	@tornado.web.asynchronous
	def get(self, page=None):
		if page == "users":
			self.db.get_users(callback=self.on_user)
		elif page == "bans":
			self.db.get_bans(callback=self.on_banlist)
		elif page == "news":
			self.db.get_all_news(callback=self.on_news)
		elif page == "boards":
			self.db.get_boards(callback=self.on_boards)
		elif page == "threads":
			self.db.get_all_threads(callback=self.on_threads)
		elif page == "posts":
			self.db.get_all_posts(callback=self.on_posts)
		elif page == "stats":
			self.write("Нот Ет")
		elif page == "wipe":
			self.render('templates/admin/wipe.html')
		else:
			self.redirect('/admin/users')
	@tornado.web.authenticated
	@tornado.web.asynchronous
	def post(self, page):
		t = self.get_argument('type')
		if t == "mod_post":
			changeset = {}
			changeset['post'] = int(self.get_argument('post'))
			try:
				changeset['message'] = self.get_argument('message')
			except:
				changeset['message'] = ''
			changeset['name'] = self.get_argument('name')
			print changeset
			self.get_argument('featured')
			changeset['featured'] = True
			self.db.mod_post(changeset, self.on_response)
		elif t == "mod_user":
			changeset = {}
			changeset['username'] = self.get_argument('user')
			try:
				changeset['password'] = self.get_argument('pass')
			except:
				changeset['password'] = None
			try:
				changeset['role'] = self.get_argument('role')
			except:
				changeset['role'] = None
			self.db.mod_user(changeset, self.on_response)
		elif t == "mod_board":
			board = self.get_argument('board')
			desc = self.get_argument('desc')
			self.db.mod_board(board, desc, self.on_response)
		elif t == "mod_news":
			changeset = {}
			changeset['id'] = self.get_argument('id')
			changeset['head'] = self.get_argument('head')
			changeset['body'] = self.get_argument('body')
			self.db.mod_news(changeset, self.on_response)
		elif t == "add_news":
			user = self.get_secure_cookie('user')
			head = self.get_argument('head')
			body = self.get_argument('body')
			self.db.add_news(head, body, user, self.on_response)
		elif t == "new_user":
			username = self.get_argument('username')
			password = self.get_argument('pass')
			role = self.get_argument('role')
			self.db.new_user(username, role, password, self.on_response)
		elif t == "new_ban":
			ip = self.get_argument('ip')
			try:
				reason = self.get_argument('reason')
			except:
				reason = None
			self.db.new_ban(ip, reason, self.on_response)
		elif t == "new_board":
			board_id = self.get_argument('id')
			desc = self.get_argument('desc')
			self.db.new_board(board_id, desc, self.on_response)
		elif t == 'lift_bans':
			bans = self.get_arguments('ip')
			print bans
			self.db.lift_bans(bans, self.on_response)
		elif t == 'remove_boards':
			self.db.remove_boards(self.get_arguments('board'), self.on_response)
		elif t == "remove_news":
			self.db.remove_news(self.get_arguments('article'), self.on_response)
		elif t == "remove_users":
			self.db.remove_users(self.get_arguments(name="user"), callback=self.on_response)
		elif t == "remove_threads":
			self.db.remove_threads(self.get_arguments(name='thread'), callback=self.on_response)
		elif t == "remove_posts":
			self.db.remove_posts(self.get_arguments(name='post'), callback=self.on_response)
		else:
			self.write('<center><font color=RED>ОШИБКА!</fort></center>')
	def on_response(self, page):
		self.redirect('/admin/%s' % page)
	def on_user(self, users):
		self.render('templates/admin/users.html', users=users, title=self.title)
	def on_banlist(self, bans):
		self.render('templates/admin/bans.html', bans=bans, title=self.title)
	def on_news(self, news):
		self.render('templates/admin/news.html', news=news, title=self.title)
	def on_boards(self, boards):
		self.render('templates/admin/boards.html', boards=boards, title=self.title)
	def on_threads(self, threads):
		self.render('templates/admin/threads.html', threads=threads, title=self.title)
	def on_posts(self, posts):
		self.render('templates/admin/posts.html', posts=posts, title=self.title)

class RemovePost(BaseHandler):
	@tornado.web.asynchronous
	def post(self):
		posts = self.get_arguments('post')
		self.db.remove_posts(posts, self.on_response)
	def on_response(self, page):
		self.redirect('/%s' % page)
application = tornado.web.Application([
                                    (r'/', MainHandler),
									(r'/img/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), "img")}),
									(r'/img/thumb/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), "img/thumb")}),
									(r'/perkel/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), "templates/board/perkel")}),
									(r'/styles/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), "styles")}),
									(r'/thread/(.*)', ThreadHandler),
									(r'/admin/login', LoginHandler),
									(r'/perkel', PerkelHandler),
									(r'/admin/logout', LogoutHandler),
									(r'/admin/rp', RemovePost),
									(r'/admin/(.*)', AdminHandler),
									(r'/post/(.*)', PostHandler),
									(r'/(.*)/(.*)', BoardHandler),
									(r'/(.*)', BoardHandler)], debug=True, cookie_secret=config.get('security', 'cookie_secret'), login_url="/admin/login")

if __name__ == '__main__':
	application.listen(80)
	tornado.ioloop.IOLoop.instance().start()
