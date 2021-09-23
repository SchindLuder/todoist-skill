from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

class Crawler(object):
    """description of class"""

    def download_url(self, url):
        return requests.get(url).text

    def get_ingredientStrings(self, url):
        html = self.download_url(url)
        soup = BeautifulSoup(html, 'html.parser')

        ingredientRootNode = soup.find(id="ingredients-0")

        ingredientStrings = []

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