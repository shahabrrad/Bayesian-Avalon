FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    coreutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g typescript

# Install Miniconda - detect architecture and download appropriate version
RUN arch=$(uname -m) && \
    if [ "$arch" = "x86_64" ]; then \
        wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh; \
    elif [ "$arch" = "aarch64" ] || [ "$arch" = "arm64" ]; then \
        wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O miniconda.sh; \
    else \
        echo "Unsupported architecture: $arch"; \
        exit 1; \
    fi && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh

# Add conda to path
ENV PATH=/opt/conda/bin:$PATH
RUN conda init bash && \
    echo "conda activate emnlp" >> ~/.bashrc

# Configure conda
RUN conda config --set channel_priority strict \
    && conda config --add channels conda-forge \
    && conda config --set solver libmamba

WORKDIR /app

# Copy only the environment file
COPY environment.yml config.json ./
# Copy the config file

# Create conda environment
RUN conda env create -f environment.yml && \
    echo "conda activate emnlp" >> ~/.bashrc

# Set Python to run unbuffered
ENV PYTHONUNBUFFERED=1
# ENV PYTHONIOENCODING=utf-8
# ENV PYTHONFAULTHANDLER=1

# Ensure we have write permissions in /app
RUN chmod 777 /app

# Run the Python script directly in the conda environment
ENTRYPOINT ["conda", "run", "-n", "emnlp", "--no-capture-output", "python"]
CMD ["agent_manager.py"]