from TodoistWrapper import TodoistWrapper
from Crawler import Crawler
from datetime import date
from datetime import datetime as dt
from datetime import timedelta
import zahlwort2num as w2n

class selfMockup(object):
    pass

self = selfMockup()

#crawler = Crawler(print)
with open('TodoistToken', 'r') as file:
    token = file.read().replace('\n', '')

self.todoist = TodoistWrapper(token, print)
self.todoist.api.sync()

self.todoist.sortShoppingList()

exit()

recipeIdsAndNames = crawler.getNamesAndRecipeIdsFromQuery('soljanka')

numberOfMatches = len(recipeIdsAndNames)

for recipeId in recipeIdsAndNames:
    ingredients = crawler.get_ingredientStrings('https://cookidoo.de/recipes/recipe/de-DE/' + recipeId)
    a = ingredients





print(openItems)