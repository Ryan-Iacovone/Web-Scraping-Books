import pandas as pd
import requests
from bs4 import BeautifulSoup
import re 
import math
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import json

# get_genre_subject function scrapes the genre and subject info about a book from the given URL

def get_genre_subject(url):
    driver = webdriver.Chrome()
    driver.get(url)

    # Click on the "Full details" button
    driver.find_element(By.XPATH, "//a[@data-key='full-details-link']").click()

    # Wait for the overlay to appear (you may need to adjust the wait time)
    driver.implicitly_wait(5)

    # Get the HTML content after the overlay is loaded
    html = driver.page_source

    # Now you can use BeautifulSoup to extract genre and subject values
    soup = BeautifulSoup(html, 'html.parser')

    # Find the genre label and ul element
    genre_label = soup.select_one('.cp-bib-field-label:-soup-contains("Genre")')

    # Creating the genre_label
    if genre_label:
        genre_ul = genre_label.find_next('ul', class_='values-list')
        # Extract the text content from each span within the li elements
        genre_values = [li.select_one('span.formatted-value').text for li in genre_ul.find_all('li')]
        # Remove dots and extra spaces from genre values
        genre_values = ', '.join([genre.replace(".", "").strip() for genre in genre_values])  
    else:
        genre_values = None

    # Similarly, extract subject values
    subject_label = soup.select_one('.cp-bib-field-label:-soup-contains("Subject")')

    # Creating the subject_label
    if subject_label:
        subject_ul = subject_label.find_next('ul', class_='values-list')
        # Extract the text content from each span within the li elements
        subject_values = [li.select_one('span.formatted-value').text for li in subject_ul.find_all('li')]
        # Remove dots and extra spaces from subject values
        subject_values = ', '.join([subject.replace(".", "").strip() for subject in subject_values])
    else:
        subject_values = None

    # Don't forget to close the Selenium WebDriver
    driver.quit()

    return genre_values, subject_values



# Takes in a KDL link to get basic information about a single book like title, description, and rating 

def book_info(url):

    html = requests.get(url)

    soup = BeautifulSoup(html.content, 'html.parser')

    # Title
    title = soup.find("h1" ,class_='cp-heading heading-modest title heading--linked') #Find_all does not have a text attribute so would need to use find
    title = title.text
    t_length = int(len(title)/2)

    # Description - need a try block here for titles that don't have descriptions listed 
    try:
        description = soup.find("div", class_="cp-bib-description").text
    except AttributeError:
        description = "No description found in Bibliocommons" 

    # Availability
    sid = soup.find(id='content')
    status = sid.find("span", class_ = "cp-screen-reader-message cp-format-chooser-sr-message")
    try:
        status = status.text.split(",")[4].replace(".", "").strip()
    except IndexError:   
        status = status.text.split(",")[3].replace(".", "").strip() 

    # Rating 
    u_rating = soup.find(class_='rating-info')
    rating = u_rating.text.split("(")[0][12:]

    # Item Type
    sid = soup.find(id='content')
    item_type = sid.find("span", class_ = "cp-screen-reader-message cp-format-chooser-sr-message")
    item_type = item_type.text.split(",")[1].strip()

    # Genre & Subject
    genre_values, subject_values = get_genre_subject(url)

    # Author
    author = soup.find("div", class_='cp-author-link')
    author = author.text
    a_length = int(len(author)/2)  

    # Book item ID (for merging datasets later)
    item_id = url.split("/")[-1]

    #print("Title: " + title[t_length:] + "\n" + "author" + author[length:] + "\n" + "Item Type: " + item_type + "\n" + "Rating: " + rating + "\n" "Status: " + status + "\n" "Description: " + description + "\n")
 
    new_data = {
    "Title": title[t_length:],
    "Author": author[a_length:],
    "Item Type": item_type,
    "Rating": rating,
    "Status": status,
    "Description": description,
    'Specific Genre': genre_values,
    'Subject': subject_values,
    'Link': url,
    'item_id': item_id
    } 

    new_data = pd.DataFrame(new_data, index=[0])
    
    return new_data



# Gathering extra info for each book from the original staff_list URL page such as Audiance, book genre, item count and number of holds
  
