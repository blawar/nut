FROM python:3.6.7

RUN pip3 install colorama pyopenssl requests tqdm unidecode image bs4 urllib3 flask

ADD . /var/opt/nut

ENTRYPOINT ["python", "/var/opt/nut/nut.py", "-s", "--scrape-delta", "-S"]
