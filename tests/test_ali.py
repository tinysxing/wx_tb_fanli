import os

from selenium import webdriver

chromedriver = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"

os.environ["webdriver.chrome.driver"] = chromedriver

driver =  webdriver.Chrome(chromedriver)

driver.get('http://stackoverflow.com')

driver.quit()
