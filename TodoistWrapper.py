# import todoist
import time
from typing import Optional, Any

from todoist_api_python.api import TodoistAPI
import re
from datetime import date
from datetime import datetime as dt

class TodoistWrapper():
    def __init__(self, token, loggingMethod):
        self.api = TodoistAPI(token)
        self.log = loggingMethod
        self.projects = None
        self.tasks = None
        self.labels = None
        self.sections = None

    def clear_caches(self):
        self.projects = None
        self.tasks = None
        self.labels = None
        self.sections = None

    def get_projects(self):
        if self.projects is None:
            self.projects = self.api.get_projects()

        return self.projects

    def get_sections(self):
        if self.sections is None:
            self.sections = self.api.get_sections()

        return self.sections

    def get_tasks(self):
        if self.tasks is None:
            self.tasks = self.api.get_tasks()

        return self.tasks

    def get_project_id_by_name(self, name):
        # project = next(x for x in self.api.state.projects if x.name == name)
        project = next(x for x in self.get_projects() if x.name == name)
        return project.id

    def get_sections_of_project(self, projectName):
        project_id = self.get_project_id_by_name(projectName)
        sections = self.get_sections()
        try:
            return list(filter(lambda x: (x.project_id == project_id), sections))
        except:
            return list()

    def get_section_id_by_name(self, section_name):
        section_id = next(x for x in self.get_sections() if x.name == section_name).id
        return section_id

    def get_open_items_of_project(self, project_name):
        project_id = self.get_project_id_by_name(project_name)
        self.log('getting open items of project:' + project_name + ' with id:' + str(project_id))

        def filter_project_id(item):
            return item.project_id == project_id

        result = list(filter(filter_project_id, self.get_tasks()))
        return result  # self.api.get_tasks(project_id=project_id)

    def addItemToProject(self, project_name: str, itemName: str, sectionId=None, descriptionString=''):
        project_id = self.get_project_id_by_name(project_name)
        return self.api.add_task(itemName, project_id=project_id, section_id=sectionId, description=descriptionString)

    def getContentListFromItems(self, itemCollection):
        return list(map(lambda x: str(x.content).lower(), itemCollection))

    def getItemOrderIds(self, orderProjectName='Sortierung_Einkaufsliste'):
        sectionsForSorting = self.get_sections_of_project(orderProjectName)

        def getSectionOrder(element):
            return element.order

        sectionsForSorting.sort(key=getSectionOrder)

        sortItems = self.get_open_items_of_project('Sortierung_Einkaufsliste')
        globalCounter = 0
        itemOrderIds = {}
        for sortSection in sectionsForSorting:
            sectionId = sortSection.id

            # sort them by their childorder within the section
            itemsInSection = list(filter(lambda x: x.section_id == sectionId, sortItems))

            def sortByChildOrder(element):
                return element.order

            itemsInSection.sort(key=sortByChildOrder)

            for itemInSection in itemsInSection:
                content = str(itemInSection.content)

                for singleItemInSection in content.split(','):
                    # item already added
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

                    # add name and counter for later sorting
                    itemOrderIds[singleItemInSection] = globalCounter;
                    globalCounter += 1

        return itemOrderIds

    def __getSortingEntriesPerLabel(self, sortingEntries: list):
        """
		Returns a dict with labels as keys and the concluded entries as values 
		@param sortingEntries: the list with labeled items
		"""
        labeledItems = dict()

        for sortingEntry in sortingEntries:
            # get the first label of the sortingEntry
            label = next(iter(sortingEntry.labels), None)

            # With the new logic all items in the sortingList should be labeled. This should not occur longterm.
            # TODO: after full migration of sortingList this could be handled as error / user-Feedback?
            if label is None:
                self.log(f'Item \'{sortingEntry}\' does not contain any label for sorting!')
                continue

            # check if the label is already existing within the dict
            labeledItem = labeledItems.get(label)

            # ... if it does not exist then create a new entry
            if labeledItem is None:
                labeledItems.update({label: sortingEntry.content})
            # otherwise append it to an existing entry (this helps avoid the maximum length per Task-title)
            else:
                # contents are comma separated to allow the limitation of max. 300 tasks per project
                newContent = f'{labeledItem},{sortingEntry.content}'
                labeledItems.update({label: newContent})

        return labeledItems

    def __createNewLabelsForUnknownLabels(self, existingLabels, requiredLabels):
        for requiredLabel in requiredLabels:
            if requiredLabel not in existingLabels:
                self.log(f'creating new label for {requiredLabel}')
                self.api.add_label(name=requiredLabel)

    def __updateContentToLabel(self, labelEntriesDict):
        self.contentToLabel = dict()

        for key in labelEntriesDict:
            contents_split = labelEntriesDict[key]

            for content in contents_split.split(','):
                if content not in self.contentToLabel:
                    self.contentToLabel.update({content: key})

    def get_label_name_for_content(self, content) -> Optional[str]:
        if content not in self.contentToLabel:
            return None

        return self.contentToLabel[content]

    def getItemOrderIdsFromLabels(self, orderProjectName='Sortierung_Einkaufsliste'):
        sortingEntries = self.get_open_items_of_project(orderProjectName)
        labels = self.api.get_labels()

        labelEntriesDict = self.__getSortingEntriesPerLabel(sortingEntries)

        # update dictionary to later retrieve a label for this content
        self.__updateContentToLabel(labelEntriesDict)

        usedLabelsInSorting = labelEntriesDict.keys()

        # createLabels that are using in sorting but unknown yet
        self.__createNewLabelsForUnknownLabels(list(map(lambda x: x.name, labels)), usedLabelsInSorting)

        orderNumberContent = dict()
        contentToLabel = dict()

        for label in labelEntriesDict:
            labelObject = next((x for x in labels if x.name == label), None)
            order = labelObject.order
            orderNumberContent.update({order: labelEntriesDict[label]})

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

                itemOrderIds.update({contentSingle: globalCounter})
                globalCounter += 1

        return itemOrderIds

    def get_config_elements(self, project_name: str, section_name: str):
        config_elements = []

        section_id = self.get_or_add_section(project_name, section_name)
        open_project_items = self.get_open_items_of_project(project_name)
        items_in_section = list(filter(lambda x: x.section_id == section_id, open_project_items))

        for item in items_in_section:
            content = str(item.content)
            config_elements.extend(content.split(','))

        return config_elements

    def __buildShoppingItemRegex(self, units, adjectives, amounts):
        unit_regex = ''
        for unit in units:
            unit_regex += unit.replace('.', '\\.') + ' |'

        unit_regex = '(' + unit_regex.rstrip('|') + '){0,2}'

        adjectives_regex = ''
        for adjective in adjectives:
            adjectives_regex += adjective.replace('.', '\\.') + ' |'

        adjectives_regex = '(' + adjectives_regex.rstrip('|') + '){0,}'

        amount_regex = ''
        for amount in amounts:
            amount_regex += amount.replace('.', '\\.') + ' |'

        amount_regex = '(' + amount_regex.rstrip('|') + '){0,1}'

        # added 0-9 for example '10 g Dinkelmehl Type 630'
        # factor detection: [0-9]{1,2},[0-9]{1} x ){0,1}
        regex = r'([0-9]{1,2}\.[0-9]{1}\sx\s){0,1}[0-9½¼¾\-\.]{0,10}\s{0,1}' + unit_regex + adjectives_regex + amount_regex + adjectives_regex + '\s{0,1}(?P<ingredient>[\D\-]{,})'

        return regex

    def sort_labeled_shoppinglist(self, list_name='Einkaufsliste'):
        shopping_items = self.get_open_items_of_project(list_name)
        item_order_ids = self.getItemOrderIdsFromLabels()

        # item_order_ids ['Wassser' :0, 'Brot':1]
        unsorted_items = []
        full_name_to_name = {}
        name_to_full_name_list = {}

        self.log(f'going through {len(shopping_items)} shopping items')

        units = ['g', 'kg', 'ml', 'l']
        adjectives = self.get_config_elements('Mycroft-Settings', 'Adjektive')
        amounts = self.get_config_elements('Mycroft-Settings', 'Einheiten')
        regex = self.__buildShoppingItemRegex(units, adjectives, amounts)

        for shoppingItem in shopping_items:
            full_name = shoppingItem.content

            # ignore recipe urls
            if 'http' in full_name:
                continue

            # remove everything inside ( )
            name = re.sub(r'\(.*\)', '', full_name).strip()

            # remove anything after commata or oder and only use first part for evaluation
            name = name.split(',')[0].split('oder')[0]

            # e.g. Weizenmehl Type 405
            name = re.sub(r'Type [0-9]{1,}', '', name)

            # remove trailing descriptions
            name = re.sub(r'( (und |etwas |mehr |zum |nach ){1,}([\D]{1,}){0,1})$', '', name).strip()

            # shorten - range indications
            name = name.replace(' - ', '-')

            match = re.search(regex, name)

            if match is not None:
                ingredient_from_match = match.group('ingredient')

                if ingredient_from_match is '':
                    self.log('got empty match for ' + name + ' -> ' + ingredient_from_match)
                    continue

                name = ingredient_from_match

                if full_name not in full_name_to_name:
                    full_name_to_name[full_name] = name
                    self.log(full_name + ' --> ' + name)

                if name not in name_to_full_name_list:
                    name_to_full_name_list[name] = [full_name]
                else:
                    name_to_full_name_list[name].append(full_name)

            if name not in item_order_ids:
                unsorted_items.append(name)

        if len(unsorted_items) > 0:
            # save unsorted (unknown) items so that an order can be configured
            unsorted_section_id = self.get_or_add_section('Sortierung_Einkaufsliste', 'Unsortiert')
            known_unsorted_items = self.getItemsOfSection('Unsortiert', 'Sortierung_Einkaufliste')
            for unsortedItem in unsorted_items:
                if next((x for x in known_unsorted_items if x.content == unsortedItem), None) is not None:
                    self.log(unsortedItem + ' is already in the unsorted section')
                    continue

                description = ''
                if unsortedItem in name_to_full_name_list:
                    description = str(name_to_full_name_list[unsortedItem])

                # add labeled item to sorting list
                self.addItemToProject('Sortierung_Einkaufsliste', unsortedItem, unsorted_section_id, description)

        self.log('ordering items')
        order = 1

        for name in item_order_ids:
            if name not in name_to_full_name_list:
                continue

            full_name_list = name_to_full_name_list[name]

            for full_name in full_name_list:
                shopping_item = next(x for x in shopping_items if x.content == full_name)
                shopping_items.remove(shopping_item)
                label_name = self.get_label_name_for_content(name)
                start = time.time()

                '''
                # = project
                / = section
                @ = label
                + = assignee
                parent id is missing 
                '''

                self.api.update_task(shopping_item.id, order = order)
                order = order+1
                continue
                result = self.api.quick_add_task(f'{shopping_item.content} #Einkaufsliste @{label_name}')

                if shopping_item.description is not '':
                    self.api.update_task(result.task.id, description=shopping_item.description)

                '''self.api.add_task(
                    content=shopping_item.content,
                    # order=orderInProject,
                    description=shopping_item.description,
                    labels=labels,
                    priority=shopping_item.priority,
                    due=shopping_item.due,
                    assignee_id=shopping_item.assignee_id,
                    project_id=shopping_item.project_id,
                    section_id=shopping_item.section_id,
                    parent_id=shopping_item.parent_id
                )'''

                self.log(f'add: {time.time() - start} seconds')

                start = time.time()
                try:
                    self.api.close_task(shopping_item.id)
                except:
                    self.log(f'Could not delete {shopping_item.content}')

                self.log(f'delete: {time.time() - start} seconds')
        return unsorted_items

    def get_or_add_section(self, project_name, section_name):
        project_id = self.get_project_id_by_name(project_name)

        section_id = None

        sections = self.get_sections()

        for section in sections:
            if section.project_id != project_id:
                continue

            if section.name != section_name:
                continue

            section_id = section.id

        if section_id is None:
            self.log(f'could not find section \'{section_name}\' in project \'{project_name}\'. Going to create it')
            section = self.api.add_section(section_name, project_id)
            section_id = section.id
            #clear cache to get all updated sections on next call
            self.sections = None

        self.log(f'Section \'{section_name}\' in project \'{project_name}\' has id \'{section_id}\'')

        return section_id

    def delete_all_sections_of_project(self, project_name):
        project_id = self.get_project_id_by_name(project_name)
        sections = self.api.get_sections()

        for section in sections:
            if section.project_id != project_id:
                continue
            self.api.delete_section(section.id)

    def getTasksOfDay(self, day=None, projectName=None):
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

    def getItemsOfSection(self, sectionname, projectname=None):
        sectionid = self.get_section_id_by_name(sectionname)
        return self.api.get_tasks(section_id=sectionid)
