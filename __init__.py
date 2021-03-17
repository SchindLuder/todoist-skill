import os
import re
import time
import subprocess
import numpy
import threading
from math import ceil
import todoist
from mycroft import MycroftSkill, intent_file_handler, intent_handler

class TodoistSkill(MycroftSkill):
	def __init__(self):
		MycroftSkill.__init__(self)
		
	def initialize(self):
		self.api = todoist.TodoistAPI(self.settings.get('Todoist-API-Token'))
	
	@intent_handler('shoppinglist.read.intent')
	def handle_read_shoppinglist(self, message):
		self.api.sync()	
		
		shoppinglist = self.api.projects.get(2174603341)
		self.log.info(str(shoppinglist))
					
def create_skill():
	return TodoistSkill()
