import os
import re
import time
import subprocess
import numpy
import threading
from math import ceil
from . import TodoistWrapper
from . import Crawler
from mycroft import MycroftSkill, intent_file_handler, intent_handler

class TodoistSkill(MycroftSkill):
	def __init__(self):
		MycroftSkill.__init__(self)
		
	def initialize(self):		
		def tryGetToken(configPath = '/home/pi/todoist.config', settingsName ='Todoist-API-Token'):
			token = None

			if os.path.exists(configPath):
				with open(configPath) as f: 
					token = f.read()
					self.log.info('got todoist token from local config file')
					return str(token)
			
			return self.settings.get(settingsName)
		
		token = tryGetToken()

		if not token:
			self.log.info('No token set in settings. Please set a token to access todoist')
			return
		
		self.todoist = TodoistWrapper.TodoistWrapper(token, self.log.info)

		self.itemsToIgnore = [
			'Wasser',
			'Salz',
			'Pfeffer',	
			'Oregano',	
			'Muskat',
			'Muskatnuss',
			'Rotweinessig',
			'Gewürzpaste für',
			'Mineralwasser', 
			'Gewürzpaste'
			]

		self.itemsToIgnoreRegex = self.getItemsIgnoreRegex(self.itemsToIgnore)
		
	def getItemsIgnoreRegex(self,itemsToIgnore):		
		ignoreItemRegex = ''

		for itemToIgnore in itemsToIgnore:
			ignoreItemRegex+=(r'\s{0,1}' + itemToIgnore + r'\s{0,1}|')
			
		return ignoreItemRegex.rstrip(r'\s|')

	def checkTodoistConfiguration(self):
		if self.todoist is None:
			self.speak_dialog('config.noapitoken.dialog')
			return False

		return True
	
	@intent_handler('shoppinglist.add.intent')
	def handle_add_shoppinglist(self,message):
		if not self.checkTodoistConfiguration():
			return

		self.log.info('add shopping list item')
		self.log.info(str(message.data))
		
		listItem = message.data.get('listitem')
		
		if listItem is None:			
			self.speak('ich hab den gewünschten Eintrag nicht verstanden')
			return
		
		self.todoist.addItemToProject('Einkaufsliste', str(listItem), None, True)
		
		self.speak_dialog('project.added.item', {
			'project': 'Einkaufsliste', 
			'item' : str(listItem)
		})						
		
	@intent_handler('shoppinglist.does.contain.intent')
	def handle_does_shoppinglist_contain(self,message):
		if not self.checkTodoistConfiguration():
			return

		self.todoist.api.sync()					
		self.log.info('does shopping list contain')						
		
		self.log.info(str(message.data))
		
		listItem = message.data.get('listitem')
		if listItem is None:			
			self.speak('ich hab den gesuchten Eintrag nicht verstanden')
			return
		
		openItems = self.todoist.getOpenItemsOfProject('Einkaufsliste')
		itemNames = self.todoist.getContentListFromItems(openItems)
		
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
		if not self.checkTodoistConfiguration():
			return

		self.todoist.api.sync()			
		self.log.info('reading shopping list')		
		openItems = self.todoist.getOpenItemsOfProject('Einkaufsliste')

		self.log.info(str(openItems))

		if len(openItems) is 0:			
			self.speak_dialog('project.empty', {'projectName': 'Einkaufsliste'})
			return

		itemNames = self.todoist.getContentListFromItems(openItems)
		numberOfItems = len(itemNames)		
		
		if numberOfItems is 0:
			self.speak_dialog('project.git empty', {'projectName': 'Einkaufsliste'})
			return		
		
		self.log.info(str(numberOfItems) + ' open items found')
		
		for i, item in enumerate(itemNames):

			item = (str(item)).split(',')[0]
			
			self.log.info(str(item))
			
			if (i == (numberOfItems -1)) & (numberOfItems != 1):
				self.speak('und ' + item)
				break
				
			if numberOfItems is 1:
				self.speak('nur ' + item)			
				break
			
			self.speak(item)

	@intent_handler('shoppinglist.sync.intent')
	def handle_sync_shoppinglist(self,message):
		if not self.checkTodoistConfiguration():
			return

		self.todoist.api.sync()

		def getUrlsToCrawl(todoist, projectName = 'Einkaufsliste', clearUrls = True ):
			urls = []
			recipes = self.todoist.getOpenItemsOfProject(projectName)
			for recipe in recipes:
				fullString = str(recipe.data['content'])
				if not 'https' in fullString: 
					continue

				url = 'https' + fullString.split('https')[-1]
				# remove trailing ) if url was added manually and not via share in Cookidoo
				url = url.strip(')')
				urls.append(url)

				if clearUrls:
					recipe.delete()

			if clearUrls:
				todoist.api.commit()

			return urls

		crawler = Crawler.Crawler(self.log.info)

		allIngredientStrings =[]

		urls = getUrlsToCrawl(self.todoist, 'Einkaufsliste', False)

		numberOfUrls = len(urls)

		if numberOfUrls > 0:
			self.speak_dialog('project.urls.found', {'numberOfUrls' : str(numberOfUrls)})

		for url in urls:
			ingredientStrings = crawler.get_ingredientStrings(url)
			allIngredientStrings.extend(ingredientStrings)

		index = 0

		if len(allIngredientStrings) > 0:
			self.speak_dialog('ingredients.add', {'numberOfIngredients' : str(len(allIngredientStrings))})

		def shallItemBeIgnored(item):
			if ingredientString in self.itemsToIgnore:
				return True

			ignoreMatch = re.search(self.itemsToIgnoreRegex, ingredientString)

			return ignoreMatch is not None

		ignoreSectionId = self.todoist.getOrAddSection('Einkaufsliste', 'Ignoriert')

		self.log.info('Regex: ' + self.getItemsIgnoreRegex(self.itemsToIgnore))
		self.log.info('IgnoreItems: ' + str(self.itemsToIgnore))

		for ingredientString in allIngredientStrings:
			if shallItemBeIgnored(ingredientString):
				self.log('adding item to ignored section: '+ ingredientString)
				self.todoist.addItemToProject('Einkaufsliste', ingredientString, ignoreSectionId)
				continue

			self.todoist.addItemToProject('Einkaufsliste', ingredientString)

		self.todoist.api.commit()

		self.todoist.sortShoppingList()
		self.speak('Einkaufsliste wurde sortiert')

		self.log.info(str(allIngredientStrings))
					
def create_skill():
	return TodoistSkill()


