from urllib.parse import urljoin
import requests
import json
from requests.structures import CaseInsensitiveDict
from bs4 import BeautifulSoup
import urllib.parse

class Crawler():
    """description of class"""
    def __init__(self, loggingMethod):
        self.log = loggingMethod

    def download_url(self, url):
        return requests.get(url).text

    def getNamesAndRecipeIdsFromQuery(self,queryWords):       
        url = "https://3ta8nt85xj-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.10.3)%3B%20Browser%20(lite)&x-algolia-api-key=NzQxMWQ2OGMxMGQ5MDExZDRhZGVmZTViZmRhOWRiYzZmODRiNWI3YWUwNGQxYjY4N2NmNzk3NGI1M2FhYmFlYXZhbGlkVW50aWw9MTY0MzU0Nzg4MyZyZXN0cmljdEluZGljZXM9JTVCJTIyc3VnZ2VzdGlvbnMtcmVjaXBlcy1wcm9kLWZyJTIyJTJDJTIyY2F0ZWdvcnktc3VnZ2VzdGlvbnMtcHJvZC1mciUyMiUyQyUyMnJlY2lwZXMtcHJvZC1mciUyMiUyQyUyMnJlY2lwZXMtcHJvZC1mci1ieS1wdWJsaXNoZWRBdC1kZXNjJTIyJTJDJTIycmVjaXBlcy1wcm9kLWZyLWJ5LXRpdGxlLWFzYyUyMiUyQyUyMnJlY2lwZXMtcHJvZC1mci1ieS10b3RhbFRpbWUtYXNjJTIyJTJDJTIycmVjaXBlcy1wcm9kLWZyLWJ5LXByZXBhcmF0aW9uVGltZS1hc2MlMjIlMkMlMjJyZWNpcGVzLXByb2QtZnItYnktcmF0aW5nLWRlc2MlMjIlMkMlMjJyZWNpcGVzLXByb2QtZnItYnktdHJlbmQlMjIlMkMlMjJjb2xsZWN0aW9ucy1wcm9kLWZyJTIyJTJDJTIyY29sbGVjdGlvbnMtcHJvZC1mci1ieS1wdWJsaXNoZWRBdC1kZXNjJTIyJTJDJTIyY29sbGVjdGlvbnMtcHJvZC1mci1ieS10aXRsZS1hc2MlMjIlMkMlMjJlZGl0b3JpYWwtcHJvZC1mciUyMiUyQyUyMmVkaXRvcmlhbC1wcm9kLWZyLWJ5LXRpdGxlLWFzYyUyMiUyQyUyMnN1Z2dlc3Rpb25zLXJlY2lwZXMtcHJvZC1kZSUyMiUyQyUyMmNhdGVnb3J5LXN1Z2dlc3Rpb25zLXByb2QtZGUlMjIlMkMlMjJyZWNpcGVzLXByb2QtZGUlMjIlMkMlMjJyZWNpcGVzLXByb2QtZGUtYnktcHVibGlzaGVkQXQtZGVzYyUyMiUyQyUyMnJlY2lwZXMtcHJvZC1kZS1ieS10aXRsZS1hc2MlMjIlMkMlMjJyZWNpcGVzLXByb2QtZGUtYnktdG90YWxUaW1lLWFzYyUyMiUyQyUyMnJlY2lwZXMtcHJvZC1kZS1ieS1wcmVwYXJhdGlvblRpbWUtYXNjJTIyJTJDJTIycmVjaXBlcy1wcm9kLWRlLWJ5LXJhdGluZy1kZXNjJTIyJTJDJTIycmVjaXBlcy1wcm9kLWRlLWJ5LXRyZW5kJTIyJTJDJTIyY29sbGVjdGlvbnMtcHJvZC1kZSUyMiUyQyUyMmNvbGxlY3Rpb25zLXByb2QtZGUtYnktcHVibGlzaGVkQXQtZGVzYyUyMiUyQyUyMmNvbGxlY3Rpb25zLXByb2QtZGUtYnktdGl0bGUtYXNjJTIyJTJDJTIyZWRpdG9yaWFsLXByb2QtZGUlMjIlMkMlMjJlZGl0b3JpYWwtcHJvZC1kZS1ieS10aXRsZS1hc2MlMjIlMkMlMjJzdWdnZXN0aW9ucy1yZWNpcGVzLXByb2QlMjIlMkMlMjJjYXRlZ29yeS1zdWdnZXN0aW9ucy1wcm9kJTIyJTJDJTIycmVjaXBlcy1wcm9kJTIyJTJDJTIycmVjaXBlcy1wcm9kLWJ5LXB1Ymxpc2hlZEF0LWRlc2MlMjIlMkMlMjJyZWNpcGVzLXByb2QtYnktdGl0bGUtYXNjJTIyJTJDJTIycmVjaXBlcy1wcm9kLWJ5LXRvdGFsVGltZS1hc2MlMjIlMkMlMjJyZWNpcGVzLXByb2QtYnktcHJlcGFyYXRpb25UaW1lLWFzYyUyMiUyQyUyMnJlY2lwZXMtcHJvZC1ieS1yYXRpbmctZGVzYyUyMiUyQyUyMnJlY2lwZXMtcHJvZC1ieS10cmVuZCUyMiUyQyUyMmNvbGxlY3Rpb25zLXByb2QlMjIlMkMlMjJjb2xsZWN0aW9ucy1wcm9kLWJ5LXB1Ymxpc2hlZEF0LWRlc2MlMjIlMkMlMjJjb2xsZWN0aW9ucy1wcm9kLWJ5LXRpdGxlLWFzYyUyMiUyQyUyMmVkaXRvcmlhbC1wcm9kJTIyJTJDJTIyZWRpdG9yaWFsLXByb2QtYnktdGl0bGUtYXNjJTIyJTVE&x-algolia-application-id=3TA8NT85XJ"

        queryWords = urllib.parse.quote(queryWords)

        headers = CaseInsensitiveDict()
        headers["Connection"] = "keep-alive"
        headers["sec-ch-ua"] = "\" Not;A Brand\";v=\"99\", \"Google Chrome\";v=\"97\", \"Chromium\";v=\"97\""
        headers["DNT"] = "1"
        headers["sec-ch-ua-mobile"] = "?0"
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36"
        headers["sec-ch-ua-platform"] = "\"Windows\""
        headers["content-type"] = "application/x-www-form-urlencoded"
        headers["Accept"] = "*/*"
        headers["Origin"] = "https://cookidoo.de"
        headers["Sec-Fetch-Site"] = "cross-site"
        headers["Sec-Fetch-Mode"] = "cors"
        headers["Sec-Fetch-Dest"] = "empty"
        headers["Referer"] = "https://cookidoo.de/"
        headers["Accept-Language"] = "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
        data = '{"requests":[{"page":0,"query":"'+ queryWords+ '","params":"attributesToHighlight=%5B%22title%22%5D&attributesToRetrieve=%5B%22title%22%5D&highlightPreTag=%3Cspan%20class%3D%22core-autocomplete__search-phrase%22%3E&highlightPostTag=%3C%2Fspan%3E&hitsPerPage=10&filters=(country.value%3A%22de%22)%20AND%20(NOT%20additionalDevices%3Acooking_station)&ruleContexts=%5B%22lang_de-DE%22%2C%22cookidoo.de%22%2C%22web%22%2C%22market_de__lang_de-DE%22%5D&analyticsTags=%5B%22touchpoint%3Aweb%22%2C%22market%3Ade%22%2C%22ui-lang%3Ade-DE%22%5D&ignorePlurals=true&queryLanguages=%5B%22de%22%5D&page=0","enableRules":true,"indexName":"recipes-prod-de"},{"indexName":"suggestions-recipes-prod-de","page":0,"query":"gulasch","params":"attributesToHighlight=%5B%22query%22%5D&attributesToRetrieve=%5B%22query%22%5D&highlightPreTag=%3Cspan%20class%3D%22core-autocomplete__search-phrase%22%3E&highlightPostTag=%3C%2Fspan%3E&hitsPerPage=5&filters=(recipes-prod-de.facets.exact_matches.country.value.value%3A%22de%22)&ruleContexts=%5B%22lang_de-DE%22%2C%22cookidoo.de%22%2C%22web%22%2C%22market_de__lang_de-DE%22%5D&analyticsTags=%5B%22touchpoint%3Aweb%22%2C%22market%3Ade%22%2C%22ui-lang%3Ade-DE%22%5D&ignorePlurals=true&queryLanguages=%5B%22de%22%5D&page=0"},{"indexName":"category-suggestions-prod-de","page":0,"query":"gulasch","params":"filters=language%3Ade&attributesToRetrieve=%5B%22category%22%2C%22id%22%5D&ruleContexts=%5B%22lang_de-DE%22%2C%22cookidoo.de%22%2C%22web%22%2C%22market_de__lang_de-DE%22%5D&analyticsTags=%5B%22touchpoint%3Aweb%22%2C%22market%3Ade%22%2C%22ui-lang%3Ade-DE%22%5D&ignorePlurals=true&queryLanguages=%5B%22de%22%5D&page=0"}]}'

        resp = requests.post(url, headers=headers, data=data)

        if not resp.ok or resp.content is None:
            self.log(f'error running query for \'{queryWords}\'')
            return None
                
        resultJson = json.loads(resp.content)
        hits = resultJson['results'][0]['hits']

        recipeNamesAndIds = {}

        for hit in hits:
            recipeNamesAndIds[str(hit['objectID'])] = hit['title']

        return recipeNamesAndIds


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