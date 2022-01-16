from TodoistWrapper import TodoistWrapper
from Crawler import Crawler

token = None

with open('TodoistToken', 'r') as file:
    token = file.read().replace('\n', '')

todoist = TodoistWrapper(token, print)
todoist.api.sync()
openItems = todoist.getOpenItemsOfProject('Einkaufsliste')
#crawler = Crawler(print)

print(openItems)