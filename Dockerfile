FROM public.ecr.aws/docker/library/python:3.12.0-slim-bullseye
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /app

COPY requirements.docker.txt ./requirements.txt

# Install system dependencies (git, build tools if needed)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive \
   apt-get install -y --no-install-recommends \
   git \
   build-essential \
&& rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

ADD . .

# Copy tools package from site-packages to /app
RUN cp -r /usr/local/lib/python3.12/site-packages/tools /app/tools

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]