FROM tomcat:9-jdk8-temurin

COPY extract_pubmed_csv.py .
COPY extract_medrxiv_web_v2_csv.py .
COPY extract_arxiv_csv.py .

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN pip3 install requests atoma bs4
RUN apt-get install -y openssh-client openssh-server

RUN python3 extract_pubmed_csv.py
RUN python3 extract_medrxiv_web_v2_csv.py
RUN python3 extract_arxiv_csv.py
