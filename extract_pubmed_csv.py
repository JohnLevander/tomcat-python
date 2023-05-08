#!/usr/bin/python3

from datetime import datetime, timedelta
import time
import requests
import xml.etree.ElementTree as ET
import codecs
import csv

import webbrowser
import subprocess

# sample query:
# https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=((((((((((((((((((%22coronavirus%22[MeSH%20Terms]%20OR%20coronavirus[Title/Abstract]%20OR%20COVID-19[Title/Abstract]%20OR%202019-nCoV[Title/Abstract]%20OR%20SARS-CoV-2[Title/Abstract])%20AND%20(estimat*[Title/Abstract]%20OR%20model*[Title/Abstract]%20OR%20reproduct*[Title/Abstract])%20NOT%20review[Title]%20NOT%20systematic[Title]%20NOT%20meta-analysis[Title]%20NOT%20patients[Title]))%20AND%20(%222020/04/19%22[Date%20-%20Create]%20:%20%222020/04/25%22[Date%20-%20Create]))))))))))))))))&retmax=300

# example fetch: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=32330703&retmode=XML

start_date_str = "2023-01-18" 
end_date_str = "2023-02-19"
# import into midascontacts using the following link
# https://members.midasnetwork.us/midascontacts/papers/modelingPapersManualImport/pubmed/pubmed_search_result_2021-04-25-2021-04-26.csv

now = datetime.now()
# assume we are running on Monday for previous week (sunday-saturday), so calculate start and end dates for search
#start_date_str = (now - timedelta(days=3)).strftime('%Y-%m-%d') # start date is 8 days ago
#end_date_str = (now - timedelta(days=2)).strftime('%Y-%m-%d') # end date is 2 days ago
print("Start: " + start_date_str)
print("End: " + end_date_str)


# for google sheet
# Retrieval Date	Search Engine	DOI	Title	Author List	Creation Date	Abstract
#retrieval_date = now.strftime("%Y-%m-%d")
#search_engine = "pubmed"

start_date = datetime.strptime(start_date_str,"%Y-%m-%d")
start_date_search = start_date.strftime("%Y/%m/%d")
end_date = datetime.strptime(end_date_str,"%Y-%m-%d")
end_date_search = end_date.strftime("%Y/%m/%d")

search_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
fetch_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

search_terms = "((\"coronavirus\" [MeSH Terms] OR coronavirus[Title/Abstract] OR COVID-19[Title/Abstract] OR 2019-nCoV[Title/Abstract] OR SARS-CoV-2[Title/Abstract]) AND (estimat*[Title/Abstract] OR model*[Title/Abstract] OR reproduct*[Title/Abstract]) NOT review[Title] NOT systematic[Title] NOT meta-analysis[Title] NOT patients[Title] NOT clinical[Title/Abstract]) AND (\""+ start_date_search + "\"[Date - Create] : \"" + end_date_search + "\"[Date - Create])"

search_params = {
	"db":"pubmed",
	"term": search_terms,
	"retmax": 999}

fetch_params = {
	"db":"pubmed",
	"retmode":"XML"}


r = requests.get(search_base,params=search_params)

