# V-Pipe on Cloud: Front-End for On-Demand Analysis

![WIP](https://img.shields.io/badge/status-WIP-yellow)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-0.84.0-brightgreen)
![Docker](https://img.shields.io/badge/docker-19.03.12-blue)
![AWS S3](https://img.shields.io/badge/AWS%20S3-Cloud-orange)

This project provides a front-end interface for two primary use cases:
- On-demand heatmaps of mutations to identify new variants emerging, based on V-Pipe outputs.
- On-demand variant deconvolution powered by LolliPop.
- On-demand heatmaps of resistance mutation – querying LAPIS of clincial data.
- On-demand heatmaps of reistance mutations - querying LAPS of wastewater data. 

## Overview

This front-end application is part of the "V-Pipe on Cloud" initiative, which aims to bring the capabilities of V-Pipe to the cloud, making it more accessible and scalable. The application leverages Streamlit to provide an interactive interface for users to generate heatmaps and perform variant deconvolution on-demand.

For more information about V-Pipe, visit the [V-Pipe website](https://cbg-ethz.github.io/V-pipe/).

## Tech Stack

- **Python**: The core programming language used for the project.
- **Streamlit**: Used for creating the front-end interface.
- **Docker**: Used to containerize the application, ensuring consistency across different environments.
- **AWS S3**: Used for storing and retrieving data files.

## Work in Progress

This project is a work in progress and is being actively developed. Contributions and feedback are welcome.

## Hackathon Project

This project was initiated as part of a hackathon project at the [BioHackathon Europe 2024](https://biohackathon-europe.org/).

## Related Repositories

This repository relates to the back-end at [vpipe-biohack24-backend](https://github.com/cbg-ethz/vpipe-biohack24-backend).

## Deployment

The current deployment of this project can be accessed at [biohack24.g15n.net](http://biohack24.g15n.net).

## Getting Started

### Prerequisites

- Docker
- AWS credentials with access to the required S3 buckets
### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/cbg-ethz/vpipe-biohack24-frontend.git
    cd vpipe-biohack24-frontend
    ```

2. Create a `.secrets.toml` file in the `.streamlit` directory with your AWS credentials and S3 bucket information:
    ```env
    AWS_ACCESS_KEY_ID=your_access_key_id
    AWS_SECRET_ACCESS_KEY=your_secret_access_key
    S3_BUCKET_NAME=your_s3_bucket_name
    ```

3. Configure the server IP addresses to LAPIS API for clinical and wastewater data in `config.yaml` including ports:
    ```env
    server:
        ip_address: "http://3.71.80.16:8000"
        lapis_address: "http://3.126.120.246:8080"
    ```

4. Build the Docker image:
    ```sh
    docker build -t vpipe-frontend .
    ```

5. Run the Docker container:
    ```sh
    docker run -p 8000:8000 vpipe-frontend
    ```

### Usage

1. Open your web browser and navigate to `http://localhost:8000` to access the application.

2. Follow the on-screen instructions to upload your data and generate heatmaps or perform variant deconvolution.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
