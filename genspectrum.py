import streamlit as st

import streamlit.components.v1 as components


LAPIS_URL = "http://localhost:8080/"

def app():
    # bootstrap 4 collapse example
    components.html(
        """
        <html>
        <head>
        <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
        </head>
            <body>
            <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
            <gs-app lapis="https://lapis.cov-spectrum.org/open/v2">
                <gs-mutations-over-time
                lapisFilter='{"region":"Europe","country":"Switzerland","dateFrom":"2024-01-23","nextcladePangoLineage":"JN.1*"}'
                sequenceType='amino acid'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='week'
                lapisDateField='date'
                />
            </gs-app>

            </head>
            <body>
            <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
            <gs-app lapis="http://localhost:8080/2">
                <gs-mutations-over-time
                lapisFilter='{"sampling_dateFrom":"2024-08-23", "sampling_dateTo": "2024-10-23"}'
                sequenceType='amino acid'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='week'
                lapisDateField='sampling_date'
                />
            </gs-app>
            </body>
        </html>
    """,
        height=600,
    )
''' 
    components.html(
        """
        <html>
        <head>
        <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
        </head>
            <body>
            <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
            <gs-app lapis="http://localhost:8080/2">
                <gs-mutations-over-time
                lapisFilter='{"sampling_dateFrom":"2024-08-23", "sampling_dateTo": "2024-10-23",}'
                sequenceType='amino acid'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='week'
                lapisDateField='date'
                />
            </gs-app>
            </body>
        </html>
    """,
        height=600,
    )
 '''

    ## Allow for user input by Gene

    ### Let user select a Data Range

    ### Allow for user input by Proportions

    ### Allow for Choice of Nucliotides // Amino Acids

    ### Make Query for list of mutations wiht Such proportions
    ### Ensure this list is not to large to be displayed

    ### For each mutation in the list get the counts of the mutation over time

    ### Display the counts of the mutation over time



if __name__ == "__main__":
    app()