FROM python:3

RUN apt-get update
RUN apt-get install -y --no-install-recommends

# set working directory
WORKDIR /app

# install required libraries
COPY requirements.txt .
RUN pip install -r requirements.txt


COPY . .

CMD [ "python3", "./BBot.py" ]