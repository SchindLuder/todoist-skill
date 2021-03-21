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
		
		self.log.info('reading shopping list')
		
		openItems = getOpenItemsOfProject(self.api, 'Einkaufsliste')
		
		
		itemNames = getContentListFromItems(openItems)
		
		for item in getContentListFromItems(openItems):
			self.log.info(str(item))
			self.speak(str(item))
					
def create_skill():
	return TodoistSkill()

def getProjectIdByName(api, name):
    project = next(x for x in api.state['projects'] if x['name'] == name)
    return project['id']

def getOpenItemsOfProject(api, projectName):
    project_id = getProjectIdByName(api, projectName)
    return list(filter(lambda x: (x['project_id'] == project_id) & (x['checked'] == 0) , api['items']))

def getOpenItemsOfProject(api, projectId):
    return list(filter(lambda x: (x['project_id'] == projectId) & (x['checked'] == 0) , api['items']))

def addItemToProject(api, projectName, itemName):
    project_id = getProjectIdByName(api, projectName)
    api.items.add(itemName, project_id=project_id)
    api.commit()

def getContentListFromItems(itemCollection):    
    return list(map(lambda x: x['content'], itemCollection))
