FROM ubuntu:bionic

RUN apt-get update && apt-get install -y python3-pip bsdtar genisoimage

ADD . /tmp/code

RUN cd /tmp/code && \
    pip3 install -r requirements.txt && \
    python3 setup.py install && \
    mkdir /data

ENTRYPOINT ["isoserverd"]
