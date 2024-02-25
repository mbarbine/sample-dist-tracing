# Use the official Node.js 18 as a parent image
FROM node:18.12.0

# Set the working directory in the container
WORKDIR /usr/src/app

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y build-essential python3 curl

# Copy package.json and package-lock.json (if available) into the container
COPY package*.json ./

# Clean up npm cache and rebuild
RUN npm cache clean --force

# Install project dependencies
RUN npm install

# Copy the Thrift file into the container
COPY echo.thrift /usr/src/app/echo.thrift

# Compile the Thrift file to JavaScript
RUN npm install -g thrift
#RUN thrift -r --gen js:node /usr/src/app/echo.thrift

# Bundle the application source inside the Docker image
COPY . .

# Expose ports for your app, Jaeger, and TChannel
EXPOSE 3000
EXPOSE 6831/udp
EXPOSE 5775/udp
EXPOSE 6832/udp
EXPOSE 80
EXPOSE 4040

# Define the command to run the app
CMD ["node", "server.js"]
