# Use the official Node.js 14 as a parent image
FROM node:14

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy package.json and package-lock.json (if available) into the container
COPY package*.json ./

# Install any dependencies
RUN npm install

# Bundle the application source inside the Docker image
COPY . .

# Expose port 3000 to the outside once the container has launched
EXPOSE 3000

# Define the command to run the app (use the command that starts your app)
CMD ["node", "server.js"]




















