from TodoistWrapper import TodoistWrapper
from Crawler import Crawler
from datetime import date
from datetime import datetime as dt
from datetime import timedelta

a = date.today()

b = timedelta(month=1)

c = a+b

token = None

with open('TodoistToken', 'r') as file:
    token = file.read().replace('\n', '')

todoist = TodoistWrapper(token, print)
todoist.api.sync()
openItems = todoist.getTasksOfDay()
#crawler = Crawler(print)

print(openItems)