if r.status_code == 200:
	tree = ET.fromstring(r.text)
	
	num_res = tree.find("Count")


	idlist = tree.find("IdList")
	master_id_list = []
	ids = idlist.findall("Id")
	for i in ids:
		master_id_list.append(i.text)
		#print(i.text)
	#int(num_res.text)
	num_left_to_process = int(num_res.text)
	chunksize = 100;
	current_paper = 0;
	while num_left_to_process > 0:
		my_id_list = master_id_list[current_paper:current_paper+chunksize]
		if (current_paper == 0):
			mode = "w"
		else:
			mode = "a"

		num_left_to_process = num_left_to_process - chunksize;
		current_paper = current_paper + chunksize + 1

		fetch_params["id"] = ",".join(my_id_list)
		#print(fetch_params)
		fetch_r = requests.get(fetch_base,params=fetch_params)
		print(fetch_r.url)
		if fetch_r.status_code == 200:
			# set output encoding to utf-8-sig since Excel requires BOM
			with codecs.open("pubmed_search_result_"+start_date_str + "-" + end_date_str + ".csv",mode=mode, encoding="utf-8-sig") as ouf:
				csvw = csv.writer(ouf, delimiter=",", quotechar='"')
				csvw.writerow(["journal","create_date","doi","pmid","title","authors","abstract"])

				infotree = ET.fromstring(fetch_r.text)

				articles = infotree.findall("PubmedArticle")
				for a in articles:
					medline = a.find("MedlineCitation")
					pmid = medline.find("PMID").text
					article = medline.find("Article")
					if article.find("Journal").find("ISOAbbreviation") != None:
						journal = article.find("Journal").find("ISOAbbreviation").text
						#print(journal)

					title = ""
					#title_list = []
					titleelement = article.find("ArticleTitle")
					title = "".join(titleelement.itertext())
					#title = article.find("ArticleTitle").text
					print(title)
					abs = article.find("Abstract")
					try:
						abstract = ""
						abstract_list = []
						#abstract = abs.find("AbstractText").text
						abstractelement = abs.findall("AbstractText") # sometimes multiple abstract tags for different abstract sections
						#print(abstractelement.text)
						for absel in abstractelement:
							#print(absel.text)
							abseltext ="".join(absel.itertext()) # don't cut off text if extra tags inside abstract tag
							abseltext = abseltext.replace("\n","").replace("\n "," ").replace("  "," ") # need to replace with regex sub to elimate weird spaces!
							abstract_list.append(abseltext)
						#print(abstract_list)
						abstract = " ".join(abstract_list)
					except:
						abstract = "NA"


					pubds = a.find("PubmedData")
					hist = pubds.find("History")
					pmpd = hist.findall("PubMedPubDate")
					#print(pmpd)
					pub_date_str = ""
					for p in pmpd:
						#print(p.get("PubStatus"))
						if p.get("PubStatus") == "pubmed":
							pub_y = p.find("Year").text
							pub_m = p.find("Month").text
							pub_d = p.find("Day").text
							print(pub_y, pub_m, pub_d)
							try:
								pub_date = datetime.strptime(pub_y + " " + pub_m + " " + pub_d, "%Y %b %d")
							except:
								pub_date = datetime.strptime(pub_y + " " + pub_m + " " + pub_d, "%Y %m %d")
							pub_date_str = pub_date.strftime("%Y-%m-%d")
							print(pub_date_str)
					doi = ""
					article_ids = article.findall("ELocationID")
					for ai in article_ids:
						if "doi" == ai.get("EIdType"):
							doi = ai.text
							break
					alist = article.find("AuthorList")
					if alist is not None:
						auths = alist.findall("Author")
					else:
						print(alist)

					authors = []
					for auth in auths:
						#print(auth)
						try:
							collel = auth.find("CollectiveName")
							if collel != None:
								coll = collel.text
								authors.append(coll)
							else:
								ln = auth.find("LastName").text

								fnel = auth.find("ForeName")
								if fnel != None:
									fn = auth.find("ForeName").text
									authors.append(fn + " "  + ln)
								else:
									authors.append(ln)
						except:
							ln = auth.find("LastName").text
							fn = auth.find("ForeName").text
							#mi = auth.find("Initials").text #initials is first and optional middle initials (eg. for citation)

							authors.append(fn + " "  + ln)

					author_string = ", ".join(authors)
					#print(author_string)
					if end_date_str == pub_date_str:
						csvw.writerow([journal,pub_date_str,doi,pmid,title,author_string,abstract])

print("")
print("Copying the file: ")
print("scp pubmed_search_result_"+start_date_str+"-"+end_date_str+".csv jeff.stazer@members.midasnetwork.us:~/extract")
#subprocess.run(["scp", "pubmed_search_result_"+start_date_str+"-"+end_date_str+".csv", "jeff.stazer@members.midasnetwork.us:~/extract"])
#e.g. subprocess.run(["scp", "foo.bar", "joe@srvr.net:/path/to/foo.bar"])
print("Login to: https://members.midasnetwork.us/midascontacts")
#webbrowser.open('https://members.midasnetwork.us/midascontacts', new=2)
print("After logging in visit: ")
print("https://members.midasnetwork.us/midascontacts/papers/modelingPapersManualImport/pubmed/pubmed_search_result_"+start_date_str+"-"+end_date_str+".csv")
#webbrowser.open("https://members.midasnetwork.us/midascontacts/papers/modelingPapersManualImport/pubmed/pubmed_search_result_"+start_date_str+"-"+end_date_str+".csv", new=2)

					
				
