import os
import re
import time
import subprocess
import numpy
import threading
from math import ceil
from mycroft import MycroftSkill, intent_file_handler, intent_handler

class TodoistSkill(MycroftSkill):
	def __init__(self):
		MycroftSkill.__init__(self)
		
	def initialize(self):
		#self.clientPath = self.settings.get('HmipClientPath')
	
	@intent_handler('lies_einkaufsliste.intent')
	def handle_set_temperature(self, message):
		self.speak_dialog("shoppingList.dialog")
		
			
def create_skill():
	return TodoistSkill()
