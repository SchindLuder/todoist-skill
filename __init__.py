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
	
	@intent_handler('shoppinglist.order.intent')
	def handle_sort_shoppinglist(self,message):
		if not self.checkTodoistConfiguration():
			return

		self.todoist.api.sync()
		shoppingItems = self.todoist.getOpenItemsOfProject('Einkaufsliste')
		itemOrderIds = self.todoist.getItemOrderIds()
		unsortedItems = []
		sortedItems = [None] * 200
		itemsWithAmounts = {}
		
		self.log.info('going trough shopping items')
		
		for shoppingItem in shoppingItems:
			name = shoppingItem['content']
			
			regex = r'[0-9]{1,5}[ kgml]{0,9}((\bEL\b)|(\bTL\b)|(\bStück\b)|(\bLiter\b)|(\bPackung\b)|(\bBund\b)|(\bPack\b)|(\bPäckchen\b)|(\bPk\b)|(\bFlasche\b)){0,1}'
			#r'[0-9]{1,5}[ kgml]{0,9}((\Stück\b)|(\bLiter\b)|(\bPackung\b)|(\bBund\b)|(\bPack\b)|(\bPäckchen\b)|(\bPk\b)|(\bFlasche\b)){0,1}'
			match = re.search(regex, name)
			
			if match is not None: 
				previousName = name
				# replace amount and leading/trailing whitespaces
				name = re.sub(regex, '', name).strip()
				
				if previousName not in itemsWithAmounts:
					itemsWithAmounts[name] = previousName        
			if name in itemOrderIds: 
				sortedItems[itemOrderIds[name]] = name
				continue
			if name in unsortedItems:
				continue
				
			unsortedItems.append(name)
			
		#save unsorted (unknown) items so that an order can be configured
		unsortedSectionId = self.todoist.getSectionIdByName('Unsortiert')
		
		unsortedItemStringsForDialog = None
		for unsortedItem in unsortedItems: 
			item = self.todoist.addItemToProject('Sortierung_Einkaufsliste', unsortedItem,unsortedSectionId)
			
			if unsortedItemStringsForDialog is None:				
				unsortedItemStringsForDialog = str(unsortedItem)
				continue											
			
			unsortedItemStringsForDialog += (' und ' + str(unsortedItem))
			
		if unsortedItemStringsForDialog is not None:
			self.speak_dialog('unsortedItem', {'listItem' : str(unsortedItemStringsForDialog)})
		
		self.log.info('ordering items')
		#build final order for items contained in shoppingList
		childOrderCount = 0
		childOrders = {}
		
		for listItem in list(filter(lambda x: x is not None, sortedItems)):
			childOrders[childOrderCount] = listItem
			childOrderCount += 1
			
		#reorder items
		for childOrder in childOrders:
			name = childOrders[childOrder]
			
			matchingItem = next((x for x in shoppingItems if x['content'] == name),None)
			if matchingItem is None:
				#get original entry with amount...
				previousName = itemsWithAmounts[name]
				matchingItem = next(x for x in shoppingItems if x['content'] == previousName)
				
			matchingItem.reorder(child_order = childOrder)
		
		self.log.info('commiting changes')
		self.todoist.api.commit();		

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

		for url in getUrlsToCrawl(self.todoist):
			ingredientStrings = crawler.get_ingredientStrings(url)
			allIngredientStrings.extend(ingredientStrings)

		index = 0

		for ingredientString in allIngredientStrings:
			self.todoist.addItemToProject('Einkaufsliste', ingredientString)

		self.todoist.api.commit()

		self.todoist.sortShoppingList()

		self.log.info(str(allIngredientStrings))
					
def create_skill():
	return TodoistSkill()


