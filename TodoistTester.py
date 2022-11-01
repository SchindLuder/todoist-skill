from TodoistWrapper import TodoistWrapper
from Crawler import Crawler
from datetime import date
from datetime import datetime as dt
from datetime import timedelta
import zahlwort2num as w2n
import re
import requests
class log(object):
	def info(self,message):
		print(message)

	def debug(self,message):
		print('debug: ' + message)
class selfMockup(object):
	def checkTodoistConfiguration(self):
		return True

	def __init__(self): 
		self.log = log()

	def speak_dialog(self, dialogName, values):
		print('dialog: ' + dialogName)

	def speak(self,message):
		print('speak: ' + message)

	def ask_yesno(self,question):
		print('ask_yesno: '+ question)


itemNames = ['1','2','3','4', '5']

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

self = selfMockup()

#readItemList(self, itemNames, 2)

crawler = Crawler(print)

results = crawler.queryRecipes('soljanka')

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
			exit()

			return getDesiredRecipeId(recipeIdsAndNames, retries + 1)

		return list(recipeIdsAndNames.keys())[index]

recipeId = getDesiredRecipeId(results, 0)

exit()

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
			self.todoist.api.commit()

		return urls

	crawler = Crawler(self.log.info)

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

		if index % 15 == 0:
			self.todoist.api.commit()

	if index % 15 != 0:
		self.todoist.api.commit()

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

				sectionId = self.todoist.getOrAddSection('Sortierung_Einkaufsliste', str(answer))

				break

				#self.todoist.moveItemToSection('Sortierung_Einkaufsliste', unsortedItem, str(answer))

	unsortedItemDialog(unsortedItems)		

	def deleteEmptySections():
		projectId = self.todoist.getProjectIdByName('Einkaufsliste')

		sections = list(filter(lambda x: x['project_id'] == projectId, self.todoist.api.sections.all()))

		openItems = self.todoist.getOpenItemsOfProject('Einkaufsliste')

		for section in sections:
			# try to get first item in section 
			itemInSection = next((openItem for openItem in openItems if openItem['section_id'] == section['id']), None)

			# delete section if its empty
			if itemInSection is None:
				section.delete()

		self.todoist.api.commit()

	deleteEmptySections()

	self.log.debug(str(allIngredientStrings))

with open('TodoistToken', 'r') as file:
    token = file.read().replace('\n', '')

self.todoist = TodoistWrapper(token, print)
self.todoist.api.sync()

openItems = self.todoist.getOpenItemsOfProject('Einkaufsliste')
handle_sync_shoppinglist(self, '')

exit()

allIngredientsStrings = crawler.get_ingredientStrings('https://cookidoo.de/recipes/recipe/de-DE/r51860')

for ingredient in allIngredientsStrings:
    self.todoist.addItemToProject('Einkaufsliste', ingredient,None, False,ingredient)      
    
self.todoist.api.commit()