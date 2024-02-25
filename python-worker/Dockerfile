# Use the official Python image as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed dependencies specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose ports for services on the container 
EXPOSE 6730 
EXPOSE 5682
EXPOSE 3000 
EXPOSE 80 

# Copy the rest of the application code into the container
COPY . .

# Run the Python script when the container launches
CMD ["python", "./worker.py"]

