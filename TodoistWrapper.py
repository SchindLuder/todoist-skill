# import todoist
import json
import time
import uuid
from typing import Optional, Any

import requests
from todoist_api_python.api import TodoistAPI
import re
from datetime import date
from datetime import datetime as dt


class TodoistWrapper():
    def __init__(self, token, loggingMethod):
        self.token = token
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
        return self.api.get_tasks()
        # todo implement caching if required
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

    def addItemToProject(self, project_name: str, item_name: str, section_id=None, description=''):
        # quick add if neither description nor section is used (will add multiple times faster
        if section_id is None and description == '':
            return self.api.quick_add_task(f'{item_name} #{project_name}')

        project_id = self.get_project_id_by_name(project_name)

        return self.api.add_task(item_name, project_id=project_id, section_id=section_id, description=description)

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

    def get_item_orderids_from_labels(self, order_project_name='Sortierung_Einkaufsliste'):
        sorting_entries = self.get_open_items_of_project(order_project_name)
        labels = self.api.get_labels()

        label_entries_dict = self.__getSortingEntriesPerLabel(sorting_entries)

        # update dictionary to later retrieve a label for this content
        self.__updateContentToLabel(label_entries_dict)

        used_labels_in_sorting = label_entries_dict.keys()

        # createLabels that are using in sorting but unknown yet
        self.__createNewLabelsForUnknownLabels(list(map(lambda x: x.name, labels)), used_labels_in_sorting)

        order_number_content = dict()
        content_to_label = dict()

        for label in label_entries_dict:
            label_object = next((x for x in labels if x.name == label), None)
            order = label_object.order
            order_number_content.update({order: label_entries_dict[label]})

        sorted_keys = sorted(order_number_content)

        global_counter = 0
        item_order_ids = dict()
        for key in sorted_keys:
            content_comma_separated = order_number_content[key]

            content_split = content_comma_separated.split(',')

            for contentSingle in content_split:
                if contentSingle in item_order_ids:
                    self.log(f'Entry \'{contentSingle}\' appears multiple times in sortingList!')
                    continue

                item_order_ids.update({contentSingle: global_counter})
                global_counter += 1

        return item_order_ids

    def get_config_elements(self, project_name: str, section_name: str):
        config_elements = []

        section_id = self.get_or_add_section(project_name, section_name)
        open_project_items = self.get_open_items_of_project(project_name)
        items_in_section = list(filter(lambda x: x.section_id == section_id, open_project_items))

        for item in items_in_section:
            content = str(item.content)
            config_elements.extend(content.split(','))

        return config_elements

    def build_shopping_ingredient_regex(self, units, adjectives, amounts):
        unit_regex = ''
        for unit in units:
            unit_regex += unit.replace('.', '\\.') + ' |'

        for amount in amounts:
            unit_regex += amount.replace('.', '\\.') + ' |'

        unit_regex = '(?P<unit>' + unit_regex.rstrip('|') + '){0,2}'

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
        regex = r'(?P<amount>[0-9\-\.\s½¼¾]{1,10}){0,1}' + unit_regex + adjectives_regex + amount_regex + adjectives_regex + '\s{0,1}(?P<ingredient>[\D\-]{,})'
        # regex = r'(?P<amount>[0-9\-\.\s½¼¾]{1,10}){0,1}' + unit_regex + adjectives_regex + amount_regex + adjectives_regex + '\s{0,1}(?P<ingredient>[\D\-]{,})'
        # regex = r'([0-9]{1,2}\.[0-9]{1}\sx\s){0,1}[0-9½¼¾\-\.]{0,10}\s{0,1}' + unit_regex + adjectives_regex + amount_regex + adjectives_regex + '\s{0,1}(?P<ingredient>[\D\-]{,})'

        return regex

    def store_unsorted_items(self, unsorted_items, name_to_full_name_list):
        if len(unsorted_items) < 1:
            return

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

    def sort_labeled_shoppinglist(self, list_name='Einkaufsliste'):
        shopping_items = self.get_open_items_of_project(list_name)
        item_order_ids = self.get_item_orderids_from_labels()

        unsorted_items = []
        full_name_to_name = {}
        name_to_full_name_list = {}

        def store_name_to_full_name(_name, _full_name):
            if _full_name not in full_name_to_name:
                full_name_to_name[_full_name] = _name
                self.log(_full_name + ' --> ' + _name)

            if _name not in name_to_full_name_list:
                name_to_full_name_list[_name] = [_full_name]
            else:
                name_to_full_name_list[_name].append(_full_name)

        self.log(f'going through {len(shopping_items)} shopping items')

        units = ['g', 'kg', 'ml', 'l']
        adjectives = self.get_config_elements('Mycroft-Settings', 'Adjektive')
        amounts = self.get_config_elements('Mycroft-Settings', 'Einheiten')
        regex = self.build_shopping_ingredient_regex(units, adjectives, amounts)
        name_amount_dict = {}

        def preformat_shopping_item(full_content):
            # remove everything inside ( )
            preformatted_content = re.sub(r'\(.*\)', '', full_content).strip()

            # remove anything after commata or oder and only use first part for evaluation
            preformatted_content = preformatted_content.split(',')[0].split('oder')[0]

            # e.g. Weizenmehl Type 405
            preformatted_content = re.sub(r'Type [0-9]{1,}', '', preformatted_content)

            # remove trailing descriptions
            preformatted_content = re.sub(r'( (und |etwas |mehr |zum |nach ){1,}([\D]{1,}){0,1})$', '', preformatted_content).strip()

            # shorten - range indications
            preformatted_content = preformatted_content.replace(' - ', '-')

            return preformatted_content

        def update_name_amount_dict(found_ingredient, found_amount, found_unit, found_task_id):
            _ingredient_unit = f'{found_ingredient}_{found_unit}'

            if _ingredient_unit in name_amount_dict:
                name_amount_dict.update({_ingredient_unit: {
                    'amount_string': (
                            name_amount_dict[_ingredient_unit]['amount_string'] + f'+{found_amount}'),
                    'task_ids': (name_amount_dict[_ingredient_unit]['task_ids'] + f'+{found_task_id}')
                }
                })
            else:
                name_amount_dict[_ingredient_unit] = {
                    'amount_string': found_amount,
                    'task_ids': found_task_id
                }

        for shoppingItem in shopping_items:
            full_name = shoppingItem.content

            # ignore recipe urls
            if 'http' in full_name:
                continue

            aggregated_match = re.search(r'(?P<ingredient>[A-Za-zäöüÄÖÜ\s\-]{1,}),\s(?P<amount>[0-9\.\,]{1,})\s(?P<unit>[A-züöäÜÖÄÜ]{1,})', full_name)

            if aggregated_match is not None:
                ingredient_from_match = aggregated_match.group('ingredient')
                amount_from_match = aggregated_match.group('amount')
                unit_from_match = aggregated_match.group('unit')

                # name_amount_dict has to be updated as further items could be concluded into it
                # e.g. Salz, 5 TL + 1 TL Salz
                update_name_amount_dict(ingredient_from_match,amount_from_match,unit_from_match, shoppingItem.id)
                store_name_to_full_name(ingredient_from_match, shoppingItem.content)

                if ingredient_from_match not in item_order_ids:
                    unsorted_items.append(ingredient_from_match)

                continue

            name = preformat_shopping_item(full_name)

            match = re.search(regex, name)

            if match is not None:
                ingredient_from_match = match.group('ingredient')
                # for unsorted logic
                name = ingredient_from_match
                unit_from_match = match.group('unit')
                amount_from_match = match.group('amount')

                if amount_from_match is None:
                    amount_from_match = '1'
                if unit_from_match is None:
                    unit_from_match = 'Stück'
                else:
                    unit_from_match = unit_from_match.rstrip(' ')

                ingredient_unit = f'{ingredient_from_match}_{unit_from_match}'

                update_name_amount_dict(ingredient_from_match,amount_from_match,unit_from_match, shoppingItem.id)

                if ingredient_from_match is '':
                    self.log('got empty match for ' + name + ' -> ' + ingredient_from_match)
                    continue

                store_name_to_full_name(ingredient_from_match, shoppingItem.content)

            if name not in item_order_ids:
                unsorted_items.append(name)

        # create aggregated items
        for name_amount in name_amount_dict:
            # todo check if the creation of new tasks and deletion of old could be prevented when already aggregated items are found
            split = name_amount.split('_')
            name = split[0]
            unit = split[1]
            amounts_ids = name_amount_dict[name_amount]
            amounts_split = amounts_ids['amount_string'].split('+')
            ids_split = amounts_ids['task_ids'].split('+')

            total_amount = 0

            for amount_string in amounts_split:
                #e.g. 1/2 - 3/4 TL
                if '-' in amount_string:
                    split = amount_string.split('-')
                    amount_string = split[0]

                # revert back to normal decimal separator . from , that is used to avoid interpretation as a date
                # replace fraction characters with decimal represenation
                amount_string = amount_string.replace(',', '.').replace('½', '.5').replace('¼', '.25').replace('¾', '.75').replace(' .',
                                                                                                                 '.')
                if amount_string.startswith('.'):
                    amount_string = f'0{amount_string}'

                amount = float(amount_string)

                total_amount = total_amount + amount

            # convert to int if no digits are contained
            if (str(total_amount)).endswith('.0'):
                try:
                    total_amount = int(total_amount)
                except ValueError:
                    self.log(f'could not convert {total_amount}')

            # todo mit quick_add und // macht man eine Beschreibung --> in add einbauen

            # do not use . as separator as the api will interprete it as a date in case of e.g. 1.5 -> 1st of may
            total_amount_string = str(total_amount).replace('.', ',')

            creation_string = f'{name}, {total_amount_string} {unit} #Einkaufsliste //{total_amount_string} {unit}'
            self.log(creation_string)
            self.api.quick_add_task(creation_string)

            for task_id in ids_split:
                self.api.delete_task(task_id)

        # store unsorted items so that they can be labeled
        self.store_unsorted_items(unsorted_items, name_to_full_name_list)

        self.log('ordering items')
        id_child_order_list = []

        shopping_items = self.get_open_items_of_project('Einkaufsliste')

        # new approach with reordering via sync api
        for shopping_item in shopping_items:
            full_name = shopping_item.content
            if 'http' in full_name:
                continue

            name = preformat_shopping_item(full_name)
            match = re.search(regex, name)

            if match is None:
                self.log(f'got empty match for _name:{name} from _full_name {full_name}')
                continue

            name = match.group('ingredient')

            # no label yet defined for the item put it to the end of the list
            if name not in item_order_ids:
                id_child_order_list.append({'id': shopping_item.id, 'child_order': 0, '_name': name})
                self.api.update_task(task_id=shopping_item.id, description='unsortiert')
                continue

            id_child_order_list.append({'id': shopping_item.id, 'child_order': item_order_ids[name], '_name': name})

            # get former description and insert label in front
            #task = self.api.get_task(shopping_item.id)
            label = self.get_label_name_for_content(name)

            # only insert label once
            if label in shopping_item.description:
                continue

            description = f'{self.get_label_name_for_content(name)}, {shopping_item.description}'
            self.api.update_task(task_id=shopping_item.id, description=description)

        def sort_by_child_order(element):
            return element['child_order']

        id_child_order_list.sort(key=sort_by_child_order)

        class Args:
            def __init__(self, items):
                self.items = items

            def to_json(self):
                return json.dumps(self, default=lambda o: o.__dict__)

        class Data:
            def __init__(self, commands):
                self.commands = [commands]

            def to_json(self):
                return json.dumps(self, default=lambda o: o.__dict__)

        args = Args(id_child_order_list)

        data = Data(
            {
                'type': 'item_reorder',
                'uuid': str(uuid.uuid4()),
                'args': Args(id_child_order_list)
            }
        )
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        response = requests.post('https://api.todoist.com/sync/v9/sync', headers=headers, data=data.to_json())

        success = str(response.content).__contains__('sync_status')
        print(f'Reordering success: {success}')

        section_id = self.get_or_add_section('Einkaufsliste', 'Gewürze')

        def find_label_in_description(task):
            return task.description is not None and task.description.startswith('Gewürze,')

        gewuerz_items = filter(find_label_in_description,self.get_open_items_of_project('Einkaufsliste'))
        #gewuerz_items = next(x for x in self.get_open_items_of_project('Einkaufsliste') if (x.description is not None and x.description.startswith('Gewürze,')))

        # as update task does not support the section_id property (readonly as of 03/2024
        for gewuerz_item in list(gewuerz_items):
            self.api.quick_add_task(f'{gewuerz_item.content} #Einkaufsliste /Gewürze //{gewuerz_item.description}')
            self.api.delete_task(gewuerz_item.id)

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
            # clear cache to get all updated sections on next call
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
