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
	def getProjectIdByName(self, name):
		project = next(x for x in self.api.state['projects'] if x['name'] == name)
		return project['id']

	def getOpenItemsOfProject(self, projectName):
		project_id = self.getProjectIdByName(projectName)
		self.log.info('project_Id of ' + projectName + '=' + str(project_id))
		return list(filter(lambda x: (x['project_id'] == project_id) & (x['checked'] == 0) , self.api['items']))

	def addItemToProject(self, projectName, itemName):
    		project_id = getProjectIdByName(projectName)
    		api.items.add(itemName, project_id=project_id)
    		api.commit()

	def getContentListFromItems(self, itemCollection):    
    		return list(map(lambda x: x['content'], itemCollection))
	
	def __init__(self):
		MycroftSkill.__init__(self)
		
	def initialize(self):
		self.api = todoist.TodoistAPI(self.settings.get('Todoist-API-Token'))
	
	@intent_handler('shoppinglist.read.intent')
	def handle_read_shoppinglist(self, message):
		self.api.sync()			
		self.log.info('reading shopping list')		
		openItems = self.getOpenItemsOfProject('Einkaufsliste')
		self.log.info('got open items')		
		for item in self.getContentListFromItems(openItems):
			self.log.info(str(item))
			self.speak(str(item))
					
def create_skill():
	return TodoistSkill()


