FROM python:3.7
RUN pip install kopf
RUN pip install kubernetes
RUN pip install pyyaml
CMD kopf run /src/handlers.py --verbose
ADD templates /templates
ADD handlers.py /src/handlers.py