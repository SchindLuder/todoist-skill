import os
import re
import time
import subprocess
import numpy
import threading
import zahlwort2num as w2n
from math import ceil
from . import TodoistWrapper
from . import Crawler
from mycroft import MycroftSkill, intent_file_handler, intent_handler
from datetime import date
from datetime import datetime as dt
from datetime import timedelta

class TodoistSkill(MycroftSkill):
	def __init__(self):
		MycroftSkill.__init__(self)
		
	def initialize(self):		
		def tryGetToken(configPath = '/home/pi/todoist.config', settingsName ='Todoist-API-Token'):
			token = None

			if os.path.exists(configPath):
				with open(configPath) as f: 
					token = f.read()
					token = token. rstrip('\r')
					token = token. rstrip('\n')
					self.log.info('got todoist token from local config file')
					return str(token)
			
			return self.settings.get(settingsName)
		
		token = tryGetToken()

		if not token:
			self.log.info('No token set in settings. Please set a token to access todoist')
			self.todoist = None
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
		self.log.info(str(message.Data))
		
		listItem = message.Data.get('listitem')
		
		if listItem is None:			
			self.speak('ich hab den gewünschten Eintrag nicht verstanden')
			return

		itemsWithNumbers = []

		for singleItem in listItem.split('und'):
			item = singleItem.strip()

			for word in item.split(' '):
				try:
					#try convert any word within to number
					number = w2n.convert(word)
					item = item.replace(word, str(number))
				except KeyError:
					#not a number so replace first character with uppercase

					if word is 'g':
						continue

					item = (str(item)).replace(word[0], word[0].upper(),1)
					continue

			self.todoist.addItemToProject('Einkaufsliste', item, None, True)
		
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
		
		self.log.info(str(message.Data))
		
		listItem = message.Data.get('listitem')
		if listItem is None:			
			self.speak('ich hab den gesuchten Eintrag nicht verstanden')
			return
		
		openItems = self.todoist.get_open_items_of_project('Einkaufsliste')
		itemNames = self.todoist.getContentListFromItems(openItems)
		
		if listItem in itemNames:
			self.speak_dialog('project.contains', {			
				'project_name': 'Einkaufsliste',
				'listItem' : str(listItem)
			})
			return
			
		self.speak_dialog('project.not.contains', {			
				'project_name': 'Einkaufsliste',
				'listItem' : str(listItem)
			})		
	
	def readItemList(self, itemNames, itemsInARow):
		numberOfItems = len(itemNames)

		for i, item in enumerate(itemNames):
			item = (str(item)).split(',')[0]
			
			if (i == (numberOfItems -1)) & (numberOfItems != 1):
				self.speak('und ' + item)
				break
				
			if numberOfItems is 1:
				self.speak('nur ' + item)			
				break
			
			self.speak(item)

			if (i != 0) and (i % itemsInARow) == 0:
				answer = self.ask_yesno('Soll ich weiterlesen?')

				if answer != 'yes':
					break

	@intent_handler('shoppinglist.read.intent')
	def handle_read_shoppinglist(self, message):
		if not self.checkTodoistConfiguration():
			return

		self.todoist.api.sync()			
		self.log.info('reading shopping list')		
		openItems = self.todoist.get_open_items_of_project('Einkaufsliste')

		#self.log.info(str(openItems))

		if len(openItems) is 0:			
			self.speak_dialog('project.empty', {'project_name': 'Einkaufsliste'})
			return

		itemNames = self.todoist.getContentListFromItems(openItems)
		numberOfItems = len(itemNames)		
		
		if numberOfItems is 0:
			self.speak_dialog('project.git empty', {'project_name': 'Einkaufsliste'})
			return		
		
		self.log.info(str(numberOfItems) + ' open items found')
		
		self.readItemList(itemNames,4)

	@intent_handler('shoppinglist.sync.intent')
	def handle_sync_shoppinglist(self,message):
		if not self.checkTodoistConfiguration():
			return

		def getUrlsToCrawl(todoist, projectName = 'Einkaufsliste', clearUrls = True ):
			urls = []
			recipes = self.todoist.get_open_items_of_project(projectName)
			for recipe in recipes:
				fullString = str(recipe.content)
				if not 'https' in fullString: 
					continue

				url = 'https' + fullString.split('https')[-1]
				# remove trailing ) if url was added manually and not via share in Cookidoo
				url = url.strip(')')
				urls.append(url)

				if clearUrls:
					self.todoist.api.delete_task(task_id=recipe.id)

			return urls

		crawler = Crawler.Crawler(self.log.info)

		allIngredientStrings =[]
		allIngredientDescriptions = []

		urls = getUrlsToCrawl(self.todoist, 'Einkaufsliste', True)

		numberOfUrls = len(urls)

		if numberOfUrls > 0:
			self.speak_dialog('project.urls.found', {'numberOfUrls' : str(numberOfUrls)})

		for url in urls:
			match = re.search(' x(?P<factor>[0-9]{1,2},[0-9]{1})$', url)

			factor = None
			
			if match is not None:
				url = url.split(' x')[0]
				url = url.strip(')')
				factor = match.group('factor')
				
				if ',' in factor:
					factor = factor.replace(',','.')


			ingredientStrings = crawler.get_ingredientStrings(url)
			ingredientDescriptions = [None] * len(ingredientStrings)

			if factor is not None:
				factorFloat = float(factor.replace(',','.'))

				for index, ingredientString in enumerate(ingredientStrings):
					ingredientDescriptions[index] = factor + ' x '+ ingredientString				
			
					amountRegex = r'^(?P<amount>[0-9½¼¾\- ]{0,10}) '
					match = re.search(amountRegex, ingredientString)

					if match:
						originalAmount = match.group('amount')
						amount = originalAmount.replace('½', '0.5').replace('¼', '0.25').replace('¾', '0.75')
				
						#2 - 3 units ingredient
						if '-' in amount:
							amount = amount.split('-')[-1]
						#2 1/2 units something
						elif ' ' in amount:
							try:
								amountSplit = amount.split(' ')
								firstNumber = float(amountSplit[0])
								secondNumber = float(amountSplit[1])
								amount = firstNumber + secondNumber
							except ValueError:
								error = 'could not convert '+amount
								self.log.debug('Error in factorizing: ' + ingredientDescriptions[index])
						
						try:
							amountFloat = float(str(amount))

							totalFloat = factorFloat * amountFloat
				
							ingredientStrings[index] = ingredientString.replace(originalAmount, str(totalFloat))

							continue

						except ValueError as e:
							f = e
							self.log.debug('Error in factorizing: ' + ingredientDescriptions[index])
							self.log.debug(e)

				# cant calculate the result of the factor. just use the full string
				ingredientStrings[index] = ingredientDescriptions[index]
								
			allIngredientStrings.extend(ingredientStrings)
			allIngredientDescriptions.extend(ingredientDescriptions)

		index = 0
		if len(allIngredientStrings) > 0:
			self.speak_dialog('ingredients.add', {'numberOfIngredients' : str(len(allIngredientStrings))})
		
		for ingredient in allIngredientStrings:
			index += 1
			self.todoist.addItemToProject('Einkaufsliste', ingredient,None, False,allIngredientDescriptions[index-1])

		unsortedItems = self.todoist.sortShoppingList()
		self.speak('Einkaufsliste wurde sortiert')

		def unsortedItemDialog(unsortedItems):
			if len(unsortedItems) == 0:
				return
			
			answer = self.ask_yesno('Es gibt Einträge, die ich nicht sortieren konnte. Möchtest du mir jetzt die Kategorien dafür sagen?')

			if answer != 'yes':
				return

			for unsortedItem in unsortedItems:
				retry = 0
				while retry < 3:
					answer = self.get_response('ask.for.category', {
								'itemName' : unsortedItem
							})

					if answer is None or answer == '' or answer == ' ':
						retry +=1
						continue

					category = answer.replace(answer[0], answer[0].upper())

					sectionId = self.todoist.get_or_add_section('Sortierung_Einkaufsliste', str(answer))

					break

					#self.todoist.moveItemToSection('Sortierung_Einkaufsliste', unsortedItem, str(answer))

		unsortedItemDialog(unsortedItems)		

		def deleteEmptySections():
			sections = self.todoist.get_sections_of_project('Einkaufsliste')

			openItems = self.todoist.get_open_items_of_project('Einkaufsliste')

			for section in sections:
				# try to get first item in section 
				itemInSection = next((openItem for openItem in openItems if openItem.section_id == section.id), None)

				# delete section if its empty
				if itemInSection is None:
					self.todoist.api.delete_section(section_id = section.id)


		deleteEmptySections()

		self.log.debug(str(allIngredientStrings))

	@intent_handler('shoppinglist.delete.list.intent')
	def handle_delete_shoppinglist(self, message):
		self.todoist.api.sync()
		response = self.ask_yesno('confirm.delete.shoppinglist')

		if response == 'no':
			return
		if response is None or response != 'yes':
			self.speak_dialog('could.not.understand')

		projectId = self.todoist.get_project_id_by_name('Einkaufsliste')

		def onlyEinkaufsliste(item):
			if item.project_id != projectId:
			   return False

			try:
				# do not delete finished tasks neither URLs of recipes
				if item.checked == 1 or 'http' in str(item.content):
				   return False 
			except:
				self.log.debug('got exception while checking items of shopping list')
				return False

			return True

		allItems = list(self.todoist.api.items.all())
		shoppingItems = list(filter(onlyEinkaufsliste, allItems))

		self.log.info(f'deleting {str(len(shoppingItems))} items from shopping list')

		counter = 0

		for shoppingItem in shoppingItems:
			shoppingItem.delete()
			counter += 1

			if counter % 10 == 0:
				self.todoist.api.commit()

		self.todoist.delete_all_sections_of_project('Einkaufsliste')

		self.speak_dialog('shoppinglist.deleted')
		self.todoist.api.commit()

	@intent_handler('read.due.items.intent')
	def handle_read_due_items_intent(self, message):
		dueDate = message.Data.get('duedate')
		self.log.info(f'read due items for dueDate:\'{dueDate}\'')
				
		dueDateTime = date.today()
		addedDays = timedelta(days = 0)
		if dueDate is 'heute':
			addedDays = timedelta(days = 0)
		elif dueDate is 'morgen':
			addedDays = timedelta(days = 1)
		elif 'woche' in dueDate:
			addedDays = timedelta(days = 7)
		elif 'monat' in dueDate:
			addedDays = timedelta(days = 31)

		dueDateTime = date.today() + addedDays

		itemsForDay = self.todoist.getTasksOfDay(dueDateTime.strftime("%Y-%m-%d"))
		self.readItemList(itemsForDay,4)

	@intent_handler('test.intent')
	def test(self,message):		
		self.log.info(f'test.intent')
		query = message.Data.get('query')
		self.log.info(query)

		crawler = Crawler.Crawler(self.log.info)

		results = crawler.queryRecipes(query)
		
		numberOfMatches = len(results)

		if numberOfMatches is 0:
			self.speak_dialog('no.recipes.to.read.found', {
					'recipeName' : query
				})
			return

		def getDesiredRecipeId(recipeIdsAndNames,retries):
			if len(recipeIdsAndNames) == 1:
				return list(recipeIdsAndNames.keys())[0]						

			def builtQuestionText(recipeIdsAndNames):
				index = 0
				questionText = ''

				for result in recipeIdsAndNames:					
					name = result
					questionText +=f'{str(index+1)} : {name}, '
					index = index + 1

					if index > 3:
						return questionText
				
				return questionText
			
			questionText = builtQuestionText(recipeIdsAndNames)

			response = self.get_response('chose.recipe.index', {'question' : questionText})

			index = None
			try:
				index = int(response)
			except ValueError:
				index = None
						
			if index is None or index < 0 or index > len(recipeIdsAndNames):
				if retries > 3:
					return None

				return getDesiredRecipeId(recipeIdsAndNames, retries + 1)

			return list(recipeIdsAndNames.values())[index-1]

		recipeId = getDesiredRecipeId(results, 0)

		if recipeId is None:
			self.speak_dialog('please.chose.valid.option')
			return
		
		ingredients = crawler.get_ingredientStrings('https://cookidoo.de/recipes/recipe/de-DE/' + recipeId)		

		self.log.info(ingredients)

		self.speak('Ja für weiter, nein zum beenden')
		time.sleep(3)

		def readIngredientsInLoop(ingredients):
			for ingredient in ingredients:			
				text = ingredient.split(',')[0]

				waitTime = 1

				while True:					
					resp = self.ask_yesno(text) 
				
					if resp == 'no':					
						return

					if resp == 'yes':
						break

					if waitTime % 3 == 0:
						self.speak('Ja für weiter, nein zum beenden')
						time.sleep(3)
						continue				

					time.sleep(waitTime)
					waitTime += 1

			self.speak('das war es')

		readIngredientsInLoop(ingredients)

def create_skill():
	return TodoistSkill()


