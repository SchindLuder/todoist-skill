from TodoistWrapper import TodoistWrapper
from Crawler import Crawler
from datetime import date
from datetime import datetime as dt
from datetime import timedelta

crawler = Crawler(print)
test = 'butter beim backen'

test = test.replace(test[0], test[0].upper(),1)




#with open('TodoistToken', 'r') as file:
#    token = file.read().replace('\n', '')

#todoist = TodoistWrapper(token, print)
#todoist.api.sync()

recipeIdsAndNames = crawler.getNamesAndRecipeIdsFromQuery('Gulasch ungarisch')

numberOfMatches = len(recipeIdsAndNames)

for recipeId in recipeIdsAndNames:
    ingredients = crawler.get_ingredientStrings('https://cookidoo.de/recipes/recipe/de-DE/' + recipeId)
    a = ingredients





print(openItems)