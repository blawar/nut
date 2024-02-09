FROM python:3.9

RUN apt-get update && apt-get install -y libusb-1.0-0-dev python3-pyqt5 libssl-dev libcurl4-openssl-dev

WORKDIR /app

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . ./

ARG USER=nut
ARG GROUP=nut
RUN addgroup --gid 1000 $USER && \
    adduser --uid 1000 --ingroup $GROUP --home /home/$USER --shell /bin/sh --disabled-password --gecos "" $USER && \
    curl -SsL https://github.com/boxboat/fixuid/releases/download/v0.5.1/fixuid-0.5.1-linux-amd64.tar.gz | tar -C /usr/local/bin -xzf - && \
    chown root:root /usr/local/bin/fixuid && \
    chmod 4755 /usr/local/bin/fixuid && \
    mkdir -p /etc/fixuid && \
    printf "user: $USER\ngroup: $GROUP\n" > /etc/fixuid/config.yml

USER $USER:$GROUP

ENTRYPOINT ["fixuid"]

CMD ["python", "/app/nut_gui.py"]
