FROM ubuntu:22.04

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@10.9.2

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with all optionals and rebuild platform-specific packages
RUN npm install --include=optional && \
    npm rebuild @parcel/watcher

# Expose port
EXPOSE 1234

# Start the application with host 0.0.0.0 to allow external connections
CMD ["npm", "start", "--", "--host", "0.0.0.0"] 