def extra_book_info(s):

    book_info = s.find_all('div', class_='pull-left list_item_image')

    extra_book_info = pd.DataFrame() # initalizing df 

    for div in book_info:
        # Extract data-analytics-payload attribute which has all the json code 
        data_payload = div.a['data-analytics-payload']
        
        # Parse JSON data
        payload = json.loads(data_payload)
        
        # Extract required information from the json code 
        bib_info = payload['args'][0]['bib']
        
        bib_audience = bib_info.get('bib_audience')
        bib_fiction_type = bib_info.get('bib_fiction_type')
        bib_hold_count = bib_info.get('bib_hold_count')
        bib_total_item_count = bib_info.get('bib_total_item_count')
        bib_metadata_id = bib_info.get('bib_metadata_id')

        #Temporary dictionay to store the data 
        tempdf = {
        "Audiance": bib_audience.title(),
        "Broad Genre": bib_fiction_type.title(),
        "Item Count": bib_total_item_count,
        "Holds": bib_hold_count,
        "item_id": bib_metadata_id
        } 

        tempdf = pd.DataFrame(tempdf, index=[0])

        extra_book_info = pd.concat([extra_book_info, tempdf], ignore_index=True)

    return extra_book_info



# "get_books_from_staff_list" function takes a staff list as input and returns information about all the books in that staff list (uses book_info & get_genre_subject functions)

def get_books_from_staff_list(staff_pick_url):

    html = requests.get(staff_pick_url)
    s = BeautifulSoup(html.content, 'html.parser')

    sleep_time = random.randint(1,15) # Sleep time adjustments 
    time.sleep(sleep_time)

    total_books = s.find('span', class_='item_count')  # Accounting for webpages that have multiple pages 
    if total_books is None:
        total_books = s.find('span', class_='item_count_label')

    match = re.search(r'\d+', total_books.text) # keeps any digits in the string
    if match:
        totbok = int(match.group())
        
        numpages = math.ceil(totbok/25) # Using math.ceil to round up answer to nearest whole number

    time.sleep(2) # breaking up the inital page requests - Sleep time adjustments 

    item_id_list = [] # initalizing our list to store item ids

    # Dictionary to store extra book info for each page
    extra_book_info_list = []

    for page in range(1, numpages + 1):  # odd way of writing this because range(4) would output as 0,1,2,3. So I have to set a starting point of 1 and add 1 to numpages at the end
        full_url = staff_pick_url + f"?page={page}"
        html = requests.get(full_url)

        sleep_time = random.randint(1,15) # Sleep time adjustments 
        time.sleep(sleep_time)

        s = BeautifulSoup(html.content, 'html.parser')
        book_divs = s.find_all('div', class_='list_item_title')

        extra_book_info_df = extra_book_info(s) # Gathering extra info for each book in each staff_list URL page (that's why it needs to be placed in for loop, to get all pages)
        extra_book_info_list.append(extra_book_info_df)

        for book_div in book_divs:
            link = book_div.find('a')
            
            if link:
                item_id = link['href'].split("/")[3]

                if item_id.endswith("174"):  # inadvertently filters out all non-books in list
                    item_id = int(item_id[:-3])
                    item_id_list.append(item_id)

    extra_book_info_df = pd.concat(extra_book_info_list, ignore_index=True)

    name_of_staff_list = s.find('h1', class_='list_title') #Gathers the name of the staff list to be printed out 
    name_of_staff_list = name_of_staff_list.text.strip()

    staff_list_books = pd.DataFrame(columns=["Title", "Author", "Item Type", "Rating", "Status", "Description", "Specific Genre", "Subject", "Link"], index=None) # Initialzing our data to store all output from book_info function 
    intervals = 0 
    total = 0 

    for id in item_id_list:
        url = f"https://kdl.bibliocommons.com/v2/record/S174C{id}"

        sleep_time = random.randint(1,15)  # Sleep time adjustments
        time.sleep(sleep_time)

        data = book_info(url)
        #staff_list_books = staff_list_books.append(data, ignore_index=True)

        staff_list_books = pd.concat([staff_list_books, data], ignore_index=True)

        intervals += 1
  
        print(f"Scraped item {intervals} out of {totbok} from \"{name_of_staff_list}\" Staff List \n")
    
    # merging the output from book_info function with the output from extra_book_info function
    staff_list_books = pd.merge(staff_list_books, extra_book_info_df, on='item_id')

    return staff_list_books, item_id_list, totbok, numpages



# Gathers a list of all of the staff lists from a KDL URL  

