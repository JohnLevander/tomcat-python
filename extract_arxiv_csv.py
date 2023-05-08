#!/usr/bin/python3


# http://export.arxiv.org/api/query?search_query=%28all:covid+OR+all:coronavirus+OR+all:2019-ncov%29+AND+%28ti:model*+OR+abs:model*+OR+ti:estimat*+OR+abs:estimat*+OR+ti:reproduct*+OR+abs:reproduct*%29+ANDNOT+%28all:clinical+OR+all:assay+OR+all:laboratory+OR+all:vaccine+OR+all:treatment+OR+all:review+OR+all:overview+OR+all:drug*+OR+all:receptor*%29+AND+lastUpdatedDate:%5B20200412+TO+20200418%5D&sortBy=submittedDate&sortOrder=descending&max_results=1000

import requests
import atoma # to parse Atom XML returned by arxiv API
from datetime import datetime, timedelta
import csv
import codecs

start_date_str = "20210101"
end_date_str = "20210113"

now = datetime.now() # assume running Monday for previous Sun-Sat week, so set start and end date for search accordingly

#start_date_str = (now - timedelta(days=69)).strftime('%Y%m%d')
#end_date_str = (now - timedelta(days=2)).strftime('%Y%m%d')

print("Start: " + start_date_str)
print("End: " + end_date_str)
# for google sheet
# Retrieval Date	Search Engine	DOI	Title	Author List	Creation Date	Abstract
#retrieval_date = now.strftime("%Y-%m-%d")
#search_engine = "arxiv"

search_string = "(ti:covid OR ti:coronavirus OR ti:2019-ncov OR ti:SARS-CoV-2 OR abs:covid OR abs:coronavirus OR abs:2019-ncov OR abs:SARS-CoV-2) AND (ti:model* OR abs:model* OR ti:estimat* OR abs:estimat* OR ti:reproduct* OR abs:reproduct*) AND lastUpdatedDate:["+start_date_str + " TO " + end_date_str+"] ANDNOT(ti:review OR ti:systematic OR ti:meta-analysis OR ti:patients or ti:clinical)"

arxiv_api_base = "https://export.arxiv.org/api/query"

parameters = {
	'search_query' : search_string,
	'sortBy': 'submittedDate',
	'sortOrder': 'descending',
	'max_results':7000}
	
r = requests.get(arxiv_api_base,params=parameters)

feed = atoma.parse_atom_bytes(r.content)

print(feed.title)
journal = "arxiv"

# set output encoding to utf-8-sig since Excel requires BOM
with codecs.open("arxiv_search_result_"+start_date_str + "-" + end_date_str + ".csv",mode="w", encoding="utf-8-sig") as ouf:
	csvw = csv.writer(ouf, delimiter=",", quotechar='"')
	csvw.writerow(["journal","update_date","pub_date","arxiv_id","title","authors","abstract"])

	for entry in feed.entries:
		#print(entry)
		title = entry.title.value.replace("\n","").replace("$","")
		published_date = entry.published
		pub_date_str = published_date.strftime("%Y-%m-%d")
		updated_date = entry.updated
		update_date_str = updated_date.strftime("%Y-%m-%d")
	
		id = entry.id_
		abstract = entry.summary.value.replace("\n"," ")
	
		authors_list = []
		for a in entry.authors:
			authors_list.append(a.name)
		
		author_string = ", ".join(authors_list)
	
		csvw.writerow([journal, update_date_str, pub_date_str, id, title, author_string, abstract])
	