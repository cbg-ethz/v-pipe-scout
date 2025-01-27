import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

LAPIS_URL = "http://localhost:8080"


def app():
    
    ## Add a title
    st.title("V-Pipe Web Explorer")

    ## Add a header
    st.header("Explore Mutations Over Time")

    ## Add a subheader
    st.subheader("This page allows you to explore mutations over time by gene and proportion.")
    
    ## select dat range
    st.write("Select a date range:")
    date_range = st.date_input("Select a date range:", [pd.to_datetime("2024-09-30"), pd.to_datetime("2024-10-16")])

    ## Add a horizontal line
    st.markdown("---")

    start_date = date_range[0].strftime("%Y-%m-%d")
    end_date = date_range[1].strftime("%Y-%m-%d")

    components.html(
        f"""
        <html>
        <head>
        <script type="module" src="https://unpkg.com/@genspectrum/dashboard-components@latest/standalone-bundle/dashboard-components.js"></script>
        <link rel="stylesheet" href="https://unpkg.com/@genspectrum/dashboard-components@latest/dist/style.css" />
        </head>
            <body>
            <!-- Component documentation: https://genspectrum.github.io/dashboard-components/?path=/docs/visualization-mutations-over-time--docs -->
            <gs-app lapis="{LAPIS_URL}">
                <gs-mutations-over-time
                lapisFilter='{{"sampling_dateFrom":"{start_date}", "sampling_dateTo": "{end_date}"}}'
                sequenceType='amino acid'
                views='["grid"]'
                width='100%'
                height='100%'
                granularity='day'
                lapisDateField='sampling_date'
                />
            </gs-app>
            </head>
            <body>
            </body>
        </html>
    """,
        height=3000,
    )


if __name__ == "__main__":
    app()