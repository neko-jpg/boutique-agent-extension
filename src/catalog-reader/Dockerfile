# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install grpcio-tools for code generation
RUN pip install --no-cache-dir grpcio-tools==1.46.3

# Copy the source proto files
COPY protos/ /app/protos/

# Generate the gRPC client code from the .proto file
# This runs inside the container during the build process
RUN python -m grpc_tools.protoc \
    -I/app/protos \
    --python_out=./genproto \
    --grpc_python_out=./genproto \
    /app/protos/demo.proto

# Create an __init__.py file in the generated directory so it's a package
RUN touch ./genproto/__init__.py

# Copy the rest of the application's code into the container at /app
COPY . .

# Add the app directory to PYTHONPATH to ensure imports from genproto work smoothly
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variables (runtime config should be in k8s manifest)
ENV PORT 8080

# Run app.py when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
