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

listItem = 'Mehl und sechs eier'
itemsWithNumbers = []

for singleItem in listItem.split('und'):
    item = singleItem.strip()

    for word in item.split(' '):
        try:
            number = w2n.convert(word)
            item = item.replace(word, str(number))
        except KeyError:
            #not a number so replace first character with uppercase
            item = (str(item)).replace(word[0], word[0].upper(),1)
            continue
    
    itemsWithNumbers.append(item)

    #upperCaseListItem = (str(singleItem)).replace(singleItem[0], singleItem[0].upper(),1)
    #self.todoist.addItemToProject('Einkaufsliste', upperCaseListItem, None, True)

exit()




recipeIdsAndNames = crawler.getNamesAndRecipeIdsFromQuery('soljanka')

numberOfMatches = len(recipeIdsAndNames)

for recipeId in recipeIdsAndNames:
    ingredients = crawler.get_ingredientStrings('https://cookidoo.de/recipes/recipe/de-DE/' + recipeId)
    a = ingredients





print(openItems)