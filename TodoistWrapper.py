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
		self.log('getting open items of project:' + projectName + ' with id:' + str(project_id))

		projectItems = self.api['items']

		openItems = list([])

		for element in projectItems:

			try:
				if element['project_id'] != project_id:
					continue

				if element['checked'] == 1:
					continue
			except:
				continue

			openItems.append(element)

		return openItems

	def addItemToProject(self, projectName, itemName, sectionId = None, commit = False, descriptionString = ''):
		project_id = self.getProjectIdByName(projectName)
		self.api.items.add(itemName, project_id=project_id,section_id=sectionId, description=descriptionString )
		if commit:
			self.api.commit()

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
			sectionId = sortSection['id']          
		
			#sort them by their childorder within the section
			itemsInSection = list(filter(lambda x: x['section_id'] == sectionId, sortItems))

			def sortByChildOrder(element):
				return element['child_order']
		
			itemsInSection.sort(key = sortByChildOrder)
		
			for itemInSection in itemsInSection:
				#item already added
				if itemInSection in itemOrderIds:
					continue
				#add name and counter for later sorting
				itemOrderIds[str(itemInSection['content'])] = globalCounter;
				globalCounter+= 1
		
		return itemOrderIds

	def sortShoppingList(self, listName = 'Einkaufsliste'):
		shoppingItems = self.getOpenItemsOfProject(listName)
		itemOrderIds = self.getItemOrderIds()
		unsortedItems = []
		sortedItems = [None] * 1000
		itemsWithAmounts = {}
		
		self.log('going trough shopping items')
		
		ignoreSection = self.getOrAddSection('Einkaufsliste', 'Ignoriert')

		def removeIgnoredItems(item):			
			return (item['section_id'] is not ignoreSection) or ('http' not in item)
			
		shoppingItems = list(filter(removeIgnoredItems, shoppingItems))


		#regex = r'[0-9½¼¾\-]{1,5}[ kgeh\.ml]{0,9}((\bEL\b)|(\bTL\b)|(\bStängel\b)|(\bZweige\b)|(\bStück\b)|(\bLiter\b)|(\bPackung\b)|(\bBund\b)|(\bPack\b)|(\bPäckchen\b)|(\bPk\b)|(\bFlasche\b)|(\bPrise\b)|(\bPrisen\b)){0,1}(.*zum (Braten|Kochen|Würzen){1})$'
		regex = r'[0-9½¼¾\-]{0,5}\s{0,1}(g |kg |ml |l |geh\. |gestrichener |gestr\. ){0,1}(grüne |rote |frische |gemischte |reife |getrocknete |gefrorene ){0,}((\bEL\b)|(\bTL\b)|(\bStängel\b)|(\bZweige\b)|(\bStück\b)|(\bLiter\b)|(\bPackung\b)|(\bBund\b)|(\bPack\b)|(\bPäckchen\b)|(\bPk\b)|(\bFlasche\b)|(\bPrise\b)|(\bPrisen\b)){0,1}\s{0,1}(?P<ingredient>[\D\-]{,})'

		for shoppingItem in shoppingItems:			
			fullName =shoppingItem['content']
			#remove anything after commata
			split = fullName.split(',')

			#only use first part for evaluation
			name = split[0]

			name = re.sub(r'\(.*\)', '', name).strip()
			name = re.sub(r'((( und mehr){0,1} zum (Würzen|Kochen|Braten){1}){0,1})$', '', name).strip()
						
			match = re.search(regex, name)
			
			if match is not None: 
				#full name as in recipe / shopping list
				#previousName = name + rest
				# replace amount and leading/trailing whitespaces
				#name = re.sub(regex, '', name).strip()						
				name = match.group('ingredient')
				#self.log(str(previousName) + ' was converted to ' + str(name))				
				#if previousName not in itemsWithAmounts:
				if fullName not in itemsWithAmounts:
					itemsWithAmounts[name] = fullName    		
			
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
			description = ''
			if unsortedItem in itemsWithAmounts:
				description = str(itemsWithAmounts[unsortedItem])

			self.addItemToProject('Sortierung_Einkaufsliste', unsortedItem,unsortedSectionId, False, description)
			
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
				if not name in itemsWithAmounts:
					continue
				
				#get original entry with amount...
				previousName = itemsWithAmounts[name]

				try:
					matchingItem = next(x for x in shoppingItems if x['content'] == previousName)

				except:
					self.log(f'could not find matching item for {previousName}')
					continue
				
			matchingItem.reorder(child_order = childOrder)
		
		self.log('commiting changes')
		self.api.commit();

	def getOrAddSection(self, projectName, sectionName):
		projectId = self.getProjectIdByName(projectName)

		sectionId = None
		allsection = self.api.sections.all()
		
		for section in allsection:
			if section['project_id'] != projectId:
				continue

			if section['name'] != sectionName:
				continue

			sectionId = section['id']		

		if sectionId is None or not isinstance(sectionId, int):
			self.log(f'could not find section \'{sectionName}\'. Going to create it')
			section = self.api.sections.add(sectionName, project_id = projectId)
			self.api.commit()
			sectionId = section['id']
				
		self.log(f'Section \'{sectionName}\' in project \'{projectName}\' has id \'{sectionId}\'')

		return sectionId
