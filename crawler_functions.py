# library imports 
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import sys
import os 

# Phase 1 - pass in starting url to get inital list of links to start crawl 
def inital_search(url):
    links = []
    response = requests.get(url)
    if response.status_code == 200:

        soup = BeautifulSoup(response.content, 'html.parser')
        for a in soup.find_all('a'):
            trial = a.get('href')
            
            if trial is not None and trial.startswith("https"):
                links.append(a.get('href'))
    
    # converting the list into a set, which automatically removes duplicates (sets don't allow duplicates) convert back to a list:
    links = list(set(links))

    return links



# Sorts raw links into KDL links list and other list  
def sort_links(links, string):
    company_links = []
    otherlinks = []

    for link in links:
        if string in link:
            company_links.append(link)
        else:
            otherlinks.append(link)
    return company_links, otherlinks



def broaden_search(company_links, sample, string):
    #initialize new list to hold new links
    new_links = [] # use a new list in order to avoid an infinite loop although if I want a real crawler I would let it loop infinitly until no more new links were found

    #initalize counter 
    tenum = 0

    # Checking if company_links is a df or list 
    if isinstance(company_links, pd.DataFrame):
        company_links = company_links['Link'].tolist()

    # Randomly sample observations, sample is an input
    try:
        company_links_smol = random.sample(company_links, sample)
    except ValueError:
        print("Sample input larger than population or is negative.")                 

    for link in company_links_smol:
        response = requests.get(link)
        num = random.randint(0,5)
        time.sleep(num)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for a in soup.find_all('a'):
                trial = a.get('href')
                if trial is not None and trial.startswith("https") and trial not in company_links:
                    new_links.append(trial)  # Append new links to separate list
                    print(f"{trial} successfully found")
        tenum += 1
        print(f"\n{link} successfully scraped --{tenum} \n")

    # Removing duplicate links from list     
    new_links = list(set(new_links))

    # Sorting links into kdl vs others  
    company_links_new, otherlinks_new = sort_links(new_links, string)

    company_links.extend(company_links_new)
    otherlinks.extend(otherlinks_new)
    
    return company_links, otherlinks


# convert lists to dfs and save as excel files locally  
def convert_and_save(company_links, otherlinks): 
    # convert to df (checking if company_links is already a df)
    if not isinstance(company_links, pd.DataFrame):
        company_df_links = pd.DataFrame(company_links, columns= ['Link']) # does not sort values 
    else:
        company_df_links = company_links
        
    other_df_links = pd.DataFrame(otherlinks, columns= ['Link'])

    # save locally
    file_path = r"C:\Users\Ryan\Coding Projects\Web Scraping\Crawler data"

    # Get today's date as a str
    today_str = datetime.date.today().strftime("%b %d") #Gets today's date in the format of "May 6"

    #Saving the kdl_df_links df to an excel
    file_name_k = rf"company_df_links {today_str}.xlsx"
    full_path_k = os.path.join(file_path, file_name_k)
    company_df_links.to_excel(full_path_k, index=False) 

    # Saving the other_df_links df to an excel
    file_name_o = rf"other_df_links {today_str}.xlsx"
    full_path_o = os.path.join(file_path, file_name_o)
    other_df_links.to_excel(full_path_o, index=False)