def staff_list_accumulation(list_of_staff_lists):

    html = requests.get(list_of_staff_lists)
    s = BeautifulSoup(html.content, 'html.parser')

    # Find all date elements
    date_boxes = s.find_all('div', class_='dataPair clearfix small list_created_date')

    # Find all titles, categories, and descriptions
    titles = s.find_all('span', class_='title')
    categories = s.find_all('div', class_='list_type small')
    descriptions = s.find_all('div', class_='description')

    # Create an empty DataFrame
    sl_df = pd.DataFrame(columns=['SL_Title', 'Category', 'SL_Description', 'SL_Created', 'SL_Link'])

    # Iterate through both the date elements and titles/categories/descriptions
    for date_box, title, category, description in zip(date_boxes, titles, categories, descriptions):
        # Extract the date
        date_u = date_box.find('span', class_='value')
        date = datetime.strptime(date_u.text.strip(), '%b %d, %Y') if date_u else None

        # Extract book list link 
        link = title.find('a')
        if link:
            link = (link.get('href'))
            init_url = "https://kdl.bibliocommons.com/"
            full_link = init_url + link

        # Extract title, category, and description
        title_text = title.text.strip() 
        category_text = category.text.strip() 
        description_text = description.text.strip() #if description else None

        # Append to the DataFrame
        new_row = {'SL_Title': title_text, 'Category': category_text, 'SL_Description': description_text, 'SL_Created': date, 'SL_Link': full_link}
        sl_df = pd.concat([sl_df, pd.DataFrame([new_row])], ignore_index=True)
    
    return sl_df



# Function that takes a list of core books (or really normal search results) and returns a list of book ID numbers to use book_info on 

def scrape_core_book_ids(core_url):

    html = requests.get(core_url)
    s = BeautifulSoup(html.content, 'html.parser')

    total_books = s.find('span', class_='cp-pagination-label')  # Accounting for webpages that have multiple pages 
    total_books = int(total_books.text.split(" ")[-2])
    if total_books:
        numpages = math.ceil(total_books/10)
    

    # Gathering the name of the list we're scraping
    list_name = s.find_all('span', class_='cp-pill pill--dismissible') # Gathers the name of the list to be printed out 
    name_of_book_list = list_name[1].text.split("Remove")[1]
    name_of_book_list = name_of_book_list.strip()

    # Initializing a list to store all book ids
    core_item_id_list = []

    for page in range(1, numpages + 1):  # odd way of writing this because range(4) would output as 0,1,2,3. So I have to set a starting point of 1 and add 1 to numpages at the end
        full_url = core_url + f"&page={page}"

        # Using Selenium to load the page because it gets 10 books per page instead of 5 with a normal get request idk why 

        driver = webdriver.Chrome()
        driver.get(full_url)
        driver.implicitly_wait(5) # Wait for the overlay to appear (you may need to adjust the wait time)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") # Scroll down the page

        # Get the HTML content after the overlay is loaded
        html = driver.page_source
        driver.quit() # Don't forget to close the Selenium WebDriver

        # Now using beautiful soup to parse the HTML content
        soup = BeautifulSoup(html, 'html.parser')

        sleep_time = random.randint(1,15) # Sleep time adjustments 
        time.sleep(sleep_time)
        
        # compiling all the book id numbers into a list   
        book_divs = soup.find_all('h2', class_='cp-title')

        for book_div in book_divs:
            link = book_div.find('a')
            if link:
                item_id = link['href'].split("/")[3]
                if item_id.endswith("174"):  # inadvertently filters out all non-books in list
                    item_id = int(item_id[:-3])
                    core_item_id_list.append(item_id)

    return core_item_id_list, name_of_book_list, total_books 




def extra_book_info_from_SL(staff_pick_url):

    html = requests.get(staff_pick_url)
    s = BeautifulSoup(html.content, 'html.parser')

    sleep_time = random.randint(1,15) # Sleep time adjustments 
    time.sleep(sleep_time)

    total_books = s.find('span', class_='item_count')  # Accounting for webpages that have multiple pages 
    if total_books is None:
        total_books = s.find('span', class_='item_count_label')

    match = re.search(r'\d+', total_books.text) # keeps any digits in the string
    if match:
        totbok = int(match.group())
        
        numpages = math.ceil(totbok/25) # Using math.ceil to round up answer to nearest whole number

    time.sleep(2) # breaking up the inital page requests - Sleep time adjustments 

    item_id_list = [] # initalizing our list to store item ids

    # Dictionary to store extra book info for each page
    extra_book_info_list = []

    for page in range(1, numpages + 1):  # odd way of writing this because range(4) would output as 0,1,2,3. So I have to set a starting point of 1 and add 1 to numpages at the end
        full_url = staff_pick_url + f"?page={page}"
        html = requests.get(full_url)

        sleep_time = random.randint(1,15) # Sleep time adjustments 
        time.sleep(sleep_time)

        s = BeautifulSoup(html.content, 'html.parser')
        book_divs = s.find_all('div', class_='list_item_title')

        extra_book_info_df = extra_book_info(s) # Gathering extra info for each book in each staff_list URL page (that's why it needs to be placed in for loop, to get all pages)
        extra_book_info_list.append(extra_book_info_df)

    extra_book_info_df = pd.concat(extra_book_info_list, ignore_index=True)


    return extra_book_info_df