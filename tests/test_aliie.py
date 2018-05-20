import os

from selenium import webdriver

driver =  webdriver.Ie()

driver.get('http://stackoverflow.com')

driver.quit()
