FROM python:3.10.1-alpine3.15

LABEL maintainer="Keval Patel <kevalpatel2106@gmail.com>"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY octopus_energy_monitor.py ./

ENTRYPOINT [ "python", "./octopus_energy_monitor.py" ]
