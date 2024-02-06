from TodoistWrapper import TodoistWrapper
from Crawler import Crawler
from datetime import date
from datetime import datetime as dt
from datetime import timedelta
import zahlwort2num as w2n
import re
import uuid
import requests
import json

class log(object):
    def info(self, message):
        print(message)

    def debug(self, message):
        print('debug: ' + message)


class selfMockup(object):
    def checkTodoistConfiguration(self):
        return True

    def __init__(self):
        self.log = log()

    def speak_dialog(self, dialogName, values):
        print('dialog: ' + dialogName)

    def speak(self, message):
        print('speak: ' + message)

    def ask_yesno(self, question):
        print('ask_yesno: ' + question)

    def set_api(self, api):
        self.api = api


itemNames = ['1', '2', '3', '4', '5']


def readItemList(self, itemNames, itemsInARow):
    numberOfItems = len(itemNames)

    for i, item in enumerate(itemNames):
        item = (str(item)).split(',')[0]

        if (i == (numberOfItems - 1)) & (numberOfItems != 1):
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

# readItemList(self, itemNames, 2)

crawler = Crawler(print)


# results = crawler.queryRecipes('soljanka')

def getDesiredRecipeId(recipeIdsAndNames, retries):
    if len(recipeIdsAndNames) == 1:
        return list(recipeIdsAndNames.keys())[0]

    def builtQuestionText(recipeIdsAndNames):
        index = 0
        questionText = ''

        for result in recipeIdsAndNames:
            name = result
            questionText += f'{str(index + 1)} : {name}, '
            index = index + 1

            if index > 3:
                return questionText

        return questionText

    questionText = builtQuestionText(recipeIdsAndNames)

    response = self.get_response('chose.recipe.index', {'question': questionText})

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


# recipeId = getDesiredRecipeId(results, 0)

def handle_sync_shoppinglist(self, message):
    if not self.checkTodoistConfiguration():
        return

    def getUrlsToCrawl(todoist, projectName='Einkaufsliste', clearUrls=True):
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

    crawler = Crawler(self.log.info)

    allIngredientStrings = []
    allIngredientDescriptions = []

    urls = getUrlsToCrawl(self.todoist, 'Einkaufsliste', True)

    numberOfUrls = len(urls)

    if numberOfUrls > 0:
        self.speak_dialog('project.urls.found', {'numberOfUrls': str(numberOfUrls)})

    for url in urls:
        match = re.search(' x(?P<factor>[0-9]{1,2},[0-9]{1})$', url)

        factor = None

        if match is not None:
            url = url.split(' x')[0]
            url = url.strip(')')
            factor = match.group('factor')

            if ',' in factor:
                factor = factor.replace(',', '.')

        ingredientStrings = crawler.get_ingredientStrings(url)
        ingredientDescriptions = [None] * len(ingredientStrings)

        if factor is not None:
            factorFloat = float(factor.replace(',', '.'))

            for index, ingredientString in enumerate(ingredientStrings):
                ingredientDescriptions[index] = factor + ' x ' + ingredientString

                amountRegex = r'^(?P<amount>[0-9½¼¾\- ]{0,10}) '
                match = re.search(amountRegex, ingredientString)

                if match:
                    originalAmount = match.group('amount')
                    amount = originalAmount.replace('½', '0.5').replace('¼', '0.25').replace('¾', '0.75')

                    # 2 - 3 units ingredient
                    if '-' in amount:
                        amount = amount.split('-')[-1]
                    # 2 1/2 units something
                    elif ' ' in amount:
                        try:
                            amountSplit = amount.split(' ')
                            firstNumber = float(amountSplit[0])
                            secondNumber = float(amountSplit[1])
                            amount = firstNumber + secondNumber
                        except ValueError:
                            error = 'could not convert ' + amount
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
        self.speak_dialog('ingredients.add', {'numberOfIngredients': str(len(allIngredientStrings))})

    for ingredient in allIngredientStrings:
        index += 1
        self.todoist.addItemToProject('Einkaufsliste', ingredient, None, allIngredientDescriptions[index - 1])

    unsorted_items = self.todoist.sort_labeled_shoppinglist()
    self.speak('Einkaufsliste wurde sortiert')

    def deleteEmptySections():
        sections = self.todoist.get_sections_of_project('Einkaufsliste')

        openItems = self.todoist.get_open_items_of_project('Einkaufsliste')

        for section in sections:
            # try to get first item in section
            itemInSection = next((openItem for openItem in openItems if openItem.section_id == section.id), None)

            # delete section if its empty
            if itemInSection is None:
                self.todoist.api.delete_section(section_id=section.id)

    deleteEmptySections()

    self.log.debug(str(allIngredientStrings))


with open('TodoistToken', 'r') as file:
    token = file.read().replace('\n', '')

self.todoist = TodoistWrapper(token, print)
self.set_api(self.todoist)

open_items = self.todoist.get_open_items_of_project('Einkaufsliste')
order_manual = [1, 3, 2, 240, 239]


class Args:
    def __init__(self):
        self.items = []

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)


def build_reorder_args(list_of_tasks):
    reorder_args = Args()

    max_order = len(list_of_tasks)
    current_order = max_order

    def get_order(object):
        return object.order

    list_of_tasks.sort(key=get_order)

    for task in list_of_tasks:
        id_order_object = {'id': task.id, 'child_order': current_order}  # task.order}
        print(f'{task.content} from {task.order} to {current_order}')
        reorder_args.items.append(id_order_object)
        current_order = current_order - 1

    return reorder_args


args = build_reorder_args(open_items)
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}  # x-www-form-urlencoded'}


class Data:
    def __init__(self, commands):
        self.commands = [commands]

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        # return json.dumps(self, default=lambda o: o.__dict__,sort_keys=True, indent=4)


data = Data(
    {
        'type': 'item_reorder',
        'uuid': str(uuid.uuid4()),
        'args': args
    }

)

response = requests.post('https://api.todoist.com/sync/v9/sync', headers=headers, data=data.toJson())

success = str(response.content).__contains__('sync_status')
print(f'success: {success}')
exit()
'''
$ curl https://api.todoist.com/sync/v9/sync \
    -H "Authorization: Bearer 0123456789abcdef0123456789abcdef01234567" \
    -d commands='[
    {
        "type": "item_move",
        "uuid": "318d16a7-0c88-46e0-9eb5-cde6c72477c8",
        "args": {
            "id": "2995104339", 
            "parent_id": "2995104340"
        }
    }]'

'''

handle_sync_shoppinglist(self, '')
# self.todoist.sortLabeledShoppingList('Einkaufsliste')

exit()

allIngredientsStrings = crawler.get_ingredientStrings('https://cookidoo.de/recipes/recipe/de-DE/r51860')

for ingredient in allIngredientsStrings:
    self.todoist.addItemToProject('Einkaufsliste', ingredient, None, ingredient)

self.todoist.api.commit()

'''
any_item_id0 = open_items[0].id
any_item_id1 = open_items[1].id

headers = {
    'Authorization': 'Bearer b4e9b236f1bbb5cd596ab5613b3fbf9f5a66a8a0',
    'Content-Type': 'application/x-www-form-urlencoded',
}

## hier muss die Ganze Liste übergeben werden
Data = """commands=[
    {
        "type": "item_reorder",
        "uuid": "bf0855a2-0138-4b76-b895-88cad8db9edc",
        "args": {
            "items": [
                {"id": "id0", "child_order": 5},
                {"id": "id1", "child_order": 4}
            ]
        }
    }]"""

Data = Data.replace('id0', any_item_id0)
Data = Data.replace('id1', any_item_id1)

print(Data)'''
