# -*- coding: utf-8 -*-
'''
Created on May 3, 2012
{'id': 'inc', 'thread':'айди_треда', 'name': 'имя', 'picture': 'путь до пикчи', 'message': 'тело пста.', 'op': 'Ture\False оп или нет'}
@author: mikoto
'''

#strftime("%Y-%m-%d %H:%M:%S", gmtime())

from time import localtime, strftime
from ConfigParser import SafeConfigParser
import pymongo
import string
import random
import os
import hashlib
from PIL import Image
import re
import tornado.escape

config = SafeConfigParser()

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for x in range(size))

class Database(object):
	def __init__(self):
		config.read('config.ini')
		connection = pymongo.Connection('localhost', 27017)
		db = connection.Mikotoboard
		self.threads = db.threads
		self.posts = db.posts
		self.boards = db.boards
		self.users = db.users
		self.bans = db.bans
		self.news = db.news
		self.anon = config.get('main', 'default_anon')
	
	def message_handler(self, message, thread_id):
		message = tornado.escape.xhtml_escape(message)
		r = re.compile(r'&gt;(.*)')
		message = r.sub(r'<span style="color:green">&gt;\1</span>', message)
		r = re.compile(r'\n')
		message = r.sub('<br>', message)
		r = re.compile(r'\&gt;&gt;([0-9]+)')
		message = r.sub(r'<a href="/thread/%s#\1" id="msg\1">&gt;&gt;\1</a>' % thread_id, message)
		r = re.compile(r'(\*\*)(.+?)\1')
		message = r.sub(r'<b>\2</b>', message)
		r = re.compile(r'(\*)(.+?)\1')
		message = r.sub(r'<i>\2</i>', message)
		r = re.compile(r'(\%\%)(.+?)\1')
		message = r.sub(r'<span class="spoiler">\2</span>', message)
		r = re.compile(r'(\-\-)(.+?)\1')
		message = r.sub(r'<s>\2</s>', message)
		
		#r = re.compile('&gt;&gt;([0-9]+)')
		#message = r.sub(r'<a href="/thread/%s#\1">&#62;\1</a>' % thread_id, message)
		#r = re.compile('&gt;(.*$)')
		#message = r.sub(r'<font color="GREEN">&#62;\1</font>', message)
		#r = re.compile(r'(\*\*)+([^.*?$]+)+(\*\*)')
		#message = r.sub(r'<b>\2</b>', message)
		return message

	def get_all_threads(self, callback):
		callback(self.threads.find())
	
	def get_all_posts(self, callback):
		callback(self.posts.find())
	
	def get_users(self, callback):
		callback(self.users.find())

	def save_picture(self, picture):
		f = open('test.txt', 'w')
		f.write(picture['content_type'])
		f.flush()
		f.close()
		_id = id_generator()
		ext = os.path.splitext(picture['filename'])[1]
		#if r.match(ext):
		for post in self.posts.find():
			if post['picture']:
				f = open('.' + post['picture'], 'rb')
				sum1 = hashlib.md5(f.read()).hexdigest()
				sum2 = hashlib.md5(picture['body']).hexdigest()
				f.close()
				if sum1 == sum2:
					return post['picture'], post['thumb']
					break
		picture_name = "/img/" + _id + ext
		thumb_name = "/img/thumb/" + _id + ext
		f = open('.' + picture_name, 'wb')
		f.write(picture['body'])
		f.flush()
		f.close()
		thumb = Image.open('.' + picture_name)
		thumb.thumbnail((200, 400), Image.ANTIALIAS)
		thumb.save('.' + thumb_name, quality=100)
		return picture_name, thumb_name
	def thumb_featured(self, post):
		post = self.posts.find_one({'id': post})
		filename = os.path.split(post['picture'])[1]
		featured_name = '/img/featured' + filename
		thumb = Image.open('.' + post['picture'])
		thumb.thumbnail((500, 300), Image.ANTIALIAS)
		thumb.save('.' + featured_name, quality=100)
		return featured_name

	def new_post(self, name, message, thread_id = None, picture = None, callback = None, op = False, thumb = None, board=None, ip=None):
		try:
			_id = int(self.posts.find().sort('id')[self.posts.count() - 1]['id']) + 1
		except:
			_id = 1
		pub_date = strftime("%Y-%m-%d %H:%M:%S", localtime())
		if name == '':
			name = self.anon
		if picture:
			picture, thumb = self.save_picture(picture)
		message = self.message_handler(message, thread_id)
		post = {'id': _id, 'name': name, 'thumb': thumb, 'picture': picture, 'message': message, 'thread': int(thread_id), 'op': op, 'pub_date': pub_date, 'ip': ip}
		self.threads.update({'id': int(thread_id)}, {'$set':{'last_post': pub_date}})
		self.posts.insert(post)
		callback(thread_id, _id, board)
	
	def new_thread(self, name=None, picture=None, message=None, callback=None, board=None, ip=None):
		try:
			post_id = int(self.posts.find().sort('id')[self.posts.count() - 1]['id']) + 1
		except:
			post_id = 1
		try:
			thread_id = int(self.threads.find().sort('id')[self.threads.count() -1]['id']) + 1
		except:
			thread_id = 1
		if name == '':
			name = self.anon
		picture, thumb = self.save_picture(picture)
		if picture == None:
			thread_id = False
			callback(thread_id)
			return
		message = self.message_handler(message, thread_id)
		pub_date = strftime("%Y-%m-%d %H:%M:%S", localtime())
		post = {'id': post_id, 'name': name,'thumb': thumb, 'picture': picture, 'message': message, 'thread':  thread_id, 'op': True, 'pub_date': pub_date, 'ip': ip}
		thread = {'id': thread_id, 'last_post': pub_date, 'board': board}
		self.posts.insert(post)
		self.threads.insert(thread)
		callback(thread_id, board)
	
	def get_pages(self,x):
		pages = x/5
		if not x%5:
			return pages
		elif x%5:
			return pages + 1

	def get_threads(self, board, page, callback):
		page_id = page
		page = (page + 1) * 5
		if self.boards.find_one({'id': board}):
			threads=[]
			for thread in self.threads.find({'board': board}).sort('last_post'):
				_thread = {}
				posts = []
				op = self.posts.find_one({'thread': thread['id'], 'op': True})
				for post in self.posts.find({'thread': thread['id']}).sort('pub_date'):
					if not post['op']:
						posts.append(post)
				_thread['count'] = self.posts.find({'thread': thread['id']}).count()
				x = int(str(_thread['count'])[len(str(_thread['count']))-1])
				if x in [2, 3, 4]:
					_thread["c_word"] = "поста"
				elif x == 1 and _thread['count'] != 11:
					_thread['c_word'] = "пост"
				else:
					_thread['c_word'] = "постов"
				posts.reverse()
				posts = posts[:3]
				posts.reverse()
				_thread['op'] = op
				_thread['posts'] = posts
				threads.append(_thread)
			#[{'op': post, 'posts':[post, post, post]}
			pages = self.get_pages(len(threads))
			threads.reverse()
			threads = threads[page-5:page]
			boards = self.boards.find()
			board = self.boards.find_one({'id': board})
			callback(threads, board, boards, pages, page_id)
		else:
			boards = None
			pages = None
			page = None
			board = None
			threads = None
			callback(threads, board, boards, pages, page)
			threads.reverse()

	def get_posts(self, thread_id, board, callback):
		thread = self.threads.find_one({'id': int(thread_id)})
		boards = self.boards.find()
		callback(self.posts.find({'thread': int(thread_id)}).sort('id'), thread, boards)
	def get_all_news(self, callback):
		news = self.news.find().sort('pub_date')
		callback(news)

	def get_main(self, callback):
		featured = self.posts.find({'featured': True})
		boards = self.boards.find()
		news = []
		for art in self.news.find().sort('pub_date'):
			news.append(art)
		news.reverse()
		news = news[:3]
		try:
			featured[0]
			boards[0]
			callback(featured, boards, news)
		except:
			callback(False, boards, news)

	def mod_post(self, changeset, callback):
		post = changeset['post']
		if changeset['name']:
			self.posts.update({'id': post}, {'$set':{'name': changeset['name']}})
			print changeset['name']
		if changeset['message']:
			self.posts.update({'id': post}, {'$set':{'message': changeset['message']}})
			print changeset['message']
		if changeset['featured']:
			self.posts.update({'id': post}, {'$set':{'featured': True, 'featured_thumb': self.thumb_featured(post)}})
			print changeset['featured']
		callback('posts')
	def remove_threads(self, threads, callback):
		for thread in threads:
			posts = self.posts.find({'thread': int(thread)})
			for post in posts:
				self.posts.remove({'id': post['id']})
			self.threads.remove({'id': int(thread)})
		callback('threads')

	def mod_user(self, changeset, callback):
		if changeset['password']:
			password = hashlib.sha256(changeset['password']).hexdigest()
		else:
			password = self.users.find_one({'username': changeset['username']})['password']
		if changeset['role']:
			role = changeset['role']
		else:
			role = self.users.find_one({'username': changeset['username']})['role']
		self.users.update({'username': changeset['username']}, {'$set':{'password': password, 'role': role}})
		callback('users')
	
	def remove_users(self, users, callback):
		for username in users:
			self.users.remove({'username': username})
		callback('users')

	def new_user(self, username, role, password, callback):
		for user in self.users.find():
			if user['username'] == username:
				callback("User allready exists")
				return False
		password = hashlib.sha256(password).hexdigest()
		user = {'username': username, 'password': password, 'role': role}
		self.users.insert(user)
		callback('users')
			
	def get_boards(self, callback):
		callback(self.boards.find())
	
	def get_bans(self, callback):
		callback(self.bans.find())
	
	def new_board(self, board_id, desc, hidden, callback):
		board = {'id': board_id, 'desc': desc, 'hidden': hidden}
		self.boards.insert(board)
		callback('boards')

	def remove_boards(self, boards, callback):
		for board in boards:
			self.boards.remove({'id': board})
		callback('boards')
	def mod_board(self, board, desc):
		self.boards.update({'id': board}, {'$set':{'desc': desc}})
		callback('boards')
	
	def new_ban(self, ip, reason, callback):
		ban = {'ip': ip, 'reason': reason, 'date': strftime("%Y-%m-%d %H:%M:%S", localtime())}
		self.bans.insert(ban)
		callback('bans')
	
	def lift_bans(self, bans, callback):
		for ip in bans:
			self.bans.remove({'ip': ip})
		callback('bans')

	def remove_posts(self, posts, callback):
		for post in posts:
			_post = self.posts.find_one({'id': int(post)})
			if _post['op']:
				tid = _post['thread']
				self.posts.remove({'thread': tid})
				self.threads.remove({'id': tid})
			else:
				self.posts.remove({'id': _post['id']})
		callback('posts')

	def add_news(self, head, body, user, callback):
		try:
			_id = int(self.news.find().sort('id')[self.news.count() - 1]['id']) + 1
		except:
			_id = 1
		art = {'id': _id, 'head': head, 'body': body, 'user': user, 'pub_date': strftime("%Y-%m-%d %H:%M:%S", localtime())}
		self.news.insert(art)
		callback('news')
	def remove_news(self, news, callback):
		for _id in news:
			self.news.remove({'id': int(_id)})
		callback('news')
	
	def mod_news(self, changeset, callback):
		_id = changeset['id']
		head = changeset['head']
		body = changeset['body']
		self.news.update({'id': int(_id)}, {"$set": {'body': body, 'head': head}})
		callback('news')
	
	def check_auth(self, user, callback = False):
		if not user: 
			return False
		record = self.users.find_one({'username': user['user']})
		if record:
			if record['password'] == user['pass']:
				if callback:
					callback(user)
				else:
					return user
			else:
				return False
		else:
			return False
