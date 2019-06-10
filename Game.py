# -*- coding: utf-8 -*-
import time
from selenium import webdriver


class Game():
    def __init__(self, ht, parent=None, ):
        self.play=False
        self.menu = []
        self.browser = webdriver.Firefox()
        self.browser.set_page_load_timeout(30)
        self.browser.get(ht)
        self.elems = self.browser.find_elements_by_xpath('//*[@class="gameContent"]/ul/li/a')
        self.parse()

    def click(self, position):
        self.elems[position].click()
        time.sleep(1)
        self.elems = self.browser.find_elements_by_xpath('//*[@class="gameContent"]/ul/li/a')
        if(len(self.elems)==0):
            self.elems = self.browser.find_elements_by_xpath('//*[@class="resultBlock"]/ul/li/a')
            self.elems = [self.elems[0]]
        self.parse()

    def parse(self):
        self.text = self.browser.find_element_by_xpath('//*[@class="gameContent"]/p').text

    def getText(self):
        return self.text

    def getMenu(self):
        self.menu = []
        for item in self.elems:
            self.menu.append(item.text)
        return self.menu


