FROM python:3.7-alpine
RUN echo -e http://mirrors.ustc.edu.cn/alpine/v3.7/main/ >> /etc/apk/repositories
ADD requirements.txt .

RUN apk add python3-dev build-base linux-headers pcre-dev && pip install --no-cache-dir -r requirements.txt -i http://pypi.douban.com/simple

# adding application files
ADD . /webapp

# configure path /webapp to HOME-dir
ENV HOME /webapp
WORKDIR /webapp

ENTRYPOINT ["uwsgi"]
CMD ["--http", "0.0.0.0:8080", "--wsgi-file", "wsgi.py", "--callable", "app", "--processes", "1", "--threads", "8"]