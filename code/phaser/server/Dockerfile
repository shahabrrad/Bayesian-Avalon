FROM ubuntu:22.04

# Install Node.js, npm, and curl
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@10.9.2

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies and rebuild platform-specific packages
RUN npm install && \
    npm rebuild esbuild

# Start the application
CMD ["npm", "start"] 