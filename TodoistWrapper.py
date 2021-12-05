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
		fullNameToName = {}
		nameToFullName = {}
		
		self.log(f'going trough {len(shoppingItems)} shopping items')

		units =['g', 'kg', 'ml', 'l']
		adjectives = ['braune', 'brauner', 'frisch', 'frische', 'frisches','gefrorene', 'gefrorenes','gelb', 'gelbe','gemischte', 'gemischtes','gestr.', 'gestrichen', 
				'gestrichene', 'getrocknete', 'getrocknetes', 'roter', 'rote', 'rot', 'grün', 'grüne',   'reife', 'reifes',   'geh.', 'gehäufte', 'gehäuftes', 'schwarze', 'schwarzer', 'weißer', 'weiße']
		amounts = [ 'EL', 'TL', 'Stängel', 'Zweig', 'Zweige','Stück','Stücke', 'Liter', 'Pack', 'Packung', 'Päckchen', 'Bund', 'Pk', 'Pck.', 'Flasche', 'Flaschen', 'Dose', 'Dosen', 'Prisen','Prise', 'Msp.', 'Messerspitze', 'Messerspitzen', 'Würfel', 'Kugel', 'Kugeln']

		unitRegex =''
		for unit in units:
			unitRegex += unit + ' |'

		unitRegex = '(' + unitRegex.rstrip('|') +'){0,2}'

		adjectivesRegex = ''
		for adjective in adjectives:
			adjectivesRegex += adjective + ' |'

		adjectivesRegex = '(' + adjectivesRegex.rstrip('|') +'){0,}'

		amountRegex = ''
		for amount in amounts:
			amountRegex += amount + ' |'

		amountRegex = '(' + amountRegex.rstrip('|') + '){0,1}'

		regex = r'[0-9½¼¾\-]{0,3}\s{0,1}' + unitRegex + adjectivesRegex + amountRegex +  adjectivesRegex +'\s{0,1}(?P<ingredient>[\D\-]{,})'
		#regex = r'[0-9½¼¾\-]{0,5}\s{0,1}(g |kg |ml |l |geh\. |gestrichener |gestr\. ){0,1}(grüne |rote |frische |gemischte |reife |getrocknete |gefrorene ){0,}((\bEL\b)|(\bTL\b)|(\bStängel\b)|(\bZweige\b)|(\bStück\b)|(\bLiter\b)|(\bPackung\b)|(\bBund\b)|(\bPack\b)|(\bPäckchen\b)|(\bPk\b)|(\bFlasche\b)|(\bPrise\b)|(\bPrisen\b)){0,1}\s{0,1}(?P<ingredient>[\D\-]{,})'

		for shoppingItem in shoppingItems:			
			fullName =shoppingItem['content'].replace(' - ', '-')

			if 'http' in fullName:
				continue
			
			#remove everything inside ( )
			name = re.sub(r'\(.*\)', '', fullName).strip()

			#remove anything after commata or oder and only use first part for evaluation
			name = name.split(',')[0].split('oder')[0]

			#remove trailing descriptions
			name = re.sub(r'((( und mehr){0,1} (zum|nach) (Würzen|Kochen|Braten|Geschmack|Einfetten){1}){0,1})$', '', name).strip()
						
			match = re.search(regex, name)
			
			if match is not None:
				ingredientFromMatch = match.group('ingredient')
				
				if ingredientFromMatch is '':
					self.log('got empty match for ' + name + ' -> ' + ingredientFromMatch)
					continue

				name = ingredientFromMatch

				if fullName not in fullNameToName:
					fullNameToName[fullName] = name
					self.log(fullName + ' --> ' + name)

					if name not in nameToFullName:
						nameToFullName[name] = fullName
			
			if name in itemOrderIds: 
				sortedItems[itemOrderIds[name]] = name
				continue
			if name in unsortedItems:
				continue
				
			unsortedItems.append(name)
			
		#save unsorted (unknown) items so that an order can be configured
		unsortedSectionId = self.getOrAddSection('Sortierung_Einkaufsliste', 'Unsortiert')
		
		unsortedItemStringsForDialog = None

		for unsortedItem in unsortedItems: 
			description = ''
			if unsortedItem in nameToFullName:
				description = str(nameToFullName[unsortedItem])

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
		
		offset = 1
		
		sorted_keys = sorted(childOrders.keys())

		sortItems = self.getOpenItemsOfProject('Sortierung_Einkaufsliste')

		def tryGetSectionForItem(itemOfSortList):
			sortItem = next((x for x in sortItems if x['content'] == orderName), None)						
			sectionName = self.api.sections.get_by_id(sortItem['section_id'])['name']
			sectionId = self.getOrAddSection('Einkaufsliste', str(sectionName))
			return sectionId

		for orderNumber in sorted_keys:			
			orderName = str(childOrders[orderNumber])
						
			def doesItemBelongToType(shoppingListItem):
				itemName = str(shoppingListItem['content'])
				if itemName == orderName:
					return True

				if itemName not in fullNameToName:
					return False

				if orderName == fullNameToName[itemName]:
					return True

				return False

			itemsOfThisType = list(filter(doesItemBelongToType, shoppingItems))

			for itemOfThisType in itemsOfThisType:				
				itemOfThisType.reorder(child_order = int(offset))

				sectionId = tryGetSectionForItem(orderName)
				itemOfThisType.move(section_id = sectionId)

				self.log(str(offset) + ' : ' + itemOfThisType['content'])

				if offset % 15 == 0:
					self.log('commiting 15 changes')
					self.api.commit();

				offset += 1

		if offset % 15 != 0:
			self.log('commiting remaining changes')
			self.api.commit();
		
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

			if not isinstance(sectionId, int):
				section.delete()
		

		if sectionId is None:
			self.log(f'could not find section \'{sectionName}\'. Going to create it')
			section = self.api.sections.add(sectionName, project_id = projectId)
			self.api.commit()
			sectionId = section['id']
				
		self.log(f'Section \'{sectionName}\' in project \'{projectName}\' has id \'{sectionId}\'')

		return sectionId	

	def deleteAllSectionsFromProject(self, projectName = 'Einkaufsliste'):
		projectId = self.getProjectIdByName(projectName)
		allsection = self.api.sections.all()

		hasSections = False

		for section in allsection:
			if section['project_id'] != projectId:
				continue

			hasSections = True
			section.delete()			

		if hasSections:
			self.api.commit()
