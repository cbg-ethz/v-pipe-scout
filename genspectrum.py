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
    </body>
    </html>
    """,
        height=600,
    )

if __name__ == "__main__":
    app()