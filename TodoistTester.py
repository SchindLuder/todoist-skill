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

        if numberOfItems == 1:
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

    def get_urls_to_crawl(todoist, project_name='Einkaufsliste', clear_urls=True):
        urls_recipenames = []
        recipes = self.todoist.get_open_items_of_project(project_name)
        for recipe in recipes:
            full_string = str(recipe.content)
            if 'https' not in full_string:
                continue

            recipe_name = full_string.split('Schau')[0]
            url = 'https' + full_string.split('https')[-1]
            # remove trailing ) if url was added manually and not via share in Cookidoo
            url = url.strip(')')
            urls_recipenames.append((url,recipe_name))

            if clear_urls:
                self.todoist.api.delete_task(task_id=recipe.id)

        return urls_recipenames

    crawler = Crawler(self.log.info)

    allIngredientStrings = []
    allIngredientDescriptions = []

    urls_descriptions = get_urls_to_crawl(self.todoist, 'Einkaufsliste', True)

    number_of_urls = len(urls_descriptions)

    if number_of_urls > 0:
        self.speak_dialog('project.urls_recipenames.found', {'numberOfUrls': str(number_of_urls)})

    for url_description in urls_descriptions:
        url = url_description[0]
        recipe_name = url_description[1]
        match = re.search(' x(?P<factor>[0-9]{1,2},[0-9]{1})$', url)
        factor = None

        # no factorized recipe
        if match is not None:
            url_description = url.split(' x')[0]
            url_description = url.strip(')')
            factor = match.group('factor')

            if ',' in factor:
                factor = factor.replace(',', '.')

        ingredient_strings = crawler.get_ingredientStrings(url)
        ingredient_descriptions = [recipe_name for x in range(len(ingredient_strings))]

        # there is a factor to be applied for the ingredients
        if factor is not None:
            factor_float = float(factor.replace(',', '.'))

            for index, ingredientString in enumerate(ingredient_strings):
                ingredient_descriptions[index] = factor + ' x ' + ingredientString

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
                            self.log.debug('Error in factorizing: ' + ingredient_descriptions[index])

                    try:
                        amountFloat = float(str(amount))

                        totalFloat = factor_float * amountFloat

                        ingredient_strings[index] = ingredientString.replace(originalAmount, str(totalFloat))

                        continue

                    except ValueError as e:
                        f = e
                        self.log.debug('Error in factorizing: ' + ingredient_descriptions[index])
                        self.log.debug(e)

            # cant calculate the result of the factor. just use the full string
            ingredient_strings[index] = ingredient_descriptions[index]

        allIngredientStrings.extend(ingredient_strings)
        allIngredientDescriptions.extend(ingredient_descriptions)

    index = 0
    if len(allIngredientStrings) > 0:
        self.speak_dialog('ingredients.add', {'numberOfIngredients': str(len(allIngredientStrings))})

    for ingredient in allIngredientStrings:
        index += 1
        self.todoist.add_item_to_project('Einkaufsliste', ingredient, None, allIngredientDescriptions[index - 1])

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

handle_sync_shoppinglist(self, '')
# self.todoist.sortLabeledShoppingList('Einkaufsliste')

exit()


class Args:
    def __init__(self):
        self.items = []

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)


def build_reorder_args(list_of_tasks):
    reorder_args = Args()

    max_order = len(list_of_tasks)
    current_order = max_order

    def get_order(task_object):
        return task_object.order

    list_of_tasks.sort(key=get_order)
    counter = 0
    for task in list_of_tasks:
        counter = counter + 1

        # if counter % 2:
        # continue

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

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        # return json.dumps(self, default=lambda o: o.__dict__,sort_keys=True, indent=4)


data = Data(
    {
        'type': 'item_reorder',
        'uuid': str(uuid.uuid4()),
        'args': args
    }

)
a = data.to_json()

response = requests.post('https://api.todoist.com/sync/v9/sync', headers=headers, data=data.to_json())

success = str(response.content).__contains__('sync_status')
print(f'success: {success}')
