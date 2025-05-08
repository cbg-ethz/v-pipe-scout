# V-Pipe Scout: Rapid Interactive Viral Variant Detection 

![POC](https://img.shields.io/badge/status-POC-yellow)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-0.84.0-brightgreen)
![Docker](https://img.shields.io/badge/docker-19.03.12-blue)

## Overview

This front-end application is part of the "V-Pipe on Cloud" initiative, which aims to bring the capabilities of V-Pipe to the cloud, making it more accessible and scalable. The application leverages Streamlit to provide an interactive interface for users to generate heatmaps and perform variant deconvolution on-demand.

For more information about V-Pipe, visit the [V-Pipe website](https://cbg-ethz.github.io/V-pipe/).

## Deployment

The current deployment of this project can be accessed at [dev.vpipe.ethz.ch](dev.vpipe.ethz.ch).


### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/cbg-ethz/vpipe-biohack24-frontend.git
    cd vpipe-biohack24-frontend    ```


2. Configure the Wise Loculus to LAPIS APIs for clinical and wastewater data in `config.yaml` including ports:
    ```env
        server:
        lapis_address: "http://88.198.54.174:80"
        cov_sprectrum_api: "https://lapis.cov-spectrum.org"
    ```

4. Build the Docker image:
    ```sh
    docker build -t v-pipe-scout .
    ```

5. Run the Docker container:
    ```sh
    docker run -p 80:8000 v-pipe-scout
    ```


## Project Origin

This project was initiated as part of a hackathon project at the [BioHackathon Europe 2024](https://biohackathon-europe.org/).


## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
