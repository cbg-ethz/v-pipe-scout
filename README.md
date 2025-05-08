# V-Pipe Scout: Rapid Interactive Viral Variant Detection 

![POC](https://img.shields.io/badge/status-POC-yellow)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.45.0-brightgreen)

## Overview

Recognizing and qualtifiying viral variants from wastwater requires expert human judgment in the final setps.
V-Pipe Scout allows for rapid exploration of wastewater viral sequences down to the single read level. 

It's aim: discovery novel viral threads a a few weeks earlier

This Proof-Of-Concept is setup for Sars-Cov-2, yet is build virus agnostic and to be expanded, to RSV and Influenza soon.

This is an effort of the V-Pipe team.
For more information about V-Pipe, visit the [V-Pipe website](https://cbg-ethz.github.io/V-pipe/).

Specifically, V-Pipe Scout enables:
- Exploration of mutations at the read level  
    - For known resistance mutations  
    - Guided by smart filters and variant signatures
- Composition of variant signatures for abundance estimates  
    - Leveraging clinical sequence databases (e.g., CovSpectrum)  
    - Using curated variant signatures

Further, we will implement:
- On-demand variant abundance estimates by [Lollipop](https://github.com/cbg-ethz/LolliPop)  

V-Pipe Scout brings toegther:
- [V-pipe](https://github.com/cbg-ethz/V-pipe) our prime Wastewater Viral Analyis Pipeline, see [publication](https://www.biorxiv.org/content/10.1101/2023.10.16.562462v1.full). 
- [GenSpectrum](https://genspectrum.org/) in particular the novel fast database for genomic sequences [LAPIS-SILO](https://github.com/GenSpectrum/LAPIS-SILO), see [publication](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-023-05364-3)


This application relies on two other repos as connecting infrastructure:
    - [WisePulse](https://github.com/cbg-ethz/WisePulse) - to pre-process and run the SILO database, powering read-level queries
    - [sr2silo](https://github.com/cbg-ethz/sr2silo) - large scale data-wrangler of nuliotide aligments, to amino-acids and SILO input format


## Deployment

The current deployment of this project can be accessed at [dev.vpipe.ethz.ch](dev.vpipe.ethz.ch).
_Only accesible within ETH Zürich Networks._


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
