#import todoist
from todoist_api_python.api import TodoistAPI
import re
from datetime import date
from datetime import datetime as dt

class TodoistWrapper():
	def __init__(self, token, loggingMethod):
		#self.api = todoist.TodoistAPI(token)
		self.api = TodoistAPI(token)
		#reset state to clean up any failed actions or zombie items
		#self.api.reset_state()
		#self.api.sync()		
		self.log = loggingMethod
		a = 1
		

	def getProjectIdByName(self, name):		
		#project = next(x for x in self.api.state.projects if x.name == name)
		project = next(x for x in self.api.get_projects() if x.name == name)
		return project.id

	def getSectionsOfProject(self, projectName):
		projectId = self.getProjectIdByName(projectName)
		sections = self.api.get_sections()		
		try:
			return list(filter(lambda x: (x.project_id == projectId), sections))
		except:
			return list()			

	def getSectionIdByName(self,sectionName):
		unsortedSectionId = next(x for x in self.api.sections if x.name == 'Unsortiert').id
		return unsortedSectionId

	def getOpenItemsOfProject(self, projectName):
		project_id = self.getProjectIdByName(projectName)
		self.log('getting open items of project:' + projectName + ' with id:' + str(project_id))
		
		return self.api.get_tasks(project_id = project_id)

	def addItemToProject(self, projectName, itemName, sectionId = None, commit = False, descriptionString = ''):
		project_id = self.getProjectIdByName(projectName)
		return self.api.add_task(itemName, project_id=project_id,section_id=sectionId, description=descriptionString )

	def getContentListFromItems(self, itemCollection):    
		return list(map(lambda x: str(x.content).lower(), itemCollection))	

	def getItemOrderIds(self, orderProjectName = 'Sortierung_Einkaufsliste'):
		sectionsForSorting = self.getSectionsOfProject(orderProjectName)
				
		def getSectionOrder(element):
			return element.order

		sectionsForSorting.sort(key = getSectionOrder)

		sortItems = self.getOpenItemsOfProject('Sortierung_Einkaufsliste')
		globalCounter = 0
		itemOrderIds = {}
		for sortSection in sectionsForSorting:
			sectionId = sortSection.id
		
			#sort them by their childorder within the section
			itemsInSection = list(filter(lambda x: x.section_id == sectionId, sortItems))

			def sortByChildOrder(element):
				return element.order
		
			itemsInSection.sort(key = sortByChildOrder)
		
			for itemInSection in itemsInSection:
				content = str(itemInSection.content)

				for singleItemInSection in content.split(','):
					#item already added
					if singleItemInSection in itemOrderIds:
						continue

					def getPluralItem(item):
						if item[-1] is 'e':
							return item.append('n')

						if item[-1] is 'l':
							return item.append('n')

						if item[-1] is 't':
							return item.append('en')

						if item[-1] is 's':
							return item.append('se')
						
						if item[-1] is 'o':
							return item.append('s')

					#add name and counter for later sorting
					itemOrderIds[singleItemInSection] = globalCounter;
					globalCounter+= 1
		
		return itemOrderIds


	def __getSortingEntriesPerLabel(self,sortingEntries:list):
		"""
		Returns a dict with labels as keys and the concluded entries as values 
		@param sortingEntries: the list with labeled items
		"""
		labeledItems = dict()

		for sortingEntry in sortingEntries:		
			#get the first label of the sortingEntry
			label = next(iter(sortingEntry.labels),None)

			#With the new logic all items in the sortingList should be labeled. This should not occur longterm. 
			#TODO: after full migration of sortingList this could be handled as error / user-Feedback?
			if label is None:
				self.log(f'Item \'{sortingEntry}\' does not contain any label for sorting!')
				continue

			#check if the label is already existing within the dict
			labeledItem = labeledItems.get(label)

			#... if it does not exist then create a new entry
			if labeledItem is None:
				labeledItems.update({label : sortingEntry.content})
			# otherwise append it to an existing entry (this helps avoid the maximum length per Task-title)
			else:
				# contents are comma separated to allow the limitation of max. 300 tasks per project
				newContent = f'{labeledItem},{sortingEntry.content}'
				labeledItems.update({label : newContent})

		return labeledItems

	def __createNewLabelsForUnknownLabels(self, existingLabels, requiredLabels):		
		for requiredLabel in requiredLabels:
			if requiredLabel not in existingLabels:
				self.log(f'creating new label for {requiredLabel}')
				self.api.add_label(name = requiredLabel)
				
	def __updateContentToLabel(self, labelEntriesDict):
		self.contentToLabel = dict()

		for key in labelEntriesDict: 
			contentsSplit = labelEntriesDict[key]

			for content in contentsSplit.split(','):
				if content not in self.contentToLabel:
					self.contentToLabel.update({content : key})

	def __getLabelForContent(self, content):
		if content not in self.contentToLabel:
			return None

		labelName = self.contentToLabel[content]
		labels = self.api.get_labels() 
		label = next((x for x in labels if x.name == labelName),None)

		return label

	def getItemOrderIdsFromLabels(self, orderProjectName = 'Sortierung_Einkaufsliste'):
		sortingEntries = self.getOpenItemsOfProject(orderProjectName)
		labels = self.api.get_labels()
				
		labelEntriesDict = self.__getSortingEntriesPerLabel(sortingEntries)				

		#update dictionary to later retrieve a label for this content
		self.__updateContentToLabel(labelEntriesDict)
		
		usedLabelsInSorting = labelEntriesDict.keys()

		#createLabels that are using in sorting but unknown yet
		self.__createNewLabelsForUnknownLabels(list(map(lambda x: x.name,labels)), usedLabelsInSorting)		

		orderNumberContent = dict()
		contentToLabel = dict()

		for label in labelEntriesDict:
			labelObject = next((x for x in labels if x.name == label),None)
			order = labelObject.order			
			orderNumberContent.update({order : labelEntriesDict[label]})

		sortedKeys = sorted(orderNumberContent)

		globalCounter = 0
		itemOrderIds = dict()
		for key in sortedKeys:
			contentCommaSeparated = orderNumberContent[key]

			contentSplit = contentCommaSeparated.split(',')

			for contentSingle in contentSplit:
				if contentSingle in itemOrderIds:
					self.log(f'Entry \'{contentSingle}\' appears multiple times in sortingList!')
					continue

				itemOrderIds.update({contentSingle:globalCounter})
				globalCounter += 1
		
		return itemOrderIds


	def getConfigElements(self, projectName, sectionName):	
		configElements = []

		sectionId = self.getOrAddSection(projectName, sectionName)
		openProjectItems = self.getOpenItemsOfProject(projectName)  
		itemsInSection = list(filter(lambda x: x.section_id == sectionId, openProjectItems))
		
		for item in itemsInSection:
			content = str(item.content)
			configElements.extend(content.split(','))

		return configElements

	def sortShoppingList(self, listName = 'Einkaufsliste'):
		shoppingItems = self.getOpenItemsOfProject(listName)
		itemOrderIds = self.getItemOrderIds()
		unsortedItems = []
		sortedItems = [None] * 1000
		fullNameToName = {}
		nameToFullName = {}
		
		self.log(f'going through {len(shoppingItems)} shopping items')

		units =['g', 'kg', 'ml', 'l']
		adjectives = self.getConfigElements('Mycroft-Settings', 'Adjektive')

		amounts = self.getConfigElements('Mycroft-Settings', 'Einheiten')

		unitRegex =''
		for unit in units:
			unitRegex += unit.replace('.','\\.') + ' |'

		unitRegex = '(' + unitRegex.rstrip('|') +'){0,2}'

		adjectivesRegex = ''
		for adjective in adjectives:
			adjectivesRegex += adjective.replace('.','\\.') + ' |'

		adjectivesRegex = '(' + adjectivesRegex.rstrip('|') +'){0,}'

		amountRegex = ''
		for amount in amounts:
			amountRegex += amount.replace('.','\\.') + ' |'

		amountRegex = '(' + amountRegex.rstrip('|') + '){0,1}'

		#added 0-9 for example '10 g Dinkelmehl Type 630'
		#factor detection: [0-9]{1,2},[0-9]{1} x ){0,1} 
		regex = r'([0-9]{1,2}\.[0-9]{1}\sx\s){0,1}[0-9½¼¾\-\.]{0,10}\s{0,1}' + unitRegex + adjectivesRegex + amountRegex +  adjectivesRegex +'\s{0,1}(?P<ingredient>[\D\-]{,})'		

		for shoppingItem in shoppingItems:			
			fullName =shoppingItem.content

			#ignore recipe urls
			if 'http' in fullName:
				continue
			
			#remove everything inside ( )
			name = re.sub(r'\(.*\)', '', fullName).strip()

			#remove anything after commata or oder and only use first part for evaluation
			name = name.split(',')[0].split('oder')[0]

			#e.g. Weizenmehl Type 405
			name = re.sub(r'Type [0-9]{1,}','', name)

			#remove trailing descriptions
			name = re.sub(r'( (und |etwas |mehr |zum |nach ){1,}([\D]{1,}){0,1})$', '', name).strip()

			#shorten - range indications
			name = name.replace(' - ','-')
						
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

		for unsortedItem in unsortedItems: 
			description = ''
			if unsortedItem in nameToFullName:
				description = str(nameToFullName[unsortedItem])

			self.addItemToProject('Sortierung_Einkaufsliste', unsortedItem,unsortedSectionId, False, description)

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
			sortItem = next((x for x in sortItems if (x.content == orderName or (orderName+',') in x.content or orderName in x.content)), None)									

			#best match: item completely matches
			sortItem = next((x for x in sortItems if x.content == orderName),None)
				   
			#2nd best: item plus description matches
			if sortItem is None:
				sortItem = next((x for x in sortItems if (orderName+',') in x.content),None)

			#3rd best: item matches anywhere
			if sortItem is None:
				sortItem = next((x for x in sortItems if orderName in x.content),None)
				
			#get section name from sorting list
			sectionName = self.api.get_section(sortItem.section_id).name

			#create found section from sorting in the target list
			return self.getOrAddSection('Einkaufsliste', str(sectionName))			

		for orderNumber in sorted_keys:			
			orderName = str(childOrders[orderNumber])
						
			def doesItemBelongToType(shoppingListItem):
				itemName = str(shoppingListItem.content)
				if itemName == orderName:
					return True

				if itemName not in fullNameToName:
					return False

				if orderName == fullNameToName[itemName]:
					return True

				return False

			itemsOfThisType = list(filter(doesItemBelongToType, shoppingItems))

			for itemOfThisType in itemsOfThisType:				
				itemOfThisType.order =  int(offset)															
				sectionId = tryGetSectionForItem(orderName)
				
				#workaround due to https://github.com/Doist/todoist-api-python/issues/8
				# create new item with all the properties and delete the old one

				self.api.add_task(
					content=itemOfThisType.content,
					description=itemOfThisType.description,
					labels=itemOfThisType.labels,
					priority=itemOfThisType.priority,
					due=itemOfThisType.due,
					assignee_id=itemOfThisType.assignee_id,
					project_id=itemOfThisType.project_id,
					section_id=sectionId,
					parent_id=itemOfThisType.parent_id,
					order = int(offset)
				)

				deleteResult = self.api.delete_task(itemOfThisType.id)
			   
				#itemOfThisType.move(section_id = sectionId)

				self.log(str(offset) + ' : ' + itemOfThisType.content)

				#hopefully not necessary anymore with new API
				#if offset % 15 == 0:
					#self.log('commiting 15 changes')
					#self.api.commit();

				offset += 1

		#hopefully not necessary anymore with new API
		#if offset % 15 != 0:
			#self.log('commiting remaining changes')
			#self.api.commit();
		
		#self.api.commit();

		return unsortedItems

	def __buildShoppingItemRegex(self, units, adjectives, amounts):
		unitRegex =''
		for unit in units:
			unitRegex += unit.replace('.','\\.') + ' |'

		unitRegex = '(' + unitRegex.rstrip('|') +'){0,2}'

		adjectivesRegex = ''
		for adjective in adjectives:
			adjectivesRegex += adjective.replace('.','\\.') + ' |'

		adjectivesRegex = '(' + adjectivesRegex.rstrip('|') +'){0,}'

		amountRegex = ''
		for amount in amounts:
			amountRegex += amount.replace('.','\\.') + ' |'

		amountRegex = '(' + amountRegex.rstrip('|') + '){0,1}'

		#added 0-9 for example '10 g Dinkelmehl Type 630'
		#factor detection: [0-9]{1,2},[0-9]{1} x ){0,1} 
		regex = r'([0-9]{1,2}\.[0-9]{1}\sx\s){0,1}[0-9½¼¾\-\.]{0,10}\s{0,1}' + unitRegex + adjectivesRegex + amountRegex +  adjectivesRegex +'\s{0,1}(?P<ingredient>[\D\-]{,})'	

		return regex

	def sortLabeledShoppingList(self, listName = 'Einkaufsliste'):
		shoppingItems = self.getOpenItemsOfProject(listName)
		itemOrderIds = self.getItemOrderIdsFromLabels()

		#itemOrderIds ['Wassser' :0, 'Brot':1]
		unsortedItems = []
		sortedItems = [None] * 1000
		fullNameToName = {}
		nameToFullName = {}
		
		self.log(f'going through {len(shoppingItems)} shopping items')

		units =['g', 'kg', 'ml', 'l']
		adjectives = self.getConfigElements('Mycroft-Settings', 'Adjektive')
		amounts = self.getConfigElements('Mycroft-Settings', 'Einheiten')
		regex = self.__buildShoppingItemRegex(units, adjectives, amounts)

		for shoppingItem in shoppingItems:			
			fullName =shoppingItem.content

			#ignore recipe urls
			if 'http' in fullName:
				continue
			
			#remove everything inside ( )
			name = re.sub(r'\(.*\)', '', fullName).strip()

			#remove anything after commata or oder and only use first part for evaluation
			name = name.split(',')[0].split('oder')[0]

			#e.g. Weizenmehl Type 405
			name = re.sub(r'Type [0-9]{1,}','', name)

			#remove trailing descriptions
			name = re.sub(r'( (und |etwas |mehr |zum |nach ){1,}([\D]{1,}){0,1})$', '', name).strip()

			#shorten - range indications
			name = name.replace(' - ','-')
						
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

		for unsortedItem in unsortedItems: 
			description = ''
			if unsortedItem in nameToFullName:
				description = str(nameToFullName[unsortedItem])

			self.addItemToProject('Sortierung_Einkaufsliste', unsortedItem,unsortedSectionId, False, description)

		self.log('ordering items')


		orderInProject = 0

		for sortedItem in sortedItems:
			if sortedItem is None: 
				continue
			
			#sortedItem contains name
			name = sortedItem
			fullName = nameToFullName[name]

			#find the task that belongs to this			
			shoppingItem = next((x for x in shoppingItems if x.content == fullName),None)
									
			#insert label of sorting object to this?
			label = self.__getLabelForContent(name)
			labels = []
			labels.append(label.name)

			# as there is no update of order available: create a new task and delete the old one			
			self.api.add_task(
					content=shoppingItem.content,
					order = orderInProject,
					description=shoppingItem.description,
					labels=labels,
					priority=shoppingItem.priority,
					due=shoppingItem.due,
					assignee_id=shoppingItem.assignee_id,
					project_id=shoppingItem.project_id,
					section_id=shoppingItem.section_id,
					parent_id=shoppingItem.parent_id					
				)

			orderInProject += 1
				
			result = self.api.close_task(task_id = shoppingItem.id)

			if not result:
				self.log(f'Could not delete {shoppingItem.content} for reordering')						

		return unsortedItems

	def getOrAddSection(self, projectName, sectionName):
		projectId = self.getProjectIdByName(projectName)

		sectionId = None

		
		allsection = self.api.get_sections()
		
		for section in allsection:
			if section.project_id != projectId:
				continue

			if section.name != sectionName:
				continue

			sectionId = section.id
			
			#previously handled zombie sections but as of now all sectionIds are strings
			#if not isinstance(sectionId, int):
				#section.delete()
				#self.api.commit()
		

		if sectionId is None:
			self.log(f'could not find section \'{sectionName}\' in project \'{projectName}\'. Going to create it')
			section = self.api.add_section(sectionName,projectId)			
			sectionId = section.id
				
		self.log(f'Section \'{sectionName}\' in project \'{projectName}\' has id \'{sectionId}\'')

		return sectionId	

	def deleteAllSectionsFromProject(self, projectName = 'Einkaufsliste'):
		projectId = self.getProjectIdByName(projectName)		
		allsection = self.api.get_sections()

		hasSections = False

		for section in allsection:
			if section.project_id != projectId:
				continue

			hasSections = True
			section.delete()			

		if hasSections:
			self.api.commit()

	def getTasksOfDay(self, day = None, projectName = None):
		self.api.sync()
	
		itemsForDay = list()		
		dateString = day
		dateObject = None

		if day is None: 			
			dateString = date.today().strftime("%Y-%m-%d")
			dateObject = dt.strptime(dateString, "%Y-%m-%d")
		else:
			dateObject = dt.strptime(day, "%Y-%m-%d")

		def filterOpenItemsWithDue(item):
			try:
				return item.is_deleted == 0 and item.checked == 0 and item.due != None
			except KeyError:
				self.log(f'item does not have property \'checked\': {item}')
				return False

		openItemsWithDue = list(filter(filterOpenItemsWithDue, self.api.items))

		for openItem in openItemsWithDue:
			openItemDueDate = openItem.due.date
			# date = Due date in the format of YYYY-MM-DD (RFC 3339). 
			itemDueDate = dt.strptime(openItemDueDate, "%Y-%m-%d")
			
			if itemDueDate < dateObject or openItemDueDate == dateString:
				itemsForDay.append(openItem.content)			

		return itemsForDay		