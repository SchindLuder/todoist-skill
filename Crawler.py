from urllib.parse import urljoin
import requests
import json
from requests.structures import CaseInsensitiveDict
from bs4 import BeautifulSoup
import urllib.parse
import re

class Crawler():
    """description of class"""
    def __init__(self, loggingMethod):
        self.log = loggingMethod
        self.initClientKeyAndAppId()

    def initClientKeyAndAppId(self):
        cookies = {    'tmde-lang': 'de-DE'}
        headers = {
            'authority': 'cookidoo.de',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
	        'dnt': '1',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
        }
        params = {
            'context': 'recipes',
            'countries': 'de',
            'query': 'test',
        }

        response = requests.get('https://cookidoo.de/search/de-DE', params=params, cookies=cookies, headers=headers)
        match = re.search('client-key=\"(?P<clientKey>[A-z0-9]{1,})\"', response.text)

        if match is None:
            exceptionMessage= 'could not get clientKey from request'
            self.log(exceptionMessage)
            raise Exception(exceptionMessage) 

        self.clientKey = match.group('clientKey')

        match = re.search('app-id=\"(?P<appId>[A-Za-z0-9]{1,})\"', response.text)

        if match is None:
            exceptionMessage= 'could not get appId from request'
            self.log(exceptionMessage)
            raise Exception(exceptionMessage) 

        self.appId = match.group('appId')

        self.log('Initialized clientKey and AppId')

    def download_url(self, url):
        return requests.get(url).text

    def queryRecipes(self,searchPhrase):
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Origin': 'https://cookidoo.de',
            'Referer': 'https://cookidoo.de/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
            'content-type': 'application/x-www-form-urlencoded',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        data = '{"requests":[{"query":"'+ searchPhrase + '","params":"page=0&hitsPerPage=20&facets=%5B%22tmversion%22%2C%22tags%22%5D&filters=(countries%3A%22de%22)%20AND%20(NOT%20accessories%3Acooking_station%20AND%20NOT%20accessories%3Ablade_cover%20AND%20NOT%20accessories%3Apeeler)&attributesToRetrieve=%5B%22id%22%2C%22title%22%2C%22rating%22%2C%22publishedAt%22%2C%22image%22%2C%22totalTime%22%5D&maxValuesPerFacet=5&attributesToHighlight=%5B%5D&clickAnalytics=true&analyticsTags=%5B%22touchpoint%3Aweb%22%2C%22market%3Ade%22%2C%22ui-lang%3Ade-DE%22%2C%22fun%3AmultiSearch%22%2C%22path%3A%2Fsearch%2Fde-DE%22%2C%22context%3Arecipes%22%2C%22component%3Anavigation%22%2C%22app%3Asearch-webapp%22%5D&ruleContexts=%5B%22lang_de-DE%22%2C%22cookidoo.de%22%2C%22web%22%2C%22market_de__lang_de-DE%22%5D&ignorePlurals=true&queryLanguages=%5B%22de%22%5D","indexName":"recipes-prod-de"}]}'

        searchResponse = requests.post('https://' + self.appId + '-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.10.3)%3B%20Browser%20(lite)&x-algolia-api-key=' 
						         + self.clientKey + '&x-algolia-application-id=3TA8NT85XJ', headers=headers, data=data)

        queryResultsJson = json.loads(searchResponse.text)

        queryResults = queryResultsJson['results']

        hits = queryResults[0]['hits']

        results =[]

        for hit in hits:
            recipeId = hit['id']
            name =  hit['title']
            result = {
                "name" : name,
                "recipeId" : recipeId                    
            }

            results.append(result)

        return results

    def get_ingredientStrings(self, url):
        self.log('crawling url: '+ url)
        html = self.download_url(url)
        soup = BeautifulSoup(html, 'html.parser')        
        
        ingredientStrings = []

        for i in range(0,10):
            ingredientRootNode = soup.find(id=f'ingredients-{str(i)}')

            if not ingredientRootNode:
                break

            for ingredientNode in ingredientRootNode.children:
                if not hasattr(ingredientNode, 'id') or not 'ingredient-' in ingredientNode['id']:
                    continue

                ingredientStringPure = str(ingredientNode.text)
                splits = ingredientStringPure.split('\n')

                ingredientStringUnescaped = ''
                for split in splits: 
                    ingredientStringUnescaped += (' ' + split.strip())

                ingredientStringUnescaped = ingredientStringUnescaped.replace('  ', ' ')
            
                if ingredientStringUnescaped is not None:
                    ingredientStrings.append(ingredientStringUnescaped.strip())

        return ingredientStrings