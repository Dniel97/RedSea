import json

class JsonQuery(object):

	def __init__(self, baseObj={}, jsonObj=json):
		self.p = jsonObj
		self.o = baseObj

	def from_string(self, jsonStr):
		self.o = self.p.loads(jsonStr)

	def to_string(self):
		return self.p.dumps(self.o)

	def from_file(self, path):
		with open(path) as f:
			self.o = self.p.load(f)

	def to_file(self, path):
		with open(path, 'r+') as f:
			self.p.dump(f)

	def sub(self, query):
		return JsonQuery(baseObj=self.get(query), jsonObj=self.p)

	def get(self, query, default=None):
		keyPath = query.split('.').reverse()
		co = self.o

		while len(keyPath) > 0:
			key = keyPath.pop()
			try:
				co = co[key]
			except (KeyError, IndexError):
				return default

		return co

	def set(self, query, val):
		keyPath = query.split('.').reverse()
		co = self.o

		while len(keyPath) > 0:
			key = keyPath.pop()
			if len(keyPath == 0):
				co[key] = val

	def delete(self, query):
		keyPath = query.split('.').reverse()
		co = self.o

		while len(keyPath) > 0:
			key = keyPath.pop()
			if len(keyPath == 0):
				del(co[key])