#!/usr/bin/python3

import requests
import json
import codecs
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import re


search_page = "medrxiv" 

excl_string = "[Rr]eview|[Ss]ystematic|[Mm]eta-[Aa]nalysis|[Pp]atients|[Cc]linical" # exclusion terms
search_terms = ["model","models","modeling","modeled","modelling","modelled","estimate","estimates","estimation","estimated","reproduction","reproductive"]

start_date_str = "2023-02-13"
end_date_str = "2023-02-14"

now = datetime.now()
start_date = (now - timedelta(days=2))
start_date_str = start_date.strftime('%Y-%m-%d')
end_date = (now - timedelta(days=1))
end_date_str = end_date.strftime('%Y-%m-%d')
print("Start: " + start_date_str)
print("End: " + end_date_str)


# for google sheet
# Retrieval Date	Search Engine	DOI	Title	Author List	Creation Date	Abstract
#retrieval_date = now.strftime("%Y-%m-%d")


excl_regex = re.compile(excl_string)

# read in json file to get list of COVID-related DOIs
url = "https://connect.medrxiv.org/relate/collection_json.php?grp=181"
r = requests.get(url)
rxjson = json.loads(r.text)

covid_doi = []
for r in rxjson['rels']:
	doi = r['rel_doi'].strip()
	if doi not in covid_doi:
		covid_doi.append(doi)
	
#print(covid_doi)
headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:73.0) Gecko/20100101 Firefox/73.0'}




start_date_search = (start_date - timedelta(days=1)).strftime('%Y-%m-%d') # run search starting 1 day before actual search, due to medrxiv weirdness
end_date_search = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')  # run search to 1 day after actual search, due to medrxiv weirdness


# retrieve 700 results (but need to verify there are not more pages!)
#search_url = "https://www.medrxiv.org/search/abstract_title:"+ search_string + "%20abstract_title_flags%3Amatch-any%20jcode:medrxiv%7C%7Cbiorxiv%20limit_from:" + start_date_search + "%20limit_to:"+ end_date_search + "%20numresults:700%20sort:publication-date%20direction:descending%20format_result:standard"

#bio_base = "https://www.biorxiv.org"
#med_base = "https://www.medrxiv.org"

# match-phrase
# match-any
# match-all

relevant_doi = dict()
num_doi = 0

# perform individual search for each term since medrxiv advanced search doesn't work right
for search_string in search_terms:
	res_per_query = 0

	search_url = "https://www.medrxiv.org/search/abstract_title:"+ search_string + "%20abstract_title_flags:match-any%20jcode:medrxiv%20limit_from:" + start_date_search + "%20limit_to:"+ end_date_search + "%20numresults:700%20sort:publication-date%20direction:descending%20format_result:standard"
	base = "https://www.medrxiv.org"
	end = ""

	r = requests.get(search_url, headers=headers)
	#print(r.headers)

	soup = BeautifulSoup(r.text,'html.parser')


	pubs = soup.find_all("div", {'class': 'highwire-cite'})
	
	for p in pubs:
		title = p.find("span", {'class':'highwire-cite-title'})
		#print(title)
		url = title.a['href'].strip()
		if url.find("http") != 0:
			url = base + url 
		
		d = p.find("span", {'class':'highwire-cite-metadata-doi'})
		
		res_per_query += 1
		
		doi = d.span.next_sibling[17:].strip()
		
		# check if doi in covid list
		if doi in covid_doi:
			# it's covid-related, so add to list to retrieve!
			if doi not in relevant_doi:
				relevant_doi[doi] = url
				num_doi += 1
		
	print(search_string, " results ", res_per_query)
	
# paper pages contain data in meta tags

# name = article:published_time - pub date

# name = citation_title - title
# name = citation_abstract - abstract
# name = citation_public_url - url ? do not need?
# name = citation_doi
# name = citation_author
# name = citation_author_institution
# name = citation_journal_title

#print("get paper info")


