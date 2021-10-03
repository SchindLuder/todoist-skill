from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

class Crawler():
    """description of class"""
    def __init__(self, loggingMethod):
        self.log = loggingMethod

    def download_url(self, url):
        return requests.get(url).text

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