# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Copy the root protos directory
COPY ../../protos /app/protos

# Generate the gRPC stubs from the proto files into a 'genproto' directory
RUN mkdir -p genproto
RUN python -m grpc_tools.protoc -I/app/protos --python_out=./genproto --grpc_python_out=./genproto /app/protos/demo.proto

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variables
# Add the app root to the PYTHONPATH to allow importing the generated stubs
ENV PORT 8080
ENV PYTHONPATH /app

# Run app.py when the container launches
# The CATALOG_READER_URL and GOOGLE_API_KEY are passed in at runtime by Kubernetes
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
