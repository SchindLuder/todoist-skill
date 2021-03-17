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
	def handle_set_temperature(self, message):
		self.speak_dialog("shoppingList.read")
		self.api.sync()
		full_name = api.state['user']['full_name']
		self.speak_dialog(full_name)		
		for project in api.state['projects']:
			self.speak_dialog(str(project['name']))
		
			
def create_skill():
	return TodoistSkill()
