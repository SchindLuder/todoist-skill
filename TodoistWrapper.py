import todoist
import re

class TodoistWrapper():
	def __init__(self, token, loggingMethod):
		self.api = todoist.TodoistAPI(token)
		self.api.sync()
		self.log = loggingMethod
		

	def getProjectIdByName(self, name):
		project = next(x for x in self.api.state['projects'] if x['name'] == name)
		return project['id']

	def getSectionIdByName(self,sectionName):
		unsortedSectionId = next(x for x in self.api['sections'] if x['name'] == 'Unsortiert')['id']
		return unsortedSectionId

	def getOpenItemsOfProject(self, projectName):
		project_id = self.getProjectIdByName(projectName)
		self.log('project_Id of ' + projectName + '=' + str(project_id))
		return list(filter(lambda x: (x['project_id'] == project_id) & (x['checked'] == 0) , self.api['items']))

	def addItemToProject(self, projectName, itemName, sectionId = None, commit = False):
		self.log.info('adding \'' + itemName + '\' to \'' + projectName )
		project_id = self.getProjectIdByName(projectName)
		self.api.items.add(itemName, project_id=project_id,section_id=sectionId)
		if commit:
			self.log.info('commiting changes')
			self.api.commit()
			self.api.sync()

	def getContentListFromItems(self, itemCollection):    
		return list(map(lambda x: str(x['content']).lower(), itemCollection))	

	def getItemOrderIds(self, orderProjectName = 'Sortierung_Einkaufsliste'):
		project_id = self.getProjectIdByName(orderProjectName)
		sectionsForSorting = list(filter(lambda x: (x['project_id'] == project_id), self.api['sections']))
				
		def getSectionOrder(element):
			return element['section_order']

		sectionsForSorting.sort(key = getSectionOrder)

		sortItems = self.getOpenItemsOfProject('Sortierung_Einkaufsliste')
		globalCounter = 0
		itemOrderIds = {}
		for sortSection in sectionsForSorting:
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

	def sortShoppingList(self, listName = 'Einkaufsliste'):
		shoppingItems = self.getOpenItemsOfProject(listName)
		itemOrderIds = self.getItemOrderIds()
		unsortedItems = []
		sortedItems = [None] * 200
		itemsWithAmounts = {}
		
		self.log('going trough shopping items')
		
		for shoppingItem in shoppingItems:
			#remove anything after commata
			split = shoppingItem['content'].split(',')

			name = split[0]

			#save the rest for the name resolution
			rest = ''

			if len(split) > 1:
				for i in range(1,len(split)):
					rest+=',' + split[i]
			
			regex = r'[0-9½¼¾\-]{1,5}[ kgeh\.ml]{0,9}((\bEL\b)|(\bTL\b)|(\bStück\b)|(\bLiter\b)|(\bPackung\b)|(\bBund\b)|(\bPack\b)|(\bPäckchen\b)|(\bPk\b)|(\bFlasche\b)|(\bPrise\b)){0,1}'
			match = re.search(regex, name)
			
			if match is not None: 
				#full name as in recipe / shopping list
				previousName = name + rest
				# replace amount and leading/trailing whitespaces
				name = re.sub(regex, '', name).strip()						
				
				#self.log(str(previousName) + ' was converted to ' + str(name))
				if previousName not in itemsWithAmounts:
					itemsWithAmounts[name] = previousName    		
			
			if name in itemOrderIds: 
				sortedItems[itemOrderIds[name]] = name
				continue
			if name in unsortedItems:
				continue
				
			unsortedItems.append(name)
			
		#save unsorted (unknown) items so that an order can be configured
		unsortedSectionId = self.getSectionIdByName('Unsortiert')
		
		unsortedItemStringsForDialog = None
		for unsortedItem in unsortedItems: 
			item = self.addItemToProject('Sortierung_Einkaufsliste', unsortedItem,unsortedSectionId)
			
			if unsortedItemStringsForDialog is None:				
				unsortedItemStringsForDialog = str(unsortedItem)
				continue											
			
			unsortedItemStringsForDialog += (' und ' + str(unsortedItem))	
		
		self.log('ordering items')
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
		
		self.log('commiting changes')
		self.api.commit();