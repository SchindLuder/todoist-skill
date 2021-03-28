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

	def addItemToProject(self, projectName, itemName, sectionId = None):
    		project_id = getProjectIdByName(projectName)
    		api.items.add(itemName, project_id=project_id,section_id=sectionId)
    		api.commit()

	def getContentListFromItems(self, itemCollection):    
    		return list(map(lambda x: str(x['content']).lower(), itemCollection))
	
	def __init__(self):
		MycroftSkill.__init__(self)
		
	def initialize(self):
		self.api = todoist.TodoistAPI(self.settings.get('Todoist-API-Token'))
	
	@intent_handler('shoppinglist.add.intent')
	def handle_add_shoppinglist(self,message):
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
			
	def getItemOrderIds(self):        
	    project_id = self.getProjectIdByName('Sortierung_Einkaufsliste')
	    sectionsForSorting = list(filter(lambda x: (x['project_id'] == project_id), self.api['sections']))

	    # sort sections by section order!
	    sortedSections = [None] * len(sectionsForSorting)

	    for section in sectionsForSorting:
		sortedSections[int(section['section_order'])-1] = section

	    #get all items of the sort project
	    sortItems = self.getOpenItemsOfProject('Sortierung_Einkaufsliste')

	    globalCounter = 0
	    itemOrderIds = {};

	    for sortSection in sortedSections:
		#get items of current section
		sectionId = sortSection['id']          
		
		#sort them by their childorder within the section
		itemsInSection = list(filter(lambda x: x['section_id'] == sectionId, sortItems))

		def sortByChildOrder(element):
            		return element['child_order']

		itemsInSection.sort(key = sortByChildOrder)
		for itemInSection in itemsInSection:
		    #item already added
		    if itemInSection in itemOrderIds:
			break

		    #add name and counter for later sorting
		    itemOrderIds[str(itemInSection['content'])] = globalCounter;
		    globalCounter+= 1

	    return itemOrderIds
			
	def handle_sort_shoppinglist(self,message):
		self.api.sync()
		shoppingItems = self.getOpenItemsOfProject('Test_Einkaufsliste')
		itemOrderIds = self.getItemOrderIds()
		
		unsortedItems = []
		sortedItems = [None] * 200
		itemsWithAmounts = {}
		
		for shoppingItem in shoppingItems:
			name = shoppingItem['content']
			
    		regex = r'[0-9]{1,5}[ kgml]{0,9}((\Stück\b)|(\bLiter\b)|(\bPackung\b)|(\bBund\b)|(\bPack\b)|(\bPäckchen\b)|(\bPk\b)|(\bFlasche\b)){0,1}'
		
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
		unsortedSectionId = next(x for x in self.api['sections'] if x['name'] == 'Unsortiert')['id']
		for unsortedItem in unsortedItems: 
			item = self.addItemToProject('Sortierung_Einkaufsliste', unsortedItem,unsortedSectionId)    

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

		self.api.commit();
					
def create_skill():
	return TodoistSkill()