# set output encoding to utf-8-sig since Excel requires BOM
with codecs.open(search_page + "_search_result_withexcl_"+start_date_str + "-" + end_date_str + ".csv",mode="w", encoding="utf-8-sig") as ouf:
	csvw = csv.writer(ouf, delimiter=",", quotechar='"')
	csvw.writerow(["journal","pub_date","doi","title","authors","abstract","url"])
	#now get info for each paper in relevant_doi list
	retrieved_doi = 0
	for d in relevant_doi:

		try:
			r2 = requests.get(relevant_doi[d])

			if r2.status_code == 200:
				soup2 = BeautifulSoup(r2.text,'html.parser')
				
				pub_date_str = soup2.head.find("meta",{'name':'article:published_time'})['content']
				pub_date = datetime.strptime(pub_date_str,'%Y-%m-%d')
				
				if pub_date >= start_date and pub_date <= end_date:
					#print(pub_date)
				
					title = soup2.head.find("meta",{'name':'citation_title'})['content']
					#print(title)
					
					# check for exclusion criteria; only retrieve if not found
					if not re.search(excl_regex,title):
						abstract = soup2.head.find("meta",{'name':'citation_abstract'})['content']
						#print(abstract)
				
						journal = soup2.head.find("meta",{'name':'citation_journal_title'})['content']
						#print(journal)
						authors = []
						auth_list = soup2.head.find_all("meta",{'name':'citation_author'})
						for a in auth_list:
		
							authors.append(a['content'])
							#print(a['content'])
	
						if len(authors) > 0:
							author_string = ", ".join(authors)
						else:
							author_string = ""
						#print(author_string)
						
						abstract = abstract.replace("<p>","").replace("</p>","") # clean up abstract
						csvw.writerow([journal,pub_date_str,d,title,author_string,abstract,relevant_doi[d]])
						
						retrieved_doi += 1
					#else:
					#	print("EXCLUDE ", title, d, relevant_doi[d])
				
				# only do this for papers that are not v1, as v1 has no other version!
				elif r2.url != "v1":
					# else date mismatch, so check article info for a previous verion in the right date range?
					infourl = r2.url + ".article-info"
					try:
						#print(infourl)
						rinfo = requests.get(infourl,headers=headers)
						if rinfo.status_code == 200:
							#print("Infopage ")
							infosoup = BeautifulSoup(rinfo.text,'html.parser')
							# pane-highwire-versions
							v_section = infosoup.find("div", {"class": "pane-highwire-versions"})
							
							if v_section:
								#print("has version")
								versions = v_section.find_all("li")
								
								# check dates on all listed versions to see if any in our range
								for v in versions:
									
									v_timestamp = v['date'].strip()
									#print(v_timestamp)
									v_date = datetime.fromtimestamp(int(v_timestamp))
									#print(v_date)
									if v_date >= start_date and v_date <= end_date:
										# if this date is in our range, get this version
										try:
											v_url = v.a['href'].strip()
										except:
											v_url = None
											
										if v_url != None:
											if v_url.find("http") != 0:
												v_url = base + v.a['href']
											#print("Version: " + v_url)
								
											try:
												vreq = requests.get(v_url, headers=headers)
												if vreq.status_code == 200:
													vsoup = BeautifulSoup(vreq.text,'html.parser')
													#print("Version status: ", vreq.status_code)
													pub_date_str = vsoup.head.find("meta",{'name':'article:published_time'})['content']
													pub_date = datetime.strptime(pub_date_str,'%Y-%m-%d')
													#print(pub_date_str)
													if pub_date >= start_date and pub_date <= end_date:
														#print(pub_date)
				
														title = vsoup.head.find("meta",{'name':'citation_title'})['content']
														#print(title)
													
														# check for exclusion criteria in this version
														if not re.search(excl_regex,title):
															abstract = vsoup.head.find("meta",{'name':'citation_abstract'})['content']
															#print(abstract)
				
															journal = vsoup.head.find("meta",{'name':'citation_journal_title'})['content']
															#print(journal)
															authors = []
															auth_list = vsoup.head.find_all("meta",{'name':'citation_author'})
															for a in auth_list:
		
																authors.append(a['content'])
																#print(a['content'])
	
															if len(authors) > 0:
																author_string = ", ".join(authors)
															else:
																author_string = ""
															#print(author_string)
														
															abstract = abstract.replace("<p>","").replace("</p>","") # clean up abstract
															csvw.writerow([journal,pub_date_str,d,title,author_string,abstract,v_url])
														
															retrieved_doi += 1
														#else:
														#	print("EXCLUDE ", title, d, relevant_doi[d])
													#else:
													#	print("WRONG DATE:", str(d), pub_date_str, relevant_doi[d])
												#else:
												#	print(v_url)
												#	print(str(vreq.status_code))
											except:
												print("Error retrieving version url " + v_url)
												print(vreq)
							#else:
							#	print ("WRONG DATE ",  str(d), pub_date_str, relevant_doi[d])
						#else:
						#	print(relevant_doi[d], d)
						#	print(str(rinfo.status_code) + " info page")
						#	print(rinfo.headers)
					except:
						print("ERROR retrieving "  + infourl)
				#else:
				#	print ("WRONG DATE ",  str(d), pub_date_str, relevant_doi[d])
			#else:
			#	print(relevant_doi[d], d)
			#	print(str(r2.status_code) + " info page")
			#	print(r2.headers)
				
				
				
		except:
			print(d)
			print(str(r2.status_code) + " for https://doi.org/" + str(d))
			exit(1)

print("Found " + str(num_doi) + " relevant dois")
print("Retrieved " + str(retrieved_doi) + " papers")
	
