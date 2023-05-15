#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Description.

Class for scraping data.

Function:
- main
- cleaning_data

Classes:
- Session
- Description
"""

from selenium import webdriver
from bs4 import BeautifulSoup as BS
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from time import sleep
from pathlib import Path
import pandas as pd
import os
import csv

def main(to_search: str) -> str:
    home_link = "https://www.europages.fr/"
    current_page = 2
    end_of_pages = 0
    while True:
        nav = Session(home_link)
        sleep(5)
        try:
            nav.accept_cookies()
        except NoSuchElementException:
            print("No cookies to accept.")
        if home_link == "https://www.europages.fr/":
            nav.to_search_in_searchbar(to_search)
            sleep(6)
            nav.get_only_results_for_France()
        for _ in range(0,5):
            sleep(6)
            nav.click_on_announcements()
            sleep(5)
            nav.change_to_next_page(current_page=current_page)
            #print(f"New page: {nav.nav_chrome.current_url}")
            sleep(5)
            current_page += 1
            if current_page>25:
                end_of_pages = 1
                nav.nav_chrome.quit()
                break
        if end_of_pages==0:
            home_link = nav.nav_chrome.current_url
            nav.nav_chrome.quit()
            sleep(2)
        else:
            break
    return "Scrapping ended."

def cleaning_data(data: pd.DataFrame) -> pd.DataFrame:
    """Function to clean the database."""
    data.drop_duplicates(keep="first", inplace=True)
    data.Activite_principale = data.Activite_principale.replace("Prestatairedeservices", "Prestataire de services")
    
    value_count_name = data.Nom.value_counts()
    data_semi_duplicate = data[data.Nom.isin(value_count_name.index[value_count_name.gt(1)])]
    list_companies_semi_duplicate = set(data_semi_duplicate.Nom)
    for company in list_companies_semi_duplicate:
        data_semi_duplicate_company = data_semi_duplicate[data_semi_duplicate.Nom==company]
        data = data.drop(data_semi_duplicate_company[data_semi_duplicate_company.Telephone.isna()].index[0])
    
    return data

class Session:
    """Class to navigate the website."""

    def __init__(self, link: str):
        self.nav_chrome = webdriver.Chrome()
        self.nav_chrome.maximize_window()
        self.nav_chrome.get(link)
    
    def accept_cookies(self) -> None:
        """Accept cookies."""
        cookies_button = self.nav_chrome.find_element(By.ID, "cookiescript_accept")
        cookies_button.click()
        del cookies_button

    def to_search_in_searchbar(self, to_search: str) -> None:
        """The words to search in the searchbar."""
        try:
            searchbar = self.nav_chrome.find_element(By.ID, "input-571")
            searchbar.send_keys(to_search)
        except NoSuchElementException:
            searchbar = self.nav_chrome.find_element(By.ID, "input-570")
            searchbar.send_keys(to_search)
        sleep(5)
        searchbar.send_keys(Keys.ENTER)
    
    def get_only_results_for_France(self) -> None:
        """Get only results for France."""
        soup = BS(self.nav_chrome.page_source, "html.parser")
        for link in soup.findAll("a"):
            if "france" in link.get("href"):
                link_france = link.get("href")
                break
        sleep(5)
        base_url = self.nav_chrome.current_url.split("/")[0:3]
        self._new_url(link_france, base_url)

    def change_to_next_page(self, current_page: int) -> None:
        """Change to next page. Current page must be 2 or above."""
        soup = BS(self.nav_chrome.page_source, "html.parser")
        list_pages = soup.findAll(
            "a", {
                "class":"ep-server-side-pagination-item rounded elevation-2"
                }
            )
        for page in list_pages:
            if f"pg-{str(current_page)}/" in page.get("href"):
                base_url = self.nav_chrome.current_url.split("/")[0:3]
                self._new_url(page.get("href"), base_url)
    
    def click_on_announcements(self):
        """Click on announcement."""
        list_link_company = self._get_link_all_companies()
        sleep(2)
        base_url = self.nav_chrome.current_url.split("/")[0:3]
        for link in list_link_company:
            self._new_url(link, base_url)
            sleep(6)
            self._create_database()
            sleep(2)
            try:
                self.nav_chrome.back()
            except WebDriverException:
                pass
            sleep(5)

    def _new_url(self, end_link: str, base_url: str) -> None:
        """Create a new url."""
        link_page_final = "/".join(base_url) + end_link
        self.nav_chrome.get(link_page_final)

    def _get_link_all_companies(self) -> list:
        """Get links of all companies in the current page."""
        list_link_company = list()
        soup = BS(self.nav_chrome.page_source, "html.parser")
        for link in soup.findAll(
            "a", {
                "class":"ep-ecard-serp__epage-link"
                }
            ):
            list_link_company.append(link.get("href"))
        return list_link_company

    def _create_database(self) -> None:
        """Create a database with key informations."""
        soup = BS(self.nav_chrome.page_source, "html.parser")
        company_name = str(
            soup.find_all(name="h1", attrs={"class":"ep-epages-header-title text-h6 text-sm-h4"})[0]
            ).split("\n")[1].replace("  ", "")
        try:
            main_activity_name = str(
                soup.find_all(name="span", attrs={"class":"ep-main-activity-name ma-0"})[0]
                ).split("\n")[1].replace("  ", "").replace(" ", "")
        except IndexError:
            main_activity_name = ""
        adress_name = str(soup.find_all(name="p", attrs={"class":"ma-0"})[3]).split(">")[-2].replace("</p", "")
        city_name = str(soup.find_all(name="p", attrs={"class":"ma-0"})[5]).split(">")[-2].replace("</p", "")
        company_detail = soup.find_all(name="p", attrs={"class":"ep-text-with-overflow__text ma-0 mt-2 ep-text-with-overflow__text--ellipsis"})[0].text.replace("\n", "")
        try:
            company_link = soup.findAll(
                name="a", 
                attrs={
                    "class":"ep-epage-sidebar__website-button v-btn v-btn--block v-btn--has-bg theme--light v-size--default"
                    }
                )[0].get("href")
        except IndexError:
            company_link = ""
        facebook_link = ""
        linkedin_link = ""
        other_link = ""
        try:
            social_media_link_list = soup.findAll(name="a", attrs={"class":"ep-epages-home-links__social-link text--secondary"})
            for social_media_link in social_media_link_list:
                if "facebook" in social_media_link.get("href"):
                    facebook_link = social_media_link.get("href")
                elif "linkedin" in social_media_link.get("href"):
                    linkedin_link = social_media_link.get("href")
                else:
                    other_link = social_media_link.get("href")
        except NoSuchElementException:
            pass
        phone_number = self._get_phone_number()
        company_europage_link = self.nav_chrome.current_url
        company_observation = [
            company_name, main_activity_name, adress_name, city_name, phone_number,
            company_detail, company_link, facebook_link, linkedin_link, other_link,
            company_europage_link
            ]
        path = os.path.abspath(os.getcwd())
        final_file = Path(path + "/companies.csv")
        if final_file.is_file():
            with open(path + "/companies.csv", "a", encoding="utf8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(company_observation)
        else:
            with open(path + "/companies.csv", "a", encoding="utf8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Nom", "Activite_principale", "Adresse", "Ville", "Telephone",
                        "Detail", "Lien_entreprise", "Facebook", "Linkedin", "Autre_lien", "Lien_europage"
                    ]
                )
                writer.writerow(company_observation)

    
    def _get_phone_number(self) -> str:
        """Click to obtain the phone number of the company."""
        try:
            phone_page = self.nav_chrome.find_element(
                By.XPATH, value="//button[@class='ep-epage-sidebar__phone-button v-btn v-btn--block v-btn--has-bg theme--light v-size--default']"
                )
            phone_page.click()
            sleep(5)
            phone_page_show_number = self.nav_chrome.find_element(
                By.XPATH, value="//button[@class='ep-epage-phone-popup-number__button v-btn v-btn--block v-btn--is-elevated v-btn--has-bg theme--light v-size--default']"
                )
            phone_page_show_number.click()
            soup = BS(self.nav_chrome.page_source, "html.parser")
            phone_number = soup.find_all(name="span", attrs={"class":"ep-epage-phone-popup-number__button-text"})[0].text
            exit_phone_page = self.nav_chrome.find_element(
                By.XPATH, value="//button[@class='v-btn v-btn--icon v-btn--round theme--light v-size--default black--text']"
                )
            exit_phone_page.click()
            return phone_number
        except NoSuchElementException:
            return ""
