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
    		return list(map(lambda x: str(x['content']).lower(), itemCollection))
	
	def __init__(self):
		MycroftSkill.__init__(self)
		
	def initialize(self):
		self.api = todoist.TodoistAPI(self.settings.get('Todoist-API-Token'))
	
	@intent_handler('shoppinglist.add.intent')
	def handle_does_shoppinglist_contain(self,message):
		self.log.info('add shopping list item')
		self.log.info(str(message.data))
		
		listItem = message.data.get('listitem')
		
		if listItem is None:			
			self.speak('ich hab den gewünschten Eintrag nicht verstanden')
			return
		
		addItemToProject('Einkaufsliste', str(listItem))
		
		self.speak_dialog('project.added.item', {
			'project': 'Einkaufsliste', 
			'item' : str(listItem)
		})						
		
	@intent_handler('shoppinglist.does.contain.intent')
	def handle_does_shoppinglist_contain(self,message):
		self.api.sync()					
		self.log.info('does shopping list contain')						
		
		self.log.info(str(message.data))
		
		listItem = message.data.get('listitem')
		if listItem is None:			
			self.speak('ich hab den gesuchten Eintrag nicht verstanden')
			return
		
		openItems = self.getOpenItemsOfProject('Einkaufsliste')
		itemNames = self.getContentListFromItems(openItems)
		
		if listItem in itemNames:
			self.speak_dialog('project.contains', {			
				'projectName': 'Einkaufsliste', 
				'listItem' : str(listItem)
			})
			return
			
		self.speak_dialog('project.not.contains', {			
				'projectName': 'Einkaufsliste', 
				'listItem' : str(listItem)
			})
		
				
	
	@intent_handler('shoppinglist.read.intent')
	def handle_read_shoppinglist(self, message):
		self.api.sync()			
		self.log.info('reading shopping list')		
		openItems = self.getOpenItemsOfProject('Einkaufsliste')
		itemNames = self.getContentListFromItems(openItems)
		numberOfItems = len(itemNames)		
		
		if numberOfItems is 0:
			self.speak_dialog('project.empty', {'projectName': 'Einkaufsliste'})
			return		
		
		self.log.info(str(numberOfItems) + ' open items found')
		
		for i, item in enumerate(itemNames):
			self.log.info(str(item))
			
			if (i == (numberOfItems -1)) & (numberOfItems != 1):
				self.speak('und ' + str(item))
				break
				
			if numberOfItems is 1:
				self.speak('nur ' + str(item))			
				break
			
			self.speak(str(item))		
					
def create_skill():
	return TodoistSkill()


