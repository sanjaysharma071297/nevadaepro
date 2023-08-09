
import requests
import re
from bs4 import BeautifulSoup as bs
import bs4
import xmltodict
import json

class NevadaEpro():

    def download_file(self, soup, file_type, file_name,number,headers, cookies):
        """
            Download a file using POST request based on the provided parameters.

            Args:
                soup (BeautifulSoup): The BeautifulSoup object containing the parsed HTML.
                file_type (str): The type of the file to be downloaded (e.g., 'pdf', 'csv').
                file_name (str): The desired name for the downloaded file (without extension).
                number (str): The downloadFileNbr parameter for the POST request.
                headers (dict): HTTP headers to include in the POST request.
                cookies (dict): Cookies to include in the POST request.

            Returns:
                None
        """

        name_value_pairs = {}
        inputs = soup.find_all('input', type='hidden')
        for input_tag in inputs:
            name = input_tag['name']
            value = input_tag['value']
            name_value_pairs[name] = value

        name_value_pairs['downloadFileNbr'] = number

        cookies['XSRF-TOKEN'] = name_value_pairs.get('_csrf')
        response = requests.post('https://nevadaepro.com/bso/external/bidDetail.sdo',headers=headers, cookies=cookies,data = name_value_pairs)
        if response.status_code == 200:
            with open(file_name+'.'+file_type, "wb") as file:
                file.write(response.content)
            print(f"File downloaded: {file_name}")
        else:
            print(f"Failed to download the file from URL: {url}")

    def set_session(self,url=''):

        """
            Set up a session by making an initial GET request to the specified URL.

            Args:
                url (str): The URL to make the initial GET request to.

            Returns:
                tuple: A tuple containing session token, cookies, headers, and a BeautifulSoup object.
        """

        s = requests.session()
        home_resp = s.get(url)
        soup = bs(home_resp.content,'lxml')
        token = re.search('id=\"j_id1:javax.faces.ViewState:0\"\svalue=\"(.*?)"',home_resp.content.decode()).group(1)
        cookies = s.cookies.get_dict()
        headers = s.headers

        return token, cookies, headers , soup

    def get_page_count(self , soup):
        """
            Get the total number of items and calculated page count from a BeautifulSoup object.

            Args:
                soup (BeautifulSoup): The BeautifulSoup object containing the parsed HTML.

            Returns:
                company_count , page_count
        """

        page_text = soup.find('span',class_='ui-paginator-current')
        company_count = int(page_text.text.split(' ')[-1])
        page_count = int(company_count/25)+1

        return company_count , page_count

    def pagination(self,url,company_count,page_count,token, headers, cookies):
        """
            A function for scraping paginated data from a website.

            Args:
                url (str): The URL of the web page to scrape.
                company_count (int): The total number of companies to scrape.
                page_count (int): The total number of pages to scrape.
                token (str): The token required for making requests.
                headers (dict): HTTP headers for the requests.
                cookies (dict): Cookies required for making requests.

            Returns:
                company_data (list): A list containing the extracted company data.
        """
        c = []
        for i in range(0,page_count):
            data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': 'bidSearchResultsForm:bidResultId',
                'javax.faces.partial.execute': 'bidSearchResultsForm:bidResultId',
                'javax.faces.partial.render': 'bidSearchResultsForm:bidResultId',
                'bidSearchResultsForm:bidResultId': 'bidSearchResultsForm:bidResultId',
                'bidSearchResultsForm:bidResultId_pagination': 'true',
                'bidSearchResultsForm:bidResultId_first': '0',
                'bidSearchResultsForm:bidResultId_rows': '25',
                'bidSearchResultsForm:bidResultId_encodeFeature': 'true',
                'bidSearchResultsForm': 'bidSearchResultsForm',
                'openBids': 'true',
            }

            # setting the page using page count and items available on page
            data["bidSearchResultsForm:bidResultId_first"] = i*25

            # Extracting Required Token for making Post Request
            data["_csrf"] = cookies.get('XSRF-TOKEN')
            data["javax.faces.ViewState"] = token

            # Making post request based on the page and getting Soup object
            data_soup = self.get_url_response(url, headers, cookies, data)

            # Extracting the URL and Hitting that and gathering Relavent Info from the Main Page
            c.append(self.extract_data(data_soup))

        return company_data

    def get_url_response(self, url, headers, cookies, data):

        """
                Sends a POST request to the given URL with provided headers, cookies, and data.
                Parses the response XML to extract HTML content and returns it as a BeautifulSoup object.

                Args:
                    url (str): The URL to send the POST request to.
                    headers (dict): Headers to be included in the request.
                    cookies (dict): Cookies to be included in the request.
                    data (dict): Data to be included in the request body.

                Returns:
                    BeautifulSoup: Parsed HTML content as a BeautifulSoup object, or None if an error occurs.
                """

        page_soup = None
        try:
            page_resp = requests.post(url,headers=headers, cookies=cookies,data=data)
            if page_resp.status_code == 200:
                # parsing the page_resp
                xpars = xmltodict.parse(page_resp.text)
                # Getting the HTML in Json so Reading the json object
                html_content = xpars.get('partial-response').get('changes').get('update')[0].get('#text')
                # HTML Content
                page_soup = bs(html_content,'html.parser')

        except Exception as e:
            print('Error in get_url_response')

        return page_soup

    def extract_data(self,soup):

        """
                Extracts data from HTML tables, handling file attachments, and returns structured data.

                Args:
                    soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML.

                Returns:
                    list: A list of dictionaries containing extracted data.

        """

        table = soup.findAll('a')
        urls = [i['href'] for i in table]
        company_info = []
        for i in urls:
            # Removing parentUrl=close from the URL
            bid_url = 'https://nevadaepro.com'+i.replace('&parentUrl=close','')
            try:
                response = requests.get(bid_url)
                if response.status_code ==200:
                    soup = bs(response.content,'lxml')
                    data_elements = soup.find_all('td', class_=['t-head-01', 'tableText-01'])

                    data = {}
                    current_key = None

                    for element in data_elements:
                        # Downloading the File Attachment and breaking the flow as we want data till that only
                        if ('File Attachments' or 'Form Attachments') in element.get_text():
                            current_key = element.get_text().replace('\n', '').replace(' ', ' ').replace('\t', '').strip(':').strip(' ')
                            file_links = soup.findAll('a')
                            for link in file_links:
                                file_url = link.get("href")
                                pattern = r"downloadFile\('(\d+)'\)"
                                match = re.search(pattern, file_url)
                                if match:
                                    number = match.group(1)

                                else:
                                    print("No number found in the JavaScript code.")
                                file_name = bid_url.split('docId=')[-1].split('&')[0].strip()+'_'.join(link.text.strip().split(' '))
                                if '.' in file_name:
                                    file_type = file_name.split('.')[-1]
                                else:
                                    file_type = 'pdf'
                                self.download_file(soup,file_type,file_name,number,headers, cookies)

                            break

                        if 't-head-01' in element['class']:
                            current_key = element.get_text().replace('\n','').replace(' ',' ').replace('\t','').strip(':').strip(' ')
                        elif 'tableText-01' in element['class'] and current_key:
                            data[current_key] = element.get_text().strip()

                    company_info.append(data)

            except Exception as e:
                print('Error in extract_data')

                return 'Error in extract_data'

        return company_info

if __name__ == "__main__":
    url ="https://nevadaepro.com/bso/view/search/external/advancedSearchBid.xhtml?openBids=true"
    obj =NevadaEpro()
    token, cookies, headers, soup = obj.set_session(url)
    company_count, page_count = obj.get_page_count(soup)
    company_data = obj.pagination(url,company_count,page_count,token, headers, cookies)
    print(company_data)